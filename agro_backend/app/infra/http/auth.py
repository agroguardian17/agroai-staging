"""Auth routes: /auth/send_otp, /auth/verify_otp, /auth/refresh, /auth/logout, /me."""


from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.application import logout as logout_uc
from app.application import refresh_token as refresh_uc
from app.application import send_otp as send_otp_uc
from app.application import verify_otp as verify_otp_uc
from app.application.ports.auth_session_repo import AuthSessionRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.otp_repo import OtpRepo
from app.application.ports.token_issuer import TokenIssuer
from app.application.ports.whatsapp_sender import WhatsappSender
from app.config import OtpTransport, Settings
from app.domain.auth import OtpTransport as DomainOtpTransport
from app.infra.http.deps import (
    ClaimsDep,
    SettingsDep,
    get_auth_session_repo,
    get_farmer_repo,
    get_otp_repo,
    get_token_issuer,
    get_whatsapp_sender,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])




# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------
class SendOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=16, description="E.164, e.g. +918123456789")




class SendOtpResponse(BaseModel):
    challenge_id: uuid.UUID
    expires_at: datetime
    masked_phone: str




class VerifyOtpRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=16)
    code: str = Field(min_length=4, max_length=10)




class TokenPairResponse(BaseModel):
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "bearer"




class RefreshRequest(BaseModel):
    refresh_token: str




class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    everywhere: bool = False




class WhoAmIResponse(BaseModel):
    farmer_id: uuid.UUID
    tenant_id: uuid.UUID
    role: str
    session_id: uuid.UUID | None




# ---------------------------------------------------------------------------
# /auth/send_otp
# ---------------------------------------------------------------------------
def _otp_transport(settings: Settings) -> DomainOtpTransport:
    """Map app config OtpTransport -> domain OtpTransport."""
    if settings.OTP_TRANSPORT is OtpTransport.WHATSAPP:
        return DomainOtpTransport.WHATSAPP
    if settings.OTP_TRANSPORT is OtpTransport.SMS:
        return DomainOtpTransport.SMS
    return DomainOtpTransport.LOG_ONLY




@router.post(
    "/send_otp",
    response_model=SendOtpResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Issue an OTP challenge to a farmer's phone.",
)
async def send_otp(
    payload: SendOtpRequest,
    settings: SettingsDep,
    farmer_repo: Annotated[FarmerRepo, Depends(get_farmer_repo)],
    otp_repo: Annotated[OtpRepo, Depends(get_otp_repo)],
    sender: Annotated[WhatsappSender, Depends(get_whatsapp_sender)],
) -> SendOtpResponse:
    deps = send_otp_uc.SendOtpDeps(
        farmer_repo=farmer_repo,
        otp_repo=otp_repo,
        sender=sender,
        transport=_otp_transport(settings),
        template_name=settings.META_WHATSAPP_OTP_TEMPLATE_NAME,
        code_ttl_seconds=settings.OTP_CODE_TTL_SECONDS,
        max_attempts_per_code=settings.OTP_MAX_ATTEMPTS,
        rate_window_minutes=settings.OTP_LOCKOUT_MINUTES,
    )
    try:
        result = await send_otp_uc.execute(phone=payload.phone, deps=deps)
    except send_otp_uc.UnknownPhoneError as exc:
        # NOTE: we deliberately do NOT distinguish "unknown phone" from
        # the rate-limited case in the response body - that would let an
        # attacker enumerate registered phones. The HTTP status (202) is
        # the same; only the server log records the reason.
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={"status": "accepted"},
        ) from exc
    except send_otp_uc.OtpThrottledError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "rate_limited", "reason": exc.reason},
        ) from exc
    except send_otp_uc.WhatsappDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"error": "delivery_failed", "provider_error": exc.provider_error},
        ) from exc
    return SendOtpResponse(
        challenge_id=result.challenge_id,
        expires_at=result.expires_at,
        masked_phone=result.masked_phone,
    )




