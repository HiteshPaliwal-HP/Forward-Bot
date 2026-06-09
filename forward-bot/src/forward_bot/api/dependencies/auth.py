"""FastAPI dependencies for operator authentication."""
import secrets
from fastapi import Header, Cookie, Depends, HTTPException, status, Request
from itsdangerous import TimestampSigner, SignatureExpired, BadTimeSignature

from forward_bot.config import Settings


def get_settings(request: Request) -> Settings:
    """Dependency to retrieve the application settings."""
    return request.app.state.settings


def verify_session_cookie(cookie_val: str, secret_key: str) -> bool:
    """Verify the signature and age of a session cookie."""
    try:
        signer = TimestampSigner(secret_key)
        # TTL is 24 hours (86400 seconds)
        unsigned_val = signer.unsign(cookie_val, max_age=24 * 3600)
        return unsigned_val.decode("utf-8") == "operator"
    except (SignatureExpired, BadTimeSignature):
        return False


async def get_current_operator(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    session: str | None = Cookie(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    """Dependency to validate the API key header or session cookie."""
    # 1. Check programmatic clients (X-API-Key header)
    if x_api_key and secrets.compare_digest(x_api_key, settings.api_key):
        return "operator"

    # 2. Check UI clients (session cookie)
    if session and verify_session_cookie(session, settings.secret_key):
        return "operator"

    # 3. Reject unauthorized requests
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "unauthorized",
                "message": "Invalid API Key or session cookie"
            }
        }
    )
