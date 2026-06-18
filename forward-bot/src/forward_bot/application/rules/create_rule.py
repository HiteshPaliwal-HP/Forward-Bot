"""Use case: Create a new Forwarding Rule."""
from datetime import datetime, timezone

from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    TimeWindowConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.application.rules.validators import (
    validate_keyword_regex,
    validate_timezone,
    validate_source_and_self_ref,
    validate_media_replacement,
)


class CreateRule:
    """Orchestrates validation and persistence of a new ForwardingRule."""

    def __init__(self, rule_repo, source_repo) -> None:
        self.rule_repo = rule_repo
        self.source_repo = source_repo

    async def execute(self, payload: dict) -> ForwardingRule:
        """Validate and create a new ForwardingRule.

        Args:
            payload: Validated data from ForwardingRuleCreateRequest.

        Returns:
            The persisted ForwardingRule entity with id and timestamps set.
        """
        source_id = payload["source_id"]
        destination_channel = payload["destination_channel"]

        # 1. Validate source exists and no self-referential rule
        await validate_source_and_self_ref(self.source_repo, source_id, destination_channel)

        # 2. Validate regex keywords if mode is "regex"
        validate_keyword_regex(payload.get("block_keywords", []), payload.get("keyword_match_mode", "literal"))
        validate_keyword_regex(payload.get("allow_keywords", []), payload.get("keyword_match_mode", "literal"))

        # 3. Validate timezone if time_window provided
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

        # 4. Validate media_replacement path required
        media_replacement_data = payload.get("media_replacement", {})
        validate_media_replacement(
            enabled=media_replacement_data.get("enabled", False),
            replacement_image_path=media_replacement_data.get("replacement_image_path"),
        )

        # 5. Build sub-configs
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

        # 6. Build entity
        now = datetime.now(timezone.utc)
        rule = ForwardingRule(
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
            created_at=now,
            updated_at=now,
        )

        # 7. Persist
        await self.rule_repo.add_rule(rule)
        return rule
