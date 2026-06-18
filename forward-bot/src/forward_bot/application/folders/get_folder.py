"""Use case for retrieving folder details."""
from forward_bot.domain.entities.source import Source
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.exceptions import FolderNotFoundException
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository


class GetFolder:
    """Orchestrates folder retrieval and optionally loads embedded sources."""

    def __init__(self, folder_repo: FolderRepository, source_repo: SourceRepository) -> None:
        self.folder_repo = folder_repo
        self.source_repo = source_repo

    async def execute(self, folder_id: str, include_sources: bool = False) -> tuple[SourceFolder, list[Source] | None]:
        """Fetch folder by ID, raise FolderNotFoundException if missing, optionally load sources."""
        folder = await self.folder_repo.get_folder_by_id(folder_id)
        if not folder:
            raise FolderNotFoundException(folder_id)

        sources = None
        if include_sources:
            sources = await self.source_repo.get_sources_by_folder_id(folder_id)

        return folder, sources
