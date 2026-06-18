"""Use case: Disable a Forwarding Rule (set is_active=False)."""
from forward_bot.domain.exceptions import RuleNotFoundException


class DisableRule:
    """Orchestrates disabling (deactivating) a forwarding rule."""

    def __init__(self, rule_repo) -> None:
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> None:
        """Set is_active=False on the given rule.

        Raises:
            RuleNotFoundException: If rule_id does not exist or is invalid (→ HTTP 404).
        """
        modified = await self.rule_repo.disable_rule(rule_id)
        if not modified:
            raise RuleNotFoundException(rule_id)
