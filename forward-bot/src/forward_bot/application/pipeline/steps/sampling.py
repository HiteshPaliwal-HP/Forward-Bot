"""Sampling filter step."""
from forward_bot.config import Settings
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


class SamplingStep:
    name: str = "SamplingStep"

    def __init__(self, sampling_repository=None) -> None:
        self.sampling_repository = sampling_repository
        self._fallback_counters = {}

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.sampling or rule.sampling.n <= 1:
            return ctx

        # Check if sampling persistence is enabled
        try:
            settings = Settings()
            persist = settings.sampling_persist
        except Exception:
            persist = False

        if persist and self.sampling_repository is not None:
            counter = await self.sampling_repository.increment_counter(rule.id)
        else:
            # InMemory counters
            counters = ctx.metadata.get("sampling_counters") if isinstance(ctx.metadata, dict) else None
            if counters is None or not isinstance(counters, dict):
                counters = self._fallback_counters
            
            current_val = counters.get(rule.id, 0)
            new_val = current_val + 1
            counters[rule.id] = new_val
            counter = new_val

        if counter % rule.sampling.n != 0:
            return BlockedOutcome(reason="sampled_out")

        return ctx
