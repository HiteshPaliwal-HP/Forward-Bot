"""Use case: List Forwarding Rules with pagination and filters."""
from forward_bot.domain.entities.forwarding_rule import ForwardingRule


class ListRules:
    """Orchestrates listing forwarding rules with pagination and optional filters."""

    def __init__(self, rule_repo, source_repo) -> None:
        self.rule_repo = rule_repo
        self.source_repo = source_repo

    async def execute(
        self,
        source_id: str | None = None,
        destination_channel: str | None = None,
        is_active: bool | None = None,
        folder_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ForwardingRule], int]:
        """Return a paginated list of forwarding rules matching the given filters."""
        page_size = min(page_size, 200)

        return await self.rule_repo.list_rules(
            source_repo=self.source_repo,
            source_id=source_id,
            destination_channel=destination_channel,
            is_active=is_active,
            folder_id=folder_id,
            page=page,
            page_size=page_size,
        )
