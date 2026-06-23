"""Structured logging configuration, secret redacting, and ring buffer integration for Forward Bot."""
import logging
from typing import Any, Dict
import structlog
from forward_bot.config import Settings
from forward_bot.infrastructure.logging.ring_buffer import init_ring_buffer, append_to_ring_buffer


class SecretRedactor:
    """Structlog processor to redact sensitive keys and raw session bytes from logs."""

    def __init__(self, api_key: str | None = None, secret_key: str | None = None) -> None:
        self.secrets = []
        if api_key and api_key != "your-api-key-here" and api_key.strip():
            stripped_api = api_key.strip()
            if len(stripped_api) >= 6:
                self.secrets.append(stripped_api)
            else:
                import sys
                print("WARNING: API_KEY is too short (less than 6 characters). Skipping redaction to avoid over-scrubbing.", file=sys.stderr)
        if secret_key and secret_key != "your-secret-key-here" and secret_key.strip():
            stripped_secret = secret_key.strip()
            if len(stripped_secret) >= 6:
                self.secrets.append(stripped_secret)
            else:
                import sys
                print("WARNING: SECRET_KEY is too short (less than 6 characters). Skipping redaction to avoid over-scrubbing.", file=sys.stderr)

    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        return self.redact(event_dict)

    def redact(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self.redact(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact(v) for v in data]
        elif isinstance(data, str):
            redacted = data
            for secret in self.secrets:
                if secret in redacted:
                    redacted = redacted.replace(secret, "[REDACTED]")
            return redacted
        elif isinstance(data, bytes):
            # Session bytes or binary keys should never be logged
            return "[REDACTED_BYTES]"
        return data


def setup_logging(settings: Settings) -> None:
    """Configure structlog for standard JSON output with secret redaction and ring buffer storage."""
    # Configure standard logging level
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
    )

    # Initialize the ring buffer
    init_ring_buffer(settings.log_ring_buffer_hours)

    redactor = SecretRedactor(
        api_key=settings.api_key,
        secret_key=settings.secret_key,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,   # Injects correlation_id
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            redactor,                                  # Scrub API key, secret key, session bytes
            append_to_ring_buffer,                     # Store and broadcast structured log events
            structlog.processors.JSONRenderer(),       # Render as structured JSON
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.PrintLoggerFactory(),
    )
