"""Shared validation helpers for forwarding rule use cases."""
import re
from zoneinfo import ZoneInfo

from forward_bot.domain.exceptions import (
    RuleInvalidRegexException,
    RuleInvalidTimezoneException,
    RuleMediaReplacementPathRequiredException,
    RuleSelfReferentialException,
    RuleSourceNotFoundException,
)


def validate_keyword_regex(keywords: list[str], mode: str) -> None:
    """Validate that all keyword patterns are valid Python regex when mode is 'regex'."""
    if mode != "regex":
        return
    for pattern in keywords:
        try:
            re.compile(pattern)
        except re.error as e:
            raise RuleInvalidRegexException(pattern=pattern, reason=str(e))


def validate_timezone(tz_name: str) -> None:
    """Validate that a timezone name is a valid IANA timezone using zoneinfo (stdlib)."""
    try:
        ZoneInfo(tz_name)
    except Exception:
        raise RuleInvalidTimezoneException(timezone=tz_name)


async def validate_source_and_self_ref(source_repo, source_id: str, destination_channel: str) -> None:
    """Validate that source_id exists and that the rule is not self-referential.

    Raises:
        RuleSourceNotFoundException: If source_id is not in the sources collection (→ HTTP 422).
        RuleSelfReferentialException: If source equals destination (→ HTTP 422).
    """
    source = await source_repo.get_source_by_id(source_id)
    if source is None:
        raise RuleSourceNotFoundException(source_id)

    # Normalize destination for comparison (strip leading @, lowercase)
    dest = destination_channel.lstrip("@").lower()

    if source.telegram_username and source.telegram_username.lower() == dest:
        raise RuleSelfReferentialException()
    if str(source.telegram_id) == dest:
        raise RuleSelfReferentialException()


def validate_media_replacement(enabled: bool, replacement_image_path) -> None:
    """Raise if media_replacement is enabled but path is not provided."""
    if enabled and replacement_image_path is None:
        raise RuleMediaReplacementPathRequiredException()
