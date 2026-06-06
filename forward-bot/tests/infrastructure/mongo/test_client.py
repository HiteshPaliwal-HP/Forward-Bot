import pytest
from datetime import datetime, timezone
from bson import ObjectId
from unittest.mock import MagicMock, patch

from forward_bot.config import Settings
from forward_bot.infrastructure.mongo.client import MongoClientHolder
from forward_bot.api.schemas.base import MongoBaseModel, FORWARDING_RULES


class MockMongoModel(MongoBaseModel):
    """Mock schema that inherits from MongoBaseModel."""
    created_at: datetime
    updated_at: datetime


def test_mongo_base_model_serialization():
    """Test MongoBaseModel serializes ObjectId and Datetime properly."""
    obj_id = ObjectId("507f1f77bcf86cd799439011")
    created = datetime(2026, 6, 6, 12, 0, 0, tzinfo=timezone.utc)
    updated = datetime(2026, 6, 6, 13, 15, 30, tzinfo=timezone.utc)

    # Initialize model using alias _id
    model = MockMongoModel(
        _id=obj_id,
        created_at=created,
        updated_at=updated
    )

    # Verify attributes
    assert model.id == "507f1f77bcf86cd799439011"
    assert model.created_at == created
    assert model.updated_at == updated

    # Verify serialization dump
    serialized = model.model_dump(mode="json")
    assert serialized["id"] == "507f1f77bcf86cd799439011"
    assert serialized["created_at"] == "2026-06-06T12:00:00Z"
    assert serialized["updated_at"] == "2026-06-06T13:15:30Z"


@pytest.mark.asyncio
async def test_mongo_client_db_name_parsing():
    """Test that MongoClientHolder parses the database name correctly from URI."""
    holder = MongoClientHolder()

    # Define various settings mocks
    settings_simple = Settings(
        api_key="api",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/custom_db_name"
    )
    
    settings_with_options = Settings(
        api_key="api",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/db_with_options?replicaSet=rs0&authSource=admin"
    )

    settings_no_db = Settings(
        api_key="api",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/"
    )

    # Mock AsyncIOMotorClient to prevent actual connection attempt
    with patch("forward_bot.infrastructure.mongo.client.AsyncIOMotorClient") as mock_motor:
        # 1. Simple db name parsing
        mock_client = MagicMock()
        mock_motor.return_value = mock_client
        
        await holder.connect(settings_simple)
        mock_motor.assert_called_with(settings_simple.mongo_uri)
        assert holder.db == mock_client["custom_db_name"]
        
        # 2. Options parsing
        await holder.connect(settings_with_options)
        assert holder.db == mock_client["db_with_options"]
        
        # 3. Fallback when no database name is specified
        await holder.connect(settings_no_db)
        assert holder.db == mock_client["forward_bot"]

        # Test close
        holder.close()
        assert holder.client is None
        assert holder.db is None
