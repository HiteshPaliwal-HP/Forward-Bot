"""Router for operator authentication and session management."""
from fastapi import APIRouter, Depends, Response, HTTPException, status
from pydantic import BaseModel
from itsdangerous import TimestampSigner
import secrets

from forward_bot.api.dependencies.auth import get_settings, get_current_operator
from forward_bot.config import Settings

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str


@router.get("/me")
async def get_me(_: str = Depends(get_current_operator)) -> dict[str, bool]:
    """Check current authentication status."""
    return {"ok": True}


@router.post("/login")
async def login(
    payload: LoginRequest,
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    """Authenticate with API key and set session cookie."""
    if secrets.compare_digest(payload.api_key, settings.api_key):
        signer = TimestampSigner(settings.secret_key)
        # Sign the 'operator' value as the session payload
        session_val = signer.sign(b"operator").decode("utf-8")
        
        # Set HttpOnly session cookie
        secure_cookie = settings.bind_host != "127.0.0.1"
        response.set_cookie(
            key="session",
            value=session_val,
            max_age=24 * 3600,  # 24 hours
            httponly=True,
            samesite="strict",
            secure=secure_cookie,
        )
        return {"ok": True}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "invalid_credentials",
                "message": "Invalid API key."
            }
        }
    )


@router.post("/logout")
async def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, bool]:
    """Log out by clearing the session cookie."""
    secure_cookie = settings.bind_host != "127.0.0.1"
    response.delete_cookie(
        key="session",
        httponly=True,
        samesite="strict",
        secure=secure_cookie,
    )
    return {"ok": True}
