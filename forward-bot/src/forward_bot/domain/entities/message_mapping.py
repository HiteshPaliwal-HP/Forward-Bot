"""Message mapping domain entity."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class MessageMapping:
    """Represents a persisted mapping of a forwarded message from source to destination."""
    forwarding_rule_id: str
    source_channel_id: int
    source_message_id: int
    destination_channel_id: int
    destination_message_id: int
    forwarded_at: datetime
    id: Optional[str] = None
