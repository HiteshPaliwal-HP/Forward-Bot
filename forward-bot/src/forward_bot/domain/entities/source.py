"""Source domain entity representation."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Source:
    """Represents a registered Telegram source (channel or group)."""
    id: str | None
    telegram_id: int
    telegram_username: str | None
    display_name: str
    type: str  # "channel" | "group"
    folder_id: str | None
    created_at: datetime
    updated_at: datetime
