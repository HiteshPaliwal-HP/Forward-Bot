"""Expose application instance for Uvicorn imports."""
import os
import sys
from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.infrastructure.logging import setup_logging

# Delay initialization if running tests to allow env var mocking
if "pytest" not in sys.modules and not os.environ.get("PYTEST_CURRENT_TEST"):
    settings = Settings()
    setup_logging(settings)
    app = create_app(settings)
else:
    # Dummy mock for test discovery
    app = None
