"""Unit tests for SamplingRepository."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId

from forward_bot.infrastructure.mongo.repositories.sampling_repository import SamplingRepository


@pytest.mark.asyncio
async def test_sampling_repository_get_counter() -> None:
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = SamplingRepository(mock_db)

    rule_id = "65c52c6f1f2e3d4a5b6c7d81"
    query_id = ObjectId(rule_id)

    # Case A: Document doesn't exist
    mock_collection.find_one.return_value = None
    count = await repo.get_counter(rule_id)
    assert count == 0
    mock_collection.find_one.assert_called_with({"_id": query_id})

    # Case B: Document exists
    mock_collection.find_one.return_value = {"_id": query_id, "counter": 42}
    count = await repo.get_counter(rule_id)
    assert count == 42


@pytest.mark.asyncio
async def test_sampling_repository_increment_counter() -> None:
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = SamplingRepository(mock_db)

    rule_id = "65c52c6f1f2e3d4a5b6c7d81"
    query_id = ObjectId(rule_id)

    # Case A: Increment document when database update is successful
    mock_collection.find_one_and_update.return_value = {"_id": query_id, "counter": 5}
    count = await repo.increment_counter(rule_id)
    assert count == 5
    mock_collection.find_one_and_update.assert_called_once()
    
    # Verify exact arguments passed to find_one_and_update
    called_args = mock_collection.find_one_and_update.call_args[0]
    called_kwargs = mock_collection.find_one_and_update.call_args[1]
    assert called_args[0] == {"_id": query_id}
    assert called_args[1] == {"$inc": {"counter": 1}}
    assert called_kwargs.get("upsert") is True

    # Case B: If update returns None (unlikely fallback but handled)
    mock_collection.find_one_and_update.return_value = None
    count = await repo.increment_counter(rule_id)
    assert count == 1
