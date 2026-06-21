"""Pipeline engine orchestrator."""
import traceback
from typing import List, Optional

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.application.pipeline.protocol import PipelineStep
from forward_bot.application.pipeline.steps import (
    TimeWindowStep,
    SamplingStep,
    MediaTypeFilterStep,
    BlockKeywordStep,
    AllowKeywordStep,
    MediaDecisionStep,
    ReplyLookupStep,
    SourceRefReplaceStep,
    TextReplacementStep,
    LinkRemovalStep,
    HashtagRemovalStep,
    MentionRemovalStep,
    MediaReplacementStep,
    WhitespaceStep,
    AttributionStep,
    EmptyCheckStep,
    DeliverStep,
    PersistMappingStep,
)
from forward_bot.infrastructure.logging import logger


class PipelineEngine:
    """Orchestrates the execution of pipeline steps on a pipeline context."""

    def __init__(
        self,
        mapping_repository=None,
        sampling_repository=None,
        steps: Optional[List[PipelineStep]] = None,
    ) -> None:
        if steps is not None:
            self.steps = steps
        else:
            # Instantiate the 18 canonical steps in exact sequence
            # PersistMappingStep needs the mapping_repository.
            if mapping_repository is None:
                raise ValueError("mapping_repository is required if steps are not explicitly provided")

            self.steps = [
                TimeWindowStep(),
                SamplingStep(sampling_repository),
                MediaTypeFilterStep(),
                BlockKeywordStep(),
                AllowKeywordStep(),
                MediaDecisionStep(),
                ReplyLookupStep(),
                SourceRefReplaceStep(),
                TextReplacementStep(),
                LinkRemovalStep(),
                HashtagRemovalStep(),
                MentionRemovalStep(),
                MediaReplacementStep(),
                WhitespaceStep(),
                AttributionStep(),
                EmptyCheckStep(),
                DeliverStep(),
                PersistMappingStep(mapping_repository),
            ]

    async def execute(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        """Executes the pipeline steps in sequence.

        Wraps step execution in a try/except block for engine-level exception isolation.
        """
        current_ctx = ctx
        for step in self.steps:
            try:
                result = await step.apply(current_ctx)
                if isinstance(result, BlockedOutcome):
                    return result
                current_ctx = result
            except Exception as e:
                traceback_str = traceback.format_exc()
                logger.error(
                    "pipeline_step_error",
                    step=step.name,
                    correlation_id=current_ctx.correlation_id,
                    error=str(e),
                    traceback=traceback_str,
                )
                return BlockedOutcome(
                    reason="step_error",
                    details=traceback_str,
                )
        return current_ctx
