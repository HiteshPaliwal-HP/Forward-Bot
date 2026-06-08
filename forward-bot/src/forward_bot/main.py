"""Expose application instance for Uvicorn imports."""
from forward_bot.app import create_app
from forward_bot.config import Settings

settings = Settings()
app = create_app(settings)
