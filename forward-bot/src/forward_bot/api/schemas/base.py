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
    
    Converts MongoDB _id to string id, serializes ObjectIds,
    and formats datetimes as ISO 8601 UTC strings with Z suffix.
    """
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
    )

    id: str = Field(alias="_id")

    @field_validator("id", mode="before")
    @classmethod
    def coerce_object_id(cls, v: Any) -> str:
        """Coerce ObjectId to string."""
        if isinstance(v, ObjectId):
            return str(v)
        return str(v)

    @field_serializer("created_at", "updated_at", "forwarded_at", check_fields=False)
    def serialize_dt(self, dt: datetime) -> str:
        """Format datetime as ISO 8601 UTC string with Z suffix."""
        if isinstance(dt, datetime):
            return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        return dt
