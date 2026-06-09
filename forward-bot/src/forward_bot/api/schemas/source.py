"""Pydantic schemas for the Source endpoints."""
from datetime import datetime
from pydantic import BaseModel, Field

from forward_bot.api.schemas.base import MongoBaseModel
from forward_bot.domain.entities.source import Source


class SourceRegisterRequest(BaseModel):
    """Payload for registering a new Source."""
    telegram_reference: str | int = Field(
        ...,
        description="Telegram username (with or without @) or numeric ID"
    )
    display_name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Display name for the source"
    )


class SourceResponse(MongoBaseModel):
    """Response payload representing a registered Source."""
    id: str = Field(validation_alias="_id", serialization_alias="id")
    telegram_id: int
    telegram_username: str | None
    display_name: str
    type: str
    folder_id: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, source: Source) -> "SourceResponse":
        """Convert a Source domain entity to a SourceResponse schema."""
        return cls(
            id=source.id,
            telegram_id=source.telegram_id,
            telegram_username=source.telegram_username,
            display_name=source.display_name,
            type=source.type,
            folder_id=source.folder_id,
            created_at=source.created_at,
            updated_at=source.updated_at
        )
