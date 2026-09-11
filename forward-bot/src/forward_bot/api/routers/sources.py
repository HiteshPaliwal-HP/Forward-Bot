"""FastAPI router for source catalog management."""
from fastapi import APIRouter, Depends, status, Query, HTTPException, BackgroundTasks
from motor.motor_asyncio import AsyncIOMotorDatabase

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_source_repository, get_telegram_client, get_db
from forward_bot.infrastructure.cache.cache_refresher import trigger_cache_rebuild
from forward_bot.api.schemas.source import (
    SourceRegisterRequest,
    SourceResponse,
    SourcesPagedResponse,
    SourceUpdateRequest,
    SourcePatchRequest,
)
from forward_bot.application.sources.register_source import RegisterSource
from forward_bot.application.sources.delete_source import DeleteSource
from forward_bot.application.sources.list_sources import ListSources
from forward_bot.application.sources.update_source import UpdateSource
from forward_bot.domain.exceptions import SourceNotFoundException
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository
from forward_bot.infrastructure.telegram.client import TelegramClientHolder

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])


@router.post(
    "",
    response_model=SourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Telegram source channel or group."
)
async def register_source(
    payload: SourceRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    source_repo: SourceRepository = Depends(get_source_repository),
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
) -> SourceResponse:
    """Resolves a Telegram reference (username or numeric ID) and registers it as a Source."""
    use_case = RegisterSource(source_repo, tg_client)
    source = await use_case.execute(
        telegram_reference=payload.telegram_reference,
        display_name=payload.display_name
    )
    background_tasks.add_task(trigger_cache_rebuild, db)
    return SourceResponse.from_entity(source)


@router.get(
    "/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve a registered source by its stable internal ID."
)
async def get_source(
    source_id: str,
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> SourceResponse:
    """Fetch a source by its internal hex string ID."""
    source = await source_repo.get_source_by_id(source_id)
    if not source:
        raise SourceNotFoundException(source_id)
    return SourceResponse.from_entity(source)


@router.delete(
    "/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an unreferenced source."
)
async def delete_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> None:
    """Delete a registered source if it is not currently referenced by any forwarding rules."""
    use_case = DeleteSource(source_repo)
    await use_case.execute(source_id)
    background_tasks.add_task(trigger_cache_rebuild, db)


@router.get(
    "",
    response_model=SourcesPagedResponse,
    status_code=status.HTTP_200_OK,
    summary="List all registered sources with pagination and filters."
)
async def list_sources(
    type: str | None = Query(None),
    folder_id: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> SourcesPagedResponse:
    # Validate type
    if type is not None and type not in ("channel", "group"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Type must be strictly 'channel' or 'group'."
        )

    # Validate folder_id format
    if folder_id is not None and folder_id != "null":
        from bson import ObjectId
        if not ObjectId.is_valid(folder_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid folder_id format."
            )

    # Enforce page size limit: capped at 200
    page_size = min(page_size, 200)

    use_case = ListSources(source_repo)
    items, total = await use_case.execute(
        filter_type=type,
        folder_id=folder_id,
        page=page,
        page_size=page_size
    )

    return SourcesPagedResponse(
        items=[SourceResponse.from_entity(item) for item in items],
        total=total,
        page=page,
        page_size=page_size
    )


@router.put(
    "/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a registered source entirely."
)
async def update_source(
    source_id: str,
    payload: SourceUpdateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> SourceResponse:
    # Validate source_id validity
    from bson import ObjectId
    if not ObjectId.is_valid(source_id):
        raise SourceNotFoundException(source_id)

    use_case = UpdateSource(source_repo)
    update_fields = payload.model_dump()
    source = await use_case.execute(
        source_id=source_id,
        update_fields=update_fields,
        partial=False
    )
    background_tasks.add_task(trigger_cache_rebuild, db)
    return SourceResponse.from_entity(source)


@router.patch(
    "/{source_id}",
    response_model=SourceResponse,
    status_code=status.HTTP_200_OK,
    summary="Partially update a registered source."
)
async def patch_source(
    source_id: str,
    payload: SourcePatchRequest,
    background_tasks: BackgroundTasks,
    db: AsyncIOMotorDatabase = Depends(get_db),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> SourceResponse:
    # Validate source_id validity
    from bson import ObjectId
    if not ObjectId.is_valid(source_id):
        raise SourceNotFoundException(source_id)

    use_case = UpdateSource(source_repo)
    update_fields = payload.model_dump(exclude_unset=True)
    source = await use_case.execute(
        source_id=source_id,
        update_fields=update_fields,
        partial=True
    )
    background_tasks.add_task(trigger_cache_rebuild, db)
    return SourceResponse.from_entity(source)


