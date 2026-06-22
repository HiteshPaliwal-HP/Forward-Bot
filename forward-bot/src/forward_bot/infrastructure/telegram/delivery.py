"""Telegram delivery implementation with reliability and retries."""
import asyncio
from pathlib import Path
from typing import Tuple

from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError

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

        except (ConnectionError, asyncio.TimeoutError, RPCError) as e:
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
