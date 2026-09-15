"""Liveness and readiness endpoints.

``/health`` is a cheap liveness check used by Lightsail/UptimeRobot/Caddy and by
the container healthcheck — it only proves the FastAPI process is up.

``/ready`` proves we can actually talk to Postgres + MQTT + ChromaDB. It returns
``200`` when every dependency is reachable and ``503`` when any is not, so an
orchestrator / load balancer can gate traffic on it. Each probe is defensive
(wrapped + short timeout) so a down dependency yields ``ok=false`` fast instead
of hanging the request.
"""

from __future__ import annotations

import asyncio
import socket
from typing import Literal

import structlog
from fastapi import APIRouter, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.config import get_settings
from app.infra.http.deps import SessionmakerDep

log = structlog.get_logger(__name__)
router = APIRouter()

# Per-probe budgets. Kept short so /ready never hangs when a dependency is down.
_DB_TIMEOUT_S = 2.0
_TCP_TIMEOUT_S = 1.5


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    version: str = Field(..., description="Application semver.")
    commit: str = Field(..., description="Git SHA at build time, or 'dev' locally.")
    env: str = Field(..., description="Deployment environment.")


class ReadinessCheck(BaseModel):
    name: str
    ok: bool
    detail: str | None = None


class ReadinessResponse(BaseModel):
    ready: bool
    checks: list[ReadinessCheck]


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 if the FastAPI process is up. Used by Caddy, UptimeRobot, and the container healthcheck.",
)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        version=settings.APP_VERSION,
        commit=settings.APP_GIT_SHA,
        env=settings.APP_ENV.value,
    )


async def _check_postgres(sessionmaker: SessionmakerDep) -> ReadinessCheck:
    try:
        async with sessionmaker() as session:
            await asyncio.wait_for(session.execute(text("SELECT 1")), timeout=_DB_TIMEOUT_S)
        return ReadinessCheck(name="postgres", ok=True)
    except Exception as exc:  # readiness probe must never raise
        return ReadinessCheck(name="postgres", ok=False, detail=type(exc).__name__)


def _tcp_reachable(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=_TCP_TIMEOUT_S):
            return True
    except OSError:
        return False


async def _check_tcp(name: str, host: str, port: int) -> ReadinessCheck:
    ok = await asyncio.to_thread(_tcp_reachable, host, port)
    return ReadinessCheck(name=name, ok=ok, detail=None if ok else f"{host}:{port} unreachable")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Checks Postgres (SELECT 1), MQTT, and ChromaDB are reachable; 503 if any is not.",
)
async def ready(sessionmaker: SessionmakerDep, response: Response) -> ReadinessResponse:
    settings = get_settings()
    checks = [
        await _check_postgres(sessionmaker),
        await _check_tcp("mosquitto", settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT),
        await _check_tcp("chroma", settings.CHROMA_HOST, settings.CHROMA_PORT),
    ]
    is_ready = all(c.ok for c in checks)
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        log.warning("readiness.not_ready", failed=[c.name for c in checks if not c.ok])
    return ReadinessResponse(ready=is_ready, checks=checks)
