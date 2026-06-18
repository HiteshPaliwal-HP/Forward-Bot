"""API integration tests for /api/v1/rules endpoints — covers all ACs for Story 3.1."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule,
    SamplingConfig,
    AttributionConfig,
    AutoReplaceSourceRefsConfig,
    MediaReplacementConfig,
)
from forward_bot.domain.entities.source import Source
from forward_bot.api.dependencies.providers import (
    get_rule_repository,
    get_source_repository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
SOURCE_OID = "65c52c6f1f2e3d4a5b6c7d8a"
RULE_OID = "65c52c6f1f2e3d4a5b6c7d8e"


@pytest.fixture(autouse=True)
def mock_db_and_telegram():
    """Mock MongoDB and Telegram clients globally for this test module."""
    with patch("forward_bot.api.dependencies.providers.mongo_client") as mock_mongo, \
         patch("forward_bot.api.dependencies.providers.telegram_client") as mock_tg:
        mock_mongo.db = MagicMock()
        yield mock_mongo, mock_tg


@pytest.fixture
def settings():
    return Settings(
        api_key="valid-api-key",
        secret_key="secret",
        mongo_uri="mongodb://localhost:27017/test_db",
        ui_enabled=False,
    )


@pytest.fixture
def app(settings):
    return create_app(settings, lifespan=None)


@pytest.fixture
def headers():
    return {"X-API-Key": "valid-api-key"}


def make_source(**kwargs) -> Source:
    defaults = dict(
        id=SOURCE_OID,
        telegram_id=123456,
        telegram_username="sourcechannel",
        display_name="Source Channel",
        type="channel",
        folder_id=None,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(kwargs)
    return Source(**defaults)


def make_rule(**kwargs) -> ForwardingRule:
    defaults = dict(
        id=RULE_OID,
        source_id=SOURCE_OID,
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
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(kwargs)
    return ForwardingRule(**defaults)


def minimal_create_payload(**kwargs) -> dict:
    defaults = {"source_id": SOURCE_OID, "destination_channel": "@target_channel"}
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# AC14: Auth gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rules_endpoints_require_authentication(app):
    """AC14: All rules endpoints return 401 without credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.post("/api/v1/rules", json=minimal_create_payload())).status_code == 401
        assert (await ac.get("/api/v1/rules")).status_code == 401
        assert (await ac.get(f"/api/v1/rules/{RULE_OID}")).status_code == 401
        assert (await ac.put(f"/api/v1/rules/{RULE_OID}", json=minimal_create_payload())).status_code == 401
        assert (await ac.delete(f"/api/v1/rules/{RULE_OID}")).status_code == 401
        assert (await ac.post(f"/api/v1/rules/{RULE_OID}/enable")).status_code == 401
        assert (await ac.post(f"/api/v1/rules/{RULE_OID}/disable")).status_code == 401


