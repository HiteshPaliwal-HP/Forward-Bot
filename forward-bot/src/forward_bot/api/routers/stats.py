"""FastAPI router for application usage statistics."""
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.infrastructure.logging import get_recent_logs

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


class StatsSummaryResponse(BaseModel):
    forwarded_24h: int
    failed_24h: int
    blocked_24h: int


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp with Z or timezone suffix to offset-aware datetime in UTC."""
    clean_str = ts_str.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"
    
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


@router.get(
    "/summary",
    response_model=StatsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get application forwarding summary statistics over the last 24 hours."
)
async def stats_summary(_: str = Depends(get_current_operator)) -> StatsSummaryResponse:
    """Returns forwarding counters (forwarded, failed, blocked) from logs in the ring buffer.

    Calculated over the last 24-hour window.
    """
    now = datetime.now(timezone.utc)
    limit_24h = now - timedelta(hours=24)

    forwarded_24h = 0
    failed_24h = 0
    blocked_24h = 0

    logs = get_recent_logs()
    for log in logs:
        log_ts_str = log.get("timestamp")
        if not log_ts_str:
            continue
        try:
            log_dt = parse_iso_timestamp(log_ts_str)
        except Exception:
            continue

        if log_dt >= limit_24h:
            event = log.get("event", "")
            level = log.get("level", "")
            
            if event == "forward_succeeded":
                forwarded_24h += 1
            elif event == "pipeline_blocked":
                blocked_24h += 1

            # Determine failures
            if level in ("error", "critical") or "failed" in event or "error" in event:
                failed_24h += 1

    return StatsSummaryResponse(
        forwarded_24h=forwarded_24h,
        failed_24h=failed_24h,
        blocked_24h=blocked_24h
    )
