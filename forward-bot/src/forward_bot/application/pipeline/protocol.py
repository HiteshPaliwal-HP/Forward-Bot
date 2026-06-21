"""Pipeline step protocol definition."""
from typing import Protocol

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class PipelineStep(Protocol):
    """Protocol for steps executing within the message forwarding pipeline."""
    name: str

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        """Apply the processing step to the given context.

        Returns either the modified/unmodified PipelineContext or a BlockedOutcome.
        """
        ...
