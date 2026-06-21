"""PersistMapping pipeline step implementation."""
from datetime import datetime, timezone
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.message_mapping import MessageMapping


class PersistMappingStep:
    name: str = "PersistMappingStep"

    def __init__(self, mapping_repository) -> None:
        self.mapping_repository = mapping_repository

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        # Check that we have the required fields in metadata
        source_message_id = ctx.metadata.get("source_message_id")
        destination_message_id = ctx.metadata.get("destination_message_id")
        destination_channel_id = ctx.metadata.get("destination_channel_id")

        if source_message_id is None:
            return BlockedOutcome(
                reason="step_error",
                details="Missing source_message_id in metadata"
            )
        if destination_message_id is None:
            return BlockedOutcome(
                reason="step_error",
                details="Missing destination_message_id in metadata"
            )
        if destination_channel_id is None:
            return BlockedOutcome(
                reason="step_error",
                details="Missing destination_channel_id in metadata"
            )

        # Build MessageMapping entity
        mapping = MessageMapping(
            forwarding_rule_id=ctx.rule.id,
            source_channel_id=ctx.source.telegram_id,
            source_message_id=int(source_message_id),
            destination_channel_id=int(destination_channel_id),
            destination_message_id=int(destination_message_id),
            forwarded_at=datetime.now(timezone.utc),
        )

        # Persist using mapping repository
        await self.mapping_repository.add_mapping(mapping)

        # Store the persisted mapping ID back in metadata
        ctx.metadata["message_mapping_id"] = mapping.id

        return ctx
