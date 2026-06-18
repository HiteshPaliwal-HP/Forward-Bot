"""Use case: Full replacement update of a Forwarding Rule."""
from datetime import datetime, timezone

from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    TimeWindowConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.domain.exceptions import RuleNotFoundException
from forward_bot.application.rules.validators import (
    validate_keyword_regex,
    validate_timezone,
    validate_source_and_self_ref,
    validate_media_replacement,
)


class UpdateRule:
    """Orchestrates full replacement update for a ForwardingRule (same validations as CreateRule)."""

    def __init__(self, rule_repo, source_repo) -> None:
        self.rule_repo = rule_repo
        self.source_repo = source_repo

    async def execute(self, rule_id: str, payload: dict) -> ForwardingRule:
        """Validate and replace a ForwardingRule document.

        PUT semantics: all fields replaced. Preserves original created_at.

        Args:
            rule_id: The target rule's ID.
            payload: Validated data from ForwardingRuleUpdateRequest.

        Returns:
            The updated ForwardingRule entity.

        Raises:
            RuleNotFoundException: If rule_id does not exist (→ HTTP 404).
            RuleSourceNotFoundException: If source_id not found (→ HTTP 422).
            RuleSelfReferentialException: If source equals destination (→ HTTP 422).
            RuleInvalidRegexException: If invalid regex pattern (→ HTTP 422).
            RuleInvalidTimezoneException: If invalid timezone (→ HTTP 422).
            RuleMediaReplacementPathRequiredException: If media_replacement enabled without path (→ HTTP 422).
        """
        # 1. Verify rule exists
        existing = await self.rule_repo.get_rule_by_id(rule_id)
        if existing is None:
            raise RuleNotFoundException(rule_id)

        source_id = payload["source_id"]
        destination_channel = payload["destination_channel"]

        # 2. Validate source exists and no self-referential rule (re-validates; AC12 note)
        await validate_source_and_self_ref(self.source_repo, source_id, destination_channel)

        # 3. Validate regex keywords
        validate_keyword_regex(payload.get("block_keywords", []), payload.get("keyword_match_mode", "literal"))
        validate_keyword_regex(payload.get("allow_keywords", []), payload.get("keyword_match_mode", "literal"))

        # 4. Validate timezone if time_window provided
        time_window_data = payload.get("time_window")
        time_window = None
        if time_window_data is not None:
            validate_timezone(time_window_data["timezone"])
            time_window = TimeWindowConfig(
                timezone=time_window_data["timezone"],
                days_of_week=time_window_data["days_of_week"],
                start_time=time_window_data["start_time"],
                end_time=time_window_data["end_time"],
            )

        # 5. Validate media_replacement path required
        media_replacement_data = payload.get("media_replacement", {})
        validate_media_replacement(
            enabled=media_replacement_data.get("enabled", False),
            replacement_image_path=media_replacement_data.get("replacement_image_path"),
        )

        # 6. Build sub-configs
        sampling_data = payload.get("sampling", {"n": 1})
        sampling = SamplingConfig(n=sampling_data.get("n", 1))

        attribution_data = payload.get("attribution", {})
        attribution = AttributionConfig(
            enabled=attribution_data.get("enabled", False),
            position=attribution_data.get("position", "prefix"),
            format=attribution_data.get("format", "From {source_name}"),
        )

        auto_replace_data = payload.get("auto_replace_source_refs", {})
        auto_replace = AutoReplaceSourceRefsConfig(
            enabled=auto_replace_data.get("enabled", False),
            replacement=auto_replace_data.get("replacement"),
            replace_display_name=auto_replace_data.get("replace_display_name", False),
        )

        media_replacement = MediaReplacementConfig(
            enabled=media_replacement_data.get("enabled", False),
            replacement_image_path=media_replacement_data.get("replacement_image_path"),
            replacement_caption_mode=media_replacement_data.get("replacement_caption_mode", "use_source"),
        )

        # 7. Build updated entity (preserve original created_at)
        now = datetime.now(timezone.utc)
        updated_rule = ForwardingRule(
            id=rule_id,
            source_id=source_id,
            destination_channel=destination_channel,
            is_active=payload.get("is_active", False),
            keyword_match_mode=payload.get("keyword_match_mode", "literal"),
            block_keywords=payload.get("block_keywords", []),
            allow_keywords=payload.get("allow_keywords", []),
            media_type_filter=payload.get("media_type_filter", ["text", "photo"]),
            remove_links=payload.get("remove_links", False),
            remove_hashtags=payload.get("remove_hashtags", False),
            remove_mentions=payload.get("remove_mentions", False),
            forward_media=payload.get("forward_media", "forward"),
            sampling=sampling,
            time_window=time_window,
            attribution=attribution,
            auto_replace_source_refs=auto_replace,
            media_replacement=media_replacement,
            created_at=existing.created_at,  # preserve original
            updated_at=now,
        )

        # 8. Persist
        await self.rule_repo.update_rule(rule_id, updated_rule)
        return updated_rule
