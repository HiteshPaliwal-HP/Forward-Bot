"""Unit tests for TimeWindowStep."""
import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from unittest.mock import MagicMock
from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.domain.entities.forwarding_rule import ForwardingRule, TimeWindowConfig
from forward_bot.domain.entities.source import Source
from forward_bot.application.pipeline.steps.time_window import TimeWindowStep


def make_context(time_window: TimeWindowConfig | None, msg_date: datetime | None) -> PipelineContext:
    rule = ForwardingRule(
        source_id="65c52c6f1f2e3d4a5b6c7d81",
        destination_channel="dest_chan",
        time_window=time_window
    )
    source = MagicMock(spec=Source)
    source.telegram_id = 123
    source.display_name = "Src"
    metadata = {}
    if msg_date:
        metadata["date"] = msg_date
    return PipelineContext(
        text="Hello",
        caption=None,
        media=None,
        attribution_decided=False,
        reply_target_destination_id=None,
        correlation_id="corr-123",
        rule=rule,
        source=source,
        metadata=metadata
    )


@pytest.mark.asyncio
async def test_time_window_step_no_config() -> None:
    step = TimeWindowStep()
    ctx = make_context(None, datetime.now(timezone.utc))
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_inside_regular_window() -> None:
    step = TimeWindowStep()
    # Mon, June 15, 2026 12:00:00 UTC. Timezone UTC. Start 09:00, End 17:00, Days MON, WED.
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON", "WED"],
        start_time="09:00",
        end_time="17:00"
    )
    dt = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_outside_regular_window_time() -> None:
    step = TimeWindowStep()
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON", "WED"],
        start_time="09:00",
        end_time="17:00"
    )
    dt = datetime(2026, 6, 15, 18, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "outside_time_window"


@pytest.mark.asyncio
async def test_time_window_step_outside_regular_window_day() -> None:
    step = TimeWindowStep()
    # Tue, June 16, 2026 is TUE (not MON or WED)
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON", "WED"],
        start_time="09:00",
        end_time="17:00"
    )
    dt = datetime(2026, 6, 16, 12, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "outside_time_window"


@pytest.mark.asyncio
async def test_time_window_step_cross_midnight_inside_leading() -> None:
    step = TimeWindowStep()
    # Mon, June 15, 2026 23:00:00 UTC. Timezone UTC. Start 22:00, End 04:00. Days MON.
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON"],
        start_time="22:00",
        end_time="04:00"
    )
    dt = datetime(2026, 6, 15, 23, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_cross_midnight_inside_trailing() -> None:
    step = TimeWindowStep()
    # Tue, June 16, 2026 02:00:00 UTC. Timezone UTC. Start 22:00, End 04:00. Days MON.
    # Note: 02:00 is Tuesday local, but window started on Mon, so active day is Mon, which is in days_of_week.
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON"],
        start_time="22:00",
        end_time="04:00"
    )
    dt = datetime(2026, 6, 16, 2, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_cross_midnight_outside_trailing_day() -> None:
    step = TimeWindowStep()
    # Wed, June 17, 2026 02:00:00 UTC. Timezone UTC. Start 22:00, End 04:00. Days MON.
    # This falls in the trailing window of a Tuesday start. Active day is TUE. MON is active day of week, so it should be blocked.
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON"],
        start_time="22:00",
        end_time="04:00"
    )
    dt = datetime(2026, 6, 17, 2, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, BlockedOutcome)
    assert res.reason == "outside_time_window"


@pytest.mark.asyncio
async def test_time_window_step_timezone_conversion() -> None:
    step = TimeWindowStep()
    # Message at Mon, June 15, 2026 12:00:00 UTC.
    # Target timezone: UTC+5:30 (Asia/Kolkata). Local time: 17:30.
    # Start: 17:00, End: 19:00.
    cfg = TimeWindowConfig(
        timezone="Asia/Kolkata",
        days_of_week=["MON"],
        start_time="17:00",
        end_time="19:00"
    )
    dt = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_fail_open_invalid_timezone() -> None:
    step = TimeWindowStep()
    cfg = TimeWindowConfig(
        timezone="Invalid/Timezone",
        days_of_week=["MON"],
        start_time="09:00",
        end_time="17:00"
    )
    dt = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    # Fail open -> return ctx
    assert isinstance(res, PipelineContext)


@pytest.mark.asyncio
async def test_time_window_step_fail_open_malformed_config() -> None:
    step = TimeWindowStep()
    cfg = TimeWindowConfig(
        timezone="UTC",
        days_of_week=["MON"],
        start_time="invalid-time",
        end_time="17:00"
    )
    dt = datetime(2026, 6, 15, 12, 0, tzinfo=timezone.utc)
    ctx = make_context(cfg, dt)
    res = await step.apply(ctx)
    assert isinstance(res, PipelineContext)
