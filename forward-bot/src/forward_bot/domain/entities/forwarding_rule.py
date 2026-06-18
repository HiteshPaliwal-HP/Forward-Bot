"""Domain entity for a Forwarding Rule."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class TimeWindowConfig:
    """Time-window restriction for when a rule is active."""
    timezone: str
    days_of_week: list[str]  # e.g. ["MON","TUE","WED"]
    start_time: str           # "HH:MM"
    end_time: str             # "HH:MM" — may be < start_time for cross-midnight windows


@dataclass
class SamplingConfig:
    """Deterministic 1-in-N message sampling."""
    n: int = 1


@dataclass
class AttributionConfig:
    """Append/prepend a source attribution footer/header."""
    enabled: bool = False
    position: str = "prefix"               # "prefix" | "suffix"
    format: str = "From {source_name}"


@dataclass
class AutoReplaceSourceRefsConfig:
    """Auto-replace references to the source channel inside message text."""
    enabled: bool = False
    replacement: Optional[str] = None
    replace_display_name: bool = False


@dataclass
class MediaReplacementConfig:
    """Replace the forwarded media with a static image."""
    enabled: bool = False
    replacement_image_path: Optional[str] = None
    replacement_caption_mode: str = "use_source"  # "use_replacement" | "use_source" | "none"


@dataclass
class ForwardingRule:
    """Core domain entity representing a forwarding rule configuration."""
    source_id: str                              # ObjectId hex string (stored as BSON ObjectId)
    destination_channel: str                   # Telegram username or numeric ID string

    # Core toggle
    is_active: bool = False

    # Keyword filtering
    keyword_match_mode: str = "literal"        # "literal" | "regex"
    block_keywords: list[str] = field(default_factory=list)
    allow_keywords: list[str] = field(default_factory=list)

    # Media type filter
    media_type_filter: list[str] = field(default_factory=lambda: ["text", "photo"])

    # Text transform toggles
    remove_links: bool = False
    remove_hashtags: bool = False
    remove_mentions: bool = False

    # Media handling
    forward_media: str = "forward"             # "forward" | "ignore" | "caption_only"

    # Sub-configs
    sampling: SamplingConfig = field(default_factory=SamplingConfig)
    time_window: Optional[TimeWindowConfig] = None
    attribution: AttributionConfig = field(default_factory=AttributionConfig)
    auto_replace_source_refs: AutoReplaceSourceRefsConfig = field(
        default_factory=AutoReplaceSourceRefsConfig
    )
    media_replacement: MediaReplacementConfig = field(default_factory=MediaReplacementConfig)

    # Timestamps and identity
    id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
