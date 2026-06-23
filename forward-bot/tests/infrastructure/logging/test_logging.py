import asyncio
import pytest
from unittest.mock import MagicMock
import structlog
from collections import deque

from forward_bot.config import Settings
from forward_bot.infrastructure.logging import (
    SecretRedactor,
    setup_logging,
    get_recent_logs,
    register_subscriber,
    unregister_subscriber,
)
from forward_bot.infrastructure.logging.ring_buffer import (
    init_ring_buffer,
    append_to_ring_buffer,
)
from forward_bot.infrastructure.logging.sse_broadcaster import (
    _subscribers,
    broadcast_log,
)


def test_secret_redactor_ignores_short_keys():
    """Verify that SecretRedactor only redacts secrets that are at least 6 characters long."""
    # Length < 6 should be ignored, length >= 6 should be loaded
    redactor = SecretRedactor(api_key="12345", secret_key="1234567")
    assert "12345" not in redactor.secrets
    assert "1234567" in redactor.secrets
    
    data = {
        "msg": "API KEY is 12345 and secret is 1234567"
    }
    redacted = redactor.redact(data)
    # "12345" is not redacted (short key ignored to prevent over-scrubbing)
    # "1234567" is redacted correctly
    assert redacted["msg"] == "API KEY is 12345 and secret is [REDACTED]"


def test_secret_redactor_redacts_bytes_and_secrets():
    """Verify SecretRedactor replaces secrets and byte arrays correctly."""
    redactor = SecretRedactor(api_key="super_secret_api_key", secret_key="super_secret_key")
    
    data = {
        "api_val": "super_secret_api_key",
        "secret_val": "super_secret_key",
        "nested": {
            "key": "my secret_key val",
        },
        "session_bytes": b"sqlite session db binary content",
        "normal_int": 42
    }
    
    redacted = redactor.redact(data)
    assert redacted["api_val"] == "[REDACTED]"
    assert redacted["secret_val"] == "[REDACTED]"
    assert redacted["nested"]["key"] == "my secret_key val"  # because the value doesn't contain "super_secret_key"
    assert redacted["session_bytes"] == "[REDACTED_BYTES]"
    assert redacted["normal_int"] == 42
def test_ring_buffer_sizing():
    """Verify ring buffer size derivation from hours."""
    # max(1000, log_ring_buffer_hours * 3600)
    init_ring_buffer(hours=0.5)
    import forward_bot.infrastructure.logging.ring_buffer as rb
    assert rb._ring_buffer.maxlen == 1800

    init_ring_buffer(hours=0.1)
    assert rb._ring_buffer.maxlen == 1000

    init_ring_buffer(hours=2.0)
    assert rb._ring_buffer.maxlen == 7200


def test_ring_buffer_eviction():
    """Verify eviction behavior when the ring buffer is full."""
    # Use 0.1 hours (maxlen = 1000)
    init_ring_buffer(hours=0.1)
    
    # Fill ring buffer and exceed capacity
    for i in range(1005):
        append_to_ring_buffer(None, "info", {"event": f"log_{i}"})
        
    logs = get_recent_logs()
    assert len(logs) == 1000
    # First 5 should be evicted
    assert logs[0]["event"] == "log_5"
    assert logs[-1]["event"] == "log_1004"


@pytest.mark.anyio
async def test_sse_broadcaster_fanout():
    """Verify logs are fanned out to subscribers and QueueFull is handled safely."""
    # Ensure subscribers set is clean
    _subscribers.clear()
    
    queue1 = asyncio.Queue(maxsize=10)
    queue2 = asyncio.Queue(maxsize=1)
    
    register_subscriber(queue1)
    register_subscriber(queue2)
    
    assert queue1 in _subscribers
    assert queue2 in _subscribers
    
    event = {"event": "test_event", "level": "info"}
    broadcast_log(event)
    
    # Both queues should have received the event
    assert queue1.qsize() == 1
    assert queue2.qsize() == 1
    assert await queue1.get() == event
    assert await queue2.get() == event
    
    # Test QueueFull handling by filling queue2
    await queue2.put({"dummy": "data"})
    
    # Now broadcast. Since queue2 is full, it should not raise QueueFull error and should just drop/ignore
    broadcast_log({"event": "another_event"})
    
    # queue1 should receive the new event
    assert queue1.qsize() == 1
    assert await queue1.get() == {"event": "another_event"}
    
    # Unregister
    unregister_subscriber(queue1)
    assert queue1 not in _subscribers
    assert queue2 in _subscribers
    
    _subscribers.clear()


def test_early_initialization_and_structlog_chain():
    """Verify setup_logging configures structlog with proper processor chain."""
    settings = Settings(
        api_key="valid-api-key",
        secret_key="my-secret-key-too",
        mongo_uri="mongodb://localhost:27017/test_db",
        telegram_api_id=123456,
        telegram_api_hash="hash",
        log_ring_buffer_hours=1,
    )
    
    # Call setup_logging
    setup_logging(settings)
    
    # Assert ring buffer is initialized
    import forward_bot.infrastructure.logging.ring_buffer as rb
    assert rb._ring_buffer is not None
    assert rb._ring_buffer.maxlen == 3600
    
    # Emit a log event through structlog to test processor chain execution
    # Bind a correlation ID
    structlog.contextvars.bind_contextvars(correlation_id="test-corr-id")
    
    # Get logger and log
    logger = structlog.get_logger()
    logger.info("source_registered", display_name="Test Source", secret_data="my-secret-key-too")
    
    # Clear variables
    structlog.contextvars.clear_contextvars()
    
    # Check ring buffer
    logs = get_recent_logs()
    assert len(logs) > 0
    
    # Find the log we just emitted
    target_log = None
    for log in reversed(logs):
        if log.get("event") == "source_registered":
            target_log = log
            break
            
    assert target_log is not None
    assert target_log["correlation_id"] == "test-corr-id"
    assert "timestamp" in target_log
    assert target_log["level"] == "info"
    assert target_log["display_name"] == "Test Source"
    # Secret must be redacted
    assert target_log["secret_data"] == "[REDACTED]"
