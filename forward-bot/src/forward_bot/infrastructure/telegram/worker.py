"""Telegram worker infrastructure for end-to-end message forwarding."""
import asyncio
import uuid
from io import BytesIO
import structlog
from telethon import events, utils
from telethon.tl.types import PeerChannel, PeerChat, PeerUser, MessageMediaPhoto, DocumentAttributeFilename
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest

from forward_bot.infrastructure.logging import logger
from forward_bot.infrastructure.cache.rule_cache import CacheHolder
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
from forward_bot.infrastructure.mongo.repositories.sampling_repository import SamplingRepository
from forward_bot.application.pipeline.engine import PipelineEngine

# How long (seconds) to wait for all album messages to arrive before flushing.
_ALBUM_COLLECT_DELAY = 1.0


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
        self._edit_handler = None
        self._delete_handler = None
        # Album (media group) buffering: keyed by grouped_id
        # Each entry: {"messages": [...], "source": source_entity, "correlation_id": str}
        self._album_buffers: dict = {}
        self._album_flush_tasks: dict = {}  # grouped_id -> asyncio.Task

    async def run(self) -> None:
        """Starts the worker, registers the event handler, and enters the lifecycle loop."""
        from forward_bot.infrastructure.telegram import telegram_client

        logger.info("telegram_worker_started", status="active")

        # Define event handlers
        async def handle_new_message(event: events.NewMessage.Event) -> None:
            await self.process_event(event)

        async def handle_message_edited(event: events.MessageEdited.Event) -> None:
            await self.process_edit_event(event)

        async def handle_message_deleted(event: events.MessageDeleted.Event) -> None:
            await self.process_delete_event(event)

        self._handler = handle_new_message
        self._edit_handler = handle_message_edited
        self._delete_handler = handle_message_deleted

        # Start subscription/reload checking task
        reload_task = asyncio.create_task(self.reload_loop())

        try:
            while True:
                # Wait until client is initialized and connected
                while not telegram_client.is_connected or telegram_client.client is None:
                    await asyncio.sleep(1.0)
                
                client = telegram_client.client
                
                # Register event handlers using add_event_handler for the current client instance
                client.add_event_handler(self._handler, events.NewMessage())
                client.add_event_handler(self._edit_handler, events.MessageEdited())
                client.add_event_handler(self._delete_handler, events.MessageDeleted())
                
                try:
                    # Await client disconnection gracefully (retains block until disconnected/cancelled)
                    await client.run_until_disconnected()
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error("telegram_worker_loop_error", error=str(e))
                finally:
                    # Cleanup handlers from the old client just in case
                    try:
                        client.remove_event_handler(self._handler, events.NewMessage())
                        client.remove_event_handler(self._edit_handler, events.MessageEdited())
                        client.remove_event_handler(self._delete_handler, events.MessageDeleted())
                    except Exception:
                        pass
                
                # Client disconnected, sleep briefly before trying to acquire the new client
                await asyncio.sleep(1.0)

        except asyncio.CancelledError:
            logger.info("telegram_worker_stopped")
            reload_task.cancel()
            await asyncio.gather(reload_task, return_exceptions=True)
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
                    input_peer = await client.get_input_entity(target)
                    # JoinChannelRequest requires InputChannel, not the generic InputPeer returned
                    # by get_input_entity(). utils.get_input_channel converts InputPeerChannel -> InputChannel.
                    channel = utils.get_input_channel(input_peer)
                except Exception as e:
                    logger.warning("worker_entity_resolution_failed", target=str(target), error=str(e))
                    return

                await client(JoinChannelRequest(channel))
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
        from forward_bot.infrastructure.telegram import telegram_client
        if not telegram_client.is_connected or not getattr(telegram_client, "_connected", True):
            logger.info("telegram_session_terminated_drop", message="Dropped incoming event because Telegram session is terminated or disconnected.")
            return

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

            # Handle album (media group): buffer and flush as a group
            grouped_id = getattr(event.message, "grouped_id", None)
            if grouped_id is not None and media is not None:
                await self._handle_album_message(
                    event, grouped_id, matching_source, matching_rules, correlation_id
                )
                return

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
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for exc in results:
                    if isinstance(exc, Exception):
                        structlog.get_logger().error(
                            "worker_task_exception",
                            error=str(exc),
                            correlation_id=correlation_id,
                        )

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

    async def _handle_album_message(
        self,
        event: events.NewMessage.Event,
        grouped_id: int,
        matching_source,
        matching_rules: list,
        correlation_id: str,
    ) -> None:
        """Buffers a single album (media group) message and schedules a group flush after a short delay."""
        key = grouped_id
        if key not in self._album_buffers:
            self._album_buffers[key] = {
                "messages": [],
                "source": matching_source,
                "rules": matching_rules,
                "correlation_id": correlation_id,
            }
        self._album_buffers[key]["messages"].append(event.message)

        # Cancel any pending flush task — we restart the timer each time a new message arrives
        if key in self._album_flush_tasks:
            self._album_flush_tasks[key].cancel()

        async def _flush_after_delay():
            await asyncio.sleep(_ALBUM_COLLECT_DELAY)
            await self._flush_album(key)

        self._album_flush_tasks[key] = asyncio.create_task(_flush_after_delay())

    async def _flush_album(
        self,
        grouped_id: int,
    ) -> None:
        """Sends all buffered album messages as a grouped media send to the destination."""
        buf = self._album_buffers.pop(grouped_id, None)
        self._album_flush_tasks.pop(grouped_id, None)
        if not buf:
            return

        messages = buf["messages"]
        matching_rules = buf["rules"]
        correlation_id = buf["correlation_id"]

        # Sort by message_id to preserve original order
        messages.sort(key=lambda m: m.id)

        from forward_bot.infrastructure.telegram import telegram_client
        client = telegram_client.client
        if not client:
            return

        album_caption = messages[0].message or ""

        # Partition rules by their forward_media setting so we only
        # download media when at least one rule actually needs it.
        ignore_rules = [r for r in matching_rules if getattr(r, "forward_media", "forward") == "ignore"]
        caption_only_rules = [r for r in matching_rules if getattr(r, "forward_media", "forward") == "caption_only"]
        forward_rules = [r for r in matching_rules if getattr(r, "forward_media", "forward") == "forward"]

        # --- caption_only: send text/caption, no media download needed ---
        for rule in caption_only_rules:
            if not album_caption:
                continue
            try:
                destination = rule.destination_channel
                try:
                    destination_entity = int(destination)
                except (ValueError, TypeError):
                    destination_entity = destination
                await client.send_message(destination_entity, message=album_caption)
                structlog.get_logger().info(
                    "album_caption_only_sent",
                    rule_id=rule.id,
                    grouped_id=grouped_id,
                    correlation_id=correlation_id,
                )
            except Exception as e:
                structlog.get_logger().error(
                    "album_caption_only_failed",
                    rule_id=rule.id,
                    grouped_id=grouped_id,
                    correlation_id=correlation_id,
                    error=str(e),
                )

        # --- ignore: nothing to do ---
        for rule in ignore_rules:
            structlog.get_logger().info(
                "album_ignored",
                rule_id=rule.id,
                grouped_id=grouped_id,
                correlation_id=correlation_id,
                message="Album skipped: rule media handling is set to ignore.",
            )

        # --- forward: try raw send first, fall back to download only if protected ---
        if not forward_rules:
            return  # No download needed at all

        # Raw media objects from the source messages — no download cost
        raw_files = [m.media for m in messages if m.media is not None]

        # After first successful send, Telegram returns Message objects whose media
        # carry the newly uploaded file_id. We reuse those for subsequent rule sends
        # to avoid re-uploading the same bytes multiple times.
        cached_sent_messages = None  # List[Message] from first successful send

        async def _download_all():
            """Download all album media to RAM (fallback for protected channels)."""
            async def _resolve_file(msg):
                media = msg.media
                if media is None:
                    return None
                try:
                    file_buf = BytesIO()
                    await client.download_media(media, file=file_buf)
                    file_buf.seek(0)
                    if isinstance(media, MessageMediaPhoto):
                        file_buf.name = "image.jpg"
                    else:
                        doc = getattr(media, "document", None)
                        if doc:
                            for attr in getattr(doc, "attributes", []):
                                if isinstance(attr, DocumentAttributeFilename):
                                    file_buf.name = attr.file_name
                                    break
                            else:
                                file_buf.name = "file"
                        else:
                            file_buf.name = "file"
                    return file_buf
                except Exception as dl_err:
                    logger.warning(
                        "album_media_download_failed",
                        message_id=msg.id,
                        correlation_id=correlation_id,
                        error=str(dl_err),
                        message="Skipping album photo: failed to download media."
                    )
                    return None

            results = await asyncio.gather(*[_resolve_file(m) for m in messages])
            return [f for f in results if f is not None]

        # files_to_send holds either raw media objects or BytesIO buffers
        files_to_send = raw_files
        downloaded = False  # Track whether we've already paid the download cost

        from telethon.errors import ChatForwardsRestrictedError

        for rule in forward_rules:
            destination = rule.destination_channel
            try:
                destination_entity = int(destination)
            except (ValueError, TypeError):
                destination_entity = destination

            try:
                # Optimization 2: reuse file_ids from first successful upload
                if cached_sent_messages is not None:
                    file_arg = [m.media for m in cached_sent_messages if m.media is not None]
                else:
                    # Rewind BytesIO buffers if we've already downloaded
                    if downloaded and files_to_send and isinstance(files_to_send[0], BytesIO):
                        for f in files_to_send:
                            f.seek(0)
                    file_arg = files_to_send

                sent = await client.send_file(
                    destination_entity,
                    file=file_arg,
                    caption=album_caption,
                )

                # Capture before updating so the flag reflects whether cache was *used* for this send
                was_cached = cached_sent_messages is not None

                # Cache the sent messages for reuse (Optimization 2)
                if cached_sent_messages is None:
                    cached_sent_messages = sent if isinstance(sent, list) else [sent]

                dest_ids = [m.id for m in sent] if isinstance(sent, list) else [sent.id]
                structlog.get_logger().info(
                    "album_forward_succeeded",
                    rule_id=rule.id,
                    grouped_id=grouped_id,
                    source_message_ids=[m.id for m in messages],
                    destination_message_ids=dest_ids,
                    correlation_id=correlation_id,
                    used_cache=was_cached,
                )

            except Exception as e:
                is_protected = isinstance(e, ChatForwardsRestrictedError) or (
                    hasattr(e, "__class__") and "ChatForwardsRestricted" in e.__class__.__name__
                ) or ("protected chat" in str(e).lower())

                # Optimization 1: only download on protected chat error, not upfront
                if is_protected and not downloaded:
                    logger.warning(
                        "album_protected_chat_fallback",
                        grouped_id=grouped_id,
                        correlation_id=correlation_id,
                        message="Source is protected. Downloading album media for re-upload.",
                    )
                    files_to_send = await _download_all()
                    downloaded = True
                    if not files_to_send:
                        logger.error(
                            "album_flush_no_files",
                            grouped_id=grouped_id,
                            correlation_id=correlation_id,
                            message="Album flush: no downloadable media found after protected chat fallback.",
                        )
                        return
                    # Retry this same rule with downloaded bytes
                    try:
                        sent = await client.send_file(
                            destination_entity,
                            file=files_to_send,
                            caption=album_caption,
                        )
                        if cached_sent_messages is None:
                            cached_sent_messages = sent if isinstance(sent, list) else [sent]
                        dest_ids = [m.id for m in sent] if isinstance(sent, list) else [sent.id]
                        structlog.get_logger().info(
                            "album_forward_succeeded",
                            rule_id=rule.id,
                            grouped_id=grouped_id,
                            source_message_ids=[m.id for m in messages],
                            destination_message_ids=dest_ids,
                            correlation_id=correlation_id,
                            used_cache=False,
                        )
                    except Exception as retry_err:
                        structlog.get_logger().error(
                            "album_forward_failed",
                            rule_id=rule.id,
                            grouped_id=grouped_id,
                            correlation_id=correlation_id,
                            error=str(retry_err),
                            message="Failed to forward album after protected chat download fallback.",
                        )
                else:
                    structlog.get_logger().error(
                        "album_forward_failed",
                        rule_id=rule.id,
                        grouped_id=grouped_id,
                        correlation_id=correlation_id,
                        error=str(e),
                        message="Failed to forward album to destination.",
                    )


    async def process_edit_event(self, event: events.MessageEdited.Event) -> None:
        """Processes an incoming message edit event and propagates it to all mapped destinations."""
        from forward_bot.infrastructure.telegram import telegram_client
        if not telegram_client.is_connected or not getattr(telegram_client, "_connected", True):
            logger.info("telegram_session_terminated_drop", message="Dropped edit event because Telegram session is terminated or disconnected.")
            return

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
            tasks.append(
                asyncio.create_task(
                    self.propagate_edit_for_mapping(mapping, event, correlation_id)
                )
            )
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for exc in results:
                if isinstance(exc, Exception):
                    structlog.get_logger().error(
                        "worker_edit_task_exception",
                        error=str(exc),
                        correlation_id=correlation_id,
                    )

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
        from forward_bot.infrastructure.telegram import telegram_client
        if not telegram_client.is_connected or not getattr(telegram_client, "_connected", True):
            logger.info("telegram_session_terminated_drop", message="Dropped delete event because Telegram session is terminated or disconnected.")
            return

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
            tasks.append(
                asyncio.create_task(
                    self.propagate_delete_for_channel(dest_channel_id, channel_mappings, correlation_id)
                )
            )
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for exc in results:
                if isinstance(exc, Exception):
                    structlog.get_logger().error(
                        "worker_delete_task_exception",
                        error=str(exc),
                        correlation_id=correlation_id,
                    )

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