# ---------------------------------------------------------------------------
# /auth/verify_otp
# ---------------------------------------------------------------------------
@router.post(
    "/verify_otp",
    response_model=TokenPairResponse,
    summary="Exchange a (phone, code) pair for an access+refresh token pair.",
)
async def verify_otp(
    payload: VerifyOtpRequest,
    request: Request,
    farmer_repo: Annotated[FarmerRepo, Depends(get_farmer_repo)],
    otp_repo: Annotated[OtpRepo, Depends(get_otp_repo)],
    session_repo: Annotated[AuthSessionRepo, Depends(get_auth_session_repo)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
    settings: SettingsDep,
) -> TokenPairResponse:
    deps = verify_otp_uc.VerifyOtpDeps(
        farmer_repo=farmer_repo,
        otp_repo=otp_repo,
        session_repo=session_repo,
        token_issuer=token_issuer,
        refresh_ttl_seconds=settings.AUTH_JWT_REFRESH_TTL_SECONDS,
    )
    try:
        pair = await verify_otp_uc.execute(
            phone=payload.phone,
            code=payload.code,
            deps=deps,
            user_agent=request.headers.get("user-agent"),
            ip_address=request.client.host if request.client else None,
        )
    except verify_otp_uc.NoActiveChallengeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "no_active_challenge"},
        ) from exc
    except verify_otp_uc.ChallengeLockedError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"error": "challenge_locked"},
        ) from exc
    except verify_otp_uc.InvalidOtpError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_otp", "attempts_remaining": exc.attempts_remaining},
        ) from exc
    except verify_otp_uc.FarmerInactiveError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "farmer_inactive"},
        ) from exc
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_expires_at=pair.access_expires_at,
        refresh_expires_at=pair.refresh_expires_at,
    )




# ---------------------------------------------------------------------------
# /auth/refresh
# ---------------------------------------------------------------------------
@router.post(
    "/refresh",
    response_model=TokenPairResponse,
    summary="Rotate a refresh token and return a fresh access+refresh pair.",
)
async def refresh(
    payload: RefreshRequest,
    farmer_repo: Annotated[FarmerRepo, Depends(get_farmer_repo)],
    session_repo: Annotated[AuthSessionRepo, Depends(get_auth_session_repo)],
    token_issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
    settings: SettingsDep,
) -> TokenPairResponse:
    deps = refresh_uc.RefreshTokenDeps(
        farmer_repo=farmer_repo,
        session_repo=session_repo,
        token_issuer=token_issuer,
        refresh_ttl_seconds=settings.AUTH_JWT_REFRESH_TTL_SECONDS,
    )
    try:
        pair = await refresh_uc.execute(refresh_secret=payload.refresh_token, deps=deps)
    except refresh_uc.InvalidRefreshTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_refresh"},
        ) from exc
    return TokenPairResponse(
        access_token=pair.access_token,
        refresh_token=pair.refresh_token,
        access_expires_at=pair.access_expires_at,
        refresh_expires_at=pair.refresh_expires_at,
    )




# ---------------------------------------------------------------------------
# /auth/logout - revoke this device, or all devices.
# ---------------------------------------------------------------------------
class LogoutResponse(BaseModel):
    revoked: int




@router.post(
    "/logout",
    response_model=LogoutResponse,
    summary="Revoke the current refresh token (or all of them).",
)
async def logout(
    payload: LogoutRequest,
    claims: ClaimsDep,
    session_repo: Annotated[AuthSessionRepo, Depends(get_auth_session_repo)],
) -> LogoutResponse:
    deps = logout_uc.LogoutDeps(session_repo=session_repo)
    if payload.everywhere:
        n = await logout_uc.logout_everywhere(farmer_id=claims.subject, deps=deps)
        return LogoutResponse(revoked=n)
    if payload.refresh_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "refresh_token_required"},
        )
    ok = await logout_uc.logout_one(refresh_secret=payload.refresh_token, deps=deps)
    return LogoutResponse(revoked=1 if ok else 0)




# ---------------------------------------------------------------------------
# /api/v1/me - convenience for the mobile client to confirm its token works.
# ---------------------------------------------------------------------------
me_router = APIRouter(prefix="/api/v1", tags=["auth"])




@me_router.get(
    "/me", response_model=WhoAmIResponse, summary="Identity carried by the access token."
)
async def me(claims: ClaimsDep) -> WhoAmIResponse:
    return WhoAmIResponse(
        farmer_id=claims.subject,
        tenant_id=claims.tenant_id,
        role=claims.role.value,
        session_id=claims.session_id,
    )




__all__ = ["me_router", "router"]
