"""FastAPI dependency providers.

Centralized so route handlers stay focused on request/response shapes
and tests can override single dependencies via ``app.dependency_overrides``.

The wiring is intentionally simple: each provider builds a fresh
adapter on demand, sharing only the long-lived async engine. There is
no DI container; FastAPI's ``Depends()`` is enough for our scale.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.application.ports.ai_suggestion_repo import AiSuggestionRepo
from app.application.ports.alert_repo import AlertRepo
from app.application.ports.auth_session_repo import AuthSessionRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.otp_repo import OtpRepo
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.application.ports.token_issuer import InvalidTokenError, TokenIssuer
from app.application.ports.whatsapp_sender import WhatsappSender
from app.config import AppEnv, Settings, get_settings
from app.domain.auth import AccessClaims
from app.infra.auth.jwt_issuer import JwtIssuer, JwtSettings
from app.infra.persistence.engine import make_async_engine, make_sessionmaker
from app.infra.persistence.pg_ai_suggestion_repo import PgAiSuggestionRepo
from app.infra.persistence.pg_alert_repo import PgAlertRepo
from app.infra.persistence.pg_auth_session_repo import PgAuthSessionRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo
from app.infra.persistence.pg_otp_repo import PgOtpRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.infra.persistence.pg_reading_repo import PgReadingRepo
from app.infra.whatsapp.log_only_sender import LogOnlyWhatsappSender
from app.infra.whatsapp.meta_cloud_sender import (
    MetaCloudSettings,
    MetaCloudWhatsappSender,
)

# ---------------------------------------------------------------------------
# Singletons. Created lazily on first request; the app lifespan disposes them.
# ---------------------------------------------------------------------------
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker | None = None


def _ensure_engine(settings: Settings) -> async_sessionmaker:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine = make_async_engine(
            settings.DATABASE_URL,
            pool_size=settings.DB_POOL_SIZE,
            max_overflow=settings.DB_MAX_OVERFLOW,
        )
        _sessionmaker = make_sessionmaker(_engine)
    return _sessionmaker


async def shutdown_engine() -> None:
    """Lifespan hook - dispose the shared engine on app shutdown."""
    global _engine, _sessionmaker
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _sessionmaker = None


# ---------------------------------------------------------------------------
# Repo + sender + token-issuer providers
# ---------------------------------------------------------------------------
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_sessionmaker(settings: SettingsDep) -> async_sessionmaker:
    return _ensure_engine(settings)


SessionmakerDep = Annotated[async_sessionmaker, Depends(get_sessionmaker)]


def get_farmer_repo(sm: SessionmakerDep) -> FarmerRepo:
    return PgFarmerRepo(sm)


def get_otp_repo(sm: SessionmakerDep) -> OtpRepo:
    return PgOtpRepo(sm)


def get_auth_session_repo(sm: SessionmakerDep) -> AuthSessionRepo:
    return PgAuthSessionRepo(sm)


def get_plot_repo(sm: SessionmakerDep) -> PlotRepo:
    return PgPlotRepo(sm)


def get_reading_repo(sm: SessionmakerDep) -> ReadingRepo:
    return PgReadingRepo(sm)


def get_alert_repo(sm: SessionmakerDep) -> AlertRepo:
    return PgAlertRepo(sm)


def get_ai_suggestion_repo(sm: SessionmakerDep) -> AiSuggestionRepo:
    return PgAiSuggestionRepo(sm)


def get_token_issuer(settings: SettingsDep) -> TokenIssuer:
    return JwtIssuer(
        JwtSettings(
            secret=settings.AUTH_JWT_SECRET.get_secret_value(),
            algorithm=settings.AUTH_JWT_ALGORITHM,
            issuer=settings.AUTH_JWT_ISSUER,
            audience=settings.AUTH_JWT_AUDIENCE,
            access_ttl_seconds=settings.AUTH_JWT_ACCESS_TTL_SECONDS,
        )
    )


def get_whatsapp_sender(settings: SettingsDep) -> WhatsappSender:
    """Pick the right adapter based on env.

    Dev/test default to log-only (no Meta dependency). Production uses
    the real Meta adapter; the config validator refuses to boot without
    the Meta credentials when APP_ENV=production.
    """
    if (
        settings.APP_ENV is AppEnv.PRODUCTION
        and settings.META_WHATSAPP_TOKEN.get_secret_value()
        and settings.META_WHATSAPP_PHONE_NUMBER_ID
    ):
        return MetaCloudWhatsappSender(
            MetaCloudSettings(
                graph_version=settings.META_WHATSAPP_GRAPH_VERSION,
                phone_number_id=settings.META_WHATSAPP_PHONE_NUMBER_ID,
                access_token=settings.META_WHATSAPP_TOKEN.get_secret_value(),
            )
        )
    return LogOnlyWhatsappSender()


# ---------------------------------------------------------------------------
# Auth: extract + verify the bearer token, return the access claims.
# ---------------------------------------------------------------------------
_bearer = HTTPBearer(auto_error=False)


def get_current_claims(
    issuer: Annotated[TokenIssuer, Depends(get_token_issuer)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    _request: Request,
) -> AccessClaims:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "missing_token"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return issuer.verify_access_token(credentials.credentials)
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "invalid_token", "reason": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


ClaimsDep = Annotated[AccessClaims, Depends(get_current_claims)]


def get_current_farmer_id(claims: ClaimsDep) -> uuid.UUID:
    """Convenience: pull the subject UUID out of the claims."""
    return claims.subject


__all__ = [
    "ClaimsDep",
    "SessionmakerDep",
    "SettingsDep",
    "get_ai_suggestion_repo",
    "get_alert_repo",
    "get_auth_session_repo",
    "get_current_claims",
    "get_current_farmer_id",
    "get_farmer_repo",
    "get_otp_repo",
    "get_plot_repo",
    "get_reading_repo",
    "get_sessionmaker",
    "get_token_issuer",
    "get_whatsapp_sender",
    "shutdown_engine",
]
