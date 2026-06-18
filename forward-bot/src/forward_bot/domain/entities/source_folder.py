"""SourceFolder domain entity representation."""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class SourceFolder:
    """Represents a folder to organize sources."""
    id: str | None
    name: str
    created_at: datetime
    updated_at: datetime
