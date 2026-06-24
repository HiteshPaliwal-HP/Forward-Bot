"""FastAPI router for streaming logs and historical logs query."""
import json
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.infrastructure.logging import (
    get_recent_logs,
    register_subscriber,
    unregister_subscriber,
)

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


class LogsListResponse(BaseModel):
    items: list[dict[str, Any]]


def parse_iso_timestamp(ts_str: str) -> datetime:
    """Parse ISO timestamp with Z or timezone suffix to offset-aware datetime in UTC."""
    clean_str = ts_str.strip()
    if clean_str.endswith("Z"):
        clean_str = clean_str[:-1] + "+00:00"
    
    dt = datetime.fromisoformat(clean_str)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def safe_json_dumps(obj: Any) -> str:
    """Safely dump logs as JSON string with fallback."""
    try:
        return json.dumps(obj)
    except TypeError:
        # Fallback to string representation for non-serializable objects
        return json.dumps(obj, default=str)


@router.get(
    "/stream",
    status_code=status.HTTP_200_OK,
    summary="Stream live log events via SSE."
)
async def stream_logs(
    event: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    _: str = Depends(get_current_operator),
) -> StreamingResponse:
    """Streams live JSON logs using Server-Sent Events (SSE).

    Replays all current ring buffer entries to the client first.
    Subsequent logs are streamed in real time.
    """
    event_filter = event
    correlation_id_filter = correlation_id

    async def event_generator():
        # Create queue and register as subscriber
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        register_subscriber(queue)
        try:
            # 1. Replay historical logs from the ring buffer
            historical = get_recent_logs()
            historical_ids = {id(log) for log in historical}
            
            for log in historical:
                if event_filter and log.get("event") != event_filter:
                    continue
                if correlation_id_filter and log.get("correlation_id") != correlation_id_filter:
                    continue
                yield f"data: {safe_json_dumps(log)}\n\n"

            # 2. Stream new logs
            while True:
                log = await queue.get()
                if id(log) in historical_ids:
                    continue  # Skip duplicate from historical overlap
                    
                if event_filter and log.get("event") != event_filter:
                    continue
                if correlation_id_filter and log.get("correlation_id") != correlation_id_filter:
                    continue
                yield f"data: {safe_json_dumps(log)}\n\n"
        except asyncio.CancelledError:
            # Client disconnected
            pass
        finally:
            unregister_subscriber(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.get(
    "/recent",
    response_model=LogsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recent logs from in-memory ring buffer."
)
async def recent_logs(
    limit: int = Query(default=50, ge=1, le=500),
    event: Optional[str] = Query(None),
    correlation_id: Optional[str] = Query(None),
    _: str = Depends(get_current_operator),
) -> LogsListResponse:
    """Returns up to limit most-recent log entries from the ring buffer in chronological order."""
    logs = get_recent_logs()

    # Filter logs
    filtered_logs = []
    for log in logs:
        if event and log.get("event") != event:
            continue
        if correlation_id and log.get("correlation_id") != correlation_id:
            continue
        filtered_logs.append(log)

    # Slice the last `limit` logs
    items = filtered_logs[-limit:]
    return LogsListResponse(items=items)


@router.get(
    "/search",
    response_model=LogsListResponse,
    status_code=status.HTTP_200_OK,
    summary="Search logs by correlation ID with since boundary."
)
async def search_logs(
    correlation_id: str = Query(...),
    since: Optional[str] = Query(None),
    _: str = Depends(get_current_operator),
) -> LogsListResponse:
    """Returns all ring buffer entries matching the correlation_id.

    Optionally filters events after the `since` ISO timestamp (default last 1h, max 24h window).
    """
    now = datetime.now(timezone.utc)
    max_past = now - timedelta(hours=24)

    if since:
        try:
            since_dt = parse_iso_timestamp(since)
            # Cap window to maximum of 24h ago
            if since_dt < max_past:
                since_dt = max_past
        except Exception:
            # Fallback to last 1h if invalid
            since_dt = now - timedelta(hours=1)
    else:
        since_dt = now - timedelta(hours=1)

    logs = get_recent_logs()
    matching_logs = []

    for log in logs:
        if log.get("correlation_id") != correlation_id:
            continue

        log_ts_str = log.get("timestamp")
        if not log_ts_str:
            continue

        try:
            log_dt = parse_iso_timestamp(log_ts_str)
        except Exception:
            continue

        if log_dt >= since_dt:
            matching_logs.append(log)

    return LogsListResponse(items=matching_logs)
