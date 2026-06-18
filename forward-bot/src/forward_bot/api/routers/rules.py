"""FastAPI router for Forwarding Rule CRUD and enable/disable operations."""
from fastapi import APIRouter, Depends, Query, status, HTTPException
from bson import ObjectId

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import (
    get_rule_repository,
    get_source_repository,
    get_replacement_repository,
)
from forward_bot.api.schemas.rule import (
    ForwardingRuleCreateRequest,
    ForwardingRuleUpdateRequest,
    ForwardingRuleResponse,
    ForwardingRulesPagedResponse,
)
from forward_bot.api.schemas.replacement_rule import (
    ReplacementRuleCreateRequest,
    ReplacementRuleUpdateRequest,
    ReplacementRuleResponse,
    ReplacementRulesListResponse,
)
from forward_bot.application.rules.create_rule import CreateRule
from forward_bot.application.rules.list_rules import ListRules
from forward_bot.application.rules.get_rule import GetRule
from forward_bot.application.rules.update_rule import UpdateRule
from forward_bot.application.rules.delete_rule import DeleteRule
from forward_bot.application.rules.enable_rule import EnableRule
from forward_bot.application.rules.disable_rule import DisableRule
from forward_bot.application.replacements.create_replacement import CreateReplacement
from forward_bot.application.replacements.list_replacements import ListReplacements
from forward_bot.application.replacements.update_replacement import UpdateReplacement
from forward_bot.application.replacements.delete_replacement import DeleteReplacement
from forward_bot.domain.exceptions import RuleNotFoundException
from forward_bot.infrastructure.mongo.repositories.rule_repository import ForwardingRuleRepository
from forward_bot.infrastructure.mongo.repositories.replacement_repository import ReplacementRuleRepository
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.post(
    "",
    response_model=ForwardingRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new forwarding rule.",
)
async def create_rule(
    payload: ForwardingRuleCreateRequest,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> ForwardingRuleResponse:
    """Create a new forwarding rule. Source must exist; self-referential rules are rejected."""
    use_case = CreateRule(rule_repo, source_repo)
    rule = await use_case.execute(payload.model_dump())
    return ForwardingRuleResponse.from_entity(rule)


@router.get(
    "",
    response_model=ForwardingRulesPagedResponse,
    status_code=status.HTTP_200_OK,
    summary="List forwarding rules with pagination and optional filters.",
)
async def list_rules(
    source_id: str | None = Query(None),
    destination_channel: str | None = Query(None),
    is_active: bool | None = Query(None),
    folder_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1),
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> ForwardingRulesPagedResponse:
    """Return a paginated list of rules sorted by created_at DESC."""
    # Validate source_id format
    if source_id is not None:
        if not ObjectId.is_valid(source_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid source_id format."
            )

    # Validate folder_id format
    if folder_id is not None:
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid folder_id format."
            )

    # Enforce page_size cap
    page_size = min(page_size, 200)

    use_case = ListRules(rule_repo, source_repo)
    rules, total = await use_case.execute(
        source_id=source_id,
        destination_channel=destination_channel,
        is_active=is_active,
        folder_id=folder_id,
        page=page,
        page_size=page_size,
    )
    return ForwardingRulesPagedResponse(
        items=[ForwardingRuleResponse.from_entity(r) for r in rules],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{rule_id}",
    response_model=ForwardingRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single forwarding rule by ID.",
)
async def get_rule(
    rule_id: str,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> ForwardingRuleResponse:
    """Retrieve a forwarding rule by its ObjectId. Returns 404 if not found or ID is invalid."""
    use_case = GetRule(rule_repo)
    rule = await use_case.execute(rule_id)
    return ForwardingRuleResponse.from_entity(rule)


@router.put(
    "/{rule_id}",
    response_model=ForwardingRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Full replacement update of a forwarding rule.",
)
async def update_rule(
    rule_id: str,
    payload: ForwardingRuleUpdateRequest,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> ForwardingRuleResponse:
    """Replace all fields of a forwarding rule. Same validation rules as POST."""
    use_case = UpdateRule(rule_repo, source_repo)
    rule = await use_case.execute(rule_id, payload.model_dump())
    return ForwardingRuleResponse.from_entity(rule)


@router.delete(
    "/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a forwarding rule and cascade-delete its replacement rules.",
)
async def delete_rule(
    rule_id: str,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> None:
    """Delete a forwarding rule. All associated replacement_rules are also deleted."""
    use_case = DeleteRule(rule_repo)
    await use_case.execute(rule_id)


@router.post(
    "/{rule_id}/enable",
    status_code=status.HTTP_200_OK,
    summary="Enable a forwarding rule (set is_active=true).",
)
async def enable_rule(
    rule_id: str,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> dict:
    """Enable a forwarding rule. Returns 404 if rule does not exist."""
    use_case = EnableRule(rule_repo)
    await use_case.execute(rule_id)
    return {"ok": True}


@router.post(
    "/{rule_id}/disable",
    status_code=status.HTTP_200_OK,
    summary="Disable a forwarding rule (set is_active=false).",
)
async def disable_rule(
    rule_id: str,
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> dict:
    """Disable a forwarding rule. Returns 404 if rule does not exist."""
    use_case = DisableRule(rule_repo)
    await use_case.execute(rule_id)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Replacement Rule sub-resource endpoints (Story 3.2)
# These are placed after enable/disable to follow route-ordering conventions.
# The /{rule_id}/replacement-rules path is unambiguous with /{rule_id} routes
# due to the additional /replacement-rules segment.
# ---------------------------------------------------------------------------

@router.post(
    "/{rule_id}/replacement-rules",
    response_model=ReplacementRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a replacement rule scoped to a forwarding rule.",
)
async def create_replacement_rule(
    rule_id: str,
    payload: ReplacementRuleCreateRequest,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRuleResponse:
    """Create a new replacement rule for a forwarding rule.

    Validates the parent forwarding rule exists (→ 404 if not).
    Validates regex pattern if match_mode='regex' (→ 422 if invalid).
    Returns 201 with the created replacement rule.
    """
    use_case = CreateReplacement(replacement_repo, rule_repo)
    replacement = await use_case.execute(rule_id, payload.model_dump())
    return ReplacementRuleResponse.from_entity(replacement)


@router.get(
    "/{rule_id}/replacement-rules",
    response_model=ReplacementRulesListResponse,
    status_code=status.HTTP_200_OK,
    summary="List replacement rules for a forwarding rule, ordered by created_at ASC.",
)
async def list_replacement_rules(
    rule_id: str,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    rule_repo: ForwardingRuleRepository = Depends(get_rule_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRulesListResponse:
    """List all replacement rules for a forwarding rule, ordered by created_at ASC (pipeline order).

    Validates the parent forwarding rule exists (→ 404 if not).
    Returns a flat list (no pagination — replacement rules per rule are bounded).
    """
    use_case = ListReplacements(replacement_repo, rule_repo)
    replacements = await use_case.execute(rule_id)
    return ReplacementRulesListResponse(
        items=[ReplacementRuleResponse.from_entity(r) for r in replacements]
    )


@router.put(
    "/{rule_id}/replacement-rules/{replacement_id}",
    response_model=ReplacementRuleResponse,
    status_code=status.HTTP_200_OK,
    summary="Full replacement update of a replacement rule.",
)
async def update_replacement_rule(
    rule_id: str,
    replacement_id: str,
    payload: ReplacementRuleUpdateRequest,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    _: str = Depends(get_current_operator),
) -> ReplacementRuleResponse:
    """Full replacement update of a replacement rule.

    Note: rule_id is accepted for URL consistency but is NOT validated against the
    replacement's forwarding_rule_id. The replacement's own id uniquely identifies it.
    This is an accepted MVP simplification (see story Dev Notes).

    Edge case (intentional, not validated): PUT /{wrong_rule_id}/replacement-rules/{id}
    where id exists but belongs to a different rule_id will succeed with HTTP 200.
    Do NOT add cross-ownership validation unless explicitly requested.
    """
    use_case = UpdateReplacement(replacement_repo)
    replacement = await use_case.execute(replacement_id, payload.model_dump())
    return ReplacementRuleResponse.from_entity(replacement)


@router.delete(
    "/{rule_id}/replacement-rules/{replacement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a replacement rule.",
)
async def delete_replacement_rule(
    rule_id: str,
    replacement_id: str,
    replacement_repo: ReplacementRuleRepository = Depends(get_replacement_repository),
    _: str = Depends(get_current_operator),
) -> None:
    """Delete a replacement rule by its ID.

    Note: rule_id is accepted for URL consistency but is NOT validated against the
    replacement's forwarding_rule_id. This is an accepted MVP simplification.
    Returns 404 if replacement_id does not exist.
    """
    use_case = DeleteReplacement(replacement_repo)
    await use_case.execute(replacement_id)
