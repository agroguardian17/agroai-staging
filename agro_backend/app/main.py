"""FastAPI application factory.

Phase 0 deliverables:
- ``GET /api/v1/health`` returns ``{status, version, commit, env}``.
- ``GET /api/v1/ready`` checks DB + MQTT + Chroma reachability (Phase 0
  ships a basic readiness probe; subsequent phases extend it).
- ``GET /metrics`` exposes Prometheus counters (Tailscale-only via Caddy in prod).
- structlog + Sentry are initialized in the lifespan.
- CORS is locked down to the comma-separated origins in CORS_ALLOWED_ORIGINS.

Hardware-enablement round: the MQTT :class:`IngestBroker` is now
constructed and started inside :func:`lifespan` (see
``app.jobs.ingest_startup``). Prior to this, ``uvicorn app.main:app``
did not consume MQTT messages - the broker had to be spawned manually.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.config import get_settings
from app.infra.http import alerts as alert_routes
from app.infra.http import auth as auth_routes
from app.infra.http import health
from app.infra.http import plots as plot_routes
from app.infra.http.deps import shutdown_engine
from app.jobs.ingest_startup import build_and_start_ingest, stop_ingest
from app.lib import metrics
from app.lib.logging import configure_logging

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from app.infra.mqtt.broker import IngestBroker

log = structlog.get_logger(__name__)


# ----- Lifespan ----------------------------------------------------------
@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Process-wide startup/shutdown.

    Order matters: logging first (so subsequent components emit structured
    events), Sentry second, MQTT IngestBroker last (so it can log through
    the configured logger and any subsequent errors go to Sentry).
    """
    configure_logging()
    settings = get_settings()
    _init_sentry(settings)
    log.info(
        "app.startup",
        env=settings.APP_ENV,
        version=settings.APP_VERSION,
        commit=settings.APP_GIT_SHA,
        calibration_mode=settings.CALIBRATION_MODE,
    )
    broker: IngestBroker | None = None
    try:
        broker = await build_and_start_ingest(settings)
        yield
    finally:
        if broker is not None:
            await stop_ingest(broker)
        await shutdown_engine()
        log.info("app.shutdown")


def _init_sentry(settings: Any) -> None:
    """Initialize Sentry only when DSN is set and we're not in tests."""
    if not settings.sentry_enabled:
        return
    import sentry_sdk
    from sentry_sdk.integrations.asyncio import AsyncioIntegration
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.APP_ENV,
        release=f"{settings.APP_VERSION}+{settings.APP_GIT_SHA}",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        send_default_pii=False,  # we strictly never log PII (.cursorrules #24)
        integrations=[
            FastApiIntegration(),
            StarletteIntegration(),
            AsyncioIntegration(),
        ],
    )


# ----- App factory -------------------------------------------------------
def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="AgroGuardian V2 API",
        version=settings.APP_VERSION,
        description="Precision agriculture platform - hexagonal FastAPI monolith.",
        openapi_url="/api/v1/openapi.json",
        docs_url=None if settings.is_production else "/api/v1/docs",
        redoc_url=None if settings.is_production else "/api/v1/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )
    if settings.trusted_hosts != ["*"]:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)

    app.middleware("http")(_metrics_middleware)

    # Routers
    app.include_router(health.router, prefix="/api/v1", tags=["health"])
    app.include_router(auth_routes.router)
    app.include_router(auth_routes.me_router)
    app.include_router(plot_routes.router)
    app.include_router(alert_routes.router)

    # Prometheus exposition. In production, Caddy gates this to Tailscale only.
    @app.get("/metrics", include_in_schema=False)
    async def metrics_endpoint() -> Response:
        return Response(content=generate_latest(metrics.REGISTRY), media_type=CONTENT_TYPE_LATEST)

    return app


async def _metrics_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    """Record request count + latency keyed by route template (not raw path)."""
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = time.perf_counter() - start
        route = request.scope.get("route")
        route_template = getattr(route, "path", request.url.path)
        status = str(response.status_code) if response is not None else "500"
        metrics.http_requests_total.labels(
            method=request.method, route=route_template, status=status
        ).inc()
        metrics.http_request_duration_seconds.labels(
            method=request.method, route=route_template
        ).observe(elapsed)


# Module-level instance for uvicorn / Coolify.
app: FastAPI = create_app()


__all__ = ["app", "create_app"]
