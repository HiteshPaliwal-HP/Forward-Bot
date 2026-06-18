"""Pydantic schemas for the Forwarding Rule API endpoints."""
from datetime import datetime
from typing import Any, Literal, Optional
from bson import ObjectId
from pydantic import BaseModel, Field, field_validator

from forward_bot.api.schemas.base import MongoBaseModel


# ---------------------------------------------------------------------------
# Sub-config schemas (request + response)
# ---------------------------------------------------------------------------

class SamplingConfigSchema(BaseModel):
    """1-in-N message sampling configuration."""
    n: int = Field(default=1, ge=1)


class TimeWindowConfigSchema(BaseModel):
    """Time window restriction for rule activation."""
    timezone: str
    days_of_week: list[Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]]
    start_time: str  # "HH:MM"
    end_time: str    # "HH:MM" — may be < start_time for cross-midnight windows (FR-32)


class AttributionConfigSchema(BaseModel):
    """Source attribution footer/header configuration."""
    enabled: bool = False
    position: Literal["prefix", "suffix"] = "prefix"
    format: str = "From {source_name}"


class AutoReplaceSourceRefsConfigSchema(BaseModel):
    """Auto-replace source channel references in message text."""
    enabled: bool = False
    replacement: Optional[str] = None
    replace_display_name: bool = False


class MediaReplacementConfigSchema(BaseModel):
    """Replace forwarded media with a static image."""
    enabled: bool = False
    replacement_image_path: Optional[str] = None
    replacement_caption_mode: Literal["use_replacement", "use_source", "none"] = "use_source"


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ForwardingRuleCreateRequest(BaseModel):
    """Request body for POST /api/v1/rules — create a new forwarding rule."""
    # Required fields
    source_id: str = Field(min_length=1)           # ObjectId hex; validated in use case
    destination_channel: str = Field(min_length=1)  # Telegram username or numeric string

    # Core toggle — defaults to inactive per AC1
    is_active: bool = False

    # Keyword filtering
    keyword_match_mode: Literal["literal", "regex"] = "literal"
    block_keywords: list[str] = Field(default_factory=list)
    allow_keywords: list[str] = Field(default_factory=list)

    # Media type filter
    media_type_filter: list[str] = Field(default_factory=lambda: ["text", "photo"])

    # Text transforms
    remove_links: bool = False
    remove_hashtags: bool = False
    remove_mentions: bool = False

    # Media handling
    forward_media: Literal["forward", "ignore", "caption_only"] = "forward"

    # Sub-configs
    sampling: SamplingConfigSchema = Field(default_factory=SamplingConfigSchema)
    time_window: Optional[TimeWindowConfigSchema] = None
    attribution: AttributionConfigSchema = Field(default_factory=AttributionConfigSchema)
    auto_replace_source_refs: AutoReplaceSourceRefsConfigSchema = Field(
        default_factory=AutoReplaceSourceRefsConfigSchema
    )
    media_replacement: MediaReplacementConfigSchema = Field(
        default_factory=MediaReplacementConfigSchema
    )


class ForwardingRuleUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/rules/{id} — full replacement update."""
    # Required fields (same as create)
    source_id: str = Field(min_length=1)
    destination_channel: str = Field(min_length=1)

    # All optional fields with defaults (full replacement semantics)
    is_active: bool = False
    keyword_match_mode: Literal["literal", "regex"] = "literal"
    block_keywords: list[str] = Field(default_factory=list)
    allow_keywords: list[str] = Field(default_factory=list)
    media_type_filter: list[str] = Field(default_factory=lambda: ["text", "photo"])
    remove_links: bool = False
    remove_hashtags: bool = False
    remove_mentions: bool = False
    forward_media: Literal["forward", "ignore", "caption_only"] = "forward"
    sampling: SamplingConfigSchema = Field(default_factory=SamplingConfigSchema)
    time_window: Optional[TimeWindowConfigSchema] = None
    attribution: AttributionConfigSchema = Field(default_factory=AttributionConfigSchema)
    auto_replace_source_refs: AutoReplaceSourceRefsConfigSchema = Field(
        default_factory=AutoReplaceSourceRefsConfigSchema
    )
    media_replacement: MediaReplacementConfigSchema = Field(
        default_factory=MediaReplacementConfigSchema
    )


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ForwardingRuleResponse(MongoBaseModel):
    """API response schema for a single Forwarding Rule document."""
    id: str = Field(validation_alias="_id", serialization_alias="id")
    # source_id is stored as BSON ObjectId in MongoDB — coerce to str on read
    source_id: str
    destination_channel: str
    is_active: bool
    keyword_match_mode: str
    block_keywords: list[str]
    allow_keywords: list[str]
    media_type_filter: list[str]
    remove_links: bool
    remove_hashtags: bool
    remove_mentions: bool
    forward_media: str
    sampling: SamplingConfigSchema
    time_window: Optional[TimeWindowConfigSchema] = None
    attribution: AttributionConfigSchema
    auto_replace_source_refs: AutoReplaceSourceRefsConfigSchema
    media_replacement: MediaReplacementConfigSchema
    created_at: datetime  # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
    updated_at: datetime  # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt

    @field_validator("source_id", mode="before")
    @classmethod
    def coerce_source_id(cls, v: Any) -> str:
        """Coerce BSON ObjectId to hex string (mirrors MongoBaseModel.coerce_object_id)."""
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)

    @classmethod
    def from_entity(cls, rule) -> "ForwardingRuleResponse":
        """Build response from a ForwardingRule domain entity."""
        return cls.model_validate({
            "_id": rule.id,
            "source_id": rule.source_id,
            "destination_channel": rule.destination_channel,
            "is_active": rule.is_active,
            "keyword_match_mode": rule.keyword_match_mode,
            "block_keywords": rule.block_keywords,
            "allow_keywords": rule.allow_keywords,
            "media_type_filter": rule.media_type_filter,
            "remove_links": rule.remove_links,
            "remove_hashtags": rule.remove_hashtags,
            "remove_mentions": rule.remove_mentions,
            "forward_media": rule.forward_media,
            "sampling": {"n": rule.sampling.n},
            "time_window": (
                {
                    "timezone": rule.time_window.timezone,
                    "days_of_week": rule.time_window.days_of_week,
                    "start_time": rule.time_window.start_time,
                    "end_time": rule.time_window.end_time,
                }
                if rule.time_window
                else None
            ),
            "attribution": {
                "enabled": rule.attribution.enabled,
                "position": rule.attribution.position,
                "format": rule.attribution.format,
            },
            "auto_replace_source_refs": {
                "enabled": rule.auto_replace_source_refs.enabled,
                "replacement": rule.auto_replace_source_refs.replacement,
                "replace_display_name": rule.auto_replace_source_refs.replace_display_name,
            },
            "media_replacement": {
                "enabled": rule.media_replacement.enabled,
                "replacement_image_path": rule.media_replacement.replacement_image_path,
                "replacement_caption_mode": rule.media_replacement.replacement_caption_mode,
            },
            "created_at": rule.created_at,
            "updated_at": rule.updated_at,
        })


class ForwardingRulesPagedResponse(BaseModel):
    """Paginated list response for GET /api/v1/rules."""
    items: list[ForwardingRuleResponse]
    total: int
    page: int
    page_size: int
