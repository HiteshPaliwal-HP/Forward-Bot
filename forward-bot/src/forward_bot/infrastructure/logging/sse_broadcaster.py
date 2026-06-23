import asyncio
import weakref
from typing import Any, Dict

# Global fan-out set of active SSE subscriber queues
_subscribers: weakref.WeakSet = weakref.WeakSet()


def register_subscriber(queue: asyncio.Queue) -> None:
    """Register a new SSE subscriber queue."""
    global _subscribers
    _subscribers.add(queue)


def unregister_subscriber(queue: asyncio.Queue) -> None:
    """Unregister an SSE subscriber queue."""
    global _subscribers
    _subscribers.discard(queue)


def broadcast_log(event: Dict[str, Any]) -> None:
    """Broadcast a log event to all registered subscribers."""
    global _subscribers
    for queue in list(_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            # Handle QueueFull safely by doing nothing (dropping the log event for this subscriber)
            pass
