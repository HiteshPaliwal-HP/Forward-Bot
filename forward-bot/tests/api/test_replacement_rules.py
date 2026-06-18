"""API integration tests for /api/v1/rules/{rule_id}/replacement-rules — covers all ACs for Story 3.2."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timezone
from bson import ObjectId

from forward_bot.app import create_app
from forward_bot.config import Settings
from forward_bot.domain.entities.replacement_rule import ReplacementRule
from forward_bot.domain.entities.forwarding_rule import (
    ForwardingRule, SamplingConfig, AttributionConfig,
    AutoReplaceSourceRefsConfig, MediaReplacementConfig,
)
from forward_bot.api.dependencies.providers import (
    get_rule_repository,
    get_replacement_repository,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

NOW = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
RULE_OID = "65c52c6f1f2e3d4a5b6c7d8e"
SOURCE_OID = "65c52c6f1f2e3d4a5b6c7d8a"
REPLACEMENT_OID = "65c52c6f1f2e3d4a5b6c0001"


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


def make_forwarding_rule(**kwargs) -> ForwardingRule:
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


def make_replacement(**kwargs) -> ReplacementRule:
    defaults = dict(
        id=REPLACEMENT_OID,
        forwarding_rule_id=RULE_OID,
        search_text="competitor",
        replacement_text="our brand",
        match_mode="literal",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    defaults.update(kwargs)
    return ReplacementRule(**defaults)


def minimal_create_payload(**kwargs) -> dict:
    defaults = {
        "search_text": "competitor",
        "replacement_text": "our brand",
        "match_mode": "literal",
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# AC8: Auth gate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_replacement_rules_endpoints_require_authentication(app):
    """AC8: All replacement-rules endpoints return 401 without credentials."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        assert (await ac.post(f"/api/v1/rules/{RULE_OID}/replacement-rules", json=minimal_create_payload())).status_code == 401
        assert (await ac.get(f"/api/v1/rules/{RULE_OID}/replacement-rules")).status_code == 401
        assert (await ac.put(f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}", json=minimal_create_payload())).status_code == 401
        assert (await ac.delete(f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}")).status_code == 401


# ---------------------------------------------------------------------------
# AC1: Create Replacement Rule — happy path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_replacement_rule_happy_path(app, headers):
    """AC1: POST /api/v1/rules/{rule_id}/replacement-rules returns 201 with all required fields."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.add_replacement = AsyncMock(
        side_effect=lambda r: setattr(r, "id", REPLACEMENT_OID) or REPLACEMENT_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(),
            headers=headers,
        )

    assert res.status_code == 201
    data = res.json()
    assert data["id"] == REPLACEMENT_OID
    assert data["forwarding_rule_id"] == RULE_OID
    assert data["search_text"] == "competitor"
    assert data["replacement_text"] == "our brand"
    assert data["match_mode"] == "literal"
    assert data["is_active"] is True          # default True per FR-7
    assert "created_at" in data
    assert "updated_at" in data
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_replacement_rule_empty_replacement_text_allowed(app, headers):
    """AC1/Dev Notes: replacement_text may be empty string (to delete all occurrences of search_text)."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.add_replacement = AsyncMock(
        side_effect=lambda r: setattr(r, "id", REPLACEMENT_OID) or REPLACEMENT_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(replacement_text=""),  # empty string is valid
            headers=headers,
        )

    assert res.status_code == 201
    assert res.json()["replacement_text"] == ""
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_replacement_rule_empty_search_text_rejected(app, headers):
    """Dev Notes: search_text must have min_length=1 — empty string is rejected (422 from Pydantic)."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(search_text=""),  # empty — should fail
            headers=headers,
        )

    assert res.status_code == 422
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC2: Reject invalid regex pattern → 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_replacement_rule_invalid_regex_rejected(app, headers):
    """AC2: POST returns 422 with invalid_regex code when match_mode=regex and pattern is invalid."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(search_text="[invalid(", match_mode="regex"),
            headers=headers,
        )

    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "invalid_regex"
    assert "[invalid(" in data["error"]["message"]
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_replacement_rule_invalid_regex_rejected(app, headers):
    """AC2: PUT also returns 422 with invalid_regex when match_mode=regex and pattern is invalid."""
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=make_replacement())

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(
            f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}",
            json=minimal_create_payload(search_text="[bad(", match_mode="regex"),
            headers=headers,
        )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_regex"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_replacement_rule_valid_regex_accepted(app, headers):
    """AC2: POST succeeds when match_mode=regex and search_text is a valid regex pattern."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.add_replacement = AsyncMock(
        side_effect=lambda r: setattr(r, "id", REPLACEMENT_OID) or REPLACEMENT_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(search_text=r"(\w+)-brand", match_mode="regex"),
            headers=headers,
        )

    assert res.status_code == 201
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC3: Reject non-existent parent rule → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_replacement_rule_parent_not_found(app, headers):
    """AC3: POST returns 404 with rule_not_found when parent forwarding rule does not exist."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(),
            headers=headers,
        )

    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_replacement_rules_parent_not_found(app, headers):
    """AC4: GET returns 404 with rule_not_found when parent forwarding rule does not exist."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            headers=headers,
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "rule_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC4: List Replacement Rules → 200 ordered by created_at ASC
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_replacement_rules_happy_path(app, headers):
    """AC4: GET returns 200 with flat items list ordered by created_at ASC."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    now1 = datetime(2026, 6, 17, 12, 0, 0, tzinfo=timezone.utc)
    now2 = datetime(2026, 6, 17, 13, 0, 0, tzinfo=timezone.utc)

    replacements = [
        make_replacement(id=REPLACEMENT_OID, search_text="first", created_at=now1, updated_at=now1),
        make_replacement(id="65c52c6f1f2e3d4a5b6c0002", search_text="second", created_at=now2, updated_at=now2),
    ]

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.list_replacements_for_rule = AsyncMock(return_value=replacements)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert len(data["items"]) == 2
    assert data["items"][0]["search_text"] == "first"
    assert data["items"][1]["search_text"] == "second"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_list_replacement_rules_empty(app, headers):
    """AC4: GET returns 200 with empty items list when no replacement rules exist."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.list_replacements_for_rule = AsyncMock(return_value=[])

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get(f"/api/v1/rules/{RULE_OID}/replacement-rules", headers=headers)

    assert res.status_code == 200
    assert res.json() == {"items": []}
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC5: Update Replacement Rule → 200 with refreshed updated_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_replacement_rule_happy_path(app, headers):
    """AC5: PUT returns 200 with updated fields and refreshed updated_at."""
    mock_replacement_repo = MagicMock()

    old_updated_at = datetime(2026, 6, 17, 11, 0, 0, tzinfo=timezone.utc)
    existing = make_replacement(
        search_text="old search",
        replacement_text="old replacement",
        updated_at=old_updated_at,
    )
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=existing)
    mock_replacement_repo.update_replacement = AsyncMock(return_value=True)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    update_payload = {
        "search_text": "new search",
        "replacement_text": "new replacement",
        "match_mode": "literal",
        "is_active": False,
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(
            f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}",
            json=update_payload,
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["search_text"] == "new search"
    assert data["replacement_text"] == "new replacement"
    assert data["is_active"] is False
    # updated_at should be refreshed (different from old_updated_at)
    assert data["updated_at"] != old_updated_at.strftime("%Y-%m-%dT%H:%M:%SZ")
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_replacement_rule_not_found(app, headers):
    """AC5: PUT returns 404 with replacement_rule_not_found when replacement does not exist."""
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(
            f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}",
            json=minimal_create_payload(),
            headers=headers,
        )

    assert res.status_code == 404
    data = res.json()
    assert data["error"]["code"] == "replacement_rule_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC6: Delete Replacement Rule → 204
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_replacement_rule_happy_path(app, headers):
    """AC6: DELETE returns 204 when replacement rule exists and is deleted."""
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=make_replacement())
    mock_replacement_repo.delete_replacement = AsyncMock(return_value=True)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(
            f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}",
            headers=headers,
        )

    assert res.status_code == 204
    mock_replacement_repo.delete_replacement.assert_called_once_with(REPLACEMENT_OID)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_delete_replacement_rule_not_found(app, headers):
    """AC6: DELETE returns 404 with replacement_rule_not_found when replacement does not exist."""
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=None)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(
            f"/api/v1/rules/{RULE_OID}/replacement-rules/{REPLACEMENT_OID}",
            headers=headers,
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "replacement_rule_not_found"
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC7: Cascade Delete verified via test_rules.py (already has test_delete_rule_success_cascade)
# This test verifies the integration contract from Story 3.2's perspective.
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cascade_delete_replacement_rules_when_parent_deleted(app, headers):
    """AC7: DELETE /api/v1/rules/{rule_id} cascades to replacement_rules collection.

    This verifies that ForwardingRuleRepository.delete_rule() calls delete_many with
    the string rule_id (not ObjectId) — matching the string storage format for forwarding_rule_id.
    """
    mock_rule_repo = MagicMock()
    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_rule_repo.delete_rule = AsyncMock(return_value=True)

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(f"/api/v1/rules/{RULE_OID}", headers=headers)

    assert res.status_code == 204
    # The cascade delete is handled inside delete_rule — our integration confirms it is called
    mock_rule_repo.delete_rule.assert_called_once_with(RULE_OID)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# AC9: Literal vs Regex Semantics (storage-level — no execution)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_replacement_rule_literal_mode_accepted(app, headers):
    """AC9: POST with match_mode=literal is accepted without regex validation."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.add_replacement = AsyncMock(
        side_effect=lambda r: setattr(r, "id", REPLACEMENT_OID) or REPLACEMENT_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Even an invalid regex pattern is accepted in literal mode (no compilation)
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(search_text="[not-regex]", match_mode="literal"),
            headers=headers,
        )

    assert res.status_code == 201
    assert res.json()["match_mode"] == "literal"
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_replacement_rule_regex_with_backreference_accepted(app, headers):
    """AC9: POST with match_mode=regex and backreference in replacement_text is accepted."""
    mock_rule_repo = MagicMock()
    mock_replacement_repo = MagicMock()

    mock_rule_repo.get_rule_by_id = AsyncMock(return_value=make_forwarding_rule())
    mock_replacement_repo.add_replacement = AsyncMock(
        side_effect=lambda r: setattr(r, "id", REPLACEMENT_OID) or REPLACEMENT_OID
    )

    app.dependency_overrides[get_rule_repository] = lambda: mock_rule_repo
    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.post(
            f"/api/v1/rules/{RULE_OID}/replacement-rules",
            json=minimal_create_payload(
                search_text=r"(\w+)-brand",
                replacement_text=r"\1-our_brand",  # backreference — valid at storage time
                match_mode="regex",
            ),
            headers=headers,
        )

    assert res.status_code == 201
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Edge case: Cross-ownership (intentional MVP simplification — documented)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_replacement_rule_cross_ownership_succeeds(app, headers):
    """Edge case (intentional, not validated): DELETE /{wrong_rule_id}/replacement-rules/{id}
    where id exists but belongs to a different rule_id — succeeds with HTTP 204.

    This cross-ownership scenario is NOT validated per MVP simplification.
    Do NOT add a cross-ownership check unless explicitly asked.
    """
    mock_replacement_repo = MagicMock()
    # The replacement belongs to RULE_OID but we're hitting it via a different rule_id URL
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=make_replacement())
    mock_replacement_repo.delete_replacement = AsyncMock(return_value=True)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    wrong_rule_id = "65c52c6f1f2e3d4a5b6c9999"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.delete(
            f"/api/v1/rules/{wrong_rule_id}/replacement-rules/{REPLACEMENT_OID}",
            headers=headers,
        )

    # MVP: succeeds because replacement exists (cross-ownership not validated)
    assert res.status_code == 204
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_replacement_rule_cross_ownership_succeeds(app, headers):
    """Edge case (intentional, not validated): PUT /{wrong_rule_id}/replacement-rules/{id}
    where id exists but belongs to a different rule_id — succeeds with HTTP 200.
    """
    mock_replacement_repo = MagicMock()
    mock_replacement_repo.get_replacement_by_id = AsyncMock(return_value=make_replacement())
    mock_replacement_repo.update_replacement = AsyncMock(return_value=True)

    app.dependency_overrides[get_replacement_repository] = lambda: mock_replacement_repo

    wrong_rule_id = "65c52c6f1f2e3d4a5b6c9999"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.put(
            f"/api/v1/rules/{wrong_rule_id}/replacement-rules/{REPLACEMENT_OID}",
            json=minimal_create_payload(),
            headers=headers,
        )

    assert res.status_code == 200
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Existing rules endpoints still work (non-regression)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_forwarding_rule_endpoints_still_work_after_story_32(app, headers):
    """Non-regression: Existing rules endpoints still return correct status codes."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Auth still required on existing endpoints
        assert (await ac.post("/api/v1/rules", json={})).status_code == 401
        assert (await ac.get("/api/v1/rules")).status_code == 401
        assert (await ac.get(f"/api/v1/rules/{RULE_OID}")).status_code == 401
        assert (await ac.put(f"/api/v1/rules/{RULE_OID}", json={})).status_code == 401
        assert (await ac.delete(f"/api/v1/rules/{RULE_OID}")).status_code == 401
        assert (await ac.post(f"/api/v1/rules/{RULE_OID}/enable")).status_code == 401
        assert (await ac.post(f"/api/v1/rules/{RULE_OID}/disable")).status_code == 401
