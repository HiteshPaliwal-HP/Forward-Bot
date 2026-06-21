"""Unit tests for SamplingStep."""
import pytest
from unittest.mock import MagicMock, AsyncMock

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, SamplingConfig
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.sampling import SamplingStep


def make_context(sampling: SamplingConfig, metadata: dict | None = None) -> PipelineContext:
    rule = ForwardingRule(
        id="rule_1",
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        sampling=sampling
    )
    source = MagicMock(spec=Source)
    source.telegram_id = 123
    source.display_name = "Src"
    return PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata=metadata if metadata is not None else {}
    )


@pytest.mark.asyncio
async def test_sampling_step_no_sampling_n_1() -> None:
    # n=1 should pass everything through
    step = SamplingStep()
    ctx = make_context(SamplingConfig(n=1))
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_sampling_step_in_memory_counters(monkeypatch) -> None:
    # Force settings.sampling_persist to False
    monkeypatch.setenv("SAMPLING_PERSIST", "false")

    step = SamplingStep()
    cfg = SamplingConfig(n=3)

    # 1st message: counter = 1 -> Blocked
    ctx1 = make_context(cfg, metadata={"sampling_counters": {}})
    res1 = await step.apply(ctx1)
    assert isinstance(res1, BlockedOutcome)
    assert res1.reason == "sampled_out"
    assert ctx1.metadata["sampling_counters"]["rule_1"] == 1

    # 2nd message: counter = 2 -> Blocked
    # Pass same metadata to simulate sequential calls
    ctx2 = make_context(cfg, metadata=ctx1.metadata)
    res2 = await step.apply(ctx2)
    assert isinstance(res2, BlockedOutcome)
    assert res2.reason == "sampled_out"
    assert ctx2.metadata["sampling_counters"]["rule_1"] == 2

    # 3rd message: counter = 3 -> Passes
    ctx3 = make_context(cfg, metadata=ctx2.metadata)
    res3 = await step.apply(ctx3)
    assert isinstance(res3, PipelineContext)
    assert ctx3.metadata["sampling_counters"]["rule_1"] == 3


@pytest.mark.asyncio
async def test_sampling_step_fallback_dict(monkeypatch) -> None:
    # Force settings.sampling_persist to False
    monkeypatch.setenv("SAMPLING_PERSIST", "false")

    step = SamplingStep()
    cfg = SamplingConfig(n=2)

    # Context with no metadata or missing sampling_counters dict
    ctx1 = PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=ForwardingRule(id="rule_1", source_id="src_id", destination_channel="dest", sampling=cfg),
        source=MagicMock(spec=Source),
        metadata={}  # empty, lacks "sampling_counters"
    )

    res1 = await step.apply(ctx1)
    assert isinstance(res1, BlockedOutcome)
    
    # Check that fallback dictionary recorded the count on the step instance
    assert step._fallback_counters["rule_1"] == 1


@pytest.mark.asyncio
async def test_sampling_step_persisted_counters(monkeypatch) -> None:
    # Force settings.sampling_persist to True
    monkeypatch.setenv("SAMPLING_PERSIST", "true")

    mock_repo = AsyncMock()
    step = SamplingStep(sampling_repository=mock_repo)
    cfg = SamplingConfig(n=2)

    # 1st call: DB returns 1 -> Blocked
    mock_repo.increment_counter.return_value = 1
    ctx1 = make_context(cfg)
    res1 = await step.apply(ctx1)
    assert isinstance(res1, BlockedOutcome)
    assert res1.reason == "sampled_out"
    mock_repo.increment_counter.assert_called_with("rule_1")

    # 2nd call: DB returns 2 -> Passes
    mock_repo.increment_counter.reset_mock()
    mock_repo.increment_counter.return_value = 2
    ctx2 = make_context(cfg)
    res2 = await step.apply(ctx2)
    assert isinstance(res2, PipelineContext)
    mock_repo.increment_counter.assert_called_with("rule_1")
