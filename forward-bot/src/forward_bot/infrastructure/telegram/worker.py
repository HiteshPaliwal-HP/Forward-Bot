"""Telegram worker infrastructure for end-to-end message forwarding."""
import asyncio
import contextvars
import uuid
import structlog
from telethon import events
from telethon.tl.types import PeerChannel, PeerChat, PeerUser
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
from forward_bot.infrastructure.mongo.repositories.sampling_repository import SamplingRepository
from forward_bot.application.pipeline.engine import PipelineEngine


class TelegramWorker:
    """Monitors active Telegram sources, reloads configurations, and dispatches pipelines."""

    def __init__(self, settings, db) -> None:
        self.settings = settings
        self.db = db
        self.mapping_repo = MappingRepository(db)
        self.sampling_repo = SamplingRepository(db)
        self.pipeline_engine = PipelineEngine(
            mapping_repository=self.mapping_repo,
            sampling_repository=self.sampling_repo,
        )
        self.joined_sources = set()  # Tracks telegram_ids (int) of joined sources
        self.sampling_counters = {}  # In-memory counters {rule_id: counter} for sampling
        self._sampling_lock = asyncio.Lock()  # Guards concurrent read-modify-write on sampling_counters
        self._handler = None

    async def run(self) -> None:
        """Starts the worker, registers the event handler, and enters the lifecycle loop."""
        from forward_bot.infrastructure.telegram import telegram_client

        if not telegram_client.is_connected or telegram_client.client is None:
            logger.error("telegram_worker_failed", error="Telegram client not connected")
            return

        client = telegram_client.client
        logger.info("telegram_worker_started", status="active")

        # Define event handler inside to access self context easily
        @client.on(events.NewMessage)
        async def handle_new_message(event: events.NewMessage.Event) -> None:
            await self.process_event(event)

        @client.on(events.MessageEdited)
        async def handle_message_edited(event: events.MessageEdited.Event) -> None:
            await self.process_edit_event(event)

        @client.on(events.MessageDeleted)
        async def handle_message_deleted(event: events.MessageDeleted.Event) -> None:
            await self.process_delete_event(event)

        self._handler = handle_new_message
        self._edit_handler = handle_message_edited
        self._delete_handler = handle_message_deleted

        # Start subscription/reload checking task
        reload_task = asyncio.create_task(self.reload_loop())

        try:
            # Await client disconnection gracefully (retains block until cancelled)
            await client.run_until_disconnected()
        except asyncio.CancelledError:
            logger.info("telegram_worker_stopped")
            reload_task.cancel()
            await asyncio.gather(reload_task, return_exceptions=True)
            # Unregister event handlers if client is still alive
            if telegram_client.client:
                telegram_client.client.remove_event_handler(self._handler, events.NewMessage)
                telegram_client.client.remove_event_handler(self._edit_handler, events.MessageEdited)
                telegram_client.client.remove_event_handler(self._delete_handler, events.MessageDeleted)
            raise

    async def reload_loop(self) -> None:
        """Periodic loop to join newly active channels/groups."""
        interval = self.settings.hot_reload_interval
        while True:
            try:
                cache = CacheHolder.current
                active_source_ids = {rule.source_id for rule in cache.rules if rule.is_active}
                
                current_telegram_ids = set()

                for source_id in active_source_ids:
                    if source_id not in cache.sources:
                        continue
                    source = cache.sources[source_id]
                    current_telegram_ids.add(source.telegram_id)

                    if source.telegram_id not in self.joined_sources:
                        self.joined_sources.add(source.telegram_id)
                        await self.join_source(source)
                
                # Prune removed sources
                self.joined_sources.intersection_update(current_telegram_ids)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("telegram_worker_reload_error", error=str(e))

            await asyncio.sleep(interval)

    async def join_source(self, source) -> None:
        """Resolves source entity and issues join request to Telegram."""
        from forward_bot.infrastructure.telegram import telegram_client
        client = telegram_client.client
        if not client:
            return

        try:
            target = source.telegram_username if source.telegram_username else source.telegram_id

            # Parse invite link format if present in target string
            is_invite = False
            invite_hash = None
            if isinstance(target, str):
                if "joinchat/" in target:
                    invite_hash = target.split("joinchat/")[-1].split("?")[0].strip("/")
                    is_invite = True
                elif target.startswith("+"):
                    invite_hash = target[1:].split("?")[0].strip("/")
                    is_invite = True

            if is_invite and invite_hash:
                await client(ImportChatInviteRequest(hash=invite_hash))
                logger.info(
                    "worker_joined_via_invite",
                    source_id=source.id,
                    hash=invite_hash,
                    message="Successfully joined private source via invite link"
                )
            else:
                # Resolve the entity first to ensure we handle channel/group IDs properly
                try:
                    entity = await client.get_entity(target)
                except Exception as e:
                    logger.warning("worker_entity_resolution_failed", target=str(target), error=str(e))
                    return

                await client(JoinChannelRequest(entity))
                logger.info(
                    "worker_joined_channel",
                    source_id=source.id,
                    target=str(target),
                    message="Successfully joined public channel/group source"
                )
        except Exception as e:
            logger.warning(
                "worker_join_source_failed",
                source_id=source.id,
                telegram_id=source.telegram_id,
                error=str(e),
                message=f"Failed to join source: {e}"
            )

    async def process_event(self, event: events.NewMessage.Event) -> None:
        """Processes an incoming message event through the pipeline engine for matching rules."""
        if not event.message:
            return

        correlation_id = uuid.uuid4().hex[:8]

        # Extract Telegram ID from message peer_id
        event_tg_id = None
        peer = event.message.peer_id
        if peer:
            if isinstance(peer, PeerChannel):
                event_tg_id = peer.channel_id
            elif isinstance(peer, PeerChat):
                event_tg_id = peer.chat_id
            elif isinstance(peer, PeerUser):
                event_tg_id = peer.user_id

        # Fallback if peer_id parsing did not yield anything
        if event_tg_id is None and event.chat_id is not None:
            chat_id_str = str(event.chat_id)
            try:
                if chat_id_str.startswith("-100"):
                    event_tg_id = int(chat_id_str[4:])
                elif chat_id_str.startswith("-"):
                    event_tg_id = int(chat_id_str[1:])
                else:
                    event_tg_id = int(chat_id_str)
            except ValueError:
                event_tg_id = None

        # Extract username
        event_username = None
        chat = getattr(event, "chat", None)
        if chat:
            username = getattr(chat, "username", None)
            if username:
                event_username = username.lstrip("@").strip().lower()

        # Capture RuleCache snapshot once for this dispatch
        cache = CacheHolder.current

        # Match against cached sources
        matching_source = None
        for source in cache.sources.values():
            if event_tg_id is not None and source.telegram_id == event_tg_id:
                matching_source = source
                break
            if event_username is not None and source.telegram_username:
                if source.telegram_username.lower() == event_username:
                    matching_source = source
                    break

        if not matching_source:
            return

        # Find active rules referencing this source
        matching_rules = [
            rule for rule in cache.rules
            if rule.source_id == matching_source.id and rule.is_active
        ]

        if not matching_rules:
            return

        # Bind logging context variables
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            source_id=matching_source.id,
            message_id=event.message.id,
        )

        try:
            # Parse text/caption/media according to Telethon convention
            media = event.message.media
            if media is not None:
                text = ""
                caption = event.message.message or ""
            else:
                text = event.message.message or ""
                caption = None

            # Get reply msg ID if present
            reply_to_msg_id = None
            if event.message.reply_to:
                reply_to_msg_id = event.message.reply_to.reply_to_msg_id

            async def run_pipeline_for_rule(rule_item) -> PipelineContext | BlockedOutcome:
                # Use a fresh metadata dictionary per rule run to avoid contamination
                metadata = {
                    "source_message_id": event.message.id,
                    "reply_to_msg_id": reply_to_msg_id,
                    "sampling_counters": self.sampling_counters,  # passed by reference
                    "sampling_lock": self._sampling_lock,  # asyncio.Lock guards concurrent counter mutations
                }
                pipeline_context = PipelineContext(
                    text=text,
                    caption=caption,
                    media=media,
                    attribution_decided=False,
                    reply_target_destination_id=None,
                    correlation_id=correlation_id,
                    rule=rule_item,
                    source=matching_source,
                    metadata=metadata,
                )
                return await self.pipeline_engine.execute(pipeline_context)

            # Process matching rules
            async def _execute_and_log(rule_item):
                result = await run_pipeline_for_rule(rule_item)
                if isinstance(result, BlockedOutcome):
                    structlog.get_logger().info(
                        "pipeline_blocked",
                        reason=result.reason,
                        rule_id=rule_item.id,
                        correlation_id=correlation_id,
                    )
                elif isinstance(result, PipelineContext):
                    dest_msg_id = result.metadata.get("destination_message_id")
                    structlog.get_logger().info(
                        "forward_succeeded",
                        rule_id=rule_item.id,
                        source_message_id=event.message.id,
                        destination_message_id=dest_msg_id,
                        correlation_id=correlation_id,
                    )

            tasks = [asyncio.create_task(_execute_and_log(rule)) for rule in matching_rules]
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            structlog.get_logger().error(
                "worker_dispatch_failed",
                error=str(e),
                correlation_id=correlation_id,
            )
        finally:
            structlog.contextvars.clear_contextvars()

    async def process_edit_event(self, event: events.MessageEdited.Event) -> None:
        """Processes an incoming message edit event and propagates it to all mapped destinations."""
        if not event.message:
            return

        # Extract source channel ID
        event_tg_id = None
        peer = event.message.peer_id
        if peer:
            if isinstance(peer, PeerChannel):
                event_tg_id = peer.channel_id
            elif isinstance(peer, PeerChat):
                event_tg_id = peer.chat_id
            elif isinstance(peer, PeerUser):
                event_tg_id = peer.user_id

        if event_tg_id is None and event.chat_id is not None:
            event_tg_id = event.chat_id

        if event_tg_id is None:
            return

        # Find mappings for this source channel and source message ID
        mappings = await self.mapping_repo.get_by_source(
            source_channel_id=event_tg_id,
            source_message_id=event.message.id
        )
        if not mappings:
            # Silently ignore if no mappings exist
            return

        correlation_id = uuid.uuid4().hex[:8]

        # For each mapping, run propagation using contextvars copy_context to isolate correlation_id
        tasks = []
        for mapping in mappings:
            ctx = contextvars.copy_context()
            tasks.append(
                asyncio.create_task(
                    ctx.run(self.propagate_edit_for_mapping, mapping, event, correlation_id)
                )
            )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def propagate_edit_for_mapping(
        self,
        mapping: MessageMapping,
        event: events.MessageEdited.Event,
        correlation_id: str
    ) -> None:
        """Propagates edit to a single mapped destination in isolated contextvars context."""
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
            source_id=mapping.source_channel_id,
            message_id=mapping.source_message_id,
        )
        try:
            from forward_bot.infrastructure.telegram.delivery import propagate_edit
            from forward_bot.infrastructure.telegram import telegram_client

            # Parse text/caption/media according to Telethon convention
            media = event.message.media
            if media is not None:
                text = ""
                caption = event.message.message or ""
            else:
                text = event.message.message or ""
                caption = None

            await propagate_edit(
                client=telegram_client.client,
                destination_channel_id=mapping.destination_channel_id,
                destination_message_id=mapping.destination_message_id,
                text=text,
                caption=caption,
                media=media,
                rule_id=mapping.forwarding_rule_id,
                correlation_id=correlation_id,
                settings=self.settings
            )

            # Log edit_propagated at INFO
            structlog.get_logger().info(
                "edit_propagated",
                rule_id=mapping.forwarding_rule_id,
                source_message_id=mapping.source_message_id,
                destination_message_id=mapping.destination_message_id,
                correlation_id=correlation_id,
            )
        except Exception as e:
            # Permanent failures log warning and do not crash the worker
            structlog.get_logger().warning(
                "edit_propagation_failed",
                rule_id=mapping.forwarding_rule_id,
                source_message_id=mapping.source_message_id,
                destination_message_id=mapping.destination_message_id,
                correlation_id=correlation_id,
                error=str(e),
                message="Edit propagation failed"
            )
        finally:
            structlog.contextvars.clear_contextvars()

    async def process_delete_event(self, event: events.MessageDeleted.Event) -> None:
        """Processes an incoming message deletion event and propagates it to all mapped destinations."""
        # Extract source channel ID
        event_tg_id = None
        if event.chat_id is not None:
            event_tg_id = event.chat_id

        if event_tg_id is None or not event.deleted_ids:
            return

        # Find mappings for this source channel and list of deleted source message IDs
        mappings = await self.mapping_repo.get_by_source_messages(
            source_channel_id=event_tg_id,
            source_message_ids=event.deleted_ids
        )
        if not mappings:
            # Silently ignore if no mappings exist
            return

        correlation_id = uuid.uuid4().hex[:8]

        # Group mappings by destination channel to batch deletes
        from collections import defaultdict
        grouped_mappings = defaultdict(list)
        for m in mappings:
            grouped_mappings[m.destination_channel_id].append(m)

        # For each destination channel, dispatch the batched deletion
        tasks = []
        for dest_channel_id, channel_mappings in grouped_mappings.items():
            ctx = contextvars.copy_context()
            tasks.append(
                asyncio.create_task(
                    ctx.run(self.propagate_delete_for_channel, dest_channel_id, channel_mappings, correlation_id)
                )
            )
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def propagate_delete_for_channel(
        self,
        dest_channel_id: int,
        channel_mappings: list[MessageMapping],
        correlation_id: str
    ) -> None:
        """Propagates deletions to a single destination channel in a batch."""
        structlog.contextvars.bind_contextvars(
            correlation_id=correlation_id,
        )
        try:
            from forward_bot.infrastructure.telegram.delivery import propagate_delete
            from forward_bot.infrastructure.telegram import telegram_client

            dest_message_ids = [m.destination_message_id for m in channel_mappings]
            rule_ids = list({m.forwarding_rule_id for m in channel_mappings})

            await propagate_delete(
                client=telegram_client.client,
                destination_channel_id=dest_channel_id,
                destination_message_ids=dest_message_ids,
                settings=self.settings,
                rule_ids=rule_ids,
                correlation_id=correlation_id
            )

            # Log delete_propagated at INFO for each mapping successfully deleted
            for m in channel_mappings:
                structlog.get_logger().info(
                    "delete_propagated",
                    rule_id=m.forwarding_rule_id,
                    source_message_id=m.source_message_id,
                    destination_message_id=m.destination_message_id,
                    correlation_id=correlation_id,
                )
        except Exception as e:
            # Permanent failures log warning and do not crash the worker
            structlog.get_logger().warning(
                "delete_propagation_failed",
                correlation_id=correlation_id,
                error=str(e),
                message=f"Delete propagation failed for destination channel {dest_channel_id}"
            )
        finally:
            structlog.contextvars.clear_contextvars()
