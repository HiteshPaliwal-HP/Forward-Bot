"""Domain entity for Replacement Rule — a text-rewriting rule scoped to a Forwarding Rule."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ReplacementRule:
    """Domain entity for a text replacement rule scoped to a Forwarding Rule.

    Each ReplacementRule belongs to exactly one ForwardingRule (parent) and defines
    a single find-and-replace operation to be applied to forwarded message text.
    Rules are applied in pipeline order (created_at ASC — FR-7).
    """
    forwarding_rule_id: str        # Parent ForwardingRule ID stored as plain hex string
    search_text: str               # Text to search for
    replacement_text: str          # Text to replace with (supports regex backrefs when match_mode=regex)
    match_mode: str                # "literal" | "regex"

    is_active: bool = True         # Default active (per FR-7) — differs from ForwardingRule default
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
