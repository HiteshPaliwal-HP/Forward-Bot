"""Configuration settings for Forward Bot using Pydantic Settings."""
from pathlib import Path
from zoneinfo import ZoneInfo
from typing import Any

from pydantic import Field, field_validator, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core settings (required, no default)
    api_key: str = Field(
        description="API key for authentication (required)",
    )
    secret_key: str = Field(
        description="Secret key for signing (required)",
    )
    mongo_uri: str = Field(
        description="MongoDB connection URI (required)",
    )
    telegram_api_id: int = Field(
        description="Telegram API ID for MTProto client connection (required)",
        validation_alias=AliasChoices("telegram_api_id", "api_id"),
    )
    telegram_api_hash: str = Field(
        description="Telegram API Hash for MTProto client connection (required)",
        validation_alias=AliasChoices("telegram_api_hash", "api_hash"),
    )

    # Telegram
    telegram_session_path: str = Field(
        default="./data/telegram.session",
        description="Path to store Telegram session data",
    )
    telegram_phone: str | None = Field(
        default=None,
        description="Optional pre-configured Telegram phone number",
    )

    # Media handling
    media_replacement_base_dir: str = Field(
        default="./data/replacement-images",
        description="Base directory for replacement media files",
    )

    # Timezone and sampling
    timezone_default: str = Field(
        default="UTC",
        description="Default timezone for timestamp operations",
    )
    sampling_persist: bool = Field(
        default=False,
        description="Whether to persist sampling counters across restarts",
    )

    # UI and server
    ui_enabled: bool = Field(
        default=True,
        description="Whether to serve the React dashboard UI",
    )
    bind_host: str = Field(
        default="127.0.0.1",
        description="Host to bind the server to (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)",
    )
    port: int = Field(
        default=8000,
        description="Port to bind the FastAPI server to",
    )
    cors_allowed_origins: list[str] = Field(
        default=["http://localhost:5173", "http://localhost:8000"],
        description="CORS allowed origins for API requests",
    )

    # Logging and caching
    log_ring_buffer_hours: int = Field(
        default=1,
        description="Ring buffer size in hours for structured logging",
    )
    hot_reload_interval: int = Field(
        default=30,
        description="Cache refresh interval in seconds",
    )
    mapping_retention_days: int = Field(
        default=30,
        description="Number of days to retain message mappings",
    )

    # Delivery reliability settings
    delivery_max_retries: int = Field(
        default=3,
        description="Maximum number of retries for transient delivery errors",
    )
    delivery_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff multiplier for delivery retries",
    )
    delivery_base_delay: float = Field(
        default=1.0,
        description="Initial delay in seconds for delivery retries",
    )

    @field_validator("timezone_default")
    @classmethod
    def validate_timezone(cls, v: str) -> str:
        """Validate timezone string using standard zoneinfo."""
        if v.upper() == "UTC":
            return v
        try:
            ZoneInfo(v)
            return v
        except Exception as e:
            raise ValueError(f"Invalid timezone: {v}. Error: {e}")

    @field_validator("hot_reload_interval")
    @classmethod
    def validate_hot_reload(cls, v: int) -> int:
        """Ensure hot_reload_interval is greater than 0."""
        if v <= 0:
            raise ValueError("hot_reload_interval must be greater than 0")
        return v

    def get_telegram_session_path(self) -> Path:
        """Get the telegram session path as a Path object."""
        try:
            return Path(self.telegram_session_path).expanduser()
        except Exception:
            return Path(self.telegram_session_path)

    def get_media_replacement_dir(self) -> Path:
        """Get the media replacement directory as a Path object."""
        try:
            return Path(self.media_replacement_base_dir).expanduser()
        except Exception:
            return Path(self.media_replacement_base_dir)


from functools import lru_cache

@lru_cache()
def get_settings() -> Settings:
    """Retrieve the cached application settings instance."""
    return Settings()
