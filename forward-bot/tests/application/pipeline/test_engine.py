import pytest
from unittest.mock import MagicMock, AsyncMock
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.engine import PipelineEngine
from forward_bot.application.pipeline.protocol import PipelineStep


class MockStep:
    def __init__(self, name: str, should_raise: bool = False, outcome = None) -> None:
        self.name = name
        self.should_raise = should_raise
        self.outcome = outcome
        self.called = False

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        self.called = True
        if self.should_raise:
            raise RuntimeError(f"Error in {self.name}")
        if self.outcome:
            return self.outcome
        ctx.metadata[self.name] = "executed"
        return ctx


@pytest.fixture
def mock_context() -> PipelineContext:
    rule = MagicMock(spec=ForwardingRule)
    rule.id = "rule_1"
    rule.time_window = None
    rule.sampling = None
    rule.media_type_filter = ["text"]
    rule.block_keywords = []
    rule.allow_keywords = []
    source = MagicMock(spec=Source)
    source.telegram_id = 12345
    return PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="xyz12345",
        rule=rule,
        source=source,
        metadata={}
    )


@pytest.mark.asyncio
async def test_engine_sequential_execution(mock_context) -> None:
    step1 = MockStep("step1")
    step2 = MockStep("step2")
    engine = PipelineEngine(steps=[step1, step2])

    result = await engine.execute(mock_context)
    assert isinstance(result, PipelineContext)
    assert result.metadata["step1"] == "executed"
    assert result.metadata["step2"] == "executed"
    assert step1.called
    assert step2.called


@pytest.mark.asyncio
async def test_engine_early_exit_on_blocked_outcome(mock_context) -> None:
    step1 = MockStep("step1")
    blocked = BlockedOutcome(reason="sampled_out")
    step2 = MockStep("step2", outcome=blocked)
    step3 = MockStep("step3")

    engine = PipelineEngine(steps=[step1, step2, step3])
    result = await engine.execute(mock_context)

    assert isinstance(result, BlockedOutcome)
    assert result.reason == "sampled_out"
    assert step1.called
    assert step2.called
    assert not step3.called


@pytest.mark.asyncio
async def test_engine_exception_isolation(mock_context) -> None:
    step1 = MockStep("step1")
    step2 = MockStep("step2", should_raise=True)
    step3 = MockStep("step3")

    engine = PipelineEngine(steps=[step1, step2, step3])
    result = await engine.execute(mock_context)

    assert isinstance(result, BlockedOutcome)
    assert result.reason == "step_error"
    assert "RuntimeError: Error in step2" in result.details
    assert step1.called
    assert step2.called
    assert not step3.called


@pytest.mark.asyncio
async def test_engine_default_18_steps() -> None:
    # Verify that constructing without custom steps instantiates 18 canonical steps
    mock_repo = MagicMock()
    mock_sampling_repo = MagicMock()
    engine = PipelineEngine(mapping_repository=mock_repo, sampling_repository=mock_sampling_repo)
    assert len(engine.steps) == 18
    assert engine.steps[0].name == "TimeWindowStep"
    assert engine.steps[1].name == "SamplingStep"
    assert engine.steps[1].sampling_repository is mock_sampling_repo
    assert engine.steps[16].name == "DeliverStep"
    assert engine.steps[17].name == "PersistMappingStep"
    assert engine.steps[17].mapping_repository is mock_repo


@pytest.mark.asyncio
async def test_engine_default_steps_execution(mock_context) -> None:
    mock_repo = MagicMock()
    mock_repo.add_mapping = AsyncMock()

    engine = PipelineEngine(mapping_repository=mock_repo)
    mock_context.metadata["source_message_id"] = 123456

    result = await engine.execute(mock_context)
    assert isinstance(result, PipelineContext)
    # Check that DeliverStep simulated delivery
    assert result.metadata["destination_message_id"] == 99999
    assert result.metadata["destination_channel_id"] == 99999
    # Check that PersistMappingStep called mock_repo.add_mapping
    mock_repo.add_mapping.assert_called_once()


@pytest.mark.asyncio
async def test_engine_steps_6_to_16_integration() -> None:
    from datetime import datetime
    from forward_bot.domain.entities.forwarding_rule import AutoReplaceSourceRefsConfig, AttributionConfig
    from forward_bot.domain.entities.replacement_rule import ReplacementRule
    from forward_bot.infrastructure.cache.rule_cache import RuleCache, CacheHolder

    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        remove_links=True,
        remove_hashtags=True,
        remove_mentions=True,
        forward_media="caption_only",
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(
            enabled=True,
            replace_display_name=True
        ),
        attribution=AttributionConfig(
            enabled=True,
            position="suffix",
            format="From {source_name}"
        )
    )
    rule.id = "rule_1"

    source = MagicMock(spec=Source)
    source.telegram_id = 12345
    source.telegram_username = "src_user"
    source.display_name = "MySource"

    rr = ReplacementRule(
        forwarding_rule_id="rule_1",
        search_text="awesome",
        replacement_text="incredible",
        match_mode="literal",
        is_active=True,
        id="rr1",
        created_at=datetime(2026, 6, 1, 12, 0)
    )

    CacheHolder.current = RuleCache(
        replacements={"rule_1": [rr]},
        compiled_patterns={}
    )

    mock_mapping_repo = MagicMock()
    mock_mapping_repo.get_by_source_message = AsyncMock(return_value=None)
    mock_mapping_repo.add_mapping = AsyncMock()

    engine = PipelineEngine(mapping_repository=mock_mapping_repo)

    media = MagicMock()
    media.type_name = "photo"

    ctx = PipelineContext(
        text="",
        caption="Visit http://t.me/src_user. #hash @mention. This is awesome by MySource.",
        media=media,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="xyz12345",
        rule=rule,
        source=source,
        metadata={"source_message_id": 123456}
    )

    result = await engine.execute(ctx)
    assert isinstance(result, PipelineContext)
    assert "incredible" in result.text
    assert "dest_chan" in result.text
    assert "From MySource" in result.text
    assert result.media is None
    assert result.caption is None
