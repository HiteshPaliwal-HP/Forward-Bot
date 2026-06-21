"""Deliver pipeline step stub."""
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class DeliverStep:
    name: str = "DeliverStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        ctx.metadata["destination_message_id"] = 99999
        ctx.metadata["destination_channel_id"] = 99999
        return ctx
