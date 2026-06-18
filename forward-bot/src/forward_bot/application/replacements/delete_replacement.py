"""Use case: Delete an existing Replacement Rule."""
from forward_bot.domain.exceptions import ReplacementRuleNotFoundException


class DeleteReplacement:
    """Validates existence of a ReplacementRule and deletes it.

    Steps:
    1. Check replacement exists — raises ReplacementRuleNotFoundException (→ HTTP 404) if not.
    2. Delete the replacement rule.
    """

    def __init__(self, replacement_repo) -> None:
        self.replacement_repo = replacement_repo

    async def execute(self, replacement_id: str) -> None:
        existing = await self.replacement_repo.get_replacement_by_id(replacement_id)
        if existing is None:
            raise ReplacementRuleNotFoundException(replacement_id)  # → 404
        await self.replacement_repo.delete_replacement(replacement_id)
