"""Use case for listing SourceFolders."""
from typing import Any
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository


class ListFolders:
    """Orchestrates folder retrieval with aggregated source count."""

    def __init__(self, folder_repo: FolderRepository) -> None:
        self.folder_repo = folder_repo

    async def execute(self, name_filter: str | None = None) -> list[dict[str, Any]]:
        """List folders with their calculated source_count, sorted by name ascending."""
        return await self.folder_repo.list_folders_with_source_count(name_filter)
