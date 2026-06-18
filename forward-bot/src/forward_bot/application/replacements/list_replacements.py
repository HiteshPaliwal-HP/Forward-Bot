"""Use case: List all Replacement Rules for a Forwarding Rule, ordered by created_at ASC."""
from forward_bot.domain.exceptions import RuleNotFoundException


class ListReplacements:
    """Validates parent ForwardingRule exists, then fetches ordered replacement rules.

    Steps:
    1. Validate parent ForwardingRule exists — raises RuleNotFoundException (→ HTTP 404) if not.
    2. Fetch all replacement rules for that parent, ordered by created_at ASC (pipeline order, FR-7).
    """

    def __init__(self, replacement_repo, rule_repo) -> None:
        self.replacement_repo = replacement_repo
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str) -> list:
        # Validate parent rule exists
        parent_rule = await self.rule_repo.get_rule_by_id(rule_id)
        if parent_rule is None:
            raise RuleNotFoundException(rule_id)  # → 404

        return await self.replacement_repo.list_replacements_for_rule(rule_id)
