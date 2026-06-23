from collections import deque
from typing import Any, Dict, List, Optional
import math

from forward_bot.infrastructure.logging.sse_broadcaster import broadcast_log

# Global ring buffer instance
_ring_buffer: Optional[deque] = None


def init_ring_buffer(hours: float) -> None:
    """Initialize the global ring buffer with a maximum size calculated from hours."""
    global _ring_buffer
    if math.isinf(hours) or math.isnan(hours):
        hours = 24.0  # Safe default fallback
    limit = max(1000, min(int(hours * 3600), 1_000_000))
    _ring_buffer = deque(maxlen=limit)


def append_to_ring_buffer(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Structlog processor to copy and append event_dict to the ring buffer and broadcast it."""
    global _ring_buffer
    if _ring_buffer is not None:
        copied_event = event_dict.copy()
        _ring_buffer.append(copied_event)
        
        # Broadcast log to SSE subscribers
        broadcast_log(copied_event)
        
    return event_dict


def get_recent_logs() -> List[Dict[str, Any]]:
    """Return recent logs from the ring buffer in chronological order."""
    global _ring_buffer
    if _ring_buffer is None:
        return []
    return list(_ring_buffer)
