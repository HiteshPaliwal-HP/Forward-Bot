"""Use case: Create a new Replacement Rule scoped to a Forwarding Rule."""
from datetime import datetime, timezone

from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.application.rules.validators import validate_keyword_regex
from forward_bot.domain.exceptions import RuleNotFoundException


class CreateReplacement:
    """Validates and persists a new ReplacementRule.

    Steps:
    1. Validate parent ForwardingRule exists — raises RuleNotFoundException (→ HTTP 404) if not.
    2. If match_mode='regex', validate search_text compiles — raises RuleInvalidRegexException (→ HTTP 422).
    3. Build ReplacementRule entity with timestamps.
    4. Persist via replacement repository.
    """

    def __init__(self, replacement_repo, rule_repo) -> None:
        self.replacement_repo = replacement_repo
        self.rule_repo = rule_repo

    async def execute(self, rule_id: str, payload: dict) -> ReplacementRule:
        # 1. Validate parent rule exists
        parent_rule = await self.rule_repo.get_rule_by_id(rule_id)
        if parent_rule is None:
            raise RuleNotFoundException(rule_id)  # → 404

        # 2. Validate regex if match_mode=regex.
        # CRITICAL: search_text MUST be wrapped in a list.
        # validate_keyword_regex iterates over the list. Passing a bare string
        # would iterate its characters — each single char compiles as a valid regex,
        # making validation silently a no-op for invalid patterns like "[invalid(".
        validate_keyword_regex([payload["search_text"]], payload["match_mode"])

        # 3. Build entity
        now = datetime.now(timezone.utc)
        replacement = ReplacementRule(
            forwarding_rule_id=rule_id,  # store as plain string (not ObjectId)
            search_text=payload["search_text"],
            replacement_text=payload["replacement_text"],
            match_mode=payload["match_mode"],
            is_active=payload.get("is_active", True),  # default True per FR-7
            created_at=now,
            updated_at=now,
        )

        # 4. Persist
        await self.replacement_repo.add_replacement(replacement)
        return replacement
