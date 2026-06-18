"""Use case for creating a new SourceFolder."""
from datetime import datetime, timezone
from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.domain.exceptions import FolderNameInUseException
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.logging import logger


class CreateFolder:
    """Orchestrates folder creation and enforces name uniqueness."""

    def __init__(self, folder_repo: FolderRepository) -> None:
        self.folder_repo = folder_repo

    async def execute(self, name: str) -> SourceFolder:
        """Create a folder after checking for duplicate name (case-insensitive)."""
        # 1. Enforce uniqueness
        existing = await self.folder_repo.get_folder_by_name(name)
        if existing:
            raise FolderNameInUseException(name)

        # 2. Save
        now = datetime.now(timezone.utc)
        folder = SourceFolder(
            id=None,
            name=name,
            created_at=now,
            updated_at=now
        )
        inserted_id = await self.folder_repo.add_folder(folder)

        # 3. Log
        logger.info(
            "folder_created",
            folder_id=inserted_id,
            name=name,
            message=f"Folder '{name}' created successfully"
        )
        return folder
