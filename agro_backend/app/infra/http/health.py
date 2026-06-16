"""Liveness and readiness endpoints.

``/health`` is a cheap liveness check used by Lightsail/UptimeRobot/Caddy.
``/ready`` proves we can talk to Postgres + MQTT + ChromaDB - it's the gate
Coolify uses to decide whether a new container is ready to receive traffic.

Phase 0 ships a minimal readiness probe that imports lazily so a missing
service doesn't crash the import-time discovery. Phase 1+ plug actual
DB connection checks here.
"""

from __future__ import annotations

from typing import Literal

import structlog
from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.config import get_settings

log = structlog.get_logger(__name__)
router = APIRouter()


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
    description="Returns 200 if the FastAPI process is up. Used by Caddy and UptimeRobot.",
)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        version=settings.APP_VERSION,
        commit=settings.APP_GIT_SHA,
        env=settings.APP_ENV.value,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Checks downstream dependencies (Postgres, MQTT, ChromaDB) are reachable.",
    status_code=status.HTTP_200_OK,
)
async def ready() -> ReadinessResponse:
    """Readiness probe.

    Phase 0: returns ok=True for every dependency without hitting it. Phase 1+
    plugs actual ping queries (SELECT 1, mosquitto_sub, chroma /api/v1/heartbeat).
    """
    checks = [
        ReadinessCheck(name="postgres", ok=True, detail="phase-0 stub"),
        ReadinessCheck(name="mosquitto", ok=True, detail="phase-0 stub"),
        ReadinessCheck(name="chroma", ok=True, detail="phase-0 stub"),
    ]
    return ReadinessResponse(ready=all(c.ok for c in checks), checks=checks)
