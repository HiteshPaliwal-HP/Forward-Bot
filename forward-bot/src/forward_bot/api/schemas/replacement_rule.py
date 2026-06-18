"""Pydantic schemas for Replacement Rule API request/response models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from forward_bot.api.schemas.base import MongoBaseModel


class ReplacementRuleCreateRequest(BaseModel):
    """Request body for POST /api/v1/rules/{rule_id}/replacement-rules."""
    search_text: str = Field(min_length=1)      # prevent empty-string records
    replacement_text: str                        # may be empty (to delete all occurrences of X)
    match_mode: Literal["literal", "regex"] = "literal"
    is_active: bool = True                       # default True per FR-7


class ReplacementRuleUpdateRequest(BaseModel):
    """Request body for PUT /api/v1/rules/{rule_id}/replacement-rules/{id}.

    Full replacement semantics — all fields are applied.

    ⚠️ NOTE: is_active defaults True (replacement rules default active).
    This differs from ForwardingRuleUpdateRequest which defaults is_active=False.
    This asymmetry is INTENTIONAL — do NOT change this default.
    """
    search_text: str = Field(min_length=1)
    replacement_text: str
    match_mode: Literal["literal", "regex"] = "literal"
    is_active: bool = True


class ReplacementRuleResponse(MongoBaseModel):
    """API response for a single Replacement Rule document.

    The `id` field is declared with `validation_alias="_id"` (from MongoBaseModel inheritance)
    and `serialization_alias="id"` so FastAPI serializes the response JSON as `{"id": ...}`.

    ⚠️ NOTE: We declare `id` here with `serialization_alias="id"` only — we do NOT add a
    `field_validator("id")` since MongoBaseModel already has `coerce_object_id`. This is safe
    in Pydantic v2 when the parent already declared the field — we're only overriding the
    serialization behavior, not re-declaring a validator.
    """
    id: str = Field(validation_alias="_id", serialization_alias="id")
    forwarding_rule_id: str
    search_text: str
    replacement_text: str
    match_mode: str
    is_active: bool
    created_at: datetime   # serialized as ISO 8601 UTC string by MongoBaseModel.serialize_dt
    updated_at: datetime
    # ⚠️ created_at and updated_at are non-Optional here. The domain entity uses
    # Optional[datetime] for flexibility, but use cases MUST always set both to
    # datetime.now(timezone.utc) before persisting. A None value here will cause
    # a Pydantic validation error at response serialization time.

    @classmethod
    def from_entity(cls, r) -> "ReplacementRuleResponse":
        return cls.model_validate({
            "_id": r.id,         # MongoBaseModel.coerce_object_id handles str→str
            "forwarding_rule_id": r.forwarding_rule_id,
            "search_text": r.search_text,
            "replacement_text": r.replacement_text,
            "match_mode": r.match_mode,
            "is_active": r.is_active,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        })


class ReplacementRulesListResponse(BaseModel):
    """List response for GET /api/v1/rules/{rule_id}/replacement-rules.

    Flat list (not paginated) — replacement rules per rule are bounded in practice.
    """
    items: list[ReplacementRuleResponse]
