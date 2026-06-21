"""Unit tests for the ReplacementRuleRepository.

Covers CRUD operations, entity/document mapping, string-based forwarding_rule_id storage,
and the list_replacements_for_rule ordering query.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from datetime import datetime, timezone

from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
RULE_OID = "65c52c6f1f2e3d4a5b6c7d8e"
PARENT_OID = "65c52c6f1f2e3d4a5b6c7d8a"
REPLACEMENT_OID = "65c52c6f1f2e3d4a5b6c0001"


def make_replacement(**kwargs) -> ReplacementRule:
    """Build a minimal ReplacementRule entity for testing."""
    defaults = dict(
        forwarding_rule_id=PARENT_OID,
        search_text="competitor",
        replacement_text="our brand",
        match_mode="literal",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(kwargs)
    return ReplacementRule(**defaults)


def make_mongo_doc(**kwargs) -> dict:
    """Build a minimal replacement_rules MongoDB document dict for testing."""
    defaults = {
        "_id": ObjectId(REPLACEMENT_OID),
        "forwarding_rule_id": PARENT_OID,      # stored as plain string
        "search_text": "competitor",
        "replacement_text": "our brand",
        "match_mode": "literal",
        "is_active": True,
        "created_at": NOW,
        "updated_at": NOW,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests: add_replacement / get_replacement_by_id
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_replacement_sets_id_and_returns_string():
    """Verify add_replacement inserts and sets entity.id to the inserted ObjectId string."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId(REPLACEMENT_OID)
    mock_collection.insert_one.return_value = mock_insert_result

    replacement = make_replacement()
    inserted_id = await repo.add_replacement(replacement)

    assert inserted_id == REPLACEMENT_OID
    assert replacement.id == REPLACEMENT_OID
    mock_collection.insert_one.assert_called_once()


@pytest.mark.asyncio
async def test_add_replacement_stores_forwarding_rule_id_as_string():
    """CRITICAL: forwarding_rule_id must be stored as plain string, not BSON ObjectId."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId(REPLACEMENT_OID)
    mock_collection.insert_one.return_value = mock_insert_result

    replacement = make_replacement()
    await repo.add_replacement(replacement)

    called_doc = mock_collection.insert_one.call_args[0][0]
    assert isinstance(called_doc["forwarding_rule_id"], str), \
        "forwarding_rule_id MUST be stored as plain string — not BSON ObjectId"
    assert called_doc["forwarding_rule_id"] == PARENT_OID


@pytest.mark.asyncio
async def test_get_replacement_by_id_returns_entity():
    """Verify get_replacement_by_id maps MongoDB document to ReplacementRule entity."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)
    mock_collection.find_one.return_value = make_mongo_doc()

    result = await repo.get_replacement_by_id(REPLACEMENT_OID)

    assert result is not None
    assert result.id == REPLACEMENT_OID
    assert result.forwarding_rule_id == PARENT_OID   # back to string in entity
    assert result.search_text == "competitor"
    assert result.replacement_text == "our brand"
    assert result.match_mode == "literal"
    assert result.is_active is True
    assert result.created_at == NOW
    assert result.updated_at == NOW


@pytest.mark.asyncio
async def test_get_replacement_by_id_returns_none_for_missing():
    """Verify get_replacement_by_id returns None when document is not found."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)
    mock_collection.find_one.return_value = None

    result = await repo.get_replacement_by_id(REPLACEMENT_OID)
    assert result is None


@pytest.mark.asyncio
async def test_get_replacement_by_id_returns_none_for_invalid_id():
    """Verify None is returned for invalid ObjectId without touching the database."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    result = await repo.get_replacement_by_id("not-a-valid-id")
    assert result is None
    mock_collection.find_one.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: update_replacement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_replacement_returns_true_when_modified():
    """Verify update_replacement returns True when document is modified."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_replace_result = MagicMock()
    mock_replace_result.modified_count = 1
    mock_collection.replace_one.return_value = mock_replace_result

    replacement = make_replacement(id=REPLACEMENT_OID)
    result = await repo.update_replacement(REPLACEMENT_OID, replacement)

    assert result is True
    mock_collection.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_update_replacement_returns_false_when_not_found():
    """Verify update_replacement returns False when modified_count=0."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_replace_result = MagicMock()
    mock_replace_result.modified_count = 0
    mock_collection.replace_one.return_value = mock_replace_result

    replacement = make_replacement(id=REPLACEMENT_OID)
    result = await repo.update_replacement(REPLACEMENT_OID, replacement)

    assert result is False


