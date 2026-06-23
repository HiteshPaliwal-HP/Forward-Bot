"""Structured logging configuration and utilities for Forward Bot."""
import structlog

from forward_bot.infrastructure.logging.setup import setup_logging, SecretRedactor
from forward_bot.infrastructure.logging.ring_buffer import get_recent_logs, append_to_ring_buffer
from forward_bot.infrastructure.logging.sse_broadcaster import register_subscriber, unregister_subscriber

# Get a bound logger
logger = structlog.get_logger()

__all__ = [
    "setup_logging",
    "logger",
    "get_recent_logs",
    "register_subscriber",
    "unregister_subscriber",
    "SecretRedactor",
    "append_to_ring_buffer",
]
