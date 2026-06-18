"""FastAPI router for folder management."""
from fastapi import APIRouter, Depends, status, Query
from bson import ObjectId

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_folder_repository, get_source_repository
from forward_bot.api.schemas.folder import (
    FolderCreateRequest,
    FolderUpdateRequest,
    FolderResponse,
    FolderDetailsResponse,
)
from forward_bot.application.folders.create_folder import CreateFolder
from forward_bot.application.folders.list_folders import ListFolders
from forward_bot.application.folders.get_folder import GetFolder
from forward_bot.application.folders.rename_folder import RenameFolder
from forward_bot.application.folders.delete_folder import DeleteFolder
from forward_bot.domain.exceptions import FolderNotFoundException
from forward_bot.infrastructure.mongo.repositories.folder_repository import FolderRepository
from forward_bot.infrastructure.mongo.repositories.source_repository import SourceRepository

router = APIRouter(prefix="/api/v1/folders", tags=["folders"])


@router.post(
    "",
    response_model=FolderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new folder."
)
async def create_folder(
    payload: FolderCreateRequest,
    folder_repo: FolderRepository = Depends(get_folder_repository),
    _: str = Depends(get_current_operator),
) -> FolderResponse:
    """Creates a new folder with a unique name."""
    use_case = CreateFolder(folder_repo)
    folder = await use_case.execute(name=payload.name)
    return FolderResponse.from_entity(folder)


@router.get(
    "",
    response_model=list[FolderResponse],
    status_code=status.HTTP_200_OK,
    summary="List folders."
)
async def list_folders(
    name: str | None = Query(None),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    _: str = Depends(get_current_operator),
) -> list[FolderResponse]:
    """Retrieve list of folders, optionally filtered by name (case-insensitive duplicate check)."""
    use_case = ListFolders(folder_repo)
    results = await use_case.execute(name_filter=name)
    return [
        FolderResponse(
            id=r["id"],
            name=r["name"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
            source_count=r["source_count"]
        )
        for r in results
    ]


@router.get(
    "/{folder_id}",
    response_model=FolderDetailsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get folder details."
)
async def get_folder(
    folder_id: str,
    include: str | None = Query(None),
    folder_repo: FolderRepository = Depends(get_folder_repository),
    source_repo: SourceRepository = Depends(get_source_repository),
    _: str = Depends(get_current_operator),
) -> FolderDetailsResponse:
    """Get details of a folder. If ?include=sources is set, embeds referencing sources."""
    if not ObjectId.is_valid(folder_id):
        raise FolderNotFoundException(folder_id)

    include_sources = (include == "sources")
    use_case = GetFolder(folder_repo, source_repo)
    folder, sources = await use_case.execute(folder_id, include_sources=include_sources)

    if sources is not None:
        source_count = len(sources)
    else:
        source_count = await source_repo.collection.count_documents({"folder_id": ObjectId(folder_id)})

    return FolderDetailsResponse.from_entity_with_sources(
        folder=folder,
        sources=sources,
        source_count=source_count
    )


@router.put(
    "/{folder_id}",
    response_model=FolderResponse,
    status_code=status.HTTP_200_OK,
    summary="Rename a folder."
)
async def rename_folder(
    folder_id: str,
    payload: FolderUpdateRequest,
    folder_repo: FolderRepository = Depends(get_folder_repository),
    _: str = Depends(get_current_operator),
) -> FolderResponse:
    """Rename folder by ID, checking name uniqueness (self-rename allowed)."""
    if not ObjectId.is_valid(folder_id):
        raise FolderNotFoundException(folder_id)

    use_case = RenameFolder(folder_repo)
    folder = await use_case.execute(folder_id=folder_id, new_name=payload.name)
    return FolderResponse.from_entity(folder)


@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a folder."
)
async def delete_folder(
    folder_id: str,
    folder_repo: FolderRepository = Depends(get_folder_repository),
    _: str = Depends(get_current_operator),
) -> None:
    """Delete folder by ID, disassociating all its sources."""
    if not ObjectId.is_valid(folder_id):
        raise FolderNotFoundException(folder_id)

    use_case = DeleteFolder(folder_repo)
    await use_case.execute(folder_id)
