"""Use case for listing registered Telegram sources."""
from typing import Tuple
from forward_bot.domain.entities.source import Source
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository


class ListSources:
    """Orchestrates listing sources with pagination and filtering."""

    def __init__(self, source_repo: SourceRepository) -> None:
        self.source_repo = source_repo

    async def execute(
        self,
        filter_type: str | None = None,
        folder_id: str | None = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[list[Source], int]:
        """List sources with pagination and filters."""
        if filter_type is not None and filter_type not in ("channel", "group"):
            raise ValueError("Type must be 'channel' or 'group'.")
            
        if page < 1:
            raise ValueError("Page must be >= 1.")
        if page_size < 1:
            raise ValueError("Page size must be >= 1.")
        
        # Enforce page size limit
        page_size = min(page_size, 200)

        if folder_id is not None and folder_id != "null":
            from bson import ObjectId
            if not ObjectId.is_valid(folder_id):
                raise ValueError("Invalid folder_id format")

        return await self.source_repo.list_sources(
            filter_type=filter_type,
            folder_id=folder_id,
            page=page,
            page_size=page_size
        )
