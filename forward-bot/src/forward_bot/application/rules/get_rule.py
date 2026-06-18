"""Use case: Retrieve a single Forwarding Rule by ID."""
from forward_bot.domain.entities.forwarding_rule import ForwardingRule
from forward_bot.domain.exceptions import RuleNotFoundException


class GetRule:
    """Orchestrates retrieval of a single forwarding rule by its ID."""

    def __init__(self, rule_repo) -> None:
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> ForwardingRule:
        """Fetch a forwarding rule by ID.

        Raises:
            RuleNotFoundException: If no rule with the given ID exists (→ HTTP 404).
        """
        rule = await self.rule_repo.get_rule_by_id(rule_id)
        if rule is None:
            raise RuleNotFoundException(rule_id)
        return rule
