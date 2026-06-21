import pytest
from datetime import datetime, timezone
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome


def test_blocked_outcome_validation() -> None:
    # Valid reasons
    reasons = [
        "outside_time_window",
        "sampled_out",
        "media_type_filtered",
        "blocked_keyword",
        "no_allow_keyword_matched",
        "empty_after_processing",
        "unsupported_media_type",
        "step_error",
    ]
    for reason in reasons:
        outcome = BlockedOutcome(reason=reason, matched_keyword="test", details="some detail")
        assert outcome.reason == reason
        assert outcome.matched_keyword == "test"
        assert outcome.details == "some detail"

    # Invalid reason raises ValueError
    with pytest.raises(ValueError, match="Invalid block reason"):
        BlockedOutcome(reason="some_invalid_reason")


def test_pipeline_context_copy_on_write() -> None:
    rule = ForwardingRule(
        source_id="507f1f77bcf86cd799439011",
        destination_channel="dest_chan",
        is_active=True,
    )
    source = Source(
        id="507f1f77bcf86cd799439012",
        telegram_id=123456,
        telegram_username="source_chan",
        display_name="Source Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    ctx = PipelineContext(
        text="Hello World",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="abcdef12",
        rule=rule,
        source=source,
        metadata={"key": "val"},
    )

    # Ensure rule and source inside context are copies (different memory addresses)
    assert ctx.rule is not rule
    assert ctx.source is not source
    assert ctx.rule.destination_channel == "dest_chan"
    assert ctx.source.telegram_id == 123456

    # Verify mutating the original objects does not affect the context's copies
    rule.destination_channel = "new_dest"
    source.display_name = "New Display Name"

    assert ctx.rule.destination_channel == "dest_chan"
    assert ctx.source.display_name == "Source Channel"
