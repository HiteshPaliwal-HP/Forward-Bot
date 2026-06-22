"""Deliver pipeline step implementation."""
import traceback
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.config import get_settings
from forward_bot.infrastructure.telegram import telegram_client
from forward_bot.infrastructure.telegram.delivery import deliver_message


class DeliverStep:
    name: str = "DeliverStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        settings = get_settings()
        try:
            msg_id, chat_id = await deliver_message(
                telegram_client.client,
                ctx,
                settings
            )
            ctx.metadata["destination_message_id"] = msg_id
            ctx.metadata["destination_channel_id"] = chat_id
            return ctx
        except Exception as e:
            return BlockedOutcome(
                reason="step_error",
                details=str(e)
            )
