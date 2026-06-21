"""Unit tests for the FolderRepository."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from datetime import datetime, timezone

from forward_bot.domain.entities.source_folder import SourceFolder
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository


@pytest.mark.asyncio
async def test_folder_repository_crud():
    """Verify that all basic CRUD methods of FolderRepository behave correctly."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()

    # Configure mock_db
    collections = {
        "source_folders": mock_collection,
        "sources": AsyncMock()
    }
    mock_db.__getitem__.side_effect = lambda name: collections[name]

    repo = FolderRepository(mock_db)

    # 1. Verify mapping and insertion
    folder = SourceFolder(
        id=None,
        name="Crypto Alerts",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
    mock_collection.insert_one.return_value = mock_insert_result

    inserted_id = await repo.add_folder(folder)
    assert inserted_id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert folder.id == "65c52c6f1f2e3d4a5b6c7d8e"
    mock_collection.insert_one.assert_called_once()

    # Verify document values passed to insert_one
    called_doc = mock_collection.insert_one.call_args[0][0]
    assert called_doc["name"] == "Crypto Alerts"

    # 2. Verify retrieval by ID
    mock_doc = {
        "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
        "name": "Crypto Alerts",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    mock_collection.find_one.return_value = mock_doc

    fetched = await repo.get_folder_by_id("65c52c6f1f2e3d4a5b6c7d8e")
    assert fetched is not None
    assert fetched.id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert fetched.name == "Crypto Alerts"

    # 3. Verify retrieval by name (case-insensitive)
    mock_collection.find_one.reset_mock()
    fetched = await repo.get_folder_by_name("crypto alerts")
    assert fetched is not None
    mock_collection.find_one.assert_called_with({"name": {"$regex": "^crypto\\ alerts$", "$options": "i"}})

    # 4. Verify retrieval by name excluding ID
    mock_collection.find_one.reset_mock()
    fetched = await repo.get_folder_by_name("crypto alerts", exclude_id="65c52c6f1f2e3d4a5b6c7d8e")
    assert fetched is not None
    mock_collection.find_one.assert_called_with({
        "name": {"$regex": "^crypto\\ alerts$", "$options": "i"},
        "_id": {"$ne": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")}
    })

    # 5. Verify update_folder
    mock_replace_result = MagicMock()
    mock_replace_result.modified_count = 1
    mock_collection.replace_one.return_value = mock_replace_result

    updated = await repo.update_folder(folder)
    assert updated is True
    mock_collection.replace_one.assert_called_once()

    # 6. Verify delete_folder with sources disassociation
    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 1
    mock_collection.delete_one.return_value = mock_delete_result

    sources_mock = collections["sources"]
    sources_mock.update_many.return_value = MagicMock(modified_count=2)

    deleted = await repo.delete_folder("65c52c6f1f2e3d4a5b6c7d8e")
    assert deleted is True
    mock_collection.delete_one.assert_called_with({"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")})
    sources_mock.update_many.assert_called_once_with(
        {"folder_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e")},
        {"$set": {"folder_id": None}}
    )


@pytest.mark.asyncio
async def test_list_folders_with_source_count():
    """Verify aggregation pipeline queries in list_folders_with_source_count."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()

    # Configure mock_db
    collections = {
        "source_folders": mock_collection,
        "sources": AsyncMock()
    }
    mock_db.__getitem__.side_effect = lambda name: collections[name]

    repo = FolderRepository(mock_db)

    # Aggregation return mock
    mock_agg_result = [
        {
            "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
            "name": "Crypto Alerts",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "source_count": 5
        }
    ]
    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_agg_result)
    mock_collection.aggregate = MagicMock(return_value=mock_cursor)

    # List all
    results = await repo.list_folders_with_source_count()
    assert len(results) == 1
    assert results[0]["id"] == "65c52c6f1f2e3d4a5b6c7d8e"
    assert results[0]["source_count"] == 5

    # Check aggregate pipeline called
    pipeline = mock_collection.aggregate.call_args[0][0]
    # Check lookup is in pipeline
    assert any("$lookup" in step for step in pipeline)
    assert any("$project" in step for step in pipeline)
    assert any("$sort" in step for step in pipeline)

    # List with filter
    mock_collection.aggregate.reset_mock()
    results_filtered = await repo.list_folders_with_source_count("crypto")
    pipeline_filtered = mock_collection.aggregate.call_args[0][0]
    assert any("$match" in step for step in pipeline_filtered)


# ---------------------------------------------------------------------------
# list_folders — Story 3.3 addition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_folders_returns_all_folders():
    """list_folders() fetches all SourceFolders with no filtering (Story 3.3)."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    now = datetime.now(timezone.utc)
    mock_docs = [
        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"), "name": "Folder A",
         "created_at": now, "updated_at": now},
        {"_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8f"), "name": "Folder B",
         "created_at": now, "updated_at": now},
    ]

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=mock_docs)
    mock_collection.find = MagicMock(return_value=mock_cursor)

    repo = FolderRepository(mock_db)
    folders = await repo.list_folders()

    assert len(folders) == 2
    assert all(isinstance(f, SourceFolder) for f in folders)
    names = {f.name for f in folders}
    assert names == {"Folder A", "Folder B"}


@pytest.mark.asyncio
async def test_list_folders_called_with_empty_filter():
    """list_folders() queries the collection with an empty filter ({})."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    repo = FolderRepository(mock_db)
    await repo.list_folders()

    mock_collection.find.assert_called_once_with({})


@pytest.mark.asyncio
async def test_list_folders_empty_collection():
    """list_folders() returns an empty list when the collection is empty."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    repo = FolderRepository(mock_db)
    folders = await repo.list_folders()

    assert folders == []


@pytest.mark.asyncio
async def test_list_folders_maps_to_domain_entity():
    """list_folders() correctly maps MongoDB documents to SourceFolder entities."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    oid = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
    now = datetime.now(timezone.utc)
    mock_doc = {"_id": oid, "name": "My Folder", "created_at": now, "updated_at": now}

    mock_cursor = MagicMock()
    mock_cursor.to_list = AsyncMock(return_value=[mock_doc])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    repo = FolderRepository(mock_db)
    folders = await repo.list_folders()

    assert len(folders) == 1
    folder = folders[0]
    assert folder.id == str(oid)
    assert folder.name == "My Folder"
    assert folder.created_at == now
    assert folder.updated_at == now

