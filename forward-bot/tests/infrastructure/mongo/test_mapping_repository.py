"""Unit tests for MappingRepository."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from datetime import datetime, timezone

from forward_bot.domain.entities.message_mapping import MessageMapping
from forward_bot.infrastructure.mongo.repositories.mapping_repository import MappingRepository


@pytest.mark.asyncio
async def test_mapping_repository_crud() -> None:
    # Mock db and collection
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = MappingRepository(mock_db)

    # 1. Test add_mapping
    mapping = MessageMapping(
        id=None,
        forwarding_rule_id="65c52c6f1f2e3d4a5b6c7d81",
        source_channel_id=12345,
        source_message_id=67890,
        destination_channel_id=54321,
        destination_message_id=98765,
        forwarded_at=datetime.now(timezone.utc),
    )

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
    mock_collection.insert_one.return_value = mock_insert_result

    inserted_id = await repo.add_mapping(mapping)
    assert inserted_id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert mapping.id == "65c52c6f1f2e3d4a5b6c7d8e"
    mock_collection.insert_one.assert_called_once()

    called_doc = mock_collection.insert_one.call_args[0][0]
    assert called_doc["forwarding_rule_id"] == ObjectId("65c52c6f1f2e3d4a5b6c7d81")
    assert called_doc["source_channel_id"] == 12345
    assert called_doc["source_message_id"] == 67890
    assert called_doc["destination_channel_id"] == 54321
    assert called_doc["destination_message_id"] == 98765

    # 2. Test get_by_source_message
    mock_doc = {
        "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
        "forwarding_rule_id": ObjectId("65c52c6f1f2e3d4a5b6c7d81"),
        "source_channel_id": 12345,
        "source_message_id": 67890,
        "destination_channel_id": 54321,
        "destination_message_id": 98765,
        "forwarded_at": datetime.now(timezone.utc),
    }
    mock_collection.find_one.return_value = mock_doc

    fetched = await repo.get_by_source_message(
        source_channel_id=12345,
        source_message_id=67890,
        forwarding_rule_id="65c52c6f1f2e3d4a5b6c7d81",
    )
    assert fetched is not None
    assert fetched.id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert fetched.forwarding_rule_id == "65c52c6f1f2e3d4a5b6c7d81"
    assert fetched.source_channel_id == 12345
    assert fetched.source_message_id == 67890
    mock_collection.find_one.assert_called_with({
        "source_channel_id": 12345,
        "source_message_id": 67890,
        "forwarding_rule_id": ObjectId("65c52c6f1f2e3d4a5b6c7d81"),
    })

    # Test with invalid forwarding_rule_id format
    mock_collection.find_one.reset_mock()
    fetched_invalid = await repo.get_by_source_message(
        source_channel_id=12345,
        source_message_id=67890,
        forwarding_rule_id="invalid-id-format",
    )
    assert fetched_invalid is None
    mock_collection.find_one.assert_not_called()
