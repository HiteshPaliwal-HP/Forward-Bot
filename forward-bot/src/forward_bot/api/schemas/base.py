"""Base schemas and MongoDB constants for API models."""
from datetime import datetime
from typing import Any
from bson import ObjectId
from pydantic import BaseModel, ConfigDict, Field, field_validator, field_serializer

# MongoDB Collection Names as constants
FORWARDING_RULES = "forwarding_rules"
REPLACEMENT_RULES = "replacement_rules"
MESSAGE_MAPPINGS = "message_mappings"
SOURCES = "sources"
SOURCE_FOLDERS = "source_folders"
SAMPLING_COUNTERS = "sampling_counters"


class MongoBaseModel(BaseModel):
    """Base model for MongoDB documents returned by the API.

    Converts MongoDB ``_id`` to a string ``id`` field, coerces BSON ObjectIds,
    and serializes datetimes as ISO 8601 UTC strings with a ``Z`` suffix.

    ── _id / id contract ────────────────────────────────────────────────────
    MongoDB stores the primary key as ``_id`` (BSON ObjectId).  The API must
    expose it as ``"id"`` (plain string) in JSON responses.  This base class
    handles the mapping via ``Field(alias="_id")``.

    SUBCLASS RULES — read before creating a new response schema:

    Pattern A — no extra field_validator needed on the subclass
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Use when the subclass does NOT need to validate any other field
    (e.g. ReplacementRuleResponse, SourceFolderResponse)::

        class MyResponse(MongoBaseModel):
            # Redeclare only the aliases — never re-add a @field_validator("id").
            id: str = Field(validation_alias="_id", serialization_alias="id")
            other_field: str

        @classmethod
        def from_entity(cls, e) -> "MyResponse":
            # Always pass "_id" (not "id") as the key to model_validate.
            return cls.model_validate({"_id": e.id, "other_field": e.x})

    Pattern B — subclass also needs a field_validator on another BSON field
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Use when another field is stored as ObjectId in MongoDB (e.g. source_id
    in ForwardingRuleResponse)::

        class MyResponse(MongoBaseModel):
            id: str = Field(validation_alias="_id", serialization_alias="id")
            foreign_id: str  # stored as ObjectId in Mongo

            @field_validator("foreign_id", mode="before")
            @classmethod
            def coerce_foreign_id(cls, v: Any) -> str:
                return str(v)

            @classmethod
            def from_entity(cls, e) -> "MyResponse":
                return cls.model_validate({"_id": e.id, "foreign_id": e.foreign_id})

    Common mistakes to avoid
    ~~~~~~~~~~~~~~~~~~~~~~~~
    - Do NOT add ``@field_validator("id")`` in a subclass — MongoBaseModel
      already has ``coerce_object_id``.  Pydantic v2 raises a duplicate-validator
      error at import time.
    - Do NOT pass ``"id": e.id`` to ``model_validate`` — always use ``"_id"``
      so the alias chain resolves correctly.
    - Do NOT use ``Field(alias="_id")`` alone and expect ``"id"`` in the JSON
      output — you also need ``serialization_alias="id"`` on the subclass field,
      because ``alias`` controls parsing only.
    ─────────────────────────────────────────────────────────────────────────
    """
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> str:
        """Coerce BSON ObjectId to hex string. Safe to call on a plain string."""
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)

    @field_serializer("created_at", "updated_at", "forwarded_at", check_fields=False)
    def serialize_dt(self, dt: datetime) -> str:
        """Format datetime as ISO 8601 UTC string with Z suffix."""
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return dt
