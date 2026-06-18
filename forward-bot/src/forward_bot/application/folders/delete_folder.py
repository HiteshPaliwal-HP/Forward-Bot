"""Use case for deleting a SourceFolder."""
from forward_bot.domain.exceptions import FolderNotFoundException
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.logging import logger


class DeleteFolder:
    """Orchestrates folder deletion, disassociates sources, and logs the event."""

    def __init__(self, folder_repo: FolderRepository) -> None:
        self.folder_repo = folder_repo

    async def execute(self, folder_id: str) -> None:
        """Verify existence, delete folder, disassociate sources, and emit log event."""
        # 1. Verify existence
        folder = await self.folder_repo.get_folder_by_id(folder_id)
        if not folder:
            raise FolderNotFoundException(folder_id)

        # 2. Delete and disassociate
        await self.folder_repo.delete_folder(folder_id)

        # 3. Log
        logger.info(
            "folder_deleted",
            folder_id=folder_id,
            name=folder.name,
            message=f"Folder '{folder.name}' with ID '{folder_id}' deleted successfully"
        )
