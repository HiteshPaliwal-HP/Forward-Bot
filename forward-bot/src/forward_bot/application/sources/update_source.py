"""Use case for updating an existing registered Telegram source."""
from datetime import datetime, timezone
from typing import Any
from forward_bot.domain.entities.source import Source
from forward_bot.domain.exceptions import (
    SourceNotFoundException,
    FolderReferenceNotFoundException,
    SourceUsernameAlreadyExistsException,
)
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository


class UpdateSource:
    """Orchestrates source updating (PUT and PATCH)."""

    def __init__(self, source_repo: SourceRepository) -> None:
        self.source_repo = source_repo

    async def execute(self, source_id: str, update_fields: dict[str, Any], partial: bool = False) -> Source:
        """Verify existence, validate inputs, check duplicates, and apply update."""
        # 1. Fetch existing source
        source = await self.source_repo.get_source_by_id(source_id)
        if not source:
            raise SourceNotFoundException(source_id)

        # 2. Validate folder_id if provided and not null/None
        if "folder_id" in update_fields:
            folder_id = update_fields["folder_id"]
            if folder_id is not None and folder_id != "null":
                from bson import ObjectId
                if not ObjectId.is_valid(folder_id):
                    raise ValueError("Invalid folder_id format")
                # Check folder existence
                exists = await self.source_repo.folder_exists(folder_id)
                if not exists:
                    raise FolderReferenceNotFoundException(folder_id)

        # 3. Validate duplicate username if telegram_username is provided
        if "telegram_username" in update_fields:
            username = update_fields["telegram_username"]
            if username:
                username = username.lstrip("@").strip()
                if not username:
                    username = None
            else:
                username = None
            
            if username is not None:
                existing = await self.source_repo.get_source_by_username(username)
                if existing and existing.id != source_id:
                    raise SourceUsernameAlreadyExistsException(username)
            
            # Store normalized username back in update_fields for mapping
            update_fields["telegram_username"] = username

        # 4. Map fields based on PUT vs PATCH
        if not partial:
            # PUT: all payload fields must be applied
            if "display_name" not in update_fields or not update_fields["display_name"]:
                raise ValueError("display_name is required for PUT update.")
            if "type" not in update_fields or update_fields["type"] not in ("channel", "group"):
                raise ValueError("type must be 'channel' or 'group' for PUT update.")
            
            source.display_name = update_fields["display_name"]
            source.type = update_fields["type"]
            # folder_id and telegram_username are optional/nullable
            source.folder_id = update_fields.get("folder_id") if update_fields.get("folder_id") != "null" else None
            source.telegram_username = update_fields.get("telegram_username")
        else:
            # PATCH: only update provided fields
            if "display_name" in update_fields:
                val = update_fields["display_name"]
                if not val:
                    raise ValueError("display_name cannot be empty.")
                source.display_name = val
            if "type" in update_fields:
                val = update_fields["type"]
                if val not in ("channel", "group"):
                    raise ValueError("type must be 'channel' or 'group'.")
                source.type = val
            if "folder_id" in update_fields:
                val = update_fields["folder_id"]
                source.folder_id = val if val != "null" else None
            if "telegram_username" in update_fields:
                source.telegram_username = update_fields["telegram_username"]

        # Update timestamp
        source.updated_at = datetime.now(timezone.utc)

        # 5. Save to database
        await self.source_repo.update_source(source)
        return source
