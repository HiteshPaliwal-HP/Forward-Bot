"""Use case for renaming/updating a SourceFolder."""
from datetime import datetime, timezone
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.exceptions import FolderNotFoundException, FolderNameInUseException
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.logging import logger


class RenameFolder:
    """Orchestrates folder renaming and ensures case-insensitive uniqueness checks."""

    def __init__(self, folder_repo: FolderRepository) -> None:
        self.folder_repo = folder_repo

    async def execute(self, folder_id: str, new_name: str) -> SourceFolder:
        """Rename folder, handling duplicates (excluding self) and logging the event."""
        # 1. Fetch folder
        folder = await self.folder_repo.get_folder_by_id(folder_id)
        if not folder:
            raise FolderNotFoundException(folder_id)

        # 2. Check case-insensitive uniqueness excluding self
        existing = await self.folder_repo.get_folder_by_name(new_name, exclude_id=folder_id)
        if existing:
            raise FolderNameInUseException(new_name)

        # 3. Apply updates
        old_name = folder.name
        folder.name = new_name
        folder.updated_at = datetime.now(timezone.utc)

        await self.folder_repo.update_folder(folder)

        # 4. Log
        logger.info(
            "folder_renamed",
            folder_id=folder_id,
            old_name=old_name,
            new_name=new_name,
            message=f"Folder '{folder_id}' renamed from '{old_name}' to '{new_name}'"
        )

        return folder
