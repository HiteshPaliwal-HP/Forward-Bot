"""FastAPI router for Telegram auth lifecycle management."""
import time
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from telethon import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
)

from forward_bot.api.dependencies.auth import get_current_operator
from forward_bot.api.dependencies.providers import get_telegram_client
from forward_bot.infrastructure.telegram.client import TelegramClientHolder
from forward_bot.infrastructure.logging import logger

router = APIRouter(prefix="/api/v1/telegram/auth", tags=["telegram-auth"])

# In-memory authentication state (10 min TTL)
# Schema: {"current": {"phone": str, "phone_code_hash": str, "expires_at": float}}
AUTH_STATE: Dict[str, Any] = {}

E164_REGEX = re.compile(r"^\+[1-9]\d{6,14}$")


class AuthStartRequest(BaseModel):
    phone: str | None = None


class AuthVerifyRequest(BaseModel):
    otp: str | None = None
    password: str | None = None


def mask_phone(phone: str | None) -> str | None:
    """Mask phone number for privacy display (e.g. +123****7890)."""
    if not phone:
        return None
    phone_str = str(phone).strip()
    if len(phone_str) <= 6:
        return phone_str[:2] + "****"
    prefix = phone_str[:3]
    suffix = phone_str[-4:]
    masked_middle = "*" * (len(phone_str) - 7)
    return f"{prefix}{masked_middle}{suffix}"


def get_active_auth_state() -> Dict[str, Any] | None:
    """Retrieve non-expired active auth state from memory."""
    state = AUTH_STATE.get("current")
    if not state:
        return None
    if time.time() > state.get("expires_at", 0):
        AUTH_STATE.clear()
        return None
    return state


@router.get("/status")
async def get_auth_status(
    request: Request,
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
):
    """Fetch current Telegram connection status, masked phone, and session metadata."""
    settings = getattr(request.app.state, "settings", tg_client.settings)
    telegram_phone = getattr(settings, "telegram_phone", None) if settings else None
    phone_required = not bool(telegram_phone)
    session_path = ""
    if settings and settings.telegram_session_path:
        session_path = str(Path(settings.telegram_session_path).resolve())

    phone = None
    if telegram_phone:
        phone = mask_phone(telegram_phone)
    elif tg_client.is_connected and tg_client.client is not None:
        try:
            me = await tg_client.client.get_me()
            if me and getattr(me, "phone", None):
                phone = mask_phone(f"+{me.phone}")
        except Exception as e:
            logger.warning("failed_to_get_me_phone", error=str(e))

    return {
        "connected": tg_client.is_connected,
        "phone": phone,
        "phone_required": phone_required,
        "session_path": session_path,
    }


@router.post("/start")
async def start_auth(
    request: Request,
    body: AuthStartRequest,
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
):
    """Initiate Telegram login process by sending OTP code."""
    if tg_client.is_connected:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "already_connected",
                    "message": "Telegram client is already connected."
                }
            }
        )

    # Check for active unexpired auth attempt
    active_state = get_active_auth_state()
    if active_state:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "auth_in_progress",
                    "message": "An authentication process is already in progress."
                }
            }
        )

    settings = getattr(request.app.state, "settings", tg_client.settings)
    if settings is None:
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "server_error", "message": "Application settings missing."}}
        )

    phone_number = body.phone or settings.telegram_phone
    if not phone_number:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "missing_phone", "message": "Phone number is required."}}
        )

    phone_number = phone_number.strip()
    if not E164_REGEX.match(phone_number):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "invalid_phone",
                    "message": "Phone number must be formatted in E.164 format (e.g. +1234567890)."
                }
            }
        )

    session_path = Path(settings.telegram_session_path).resolve()
    session_path.parent.mkdir(parents=True, exist_ok=True)

    if tg_client.client is None:
        tg_client.client = TelegramClient(
            str(session_path),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )

    if not tg_client.client.is_connected():
        await tg_client.client.connect()

    try:
        res = await tg_client.client.send_code_request(phone_number)
        phone_code_hash = getattr(res, "phone_code_hash", None)
        AUTH_STATE["current"] = {
            "phone": phone_number,
            "phone_code_hash": phone_code_hash,
            "expires_at": time.time() + 600,  # 10 minute window
        }
        logger.info("telegram_otp_sent", phone=mask_phone(phone_number))
        return {"status": "code_sent"}
    except Exception as e:
        logger.error("telegram_send_code_failed", error=str(e))
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "send_code_failed", "message": str(e)}}
        )


@router.post("/verify")
async def verify_auth(
    request: Request,
    body: AuthVerifyRequest,
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
):
    """Verify OTP code or 2FA password to complete Telegram authentication."""
    if tg_client.is_connected:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "already_connected",
                    "message": "Telegram client is already connected."
                }
            }
        )

    state = get_active_auth_state()
    if not state:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "otp_expired",
                    "message": "OTP session expired or not started."
                }
            }
        )

    phone = state["phone"]
    phone_code_hash = state["phone_code_hash"]

    if tg_client.client is None:
        settings = getattr(request.app.state, "settings", tg_client.settings)
        if settings is None:
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "server_error", "message": "Application settings missing."}}
            )
        session_path = Path(settings.telegram_session_path).resolve()
        tg_client.client = TelegramClient(
            str(session_path),
            settings.telegram_api_id,
            settings.telegram_api_hash,
        )

    if not tg_client.client.is_connected():
        await tg_client.client.connect()

    try:
        if body.password:
            await tg_client.client.sign_in(password=body.password)
        else:
            if not body.otp:
                return JSONResponse(
                    status_code=400,
                    content={"error": {"code": "invalid_otp", "message": "OTP code is required."}}
                )
            await tg_client.client.sign_in(phone=phone, code=body.otp, phone_code_hash=phone_code_hash)

        # Successful authorization
        AUTH_STATE.clear()
        settings = getattr(request.app.state, "settings", tg_client.settings)
        await tg_client.reconnect(settings)
        logger.info("telegram_auth_successful", phone=mask_phone(phone))
        return {"status": "connected"}

    except SessionPasswordNeededError:
        logger.info("telegram_auth_requires_2fa", phone=mask_phone(phone))
        return JSONResponse(status_code=202, content={"requires_2fa": True})
    except (PhoneCodeInvalidError, PasswordHashInvalidError):
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "invalid_otp",
                    "message": "Invalid OTP code or password provided."
                }
            }
        )
    except PhoneCodeExpiredError:
        AUTH_STATE.clear()
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "otp_expired",
                    "message": "OTP code has expired. Please request a new code."
                }
            }
        )
    except Exception as e:
        logger.error("telegram_verify_failed", error=str(e))
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "verify_failed", "message": str(e)}}
        )


@router.post("/terminate")
async def terminate_auth(
    tg_client: TelegramClientHolder = Depends(get_telegram_client),
    _: str = Depends(get_current_operator),
):
    """Terminate the active Telegram session mid-runtime."""
    if not tg_client.is_connected:
        return JSONResponse(
            status_code=409,
            content={
                "error": {
                    "code": "not_connected",
                    "message": "Telegram client is not currently connected."
                }
            }
        )

    await tg_client.terminate()
    return {"status": "terminated"}
