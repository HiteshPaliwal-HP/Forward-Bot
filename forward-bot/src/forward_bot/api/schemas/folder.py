"""Pydantic schemas for the Folder endpoints."""
from datetime import datetime
from pydantic import BaseModel, Field

from forward_bot.api.schemas.base import MongoBaseModel
from forward_bot.api.schemas.source import SourceResponse
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.entities.source import Source


class FolderCreateRequest(BaseModel):
    """Payload for creating a new Folder."""
    name: str = Field(..., min_length=1, max_length=100, description="Name of the folder")


class FolderUpdateRequest(BaseModel):
    """Payload for updating a Folder (rename)."""
    name: str = Field(..., min_length=1, max_length=100, description="New name for the folder")


class FolderResponse(MongoBaseModel):
    """Response payload representing a Folder."""
    id: str = Field(validation_alias="_id", serialization_alias="id")
    name: str
    created_at: datetime
    updated_at: datetime
    source_count: int = 0

    @classmethod
    def from_entity(cls, folder: SourceFolder, source_count: int = 0) -> "FolderResponse":
        """Convert a SourceFolder domain entity to a FolderResponse schema."""
        return cls(
            id=folder.id,
            name=folder.name,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            source_count=source_count
        )


class FolderDetailsResponse(FolderResponse):
    """Response payload representing detailed Folder information with sources."""
    sources: list[SourceResponse] | None = None

    @classmethod
    def from_entity_with_sources(
        cls,
        folder: SourceFolder,
        sources: list[Source] | None = None,
        source_count: int = 0
    ) -> "FolderDetailsResponse":
        """Convert folder and optional sources to FolderDetailsResponse."""
        sources_schemas = None
        if sources is not None:
            sources_schemas = [SourceResponse.from_entity(s) for s in sources]

        return cls(
            id=folder.id,
            name=folder.name,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            source_count=source_count,
            sources=sources_schemas
        )