# ---------------------------------------------------------------------------
# AC1: Create rule — happy path with defaults
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_happy_path(app, headers):
    """AC1: POST /api/v1/rules returns 201 with all default field values."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()

    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())
    mock_rule_repo.add_rule = AsyncMock(
        side_effect=lambda r: setattr(r, "id", RULE_OID) or RULE_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=minimal_create_payload(), headers=headers)

    assert res.status_code == 201
    data = res.json()
    assert data["id"] == RULE_OID
    assert data["source_id"] == SOURCE_OID
    assert data["destination_channel"] == "@target_channel"
    assert data["is_active"] is False
    assert data["keyword_match_mode"] == "literal"
    assert data["block_keywords"] == []
    assert data["allow_keywords"] == []
    assert data["media_type_filter"] == ["text", "photo"]
    assert data["remove_links"] is False
    assert data["remove_hashtags"] is False
    assert data["remove_mentions"] is False
    assert data["forward_media"] == "forward"
    assert data["sampling"] == {"n": 1}
    assert data["time_window"] is None
    assert data["attribution"] == {"enabled": False, "position": "prefix", "format": "From {source_name}"}
    assert data["auto_replace_source_refs"] == {"enabled": False, "replacement": None, "replace_display_name": False}
    assert data["media_replacement"] == {
        "enabled": False, "replacement_image_path": None, "replacement_caption_mode": "use_source"
    }
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC1: Duplicate (source_id, destination_channel) — permitted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_duplicate_pair_permitted(app, headers):
    """AC1: Duplicate (source_id, destination_channel) pairs are allowed — no uniqueness constraint."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())
    mock_rule_repo.add_rule = AsyncMock(
        side_effect=lambda r: setattr(r, "id", RULE_OID) or RULE_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res1 = await ac.post("/api/v1/rules", json=minimal_create_payload(), headers=headers)
        res2 = await ac.post("/api/v1/rules", json=minimal_create_payload(), headers=headers)
    assert res1.status_code == 201
    assert res2.status_code == 201
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC2: Reject non-existent source_id → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_source_not_found_returns_422(app, headers):
    """AC2: POST returns 422 with source_not_found code when source_id does not exist."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=minimal_create_payload(), headers=headers)

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "source_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC3: Reject self-referential rule → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_self_referential_rejected(app, headers):
    """AC3: POST returns 422 with self_referential_rule code when source equals destination."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    # Source whose username matches destination_channel
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source(telegram_username="sourcechannel"))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    # destination matches source's telegram_username (with @)
    payload = minimal_create_payload(destination_channel="@sourcechannel")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "self_referential_rule"
    assert "source equals destination" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_rule_self_referential_by_telegram_id(app, headers):
    """AC3: Self-referential check also works when destination_channel is the telegram_id."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source(telegram_id=123456))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(destination_channel="123456")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "self_referential_rule"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC4: Reject invalid regex keywords → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_invalid_regex_rejected(app, headers):
    """AC4: POST returns 422 with invalid_regex code for bad block_keywords pattern."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        keyword_match_mode="regex",
        block_keywords=["[invalid("]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "invalid_regex"
    assert "[invalid(" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_rule_invalid_regex_allow_keywords(app, headers):
    """AC4: Regex validation also covers allow_keywords."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        keyword_match_mode="regex",
        allow_keywords=["**bad**"]
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_regex"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC5: Accept cross-midnight time windows
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_cross_midnight_time_window_accepted(app, headers):
    """AC5: POST returns 201 for cross-midnight time windows (end_time < start_time)."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())
    mock_rule_repo.add_rule = AsyncMock(
        side_effect=lambda r: setattr(r, "id", RULE_OID) or RULE_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        time_window={
            "timezone": "UTC",
            "days_of_week": ["MON", "TUE"],
            "start_time": "22:00",
            "end_time": "06:00"  # cross-midnight
        }
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 201
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC6: Reject invalid IANA timezone → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_invalid_timezone_rejected(app, headers):
    """AC6: POST returns 422 with invalid_timezone code for bad timezone string."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        time_window={
            "timezone": "Not/AZone",
            "days_of_week": ["MON"],
            "start_time": "09:00",
            "end_time": "17:00"
        }
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "invalid_timezone"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC7: Reject media_replacement enabled + null path → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_rule_media_replacement_path_required(app, headers):
    """AC7: POST returns 422 when media_replacement.enabled=true and path is null."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        media_replacement={"enabled": True, "replacement_image_path": None, "replacement_caption_mode": "use_source"}
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post("/api/v1/rules", json=payload, headers=headers)

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "media_replacement_path_required"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC8 & AC9: Enable and Disable Rule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enable_rule_success(app, headers):
    """AC8: POST /enable returns 200 {ok: true} and is_active becomes true."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.enable_rule = AsyncMock(return_value=True)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/rules/{RULE_OID}/enable", headers=headers)

    assert res.status_code == 200
    assert res.json() == {"ok": True}
    mock_rule_repo.enable_rule.assert_called_once_with(RULE_OID)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_enable_rule_not_found(app, headers):
    """AC8: POST /enable returns 404 with rule_not_found for nonexistent ID."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.enable_rule = AsyncMock(return_value=False)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/rules/{RULE_OID}/enable", headers=headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_disable_rule_success(app, headers):
    """AC9: POST /disable returns 200 {ok: true}."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.disable_rule = AsyncMock(return_value=True)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/rules/{RULE_OID}/disable", headers=headers)

    assert res.status_code == 200
    assert res.json() == {"ok": True}
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_disable_rule_not_found(app, headers):
    """AC9: POST /disable returns 404 with rule_not_found for nonexistent ID."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.disable_rule = AsyncMock(return_value=False)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(f"/api/v1/rules/{RULE_OID}/disable", headers=headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC10: List Rules with pagination and filters
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_rules_success(app, headers):
    """AC10: GET /api/v1/rules returns paginated response sorted by created_at DESC."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()

    mock_rule_repo.list_rules = AsyncMock(return_value=([make_rule()], 1))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 1
    assert data["page"] == 1
    assert data["page_size"] == 50
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == RULE_OID
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_rules_page_size_capped_at_200(app, headers):
    """AC10: page_size is capped at 200."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([], 0))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules?page_size=500", headers=headers)

    assert res.status_code == 200
    assert res.json()["page_size"] == 200
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_rules_filter_by_source_id(app, headers):
    """AC10: source_id filter is forwarded to use case."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([], 0))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/rules?source_id={SOURCE_OID}", headers=headers)

    assert res.status_code == 200
    # Verify list_rules was called with correct source_id
    call_kwargs = mock_rule_repo.list_rules.call_args.kwargs
    assert call_kwargs["source_id"] == SOURCE_OID
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_rules_filter_by_is_active(app, headers):
    """AC10: is_active filter is forwarded to use case."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([], 0))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules?is_active=true", headers=headers)

    assert res.status_code == 200
    call_kwargs = mock_rule_repo.list_rules.call_args.kwargs
    assert call_kwargs["is_active"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_rules_filter_by_destination_channel(app, headers):
    """AC10: destination_channel filter is forwarded to use case."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([], 0))

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules?destination_channel=@test", headers=headers)

    assert res.status_code == 200
    call_kwargs = mock_rule_repo.list_rules.call_args.kwargs
    assert call_kwargs["destination_channel"] == "@test"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_rules_filter_by_folder_id(app, headers):
    """AC10: folder_id filter is forwarded to use case."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.list_rules = AsyncMock(return_value=([], 0))
    folder_id = "65c52c6f1f2e3d4a5b6c0001"

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/rules?folder_id={folder_id}", headers=headers)

    assert res.status_code == 200
    call_kwargs = mock_rule_repo.list_rules.call_args.kwargs
    assert call_kwargs["folder_id"] == folder_id
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC11: Get Single Rule
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_rule_success(app, headers):
    """AC11: GET /api/v1/rules/{id} returns 200 with full rule document."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_rule())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/rules/{RULE_OID}", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["id"] == RULE_OID
    assert data["source_id"] == SOURCE_OID
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_rule_not_found(app, headers):
    """AC11: GET /api/v1/rules/{id} returns 404 with rule_not_found for missing/invalid ID."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/rules/{RULE_OID}", headers=headers)

    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "rule_not_found"
    assert RULE_OID in data["error"]["message"]
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC12: Update Rule (PUT)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_rule_success(app, headers):
    """AC12: PUT /api/v1/rules/{id} returns 200 with updated rule."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()

    existing = make_rule()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=existing)
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())
    mock_rule_repo.update_rule = AsyncMock(return_value=True)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    update_payload = {
        "source_id": SOURCE_OID,
        "destination_channel": "@new_target",
        "is_active": True,
        "remove_links": True,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(f"/api/v1/rules/{RULE_OID}", json=update_payload, headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["destination_channel"] == "@new_target"
    assert data["is_active"] is True
    assert data["remove_links"] is True
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_rule_not_found(app, headers):
    """AC12: PUT returns 404 if rule does not exist."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(f"/api/v1/rules/{RULE_OID}", json=minimal_create_payload(), headers=headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_rule_source_deleted_after_create_returns_422(app, headers):
    """AC12 note: PUT re-validates source_id; returns 422 if source was deleted."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_rule())
    mock_source_repo.get_source_by_id = AsyncMock(return_value=None)  # source deleted

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(f"/api/v1/rules/{RULE_OID}", json=minimal_create_payload(), headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "source_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC13: Delete Rule (cascade)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_rule_success_cascade(app, headers):
    """AC13: DELETE /api/v1/rules/{id} returns 204 and cascades to replacement_rules."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_rule())
    mock_rule_repo.delete_rule = AsyncMock(return_value=True)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(f"/api/v1/rules/{RULE_OID}", headers=headers)

    assert res.status_code == 204
    mock_rule_repo.delete_rule.assert_called_once_with(RULE_OID)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_rule_not_found(app, headers):
    """AC13: DELETE returns 404 with rule_not_found if rule does not exist."""
    mock_rule_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(f"/api/v1/rules/{RULE_OID}", headers=headers)

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Additional: PUT with invalid regex / invalid timezone (same validation as POST)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_rule_invalid_regex_rejected(app, headers):
    """AC12: PUT applies same regex validation as POST."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_rule())
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(keyword_match_mode="regex", block_keywords=["[bad"])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(f"/api/v1/rules/{RULE_OID}", json=payload, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_regex"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_rule_invalid_timezone_rejected(app, headers):
    """AC12: PUT applies same timezone validation as POST."""
    mock_rule_repo = MagicMock()
    mock_source_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_rule())
    mock_source_repo.get_source_by_id = AsyncMock(return_value=make_source())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_source_repository] = lambda: mock_source_repo

    payload = minimal_create_payload(
        time_window={"timezone": "Not/Valid", "days_of_week": ["MON"], "start_time": "09:00", "end_time": "17:00"}
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(f"/api/v1/rules/{RULE_OID}", json=payload, headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_timezone"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Invalid list filter formats
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_rules_invalid_source_id_format(app, headers):
    """Verify that GET /api/v1/rules?source_id=invalid returns HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules?source_id=invalid-hex", headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "http_error"
    assert res.json()["error"]["message"] == "Invalid source_id format."


@pytest.mark.asyncio
async def test_list_rules_invalid_folder_id_format(app, headers):
    """Verify that GET /api/v1/rules?folder_id=invalid returns HTTP 422."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/rules?folder_id=invalid-hex", headers=headers)

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "http_error"
    assert res.json()["error"]["message"] == "Invalid folder_id format."

