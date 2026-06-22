"""Reply message mapping lookup step of the forwarding pipeline."""
from typing import Optional
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository
from forward_bot.infrastructure.logging import logger


class ReplyLookupStep:
    """Checks if the source message is a reply and looks up parent mapping (FR-31a)."""
    name: str = "ReplyLookupStep"

    def __init__(self, mapping_repository: Optional[MappingRepository] = None) -> None:
        self.mapping_repository = mapping_repository

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        reply_to_msg_id = ctx.metadata.get("reply_to_msg_id")
        if reply_to_msg_id is None:
            return ctx

        if self.mapping_repository is None:
            logger.warning(
                "reply_lookup_failed",
                reason="mapping_repository_not_configured",
                correlation_id=ctx.correlation_id,
            )
            ctx.reply_target_destination_id = None
            return ctx

        try:
            parent_mapping = await self.mapping_repository.get_by_source_message(
                source_channel_id=ctx.source.telegram_id,
                source_message_id=reply_to_msg_id,
                forwarding_rule_id=ctx.rule.id,
            )
            if parent_mapping:
                ctx.reply_target_destination_id = parent_mapping.destination_message_id
            else:
                logger.warning(
                    "reply_parent_not_found",
                    source_channel_id=ctx.source.telegram_id,
                    source_message_id=reply_to_msg_id,
                    forwarding_rule_id=ctx.rule.id,
                    correlation_id=ctx.correlation_id,
                )
                ctx.reply_target_destination_id = None
        except Exception:
            # Propagate catastrophic exceptions to be caught by the engine
            raise

        return ctx
