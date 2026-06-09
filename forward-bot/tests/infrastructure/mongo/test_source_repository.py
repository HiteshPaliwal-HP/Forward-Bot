"""Unit tests for the SourceRepository."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from datetime import datetime, timezone

from forward_bot.domain.entities.source import Source
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository


@pytest.mark.asyncio
async def test_source_repository_crud():
    """Verify that all basic CRUD methods of SourceRepository behave correctly."""
    # Mock db and collection
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = SourceRepository(mock_db)

    # 1. Verify mapping and insertion
    source = Source(
        id=None,
        telegram_id=987654,
        telegram_username="my_channel",
        display_name="My Channel",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
    mock_collection.insert_one.return_value = mock_insert_result

    inserted_id = await repo.add_source(source)
    assert inserted_id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert source.id == "65c52c6f1f2e3d4a5b6c7d8e"
    mock_collection.insert_one.assert_called_once()

    # Verify document values passed to insert_one
    called_doc = mock_collection.insert_one.call_args[0][0]
    assert called_doc["telegram_id"] == 987654
    assert called_doc["telegram_username"] == "my_channel"
    assert called_doc["display_name"] == "My Channel"
    assert called_doc["type"] == "channel"
    assert called_doc["folder_id"] is None

    # 2. Verify retrieval by ID
    mock_doc = {
        "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
        "telegram_id": 987654,
        "telegram_username": "my_channel",
        "display_name": "My Channel",
        "type": "channel",
        "folder_id": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mock_collection.find_one.return_value = mock_doc

    fetched = await repo.get_source_by_id("65c52c6f1f2e3d4a5b6c7d8e")
    assert fetched is not None
    assert fetched.id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert fetched.telegram_id == 987654
    assert fetched.telegram_username == "my_channel"

    # 3. Verify retrieval by telegram_id
    mock_collection.find_one.reset_mock()
    fetched = await repo.get_source_by_telegram_id(987654)
    assert fetched is not None
    mock_collection.find_one.assert_called_with({"telegram_id": 987654})

    # 4. Verify username resolution trims "@"
    mock_collection.find_one.reset_mock()
    fetched = await repo.get_source_by_username("@my_channel")
    assert fetched is not None
    mock_collection.find_one.assert_called_with({"telegram_username": "my_channel"})

    # 5. Verify deletion
    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 1
    mock_collection.delete_one.return_value = mock_delete_result

    deleted = await repo.delete_source("65c52c6f1f2e3d4a5b6c7d8e")
    assert deleted is True
    mock_collection.delete_one.assert_called_with({"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")})


@pytest.mark.asyncio
async def test_get_referencing_rules_count():
    """Verify rules lookup query for checking source usage."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = SourceRepository(mock_db)

    mock_collection.count_documents.return_value = 3
    count = await repo.get_referencing_rules_count("65c52c6f1f2e3d4a5b6c7d8e")

    assert count == 3
    mock_db.__getitem__.assert_called_with("forwarding_rules")
    mock_collection.count_documents.assert_called_once_with({"source_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")})


@pytest.mark.asyncio
async def test_source_repository_extended():
    """Verify list_sources, update_source, and folder_exists methods of SourceRepository."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    
    # Configure mock_db so that accessing collections returns correct mocks
    collections = {
        "sources": mock_collection,
        "source_folders": AsyncMock()
    }
    mock_db.__getitem__.side_effect = lambda name: collections[name]

    repo = SourceRepository(mock_db)

    # 1. Test folder_exists
    folder_mock = collections["source_folders"]
    folder_mock.find_one.return_value = {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"), "name": "Test Folder"}
    exists = await repo.folder_exists("65c52c6f1f2e3d4a5b6c7d8e")
    assert exists is True
    folder_mock.find_one.assert_called_with({"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")})

    exists_invalid = await repo.folder_exists("invalid-id")
    assert exists_invalid is False

    folder_mock.find_one.return_value = None
    exists_none = await repo.folder_exists("65c52c6f1f2e3d4a5b6c7d8e")
    assert exists_none is False

    # 2. Test update_source
    source = Source(
        id="65c52c6f1f2e3d4a5b6c7d8e",
        telegram_id=987654,
        telegram_username="my_channel",
        display_name="Updated Name",
        type="channel",
        folder_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    mock_replace_result = MagicMock()
    mock_replace_result.modified_count = 1
    mock_collection.replace_one.return_value = mock_replace_result
    
    updated = await repo.update_source(source)
    assert updated is True
    mock_collection.replace_one.assert_called_once()

    # 3. Test list_sources
    mock_collection.count_documents.return_value = 1
    
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    
    # Mock to_list on cursor
    mock_doc = {
        "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
        "telegram_id": 987654,
        "telegram_username": "my_channel",
        "display_name": "My Channel",
        "type": "channel",
        "folder_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8a"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    # Call list_sources with pagination and filters
    items, total = await repo.list_sources(
        filter_type="channel",
        folder_id="65c52c6f1f2e3d4a5b6c7d8a",
        page=2,
        page_size=10
    )
    assert total == 1
    assert len(items) == 1
    assert items[0].id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert items[0].folder_id == "65c52c6f1f2e3d4a5b6c7d8a"

    # Verify query generated
    mock_collection.find.assert_called_with({
        "type": "channel",
        "folder_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8a")
    })
    mock_cursor.sort.assert_called_with("created_at", -1)
    mock_cursor.skip.assert_called_with(10)
    mock_cursor.limit.assert_called_with(10)

