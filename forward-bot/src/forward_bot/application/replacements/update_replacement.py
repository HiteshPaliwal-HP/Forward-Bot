"""Use case: Update an existing Replacement Rule (full replacement semantics)."""
from datetime import datetime, timezone

from forward_bot.application.rules.validators import validate_keyword_regex
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.exceptions import ReplacementRuleNotFoundException


class UpdateReplacement:
    """Validates and applies a full replacement update to an existing ReplacementRule.

    Steps:
    1. Check replacement exists — raises ReplacementRuleNotFoundException (→ HTTP 404) if not.
    2. If match_mode='regex', validate search_text compiles — raises RuleInvalidRegexException (→ HTTP 422).
    3. Apply payload fields to the existing entity (preserves forwarding_rule_id and created_at).
    4. Persist the update.
    """

    def __init__(self, replacement_repo) -> None:
        self.replacement_repo = replacement_repo

    async def execute(self, replacement_id: str, payload: dict) -> ReplacementRule:
        # 1. Check replacement exists
        existing = await self.replacement_repo.get_replacement_by_id(replacement_id)
        if existing is None:
            raise ReplacementRuleNotFoundException(replacement_id)  # → 404

        # 2. Validate regex if match_mode=regex.
        # CRITICAL: search_text MUST be wrapped in a list (see CreateReplacement for rationale).
        validate_keyword_regex([payload["search_text"]], payload["match_mode"])

        # 3. Update entity fields (preserve forwarding_rule_id and created_at)
        existing.search_text = payload["search_text"]
        existing.replacement_text = payload["replacement_text"]
        existing.match_mode = payload["match_mode"]
        existing.is_active = payload.get("is_active", existing.is_active)
        existing.updated_at = datetime.now(timezone.utc)

        # 4. Persist update
        await self.replacement_repo.update_replacement(replacement_id, existing)
        return existing