@pytest.mark.asyncio
async def test_update_replacement_invalid_id_returns_false():
    """Verify update_replacement returns False for invalid ObjectId without touching DB."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    replacement = make_replacement()
    result = await repo.update_replacement("invalid-id", replacement)

    assert result is False
    mock_collection.replace_one.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: delete_replacement
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_replacement_returns_true_when_deleted():
    """Verify delete_replacement returns True when document is deleted."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 1
    mock_collection.delete_one.return_value = mock_delete_result

    result = await repo.delete_replacement(REPLACEMENT_OID)
    assert result is True


@pytest.mark.asyncio
async def test_delete_replacement_returns_false_when_not_found():
    """Verify delete_replacement returns False when deleted_count=0."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 0
    mock_collection.delete_one.return_value = mock_delete_result

    result = await repo.delete_replacement(REPLACEMENT_OID)
    assert result is False


@pytest.mark.asyncio
async def test_delete_replacement_invalid_id_returns_false():
    """Verify delete_replacement returns False for invalid ObjectId without touching DB."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    result = await repo.delete_replacement("not-a-valid-oid")
    assert result is False
    mock_collection.delete_one.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: list_replacements_for_rule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_replacements_for_rule_returns_ordered_entities():
    """Verify list_replacements_for_rule queries with string forwarding_rule_id and sorts ASC."""
    mock_db = MagicMock()
    mock_collection = MagicMock()  # NOTE: find() returns cursor synchronously
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    now1 = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    now2 = datetime(2026, 6, 17, 13, 0, 0, tzinfo=timezone.utc)

    doc1 = make_mongo_doc(_id=ObjectId(REPLACEMENT_OID), created_at=now1)
    doc2 = make_mongo_doc(
        _id=ObjectId("65c52c6f1f2e3d4a5b6c0002"),
        search_text="rival",
        replacement_text="us",
        created_at=now2,
    )

    # Motor mock pattern (from Epic 2 retrospective):
    # collection.find() returns cursor synchronously (MagicMock),
    # cursor.sort() also returns synchronously, cursor.to_list() is async.
    mock_cursor = MagicMock()
    mock_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[doc1, doc2])

    results = await repo.list_replacements_for_rule(PARENT_OID)

    assert len(results) == 2
    assert results[0].id == REPLACEMENT_OID
    assert results[0].search_text == "competitor"
    assert results[1].search_text == "rival"

    # Verify query uses string comparison (not ObjectId)
    mock_collection.find.assert_called_once_with({"forwarding_rule_id": PARENT_OID})
    mock_cursor.sort.assert_called_once_with([("created_at", 1), ("_id", 1)])   # ASC with secondary sort


@pytest.mark.asyncio
async def test_list_replacements_for_rule_returns_empty_list():
    """Verify list_replacements_for_rule returns [] when no replacement rules exist."""
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_cursor = MagicMock()
    mock_collection.find.return_value = mock_cursor
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[])

    results = await repo.list_replacements_for_rule(PARENT_OID)

    assert results == []
    mock_collection.find.assert_called_once_with({"forwarding_rule_id": PARENT_OID})


@pytest.mark.asyncio
async def test_to_document_excludes_id_when_none():
    """Verify _to_document does not inject _id key when entity.id is None (insert case)."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ReplacementRuleRepository(mock_db)

    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId(REPLACEMENT_OID)
    mock_collection.insert_one.return_value = mock_insert_result

    replacement = make_replacement()   # id=None
    await repo.add_replacement(replacement)

    called_doc = mock_collection.insert_one.call_args[0][0]
    assert "_id" not in called_doc, "_id must not be injected when entity.id is None"
