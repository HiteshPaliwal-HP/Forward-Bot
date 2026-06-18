"""Use case: Delete a Forwarding Rule (with cascade delete of replacement_rules)."""
from forward_bot.domain.exceptions import RuleNotFoundException


class DeleteRule:
    """Orchestrates forwarding rule deletion with cascade on replacement_rules."""

    def __init__(self, rule_repo) -> None:
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> None:
        """Delete a forwarding rule and cascade-delete all its replacement rules.

        Raises:
            RuleNotFoundException: If rule_id does not exist (→ HTTP 404).
        """
        # 1. Verify existence
        rule = await self.rule_repo.get_rule_by_id(rule_id)
        if rule is None:
            raise RuleNotFoundException(rule_id)

        # 2. Delete (cascade is handled inside the repository)
        await self.rule_repo.delete_rule(rule_id)
