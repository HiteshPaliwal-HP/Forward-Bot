"""Use case for deleting a registered Telegram source."""
from forward_bot.domain.exceptions import (
    SourceNotFoundException,
    SourceInUseException,
)
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository


class DeleteSource:
    """Orchestrates source deletion and ensures referential integrity checks."""

    def __init__(self, source_repo: SourceRepository) -> None:
        self.source_repo = source_repo

    async def execute(self, source_id: str) -> None:
        """Verify existence, ensure no referencing forwarding rules exist, and delete source."""
        # 1. Verify existence
        source = await self.source_repo.get_source_by_id(source_id)
        if not source:
            raise SourceNotFoundException(source_id)

        # 2. Check if referenced by forwarding rules
        referencing_count = await self.source_repo.get_referencing_rules_count(source_id)
        if referencing_count > 0:
            raise SourceInUseException(source_id, referencing_count)

        # 3. Perform deletion
        await self.source_repo.delete_source(source_id)
