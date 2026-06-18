"""Unit tests for the ForwardingRuleRepository."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from bson import ObjectId
from datetime import datetime, timezone

from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_rule(**kwargs) -> ForwardingRule:
    """Build a minimal ForwardingRule for testing."""
    defaults = dict(
        source_id="65c52c6f1f2e3d4a5b6c7d8a",
        destination_channel="@target_channel",
        is_active=False,
        keyword_match_mode="literal",
        block_keywords=[],
        allow_keywords=[],
        media_type_filter=["text", "photo"],
        remove_links=False,
        remove_hashtags=False,
        remove_mentions=False,
        forward_media="forward",
        sampling=SamplingConfig(n=1),
        time_window=None,
        attribution=AttributionConfig(),
        auto_replace_source_refs=AutoReplaceSourceRefsConfig(),
        media_replacement=MediaReplacementConfig(),
        created_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc),
    )
    defaults.update(kwargs)
    return ForwardingRule(**defaults)


def make_mongo_doc(**kwargs) -> dict:
    """Build a minimal MongoDB document dict for testing."""
    now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    defaults = {
        "_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8e"),
        "source_id": ObjectId("65c52c6f1f2e3d4a5b6c7d8a"),
        "destination_channel": "@target_channel",
        "is_active": False,
        "keyword_match_mode": "literal",
        "block_keywords": [],
        "allow_keywords": [],
        "media_type_filter": ["text", "photo"],
        "remove_links": False,
        "remove_hashtags": False,
        "remove_mentions": False,
        "forward_media": "forward",
        "sampling": {"n": 1},
        "time_window": None,
        "attribution": {"enabled": False, "position": "prefix", "format": "From {source_name}"},
        "auto_replace_source_refs": {"enabled": False, "replacement": None, "replace_display_name": False},
        "media_replacement": {"enabled": False, "replacement_image_path": None, "replacement_caption_mode": "use_source"},
        "created_at": now,
        "updated_at": now,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_rule_and_get_rule_by_id():
    """Verify insertion mapping and retrieval by ID."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    # Setup insert mock
    mock_insert_result = MagicMock()
    mock_insert_result.inserted_id = ObjectId("65c52c6f1f2e3d4a5b6c7d8e")
    mock_collection.insert_one.return_value = mock_insert_result

    rule = make_rule()
    inserted_id = await repo.add_rule(rule)

    assert inserted_id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert rule.id == "65c52c6f1f2e3d4a5b6c7d8e"
    mock_collection.insert_one.assert_called_once()

    # Verify BSON ObjectId storage for source_id (critical constraint)
    called_doc = mock_collection.insert_one.call_args[0][0]
    assert isinstance(called_doc["source_id"], ObjectId), \
        "source_id must be stored as BSON ObjectId — not a string"
    assert str(called_doc["source_id"]) == "65c52c6f1f2e3d4a5b6c7d8a"

    # Now test get by ID
    mock_collection.find_one.return_value = make_mongo_doc()
    fetched = await repo.get_rule_by_id("65c52c6f1f2e3d4a5b6c7d8e")
    assert fetched is not None
    assert fetched.id == "65c52c6f1f2e3d4a5b6c7d8e"
    assert fetched.source_id == "65c52c6f1f2e3d4a5b6c7d8a"  # back to string in entity
    assert fetched.destination_channel == "@target_channel"
    assert fetched.is_active is False
    assert fetched.sampling.n == 1


@pytest.mark.asyncio
async def test_get_rule_by_id_returns_none_for_invalid():
    """Verify None returned for invalid ObjectId strings."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    result = await repo.get_rule_by_id("not-a-valid-id")
    assert result is None
    mock_collection.find_one.assert_not_called()


@pytest.mark.asyncio
async def test_update_rule():
    """Verify update sends a replace_one with stripped _id."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    mock_replace_result = MagicMock()
    mock_replace_result.modified_count = 1
    mock_collection.replace_one.return_value = mock_replace_result

    rule = make_rule(id="65c52c6f1f2e3d4a5b6c7d8e")
    updated = await repo.update_rule("65c52c6f1f2e3d4a5b6c7d8e", rule)
    assert updated is True
    mock_collection.replace_one.assert_called_once()


@pytest.mark.asyncio
async def test_delete_rule_cascade():
    """Verify delete_rule cascades to replacement_rules and then deletes the rule itself."""
    now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)

    mock_db = MagicMock()
    mock_rules_collection = AsyncMock()
    mock_replacement_collection = AsyncMock()

    # Both FORWARDING_RULES and REPLACEMENT_RULES collections
    collections = {
        "forwarding_rules": mock_rules_collection,
        "replacement_rules": mock_replacement_collection,
    }
    mock_db.__getitem__.side_effect = lambda name: collections[name]

    repo = ForwardingRuleRepository(mock_db)

    # Mock delete_many on replacement_rules
    mock_delete_many_result = MagicMock()
    mock_delete_many_result.deleted_count = 2
    mock_replacement_collection.delete_many.return_value = mock_delete_many_result

    # Mock delete_one on forwarding_rules
    mock_delete_result = MagicMock()
    mock_delete_result.deleted_count = 1
    mock_rules_collection.delete_one.return_value = mock_delete_result

    rule_id = "65c52c6f1f2e3d4a5b6c7d8e"
    result = await repo.delete_rule(rule_id)

    assert result is True
    # Verify cascade delete was called on replacement_rules with string rule_id
    mock_replacement_collection.delete_many.assert_called_once_with(
        {"forwarding_rule_id": rule_id}
    )
    # Verify rule itself was deleted
    mock_rules_collection.delete_one.assert_called_once_with(
        {"_id": ObjectId(rule_id)}
    )


