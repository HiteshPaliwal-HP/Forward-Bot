"""FastAPI router for source catalog management."""
from fastapi import APIRouter, Depends, status

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_source_repository, get_telegram_client
from forward_bot.api.schemas.source import SourceRegisterRequest, SourceResponse
from forward_bot.application.sources.register_source import RegisterSource
from forward_bot.application.sources.delete_source import DeleteSource
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
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> None:
    """Delete a registered source if it is not currently referenced by any forwarding rules."""
    use_case = DeleteSource(source_repo)
    await use_case.execute(source_id)
