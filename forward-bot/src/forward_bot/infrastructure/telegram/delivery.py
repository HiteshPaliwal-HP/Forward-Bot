"""Telegram delivery implementation with reliability and retries."""
import asyncio
from io import BytesIO
from pathlib import Path
from typing import Tuple, Any, List

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError, MessageNotModifiedError, ChatForwardsRestrictedError
from telethon.tl.types import MessageMediaPhoto

from forward_bot.config import Settings
from forward_bot.domain.entities.pipeline_context import PipelineContext
from forward_bot.infrastructure.logging import logger


async def deliver_message(
    client: TelegramClient,
    ctx: PipelineContext,
    settings: Settings
) -> Tuple[int, int]:
    """Deliver a message to the target channel with transient error retries and FloodWait handling.

    Returns:
        A tuple of (destination_message_id, destination_channel_id).
    """
    if client is None:
        raise ValueError("Telegram client is not initialized")

    destination = ctx.rule.destination_channel
    try:
        destination_entity = int(destination)
    except (ValueError, TypeError):
        destination_entity = destination

    attempt = 0
    while True:
        try:
            # Prepare arguments
            file_arg = str(ctx.media) if isinstance(ctx.media, Path) else ctx.media

            if ctx.media is not None:
                msg = await asyncio.shield(
                    client.send_message(
                        destination_entity,
                        message=ctx.caption,
                        file=file_arg,
                        reply_to=ctx.reply_target_destination_id
                    )
                )
            else:
                msg = await asyncio.shield(
                    client.send_message(
                        destination_entity,
                        message=ctx.text,
                        reply_to=ctx.reply_target_destination_id
                    )
                )

            # Ensure we got a valid response message
            if not msg:
                raise RuntimeError("Empty response message from Telegram client")

            destination_message_id = msg.id
            destination_channel_id = msg.chat_id

            return destination_message_id, destination_channel_id

        except FloodWaitError as e:
            logger.warning(
                "flood_wait",
                wait_seconds=e.seconds,
                rule_id=str(ctx.rule.id),
                correlation_id=ctx.correlation_id,
                message=f"Telegram flood wait triggered. Must wait {e.seconds} seconds."
            )
            if e.seconds > 300:
                logger.error(
                    "forward_failed",
                    rule_id=str(ctx.rule.id),
                    correlation_id=ctx.correlation_id,
                    error=f"FloodWait too long: {e.seconds}s (max 300s)",
                    message="Flood wait duration exceeds threshold. Aborting delivery."
                )
                raise e
            await asyncio.sleep(e.seconds)
            # FloodWait retry does NOT count against the transient error retry budget.
            continue

        except (ChatForwardsRestrictedError, RPCError) as e:
            # Handle Telegram "Protect Content" restriction: download media locally then re-upload.
            is_protected_chat_error = isinstance(e, ChatForwardsRestrictedError) or (
                isinstance(e, RPCError) and "protected chat" in str(e).lower()
            )
            if is_protected_chat_error and ctx.media is not None and not isinstance(ctx.media, (Path, bytes, BytesIO)):
                logger.warning(
                    "protected_chat_download_fallback",
                    rule_id=str(ctx.rule.id),
                    correlation_id=ctx.correlation_id,
                    message="Source chat has Protect Content enabled. Downloading media and re-uploading."
                )
                try:
                    buf = BytesIO()
                    await client.download_media(ctx.media, file=buf)
                    buf.seek(0)
                    # Preserve original media type: photos must have an image extension
                    # so Telethon uploads them as photos rather than documents.
                    if isinstance(ctx.media, MessageMediaPhoto):
                        buf.name = "image.jpg"
                    else:
                        # Try to derive filename from document attributes if present
                        doc = getattr(ctx.media, "document", None)
                        if doc:
                            from telethon.tl.types import DocumentAttributeFilename
                            for attr in getattr(doc, "attributes", []):
                                if isinstance(attr, DocumentAttributeFilename):
                                    buf.name = attr.file_name
                                    break
                            else:
                                buf.name = "file"
                        else:
                            buf.name = "file"
                    # Replace ctx.media with the named buffer so subsequent attempts use re-upload
                    ctx.media = buf
                    continue  # Retry immediately with downloaded bytes — does not count as an error attempt
                except Exception as dl_err:
                    logger.error(
                        "protected_chat_download_failed",
                        rule_id=str(ctx.rule.id),
                        correlation_id=ctx.correlation_id,
                        error=str(dl_err),
                        message="Failed to download media from protected chat. Skipping message."
                    )
                    raise e

            if isinstance(e, RPCError) and "REPLY_MESSAGE_ID_INVALID" in str(e) and ctx.reply_target_destination_id is not None:
                logger.warning(
                    "reply_target_missing",
                    rule_id=str(ctx.rule.id),
                    correlation_id=ctx.correlation_id,
                    message="Reply target message has been deleted on destination. Sending standalone."
                )
                ctx.reply_target_destination_id = None
                continue

            attempt += 1
            if attempt > settings.delivery_max_retries:
                logger.error(
                    "forward_failed",
                    rule_id=str(ctx.rule.id),
                    correlation_id=ctx.correlation_id,
                    error=str(e),
                    message=f"Forwarding failed after {attempt - 1} retries due to transient error."
                )
                raise e

            delay = settings.delivery_base_delay * (settings.delivery_backoff_factor ** (attempt - 1))
            logger.warning(
                "delivery_transient_error",
                attempt=attempt,
                rule_id=str(ctx.rule.id),
                correlation_id=ctx.correlation_id,
                error=str(e),
                backoff_delay=delay,
                message=f"Transient Telegram error encountered. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)

        except (ConnectionError, asyncio.TimeoutError) as e:
            attempt += 1
            if attempt > settings.delivery_max_retries:
                logger.error(
                    "forward_failed",
                    rule_id=str(ctx.rule.id),
                    correlation_id=ctx.correlation_id,
                    error=str(e),
                    message=f"Forwarding failed after {attempt - 1} retries due to transient error."
                )
                raise e

            delay = settings.delivery_base_delay * (settings.delivery_backoff_factor ** (attempt - 1))
            logger.warning(
                "delivery_transient_error",
                attempt=attempt,
                rule_id=str(ctx.rule.id),
                correlation_id=ctx.correlation_id,
                error=str(e),
                backoff_delay=delay,
                message=f"Transient Telegram error encountered. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)


async def propagate_edit(
    client: TelegramClient,
    destination_channel_id: int,
    destination_message_id: int,
    text: str,
    caption: str | None,
    media: Any | None,
    rule_id: str,
    correlation_id: str,
    settings: Settings
) -> None:
    """Propagates a message edit to a specific destination message with transient error retries."""
    if client is None:
        raise ValueError("Telegram client is not initialized")

    # Determine updated content
    message_text = caption if media is not None else text

    attempt = 0
    flood_wait_retries = 0
    while True:
        try:
            await asyncio.wait_for(
                asyncio.shield(
                    client.edit_message(
                        entity=destination_channel_id,
                        message=destination_message_id,
                        text=message_text
                    )
                ),
                timeout=5.0
            )
            return
        except MessageNotModifiedError:
            # Caught and treated as a success (no-op)
            logger.info(
                "edit_propagation_ignored",
                rule_id=rule_id,
                correlation_id=correlation_id,
                message="Message not modified on Telegram, ignoring"
            )
            return
        except FloodWaitError as e:
            logger.warning(
                "flood_wait",
                wait_seconds=e.seconds,
                rule_id=rule_id,
                correlation_id=correlation_id,
                message=f"Telegram flood wait triggered during edit propagation. Must wait {e.seconds} seconds."
            )
            if e.seconds > 300:
                logger.error(
                    "edit_propagation_failed",
                    rule_id=rule_id,
                    correlation_id=correlation_id,
                    error=f"FloodWait too long: {e.seconds}s (max 300s)",
                    message="Flood wait duration exceeds threshold. Aborting edit propagation."
                )
                raise e
            flood_wait_retries += 1
            if flood_wait_retries > 3:
                logger.error(
                    "edit_propagation_failed",
                    rule_id=rule_id,
                    correlation_id=correlation_id,
                    error="Max FloodWait retries exceeded",
                    message="Exceeded max flood wait retries. Aborting edit propagation."
                )
                raise e
            await asyncio.sleep(e.seconds)
            continue
        except (ConnectionError, asyncio.TimeoutError, RPCError) as e:
            attempt += 1
            if attempt > settings.delivery_max_retries:
                logger.error(
                    "edit_propagation_failed",
                    rule_id=rule_id,
                    correlation_id=correlation_id,
                    error=str(e),
                    message=f"Edit propagation failed after {attempt - 1} retries due to transient error."
                )
                raise e
            delay = settings.delivery_base_delay * (settings.delivery_backoff_factor ** (attempt - 1))
            logger.warning(
                "edit_propagation_transient_error",
                attempt=attempt,
                rule_id=rule_id,
                correlation_id=correlation_id,
                error=str(e),
                backoff_delay=delay,
                message=f"Transient Telegram error during edit propagation. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)


async def propagate_delete(
    client: TelegramClient,
    destination_channel_id: int,
    destination_message_ids: List[int],
    settings: Settings,
    rule_ids: List[str],
    correlation_id: str
) -> None:
    """Propagates message deletions to a specific destination channel in a batch with retry handling."""
    if client is None:
        raise ValueError("Telegram client is not initialized")
    if not destination_message_ids:
        return

    attempt = 0
    flood_wait_retries = 0
    while True:
        try:
            for i in range(0, len(destination_message_ids), 100):
                chunk = destination_message_ids[i:i + 100]
                await asyncio.wait_for(
                    asyncio.shield(
                        client.delete_messages(
                            entity=destination_channel_id,
                            message_ids=chunk
                        )
                    ),
                    timeout=5.0
                )
            return
        except FloodWaitError as e:
            logger.warning(
                "flood_wait",
                wait_seconds=e.seconds,
                rule_ids=rule_ids,
                correlation_id=correlation_id,
                message=f"Telegram flood wait triggered during delete propagation. Must wait {e.seconds} seconds."
            )
            if e.seconds > 300:
                logger.error(
                    "delete_propagation_failed",
                    rule_ids=rule_ids,
                    correlation_id=correlation_id,
                    error=f"FloodWait too long: {e.seconds}s (max 300s)",
                    message="Flood wait duration exceeds threshold. Aborting delete propagation."
                )
                raise e
            flood_wait_retries += 1
            if flood_wait_retries > 3:
                logger.error(
                    "delete_propagation_failed",
                    rule_ids=rule_ids,
                    correlation_id=correlation_id,
                    error="Max FloodWait retries exceeded",
                    message="Exceeded max flood wait retries. Aborting delete propagation."
                )
                raise e
            await asyncio.sleep(e.seconds)
            continue
        except (ConnectionError, asyncio.TimeoutError, RPCError) as e:
            attempt += 1
            if attempt > settings.delivery_max_retries:
                logger.error(
                    "delete_propagation_failed",
                    rule_ids=rule_ids,
                    correlation_id=correlation_id,
                    error=str(e),
                    message=f"Delete propagation failed after {attempt - 1} retries due to transient error."
                )
                raise e
            delay = settings.delivery_base_delay * (settings.delivery_backoff_factor ** (attempt - 1))
            logger.warning(
                "delete_propagation_transient_error",
                attempt=attempt,
                rule_ids=rule_ids,
                correlation_id=correlation_id,
                error=str(e),
                backoff_delay=delay,
                message=f"Transient Telegram error during delete propagation. Retrying in {delay}s..."
            )
            await asyncio.sleep(delay)

