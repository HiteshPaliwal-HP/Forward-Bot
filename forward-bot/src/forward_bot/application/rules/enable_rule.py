"""Use case: Enable a Forwarding Rule (set is_active=True)."""
from forward_bot.domain.exceptions import RuleNotFoundException


class EnableRule:
    """Orchestrates enabling (activating) a forwarding rule."""

    def __init__(self, rule_repo) -> None:
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> None:
        """Set is_active=True on the given rule.

        Raises:
            RuleNotFoundException: If rule_id does not exist or is invalid (→ HTTP 404).
        """
        modified = await self.rule_repo.enable_rule(rule_id)
        if not modified:
            raise RuleNotFoundException(rule_id)
