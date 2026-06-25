"""Router for listing media replacement images."""
from fastapi import APIRouter, Depends
from forward_bot.api.dependencies.auth import get_settings, get_current_operator
from forward_bot.config import Settings

router = APIRouter(prefix="/api/v1/media", tags=["media"])


@router.get("/replacement-images", response_model=list[str])
async def list_replacement_images(
    settings: Settings = Depends(get_settings),
    _: str = Depends(get_current_operator),
) -> list[str]:
    """List all available replacement images in the configured base directory."""
    base_dir = settings.get_media_replacement_dir()
    if not base_dir.exists():
        # Auto-create directory if it doesn't exist
        base_dir.mkdir(parents=True, exist_ok=True)
        return []

    # Get filenames, filter for files only (not subdirectories)
    return [entry.name for entry in base_dir.iterdir() if entry.is_file()]
