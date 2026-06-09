"""Pydantic schemas for the Source endpoints."""
from datetime import datetime
from pydantic import BaseModel, Field, field_validator

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


class SourcesPagedResponse(BaseModel):
    """Response payload for paginated list of sources."""
    items: list[SourceResponse]
    total: int
    page: int
    page_size: int


class SourceUpdateRequest(BaseModel):
    """Payload for updating a Source entirely (PUT)."""
    display_name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., description="Must be channel or group")
    folder_id: str | None = Field(default=None, description="Assigned folder ID or null")
    telegram_username: str | None = Field(default=None, description="Optional telegram username")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in ("channel", "group"):
            raise ValueError("Type must be strictly 'channel' or 'group'.")
        return v

    @field_validator("folder_id")
    @classmethod
    def validate_folder_id(cls, v: str | None) -> str | None:
        if v is not None and v != "null":
            from bson import ObjectId
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid folder_id format")
        return v


class SourcePatchRequest(BaseModel):
    """Payload for partially updating a Source (PATCH)."""
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    type: str | None = Field(default=None, description="Must be channel or group")
    folder_id: str | None = Field(default=None, description="Assigned folder ID or null")
    telegram_username: str | None = Field(default=None, description="Optional telegram username")

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str | None) -> str | None:
        if v is not None and v not in ("channel", "group"):
            raise ValueError("Type must be strictly 'channel' or 'group'.")
        return v

    @field_validator("folder_id")
    @classmethod
    def validate_folder_id(cls, v: str | None) -> str | None:
        if v is not None and v != "null":
            from bson import ObjectId
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid folder_id format")
        return v


