"""Time Window filter step."""
from datetime import datetime, timezone, time, timedelta
from zoneinfo import ZoneInfo

from forward_bot.domain.entities.pipeline_context import PipelineContext, BlockedOutcome
from forward_bot.infrastructure.logging import logger


class TimeWindowStep:
    name: str = "TimeWindowStep"

    async def apply(self, ctx: PipelineContext) -> PipelineContext | BlockedOutcome:
        rule = ctx.rule
        if not rule.time_window:
            return ctx

        try:
            # Extract date
            dt = ctx.metadata.get("date")
            if not isinstance(dt, datetime):
                dt = datetime.now(timezone.utc)
            elif dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            # Resolve timezone
            tz = ZoneInfo(rule.time_window.timezone)
            local_dt = dt.astimezone(tz)
            local_t = local_dt.time()

            # Parse start and end times
            sh, sm = map(int, rule.time_window.start_time.split(":"))
            eh, em = map(int, rule.time_window.end_time.split(":"))
            start_t = time(hour=sh, minute=sm)
            end_t = time(hour=eh, minute=em)

            in_window = False
            active_day_dt = local_dt

            if end_t < start_t:
                # Cross-midnight window
                if local_t >= start_t or local_t <= end_t:
                    in_window = True
                    if local_t <= end_t:
                        active_day_dt = local_dt - timedelta(days=1)
            else:
                # Regular window
                if start_t <= local_t <= end_t:
                    in_window = True

            if not in_window:
                return BlockedOutcome(reason="outside_time_window")

            # Check days of week
            active_day_str = active_day_dt.strftime("%a").upper()
            if active_day_str not in rule.time_window.days_of_week:
                return BlockedOutcome(reason="outside_time_window")

            return ctx

        except Exception as e:
            logger.warning(
                "time_window_eval_error",
                rule_id=rule.id,
                error=str(e),
                message="Error evaluating time window filter. Failing open.",
            )
            return ctx