@pytest.mark.asyncio
async def test_enable_and_disable_rule():
    """Verify enable_rule and disable_rule issue $set update_one calls."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    rule_id = "65c52c6f1f2e3d4a5b6c7d8e"

    # enable_rule
    mock_update_result = MagicMock()
    mock_update_result.modified_count = 1
    mock_collection.update_one.return_value = mock_update_result

    enabled = await repo.enable_rule(rule_id)
    assert enabled is True
    call_args = mock_collection.update_one.call_args
    assert call_args[0][0] == {"_id": ObjectId(rule_id)}
    assert call_args[0][1]["$set"]["is_active"] is True

    # disable_rule — modified_count=0 (nonexistent)
    mock_update_result.modified_count = 0
    disabled = await repo.disable_rule(rule_id)
    assert disabled is False


@pytest.mark.asyncio
async def test_enable_rule_invalid_id_returns_false():
    """Verify enable_rule returns False for invalid ObjectId without touching DB."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    result = await repo.enable_rule("not-valid-id")
    assert result is False
    mock_collection.update_one.assert_not_called()


@pytest.mark.asyncio
async def test_list_rules_with_filters():
    """Verify list_rules builds correct MongoDB query with source_id, destination_channel, is_active."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    mock_collection.count_documents.return_value = 1
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[make_mongo_doc()])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    source_id = "65c52c6f1f2e3d4a5b6c7d8a"
    rules, total = await repo.list_rules(
        source_repo=None,
        source_id=source_id,
        destination_channel="@target",
        is_active=True,
        page=2,
        page_size=10,
    )

    assert total == 1
    assert len(rules) == 1

    # Verify query
    mock_collection.find.assert_called_once_with({
        "source_id": ObjectId(source_id),
        "destination_channel": "@target",
        "is_active": True,
    })
    mock_cursor.sort.assert_called_with("created_at", -1)
    mock_cursor.skip.assert_called_with(10)  # (page-1) * page_size = 1 * 10
    mock_cursor.limit.assert_called_with(10)


@pytest.mark.asyncio
async def test_list_rules_folder_id_two_step_join():
    """Verify folder_id filter performs two-step join via source_repo."""
    from forward_bot.domain.entities.source import Source

    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    # Mock source_repo returning sources in folder
    mock_source_repo = MagicMock()
    now = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    mock_source_repo.get_sources_by_folder_id = AsyncMock(return_value=[
        Source(
            id="65c52c6f1f2e3d4a5b6c7d8a",
            telegram_id=111,
            telegram_username="src1",
            display_name="Src1",
            type="channel",
            folder_id="65c52c6f1f2e3d4a5b6c0001",
            created_at=now,
            updated_at=now,
        )
    ])

    mock_collection.count_documents.return_value = 0
    mock_cursor = MagicMock()
    mock_cursor.sort.return_value = mock_cursor
    mock_cursor.skip.return_value = mock_cursor
    mock_cursor.limit.return_value = mock_cursor
    mock_cursor.to_list = AsyncMock(return_value=[])
    mock_collection.find = MagicMock(return_value=mock_cursor)

    folder_id = "65c52c6f1f2e3d4a5b6c0001"
    rules, total = await repo.list_rules(
        source_repo=mock_source_repo,
        folder_id=folder_id,
        page=1,
        page_size=50,
    )

    mock_source_repo.get_sources_by_folder_id.assert_called_once_with(folder_id)
    # Verify the query uses $in with ObjectIds
    call_query = mock_collection.find.call_args[0][0]
    assert "$in" in call_query["source_id"]
    assert call_query["source_id"]["$in"] == [ObjectId("65c52c6f1f2e3d4a5b6c7d8a")]


@pytest.mark.asyncio
async def test_to_entity_mapping_with_time_window():
    """Verify full _to_entity mapping including time_window sub-config."""
    mock_db = MagicMock()
    mock_collection = AsyncMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = ForwardingRuleRepository(mock_db)

    doc = make_mongo_doc(
        time_window={
            "timezone": "Asia/Kolkata",
            "days_of_week": ["MON", "TUE"],
            "start_time": "09:00",
            "end_time": "17:00",
        },
        sampling={"n": 3},
        attribution={"enabled": True, "position": "suffix", "format": "Via {source_name}"},
    )
    mock_collection.find_one.return_value = doc
    rule = await repo.get_rule_by_id("65c52c6f1f2e3d4a5b6c7d8e")

    assert rule.time_window is not None
    assert rule.time_window.timezone == "Asia/Kolkata"
    assert rule.time_window.days_of_week == ["MON", "TUE"]
    assert rule.sampling.n == 3
    assert rule.attribution.enabled is True
    assert rule.attribution.position == "suffix"
