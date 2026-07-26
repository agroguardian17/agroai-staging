#!/usr/bin/env bash
# =============================================================================
# AgroGuardian — Hardware Enablement bootstrap
# =============================================================================
#
# Idempotent: re-running overwrites the same files byte-for-byte. Safe.
#
# What this installs on the Mac at ~/Documents/agri-AI/agro_backend/:
#
#   1. app/main.py                            — lifespan spawns/stops IngestBroker
#   2. app/config.py                          — adds CALIBRATION_MODE flag
#   3. app/application/evaluate_rules.py       — short-circuits when calibrating
#   4. app/jobs/ingest_startup.py             — NEW; builds broker + deps
#   5. scripts/dev/seed_pilot.py              — Main + 2 Sub Nodes + 4 plots
#   6. scripts/dev/provision_mqtt_credential.sh — NEW; adds device creds
#   7. scripts/dev/tail_ingest.py             — NEW; live ingest diagnostics
#   8. docs/HARDWARE_WIRE_CONTRACT.md         — NEW; firmware-facing spec
#   9. deploy/staging/README.md               — NEW; trimmed Lightsail runbook
#
# Usage on the Mac:
#   cd ~/Documents/agri-AI/agro_backend
#   bash /path/to/bootstrap_hardware.sh
#
# After it runs:
#   1. Set CALIBRATION_MODE=true in .env
#   2. Follow deploy/staging/README.md to bring up the Lightsail staging box
#   3. Provision the Main Node MQTT credential
#   4. Bench-test with mosquitto_pub before flashing firmware
# =============================================================================
set -euo pipefail

if [[ ! -f pyproject.toml ]] || ! grep -Eq 'name = "agro[_-]backend"' pyproject.toml 2>/dev/null; then
    echo "ERROR: run this from the agro_backend/ project root." >&2
    echo "       Expected: ~/Documents/agri-AI/agro_backend/" >&2
    exit 1
fi

echo ">>> Hardware Enablement bootstrap"
echo "    Target: $(pwd)"
echo ""

mkdir -p app/jobs app/application app/infra/mqtt
mkdir -p deploy/staging
mkdir -p docs
mkdir -p scripts/dev

write_file() {
    local dest="$1"
    local size
    printf "    writing %-55s" "$dest"
    if [[ -f "$dest" ]]; then
        printf " (overwriting)"
    fi
    printf "\n"
}


write_file app/main.py
cat > app/main.py <<'__AGRO_HW_EOF_1__'
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
__AGRO_HW_EOF_1__

write_file app/config.py
cat > app/config.py <<'__AGRO_HW_EOF_2__'
"""Centralized typed settings loaded from environment variables.

Every setting is declared once here. Code reads ``settings.X`` rather than
``os.environ[...]``, so missing variables are surfaced at startup with a
clear pydantic validation error instead of an opaque KeyError mid-request.

Provider portability charter (roadmap Part 0.5) lives in this file too:
endpoint URLs are env-configurable; no AWS-specific hosts hardcoded.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class OtpTransport(StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"  # only after Phase 13 wires MSG91 adapter


class Settings(BaseSettings):
    """Single source of truth for runtime configuration.

    Validation rules:
    - Production environments must have non-default secrets.
    - URLs are stripped of trailing slashes for predictable joining.
    - Anything that looks like a credential is wrapped in SecretStr so it
      never leaks into ``repr()``, structlog renderers or Sentry breadcrumbs.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----------------------------------------------------------------
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    APP_VERSION: str = "0.0.1"
    APP_GIT_SHA: str = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ---- Database -----------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://agro:agro@localhost:5432/agro",
        description="Async DSN for SQLAlchemy 2.0 / asyncpg.",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://agro:agro@localhost:5432/agro",
        description="Sync DSN for Alembic migrations.",
    )
    POSTGRES_USER: str = "agro"
    POSTGRES_DB: str = "agro"
    POSTGRES_PASSWORD: SecretStr = SecretStr("agro")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT_S: int = 30

    # ---- Auth ---------------------------------------------------------------
    AUTH_JWT_SECRET: SecretStr = SecretStr("CHANGE_ME_dev_only_32_byte_secret")
    AUTH_JWT_ACCESS_TTL_SECONDS: int = 900
    AUTH_JWT_REFRESH_TTL_SECONDS: int = 2_592_000
    AUTH_JWT_ISSUER: str = "agroguardian"
    AUTH_JWT_AUDIENCE: str = "agroguardian-app"
    AUTH_JWT_ALGORITHM: Literal["HS256"] = "HS256"
    OTP_TRANSPORT: OtpTransport = OtpTransport.WHATSAPP
    OTP_CODE_TTL_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_LOCKOUT_MINUTES: int = 30

    # ---- MQTT ---------------------------------------------------------------
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_BROKER_USER: str = "service"
    MQTT_BROKER_PASSWORD: SecretStr = SecretStr("CHANGE_ME")
    MQTT_TLS_CA_PATH: str = "/etc/ssl/certs/ca-certificates.crt"
    MQTT_USE_TLS: bool = False
    MQTT_QUEUE_MAXSIZE: int = 5000

    # ---- Hardware bench flags -----------------------------------------------
    # When True, evaluate_rules.execute short-circuits (no alerts fire, no
    # events publish). Use during initial sensor calibration so unrealistic
    # readings don't spam the dashboard/WhatsApp/push channels. Flip to False
    # once the sensors are dialed in and the ruleset should engage.
    CALIBRATION_MODE: bool = False

    # ---- ChromaDB -----------------------------------------------------------
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_PATH: str = "/data/chroma"
    CHROMA_EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"

    # ---- Anthropic ----------------------------------------------------------
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    ANTHROPIC_MODEL_SONNET: str = "claude-sonnet-4-5"
    ANTHROPIC_MODEL_HAIKU: str = "claude-haiku-4-5"
    USD_INR_RATE: float = 83.0
    LLM_MAX_TOOL_ITER: int = 5

    # ---- WhatsApp / Meta Cloud API ------------------------------------------
    META_WHATSAPP_PHONE_NUMBER_ID: str = ""
    META_WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    META_WHATSAPP_TOKEN: SecretStr = SecretStr("")
    META_WHATSAPP_VERIFY_TOKEN: SecretStr = SecretStr("")
    META_WHATSAPP_OTP_TEMPLATE_NAME: str = "agroguardian_otp_v1"
    META_WHATSAPP_ADVISORY_TEMPLATE_NAME: str = "agroguardian_advisory_v1"
    META_WHATSAPP_GRAPH_VERSION: str = "v20.0"

    # ---- FCM ----------------------------------------------------------------
    FCM_SERVICE_ACCOUNT_JSON_PATH: str = "/secrets/fcm-sa.json"
    FCM_PROJECT_ID: str = ""

    # ---- Satellite ----------------------------------------------------------
    COPERNICUS_CLIENT_ID: str = ""
    COPERNICUS_CLIENT_SECRET: SecretStr = SecretStr("")
    COPERNICUS_BASE_URL: str = "https://sh.dataspace.copernicus.eu"
    COPERNICUS_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    NASA_EARTHDATA_USERNAME: str = ""
    NASA_EARTHDATA_PASSWORD: SecretStr = SecretStr("")

    # ---- Forecast -----------------------------------------------------------
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    IMD_BASE_URL: str = "https://mausam.imd.gov.in/api"

    # ---- Object storage (S3-compatible only; never AWS) ---------------------
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: SecretStr = SecretStr("")
    R2_ENDPOINT_URL: str = ""
    R2_BUCKET_RASTERS: str = "agro-rasters"
    R2_BUCKET_PHOTOS: str = "agro-photos"
    R2_BUCKET_FIRMWARE: str = "agro-firmware"

    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: SecretStr = SecretStr("")
    B2_ENDPOINT_URL: str = ""
    B2_BUCKET_BACKUPS: str = "agro-backups"

    # ---- Monitoring ---------------------------------------------------------
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1
    BETTER_STACK_TOKEN: SecretStr = SecretStr("")
    BETTER_STACK_INGEST_HOST: str = "in.logs.betterstack.com"

    # ---- HTTP / CORS --------------------------------------------------------
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8000,http://localhost:8501"
    TRUSTED_HOSTS: str = "*"

    # ---- OTA (Phase 8) ------------------------------------------------------
    OTA_SIGNING_PRIVATE_KEY_PEM: SecretStr = SecretStr("")
    OTA_SIGNING_PUBLIC_KEY_PEM: str = ""

    # ---- Project paths (resolved at runtime) --------------------------------
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    # ------------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------------
    @field_validator(
        "COPERNICUS_BASE_URL",
        "COPERNICUS_TOKEN_URL",
        "OPEN_METEO_BASE_URL",
        "IMD_BASE_URL",
        "R2_ENDPOINT_URL",
        "B2_ENDPOINT_URL",
        "BETTER_STACK_INGEST_HOST",
    )
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def _cors_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("CORS_ALLOWED_ORIGINS must list at least one origin")
        return v

    @field_validator("APP_ENV", mode="after")
    @classmethod
    def _enforce_production_secrets(cls, v: AppEnv, info: object) -> AppEnv:
        # Note: cross-field validation runs in model_validator below.
        return v

    # ------------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------------
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV is AppEnv.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.APP_ENV is AppEnv.TEST

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.SENTRY_DSN.strip()) and self.APP_ENV is not AppEnv.TEST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached factory. Tests can override by calling ``get_settings.cache_clear()``."""
    settings = Settings()
    if settings.is_production:
        _assert_production_safe(settings)
    return settings


def _assert_production_safe(s: Settings) -> None:
    """Refuse to start in production with obvious dev defaults."""
    fatal: list[str] = []
    if s.AUTH_JWT_SECRET.get_secret_value().startswith("CHANGE_ME"):
        fatal.append("AUTH_JWT_SECRET")
    if s.POSTGRES_PASSWORD.get_secret_value() in {"agro", "CHANGE_ME"}:
        fatal.append("POSTGRES_PASSWORD")
    if s.MQTT_BROKER_PASSWORD.get_secret_value() == "CHANGE_ME":
        fatal.append("MQTT_BROKER_PASSWORD")
    if not s.ANTHROPIC_API_KEY.get_secret_value():
        fatal.append("ANTHROPIC_API_KEY")
    if fatal:
        raise RuntimeError(
            "Refusing to start in production with default/empty secrets: " + ", ".join(fatal)
        )


__all__ = ["AppEnv", "OtpTransport", "Settings", "get_settings"]
__AGRO_HW_EOF_2__

write_file app/application/evaluate_rules.py
cat > app/application/evaluate_rules.py <<'__AGRO_HW_EOF_3__'
"""Use case: evaluate the pilot ruleset against one Reading and persist
the surviving alerts.


Steps:


1. ``metrics.compute(reading)`` builds the DerivedMetrics.
2. ``rules.evaluate_to_hits(reading, metrics, ruleset)`` runs the rules.
3. For each hit: query ``AlertRepo.last_triggered_at`` against the rule's
   ``cooldown_minutes``; suppress when the cooldown hasn't elapsed.
4. Persist surviving candidates via ``AlertRepo.create``.
5. Publish ``alert.created`` on the event bus for each persisted row.


The use case is the seam between the pure rule engine (Round 9) and
the persistence + event-bus side effects. The engine itself stays
pure; the cooldown lookup and write happens here.


CALIBRATION_MODE short-circuit
------------------------------
When ``deps.calibration_mode`` is ``True`` the use case returns a
zero-count result immediately without touching metrics, rules, repo, or
bus. This is the "hardware bench" flag: during initial sensor dial-in
the probes emit unrealistic values that would otherwise trigger every
rule on every reading and spam the dashboard/WhatsApp/push. Flip the
flag off (via the ``CALIBRATION_MODE`` env var) once the sensors are
producing sane values.


PURE w.r.t. imports: stdlib + ports + domain only. No infra imports.
The application-purity AST test enforces this.
"""


from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


from app.application.ports.alert_repo import AlertRepo
from app.application.ports.event_bus import EVENT_ALERT_CREATED, EventBus
from app.domain.alert import AlertCandidate
from app.domain.metrics import MetricsContext, compute
from app.domain.rule_definitions import PILOT_RULESET
from app.domain.rules import Rule, RuleHit, RuleSet, evaluate_to_hits
from app.domain.sensor import Reading




@dataclass(frozen=True, slots=True)
class EvaluateRulesDeps:
    """Ports + the active RuleSet + calibration flag.


    ``ruleset`` defaults to the pilot set; tests can pin a smaller set
    to keep their assertions focused. ``metrics_context`` likewise
    defaults to the standard MetricsContext; future per-plot crop-stage
    awareness will pass a richer one constructed from the CropSeason.


    ``calibration_mode`` short-circuits execute() when True. Wired from
    ``Settings.CALIBRATION_MODE`` in :mod:`app.jobs.ingest_startup`.
    """


    alert_repo: AlertRepo
    event_bus: EventBus
    ruleset: RuleSet = PILOT_RULESET
    metrics_context: MetricsContext = field(default_factory=MetricsContext)
    calibration_mode: bool = False




@dataclass(frozen=True, slots=True)
class EvaluateRulesResult:
    """Counts surfaced as Prometheus deltas by the caller."""


    hits: int
    created: int
    cooldown_suppressed: int




async def execute(
    reading: Reading,
    deps: EvaluateRulesDeps,
    *,
    now: datetime,
) -> EvaluateRulesResult:
    """Run the pipeline; return how many alerts were created vs suppressed."""
    if deps.calibration_mode:
        # Bench mode: rules are disabled. No metrics, no repo, no bus.
        # Ingest still persists the row (that's what we want to inspect).
        return EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0)

    metrics = compute(reading, deps.metrics_context)
    hits = evaluate_to_hits(reading, metrics, deps.ruleset)


    created = 0
    suppressed = 0
    for hit in hits:
        if await _is_in_cooldown(hit.rule, reading.plot_id, now, deps.alert_repo):
            suppressed += 1
            continue
        candidate = _build_candidate(hit, reading, now)
        alert_id = await deps.alert_repo.create(candidate)
        await _publish_alert_created(
            event_bus=deps.event_bus,
            alert_id=alert_id,
            hit=hit,
            reading=reading,
        )
        created += 1


    return EvaluateRulesResult(
        hits=len(hits),
        created=created,
        cooldown_suppressed=suppressed,
    )




# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------




async def _is_in_cooldown(
    rule: Rule,
    plot_id: str,
    now: datetime,
    alert_repo: AlertRepo,
) -> bool:
    """Has the same alert_type fired on this plot within rule.cooldown_minutes?


    AlertRepo.last_triggered_at is keyed by (plot_id, alert_type) not by
    rule_id; two rules that share an alert_type therefore share a
    cooldown. The pilot's only collision is low_battery + battery_critical
    (both AlertType.LOW_BATTERY). The cooldowns are set so battery_critical
    (2h) is shorter than low_battery (12h), so a critical drop after a
    routine low warn fires through.
    """
    last_at = await alert_repo.last_triggered_at(plot_id, rule.alert_type)
    if last_at is None:
        return False
    elapsed_minutes = (now - last_at).total_seconds() / 60.0
    return elapsed_minutes < rule.cooldown_minutes




def _build_candidate(hit: RuleHit, reading: Reading, now: datetime) -> AlertCandidate:
    return AlertCandidate(
        alert_type=hit.rule.alert_type,
        severity=hit.rule.severity,
        alert_message_marathi=hit.render_message(),
        tenant_id=reading.tenant_id,
        farm_id=reading.farm_id,
        farmer_id=reading.farmer_id,
        triggered_at=now,
        device_id=reading.node_id,
        alert_value=_decimal_or_none(hit.substitutions.get("value")),
        alert_threshold=_decimal_or_none(hit.substitutions.get("threshold")),
    )




async def _publish_alert_created(
    *,
    event_bus: EventBus,
    alert_id: int,
    hit: RuleHit,
    reading: Reading,
) -> None:
    """Publish IDs only (Roadmap 1.3 - never full domain objects).


    The dispatcher (Phase 7) will re-fetch the alert by id when it
    needs the full row.
    """
    payload: dict[str, Any] = {
        "alert_id": alert_id,
        "alert_type": hit.rule.alert_type.value,
        "severity": hit.rule.severity.value,
        "rule_id": hit.rule.rule_id,
        "plot_id": reading.plot_id,
        "farmer_id": str(reading.farmer_id),
    }
    await event_bus.publish(EVENT_ALERT_CREATED, payload)




def _decimal_or_none(v: object) -> object:
    """Wrapper around the same helper used by rules.evaluate."""
    from decimal import Decimal


    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str)):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    if isinstance(v, float):
        return Decimal(str(v))
    return None




__all__ = ["EvaluateRulesDeps", "EvaluateRulesResult", "execute"]
__AGRO_HW_EOF_3__

write_file app/jobs/ingest_startup.py
cat > app/jobs/ingest_startup.py <<'__AGRO_HW_EOF_4__'
"""Wire the MQTT :class:`IngestBroker` into the FastAPI lifespan.

Hardware-enablement round: prior to this file, running ``uvicorn`` did
not consume MQTT messages. The comment in ``main.py``'s lifespan said
"later phases register the MQTT broker" - this is that phase.

Two functions:

* :func:`build_and_start_ingest` constructs ``BrokerSettings`` +
  ``ProcessReadingDeps``, instantiates :class:`IngestBroker`, calls
  ``start()``, and returns the handle so the lifespan can shut it
  down cleanly on process exit.
* :func:`stop_ingest` is a thin wrapper for symmetry + a structlog line.

Failure modes:

* If ``MQTT_BROKER_HOST`` is empty we skip and return ``None`` - the
  caller no-ops on shutdown. This is the "MQTT disabled" mode.
* If the broker can't reach Mosquitto at boot, paho auto-retries in
  its own thread; ``start()`` returns cleanly. Metrics + logs surface
  the reconnect attempts.

This module lives in :mod:`app.jobs` (previously an empty package
reserved for the Round 13 subscriber). Placing startup wiring here
keeps ``main.py`` under 200 lines and lets tests exercise the builder
without spinning up FastAPI.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from app.application.evaluate_rules import EvaluateRulesDeps
from app.application.ingest_telemetry import IngestDeps
from app.application.process_reading import ProcessReadingDeps
from app.infra.events.pg_notify_bus import PgNotifyEventBus
from app.infra.http.deps import _ensure_engine
from app.infra.mqtt.broker import BrokerSettings, IngestBroker
from app.infra.persistence.pg_alert_repo import PgAlertRepo
from app.infra.persistence.pg_reading_repo import PgReadingRepo

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_ingest(settings: Settings) -> IngestBroker | None:
    """Construct + start the IngestBroker. Returns None if MQTT is disabled."""
    if not settings.MQTT_BROKER_HOST:
        log.warning("ingest_startup.skipped", reason="MQTT_BROKER_HOST is empty")
        return None

    sessionmaker = _ensure_engine(settings)
    reading_repo = PgReadingRepo(sessionmaker)
    alert_repo = PgAlertRepo(sessionmaker)
    event_bus = PgNotifyEventBus(sessionmaker)

    ingest_deps = IngestDeps(reading_repo=reading_repo, event_bus=event_bus)
    evaluate_deps = EvaluateRulesDeps(
        alert_repo=alert_repo,
        event_bus=event_bus,
        calibration_mode=settings.CALIBRATION_MODE,
    )
    deps = ProcessReadingDeps(ingest_deps=ingest_deps, evaluate_deps=evaluate_deps)

    # ``MQTT_BROKER_USER`` defaults to "service"; treat empty/default as
    # "anonymous". paho will send AUTH only if username is truthy.
    user = settings.MQTT_BROKER_USER or None
    password = (
        settings.MQTT_BROKER_PASSWORD.get_secret_value() or None if user else None
    )

    broker_settings = BrokerSettings(
        host=settings.MQTT_BROKER_HOST,
        port=settings.MQTT_BROKER_PORT,
        username=user,
        password=password,
        use_tls=settings.MQTT_USE_TLS,
        tls_ca_path=settings.MQTT_TLS_CA_PATH if settings.MQTT_USE_TLS else None,
        client_id=f"agro-backend-{settings.APP_ENV.value}",
    )

    broker = IngestBroker(broker_settings, deps, max_queue=settings.MQTT_QUEUE_MAXSIZE)
    await broker.start()
    log.info(
        "ingest_startup.started",
        host=broker_settings.host,
        port=broker_settings.port,
        tls=broker_settings.use_tls,
        calibration_mode=settings.CALIBRATION_MODE,
    )
    return broker


async def stop_ingest(broker: IngestBroker) -> None:
    """Symmetric shutdown for the lifespan cleanup path."""
    await broker.stop()
    log.info("ingest_startup.stopped")


__all__ = ["build_and_start_ingest", "stop_ingest"]
__AGRO_HW_EOF_4__

write_file scripts/dev/seed_pilot.py
cat > scripts/dev/seed_pilot.py <<'__AGRO_HW_EOF_5__'
"""Seed pilot data for the Aurangabad deployment.


Aggregate-mode hardware topology:


* **1 Main Node** (``AGR-MN-0001``, device_type = ``master_node``).
  Owns the MQTT credential. Aggregates LoRa frames from Sub Nodes and
  publishes to ``agro/v2/{tenant}/{farm}/{node}/telemetry`` on behalf
  of each Sub Node (the ``node_id`` in each MQTT payload identifies the
  originating Sub Node, not the Main Node).
* **2 Sub Nodes** (``AGR-SN-0001``, ``AGR-SN-0002``, device_type =
  ``sub_node``). Each Sub Node covers 2 plots.
* **4 Plots** (``PLOT_PILOT_001``..``004``).
  - Plots 001, 002 are covered by Sub Node 1.
  - Plots 003, 004 are covered by Sub Node 2.
* **1 Farmer**, **1 Farm**, **4 active crop seasons** (one per plot;
  ``compose_advisory`` requires an active season for context).


Idempotent: fixed UUIDs, so re-running upserts.


Backward compatibility: the pilot used to be seeded with a single device
``AGR-MH-0001`` mapped to ``PLOT_PILOT_001``. We keep an ON CONFLICT DO
NOTHING for those exact identifiers so old fake_main_node.py invocations
continue to work; the new devices are added alongside.


Run::


    set -a; source .env; set +a
    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"
    python scripts/dev/seed_pilot.py


Reads ``DATABASE_URL_SYNC`` from the shell. Prints the IDs at the end so
you can copy them into ``fake_main_node.py`` + the OTP curl + the Main
Node firmware config.
"""


from __future__ import annotations


import os
import sys
import uuid


from sqlalchemy import create_engine, text


PILOT_TENANT = "11111111-1111-1111-1111-111111111111"


# Stable identifiers - re-running won't multiply rows.
FARMER_ID = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")
FARM_ID = uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222")


# ----- Hardware identities (aggregate mode) -----
MAIN_NODE_ID = "AGR-MN-0001"
SUB_NODE_1_ID = "AGR-SN-0001"
SUB_NODE_2_ID = "AGR-SN-0002"


# ----- Backward-compat sub node (used by earlier tests + fake_main_node.py) -----
LEGACY_DEVICE_ID = "AGR-MH-0001"


# ----- Plots + seasons -----
PLOTS = [
    # (plot_id, sub_node_device_id, season_id, crop_marathi, crop_english)
    ("PLOT_PILOT_001", SUB_NODE_1_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000001"), "कापूस", "Cotton"),
    ("PLOT_PILOT_002", SUB_NODE_1_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000002"), "सोयाबीन", "Soybean"),
    ("PLOT_PILOT_003", SUB_NODE_2_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000003"), "तूर", "Pigeon pea"),
    ("PLOT_PILOT_004", SUB_NODE_2_ID, uuid.UUID("cccccccc-3333-3333-3333-000000000004"), "मका", "Maize"),
]


PHONE = os.environ.get("PILOT_PHONE", "+919999999999")




def main() -> int:
    sync_url = os.environ.get("DATABASE_URL_SYNC")
    if not sync_url:
        print(
            "ERROR: DATABASE_URL_SYNC must be set. Run:\n"
            "    set -a; source .env; set +a\n"
            '    export DATABASE_URL_SYNC="postgresql://agro:$POSTGRES_PASSWORD@localhost:5433/agro"',
            file=sys.stderr,
        )
        return 1


    eng = create_engine(sync_url, future=True)
    with eng.begin() as conn:
        # ---- Farmer ----
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :fid, :tenant, 'Pilot Farmer', 'पायलट शेतकरी', :phone,
                    :phone, 'marathi', 'Aurangabad-V', 'Aurangabad', 'Aurangabad',
                    'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                ON CONFLICT (farmer_id) DO UPDATE
                    SET phone_primary = EXCLUDED.phone_primary,
                        whatsapp_number = EXCLUDED.whatsapp_number
                """
            ),
            {"fid": FARMER_ID, "tenant": PILOT_TENANT, "phone": PHONE},
        )


        # ---- Farm ----
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre,
                    gps_lat_center, gps_lng_center, soil_type,
                    water_source_primary, irrigation_type, electricity_source
                ) VALUES (
                    :farm, :tenant, :farmer, 4.0, 19.9, 75.7, 'black',
                    'well', 'drip', 'grid'
                )
                ON CONFLICT (farm_id) DO NOTHING
                """
            ),
            {"farm": FARM_ID, "tenant": PILOT_TENANT, "farmer": FARMER_ID},
        )


        # ---- Legacy sub node (backward compat with older tests + fake_main_node.py) ----
        conn.execute(
            text(
                """
                INSERT INTO device_registry (
                    device_id, tenant_id, device_type, serial_number,
                    mac_address, qr_code_data, farm_id, device_tier,
                    installation_date, device_status
                ) VALUES (
                    :dev, :tenant, 'sub_node', 'SN-LEGACY-001',
                    'AA:BB:CC:DD:EE:01', 'QR_LEGACY_001', :farm, 'basic',
                    '2025-06-01', 'online'
                )
                ON CONFLICT (device_id) DO NOTHING
                """
            ),
            {"dev": LEGACY_DEVICE_ID, "tenant": PILOT_TENANT, "farm": FARM_ID},
        )


        # ---- Main Node (holds the MQTT credential) ----
        conn.execute(
            text(
                """
                INSERT INTO device_registry (
                    device_id, tenant_id, device_type, serial_number,
                    mac_address, qr_code_data, farm_id, device_tier,
                    installation_date, device_status
                ) VALUES (
                    :dev, :tenant, 'master_node', 'MN-PILOT-001',
                    'AA:BB:CC:DD:EE:MN', 'QR_MN_001', :farm, 'pro',
                    '2026-07-20', 'online'
                )
                ON CONFLICT (device_id) DO NOTHING
                """
            ),
            {"dev": MAIN_NODE_ID, "tenant": PILOT_TENANT, "farm": FARM_ID},
        )


        # ---- Sub Nodes (LoRa endpoints) ----
        for sub_id, mac_tail, serial_tail, qr_tail in [
            (SUB_NODE_1_ID, "S1", "SN-PILOT-01", "QR_SN_01"),
            (SUB_NODE_2_ID, "S2", "SN-PILOT-02", "QR_SN_02"),
        ]:
            conn.execute(
                text(
                    """
                    INSERT INTO device_registry (
                        device_id, tenant_id, device_type, serial_number,
                        mac_address, qr_code_data, farm_id, device_tier,
                        installation_date, device_status
                    ) VALUES (
                        :dev, :tenant, 'sub_node', :serial,
                        :mac, :qr, :farm, 'standard',
                        '2026-07-20', 'online'
                    )
                    ON CONFLICT (device_id) DO NOTHING
                    """
                ),
                {
                    "dev": sub_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "serial": serial_tail,
                    "mac": f"AA:BB:CC:DD:EE:{mac_tail}",
                    "qr": qr_tail,
                },
            )


        # ---- Plots + Crop Seasons ----
        for i, (plot_id, sub_dev, season_id, crop_mr, crop_en) in enumerate(PLOTS):
            conn.execute(
                text(
                    """
                    INSERT INTO plots (
                        plot_id, tenant_id, farm_id, plot_number, area_acre,
                        gps_lat, gps_lng, irrigation_valve_id, node_id
                    ) VALUES (
                        :plot, :tenant, :farm, :n, 1.0, 19.9, 75.7, :valve, :dev
                    )
                    ON CONFLICT (plot_id) DO NOTHING
                    """
                ),
                {
                    "plot": plot_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "n": i + 1,
                    "valve": f"V_{i + 1:03d}",
                    "dev": sub_dev,
                },
            )
            conn.execute(
                text(
                    """
                    INSERT INTO crop_seasons (
                        season_id, tenant_id, farm_id, plot_id, season_name,
                        season_type, year, crop_name_marathi, crop_name_english,
                        crop_variety, crop_category, sowing_date, expected_harvest_date,
                        current_growth_stage, crop_age_days_today, season_status
                    ) VALUES (
                        :sid, :tenant, :farm, :plot, 'Kharif 2026',
                        'kharif', 2026, :cmr, :cen,
                        'default', 'cash_crop', '2026-06-01', '2026-12-01',
                        'vegetative', 50, 'active'
                    )
                    ON CONFLICT (season_id) DO NOTHING
                    """
                ),
                {
                    "sid": season_id,
                    "tenant": PILOT_TENANT,
                    "farm": FARM_ID,
                    "plot": plot_id,
                    "cmr": crop_mr,
                    "cen": crop_en,
                },
            )


    print()
    print("=========================================")
    print("Pilot data seeded successfully")
    print("=========================================")
    print(f"Tenant ID:     {PILOT_TENANT}")
    print(f"Farmer ID:     {FARMER_ID}")
    print(f"Farm ID:       {FARM_ID}")
    print(f"Phone:         {PHONE}")
    print()
    print("Devices (aggregate mode - Main Node owns MQTT credential):")
    print(f"  Main Node:   {MAIN_NODE_ID}    (master_node, pro tier)")
    print(f"  Sub Node 1:  {SUB_NODE_1_ID}   -> PLOT_PILOT_001, PLOT_PILOT_002")
    print(f"  Sub Node 2:  {SUB_NODE_2_ID}   -> PLOT_PILOT_003, PLOT_PILOT_004")
    print(f"  Legacy:      {LEGACY_DEVICE_ID}   (unchanged; older tests + fake_main_node.py)")
    print()
    print("Plots + crops:")
    for plot_id, sub_dev, _sid, cmr, cen in PLOTS:
        print(f"  {plot_id} -> {sub_dev}  crop={cen} ({cmr})")
    print()
    print("MQTT topic pattern (Main Node publishes on behalf of Sub Nodes):")
    print(f"  agro/v2/{PILOT_TENANT}/{FARM_ID}/<sub_node_id>/telemetry")
    print()
    print("Auth: /auth/send_otp body: {{'phone':'" + PHONE + "'}}")
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
__AGRO_HW_EOF_5__

write_file scripts/dev/provision_mqtt_credential.sh
cat > scripts/dev/provision_mqtt_credential.sh <<'__AGRO_HW_EOF_6__'
#!/usr/bin/env bash
# Provision an MQTT credential for a hardware device (Main Node).
#
# Uses the running Mosquitto container's mosquitto_passwd tool to bcrypt
# the password directly into deploy/mosquitto/passwd, then appends the
# ACL entry that scopes this user to publishing telemetry topics only.
#
# Idempotent: if the username already exists in passwd, we UPDATE (mosquitto_passwd
# overwrites the entry). ACL append is guarded with a grep so re-runs don't
# duplicate lines.
#
# Usage:
#   scripts/dev/provision_mqtt_credential.sh <username> <password>
#
# After running:
#   1. Restart the mosquitto container so it picks up the new passwd/acl:
#        docker compose -f docker-compose.dev.yml restart mosquitto
#   2. Test from another machine:
#        mosquitto_pub -h <mac-lan-ip> -p 1883 -u <username> -P <password> \
#          -t 'agro/v2/<tenant>/<farm>/<node>/telemetry' -m '{"$schema":"..."}'
#
# Notes:
# - The listener on port 1883 in the current mosquitto.conf allows anonymous
#   connections. If you want to enforce this credential on 1883 as well as
#   8883, set ``allow_anonymous false`` on the 1883 listener block.
# - Production (Round 15) will use listener 8883 with TLS + this same
#   passwd/acl pair.
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 <username> <password>" >&2
    echo "Example: $0 main-node-001 <strong-random-secret>" >&2
    exit 1
fi

USERNAME="$1"
PASSWORD="$2"

# Locate agro_backend root (this script lives at scripts/dev/).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PASSWD_FILE="$ROOT_DIR/deploy/mosquitto/passwd"
ACL_FILE="$ROOT_DIR/deploy/mosquitto/acl"

if [[ ! -f "$PASSWD_FILE" ]]; then
    echo "ERROR: passwd file not found at $PASSWD_FILE" >&2
    exit 2
fi
if [[ ! -f "$ACL_FILE" ]]; then
    echo "ERROR: acl file not found at $ACL_FILE" >&2
    exit 2
fi

# Ensure the mosquitto container is up so we can invoke its passwd tool.
if ! docker ps --format '{{.Names}}' | grep -q '^agro_mosquitto$'; then
    echo "ERROR: agro_mosquitto container is not running." >&2
    echo "       Start it with: docker compose -f docker-compose.dev.yml up -d mosquitto" >&2
    exit 3
fi

# 1. Set / update the password via mosquitto_passwd inside the container.
#    -b: batch mode (non-interactive)
#    -c: create file (only used if empty; safe to omit because file exists)
echo ">>> Updating $PASSWD_FILE for user '$USERNAME'"
docker exec -i agro_mosquitto mosquitto_passwd -b /mosquitto/config/passwd "$USERNAME" "$PASSWORD"

# 2. Append ACL entry if it isn't already present. Scope: publish + subscribe
#    on ``agro/v2/#``. Tighten to a specific tenant/farm prefix if you're
#    onboarding a multi-tenant deployment.
ACL_LINE_USER="user $USERNAME"
if ! grep -qxF "$ACL_LINE_USER" "$ACL_FILE"; then
    echo ">>> Appending ACL entry for '$USERNAME'"
    {
        echo ""
        echo "# device credential provisioned $(date -u +%Y-%m-%dT%H:%M:%SZ)"
        echo "$ACL_LINE_USER"
        echo "topic write agro/v2/#"
        echo "topic read \$SYS/#"
    } >> "$ACL_FILE"
else
    echo ">>> ACL entry for '$USERNAME' already present; leaving as-is"
fi

echo ""
echo ">>> Restart mosquitto to pick up the new credentials:"
echo "    docker compose -f docker-compose.dev.yml restart mosquitto"
echo ""
echo ">>> Credential summary:"
echo "    username: $USERNAME"
echo "    password: (as supplied, not echoed)"
echo "    ACL scope: publish agro/v2/#"
__AGRO_HW_EOF_6__

write_file scripts/dev/tail_ingest.py
cat > scripts/dev/tail_ingest.py <<'__AGRO_HW_EOF_7__'
"""Live diagnostic tail for MQTT ingest failures.


Reads structlog JSON events off the backend's stdout via ``docker compose
logs -f app`` (or plain uvicorn stdout via a pipe) and prints a compact,
color-tagged line for every ``ingest_broker.*`` event plus every
pydantic validation error, so firmware devs can see exactly what the
backend rejected without grepping through raw JSON.


Usage::


    # Inside agro_backend/ with the dev stack up:
    docker compose -f docker-compose.dev.yml logs -f app | python scripts/dev/tail_ingest.py


    # Or against a raw uvicorn stdout pipe:
    uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | python scripts/dev/tail_ingest.py


Filters (case-insensitive substrings in the ``event`` field):
* ``ingest_broker.``    - broker lifecycle + drops
* ``app.startup``       - config surface at boot (calibration_mode etc.)
* ``ingest_startup.``   - IngestBroker wiring log lines


Non-JSON stdout lines (paho debug etc.) are passed through untouched.


Zero dependencies beyond stdlib.
"""


from __future__ import annotations


import json
import sys
from typing import Any


COLORS: dict[str, str] = {
    "reset": "\033[0m",
    "dim": "\033[2m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "cyan": "\033[36m",
    "magenta": "\033[35m",
}


INTERESTING_PREFIXES: tuple[str, ...] = (
    "ingest_broker.",
    "ingest_startup.",
    "app.startup",
    "app.shutdown",
)




def _colorize(event: str, level: str | None) -> str:
    if event.endswith((".error", "_failed", ".connect_failed", ".unexpected_error")):
        return f"{COLORS['red']}{event}{COLORS['reset']}"
    if "queue_full" in event or "validation_error" in event or "parse_error" in event:
        return f"{COLORS['yellow']}{event}{COLORS['reset']}"
    if event.startswith("app."):
        return f"{COLORS['magenta']}{event}{COLORS['reset']}"
    if level == "warning":
        return f"{COLORS['yellow']}{event}{COLORS['reset']}"
    if level == "error":
        return f"{COLORS['red']}{event}{COLORS['reset']}"
    return f"{COLORS['cyan']}{event}{COLORS['reset']}"




def _format_record(rec: dict[str, Any]) -> str:
    event = str(rec.get("event", ""))
    level = rec.get("level")
    ts = rec.get("timestamp", "")
    # Strip common noise keys so the interesting bits stand out.
    payload = {
        k: v
        for k, v in rec.items()
        if k not in {"event", "level", "timestamp", "logger", "logger_name"}
    }
    payload_str = " ".join(f"{k}={v!r}" for k, v in payload.items())
    return (
        f"{COLORS['dim']}{ts}{COLORS['reset']} "
        f"{_colorize(event, level)} "
        f"{payload_str}"
    )




def _is_interesting(rec: dict[str, Any]) -> bool:
    event = str(rec.get("event", ""))
    if event.startswith(INTERESTING_PREFIXES):
        return True
    # Also surface any error/warning across the app so ingest-adjacent
    # problems (DB timeout, missing plot FK) are visible.
    level = rec.get("level")
    if level in {"warning", "error", "critical"}:
        return True
    return False




def main() -> int:
    for raw in sys.stdin:
        line = raw.rstrip("\n")
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            # Not structured JSON (paho debug, docker prefix, uvicorn header).
            # Pass through so nothing hides from the operator.
            print(line, flush=True)
            continue
        if not isinstance(rec, dict):
            print(line, flush=True)
            continue
        if _is_interesting(rec):
            print(_format_record(rec), flush=True)
    return 0




if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
__AGRO_HW_EOF_7__

write_file docs/HARDWARE_WIRE_CONTRACT.md
cat > docs/HARDWARE_WIRE_CONTRACT.md <<'__AGRO_HW_EOF_8__'
# AgroGuardian Hardware Wire Contract

> **Audience:** Main Node firmware engineers.
> **Truth source:** `app/infra/mqtt/schemas.py::TelemetryIn`.
> If this doc and the code disagree, the code wins — update the doc.

## 1. Topology (aggregate mode)

```
Sub Node 1  ──LoRa──┐
Sub Node 2  ──LoRa──┴──> Main Node ──MQTTS/8883──> AgroGuardian backend
```

Only the **Main Node** speaks MQTT. It aggregates LoRa frames from each Sub Node, unpacks the sensor readings, and publishes **one MQTT message per Sub-Node reading** with that Sub Node's `node_id` in the payload.

The Main Node holds the only MQTT credential. Sub Nodes never authenticate to MQTT directly.

## 2. Transport

| Field | Value |
| :--- | :--- |
| Broker host | `staging.<your-lightsail-ip-with-dashes>.sslip.io` (Round 15 staging) |
| Broker port | `8883` (TLS) — bench-test may use `1883` on the Mac's LAN IP |
| Protocol | MQTT v5 (`mqtt.MQTTv5`) |
| QoS | **1** (at-least-once); the backend deduplicates on `(node_id, recorded_at)` |
| Auth | username + password from `provision_mqtt_credential.sh` |
| TLS | Let's Encrypt cert on port 8883; use the system CA bundle |
| Keepalive | 60 s |
| Reconnect | firmware must auto-reconnect on disconnect |

## 3. Topic pattern

Exactly six slash-separated segments:

```
agro/v2/<tenant_id>/<farm_id>/<node_id>/telemetry
```

- `agro` and `v2` are literal.
- `<tenant_id>` — UUID from `seed_pilot.py` output. For the pilot: `11111111-1111-1111-1111-111111111111`.
- `<farm_id>` — UUID from `seed_pilot.py` output. For the pilot: `bbbbbbbb-2222-2222-2222-222222222222`.
- `<node_id>` — the **originating Sub Node** identifier, not the Main Node. Example: `AGR-SN-0001`.
- `<kind>` — currently only `telemetry` is accepted. Other kinds (`weather`, `heartbeat`, `alert`, `health`) will be added in later rounds; the backend rejects them today with `UnknownTopicKindError`.

**Backend behavior on malformed topic:** log + drop, metric `ingest_dropped_total{reason="parse_error"}` increments.

## 4. Payload — JSON

`Content-Type` is implicit JSON. UTF-8. No BOM. **Unknown fields are rejected** (`extra="forbid"` in the pydantic model), so don't add exploratory fields to the payload — the whole message will be dropped with a validation error.

### 4.1 Required fields

| Field | Type | Notes |
| :--- | :--- | :--- |
| `$schema` | string literal | Must be exactly `"agro-guardian/telemetry/v2"`. |
| `tenant_id` | UUID string | Same as topic's `<tenant_id>`. |
| `farmer_id` | UUID string | From `seed_pilot.py`. Pilot: `aaaaaaaa-1111-1111-1111-111111111111`. |
| `farm_id` | UUID string | Same as topic's `<farm_id>`. |
| `plot_id` | string (1–64 chars) | Which plot this reading covers. Pilot values: `PLOT_PILOT_001` … `PLOT_PILOT_004`. |
| `node_id` | string (1–64 chars) | Same as topic's `<node_id>` — the originating Sub Node. |
| `recorded_at` | RFC 3339 timestamp **with offset** | e.g. `"2026-07-21T13:12:00+00:00"`. Naive timestamps (no `Z`/offset) are rejected. |
| `received_at_master` | RFC 3339 timestamp with offset | When the Main Node received the LoRa frame from the Sub Node. Usually same as `recorded_at` if the Sub Node has an RTC. |
| `transmission_type` | enum string | One of: `"lora"`, `"wifi"`, `"cellular"`, `"ethernet"`. Aggregate mode almost always sends `"lora"`. |

### 4.2 Optional numeric fields (all `null` if unavailable)

Signal / diagnostics:

| Field | Type | Range / units |
| :--- | :--- | :--- |
| `signal_rssi_dbm` | integer | −150 to 20 dBm (LoRa RSSI at Main Node) |
| `firmware_version` | string | e.g. `"sub-node-1.0.0"` |
| `uptime_seconds` | integer ≥ 0 | Sub Node uptime |

Battery:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `battery_voltage_v` | decimal (string or number) | e.g. `3.62` |
| `battery_percent` | decimal | 0–100 |
| `solar_charging` | boolean | true when panel is actively charging |
| `low_battery_flag` | boolean | firmware's own low-battery signal |

Soil:

| Field | Type | Units |
| :--- | :--- | :--- |
| `soil_moisture_1_pct` | decimal | 0–100 % VWC |
| `soil_moisture_2_pct` | decimal | 0–100 % VWC (second probe) |
| `soil_moisture_avg_pct` | decimal | mean of the two probes |
| `soil_temp_c` | decimal | °C |
| `soil_temp_rootzone_c` | decimal | °C at root depth |
| `soil_ph` | decimal | 0–14 |
| `soil_ec_ms_cm` | decimal | mS/cm |
| `soil_n_mg_kg` | decimal | mg N per kg soil |
| `soil_p_mg_kg` | decimal | mg P per kg soil |
| `soil_k_mg_kg` | decimal | mg K per kg soil |
| `soil_n_bucket` | integer 0–63 | if the probe returns bucketed values |
| `soil_p_bucket` | integer 0–63 | ″ |
| `soil_k_bucket` | integer 0–63 | ″ |
| `npk_sensor_raw_hex` | string | raw Modbus frame if useful for diagnostics |

Environment / diagnostics:

| Field | Type | Notes |
| :--- | :--- | :--- |
| `tamper_detected` | boolean | tilt/tamper switch |
| `enclosure_temp_c` | decimal | °C inside the Sub Node enclosure |
| `fault_flags` | string | firmware-defined bitfield encoded as hex or CSV |
| `sensor_health_json` | object | free-form; backend stores as JSONB |
| `cadence_mode` | enum string | `"normal"`, `"conservation"`, `"burst"` — how often this Sub Node samples |
| `backlog_pending` | boolean | true if the Sub Node has unsent readings queued |
| `validation_warn` | boolean | firmware-side pre-flight check flagged the reading |

## 5. Number format — Decimal safety

Every numeric field goes through a **Decimal coercion** at the backend boundary (`Decimal(str(v))`). This dodges float-precision drift like `7.2 → 7.199999…`. Firmware can send numbers as either JSON numbers (`3.62`) or JSON strings (`"3.62"`) — both work. Sending as string avoids any risk of the JSON encoder losing a trailing digit.

**Booleans are strictly booleans.** The backend rejects `0` / `1` in a boolean field with `ValidationError`.

## 6. Timestamp format

RFC 3339, timezone-aware. Both of these are valid:

```
2026-07-21T13:12:00+00:00
2026-07-21T13:12:00.500+05:30
```

**These are all rejected:**

```
2026-07-21T13:12:00        # no timezone
2026-07-21 13:12:00Z       # space instead of T
1721560320                 # unix seconds
```

Recommendation for the Main Node: keep clock in UTC, format with `strftime("%Y-%m-%dT%H:%M:%S+00:00", ...)`. Sub Nodes without an RTC should send their reading time as `received_at_master` (i.e. the time the Main Node saw the frame).

## 7. Two example payloads

### 7.1 Minimal — just the required fields + one sensor

```json
{
  "$schema": "agro-guardian/telemetry/v2",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id":   "PLOT_PILOT_001",
  "node_id":   "AGR-SN-0001",
  "recorded_at":        "2026-07-21T13:12:00+00:00",
  "received_at_master": "2026-07-21T13:12:00+00:00",
  "transmission_type":  "lora",
  "soil_moisture_avg_pct": 42.15
}
```

Published on topic:
```
agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry
```

### 7.2 Full — typical rich Sub-Node reading

```json
{
  "$schema": "agro-guardian/telemetry/v2",
  "tenant_id": "11111111-1111-1111-1111-111111111111",
  "farmer_id": "aaaaaaaa-1111-1111-1111-111111111111",
  "farm_id":   "bbbbbbbb-2222-2222-2222-222222222222",
  "plot_id":   "PLOT_PILOT_001",
  "node_id":   "AGR-SN-0001",
  "recorded_at":        "2026-07-21T13:12:00+00:00",
  "received_at_master": "2026-07-21T13:12:01+00:00",
  "transmission_type":  "lora",
  "signal_rssi_dbm":    -72,
  "firmware_version":   "sub-node-1.0.0",
  "uptime_seconds":     864230,
  "battery_voltage_v":  3.62,
  "battery_percent":    58.4,
  "solar_charging":     true,
  "low_battery_flag":   false,
  "soil_moisture_1_pct":  41.9,
  "soil_moisture_2_pct":  42.4,
  "soil_moisture_avg_pct": 42.15,
  "soil_temp_rootzone_c": 24.7,
  "soil_ph":            6.9,
  "soil_ec_ms_cm":      0.42,
  "soil_n_mg_kg":       95,
  "soil_p_mg_kg":       48,
  "soil_k_mg_kg":       82,
  "tamper_detected":    false,
  "enclosure_temp_c":   31.2,
  "cadence_mode":       "normal",
  "backlog_pending":    false,
  "validation_warn":    false
}
```

## 8. Backend behavior at a glance

| What happens | Backend response |
| :--- | :--- |
| Topic doesn't match `agro/v2/…/telemetry` | log + drop, metric `ingest_dropped_total{reason="parse_error"}` |
| Topic kind is not `telemetry` (e.g. `heartbeat`) | log + drop, metric `ingest_dropped_total{reason="unknown_topic"}` |
| Payload isn't JSON | log + drop, metric `ingest_dropped_total{reason="parse_error"}` |
| Extra/unknown field in payload | log + drop, metric `ingest_dropped_total{reason="validation"}` |
| Required field missing | ″ |
| Timestamp is naive (no offset) | ″ |
| Everything valid | UPSERT into `node_sensor_readings`; rules evaluate (unless `CALIBRATION_MODE=true`) |

## 9. Bench test checklist for firmware

1. Backend up on the target host. Run `scripts/dev/tail_ingest.py` in a second terminal to watch.
2. `seed_pilot.py` has been run — Sub Node IDs and plot IDs exist in the DB.
3. MQTT credential provisioned via `provision_mqtt_credential.sh`.
4. `CALIBRATION_MODE=true` in the backend `.env` so early wonky readings don't fire alerts.
5. First test: `mosquitto_pub` from your laptop with the minimal payload from §7.1. If that lands, the Main Node firmware is doing the same job, just with real sensor values.
6. Only flip `CALIBRATION_MODE=false` once the sensors are producing plausible values.

## 10. Change control

Fields can be **added** to the schema in a later round; existing fields cannot be removed or renamed without a migration + a version bump on the `$schema` literal (`agro-guardian/telemetry/v3`). The backend will reject `v3` until it explicitly supports it, so firmware and backend need to move together.
__AGRO_HW_EOF_8__

write_file deploy/staging/README.md
cat > deploy/staging/README.md <<'__AGRO_HW_EOF_9__'
# AgroGuardian Staging Deploy — Trimmed Round 15

> **Purpose:** stand up a Lightsail Mumbai VPS quickly so hardware has a real endpoint to publish to. No Coolify, no domain, no backups yet — that's full Round 15.
> **Runtime:** ~40 minutes end-to-end.
> **Prereqs:** AWS account, Anthropic API key (optional for the pure ingest test).

## Step 1 — Provision the Lightsail instance (5 min)

- Lightsail console → **Create instance** → **Mumbai (ap-south-1)** → **Linux/Unix** → **OS Only** → **Ubuntu 22.04 LTS** → **$20/month** (`medium_2_0`, 2 vCPU, 4 GB RAM, 80 GB SSD, 3 TB egress).
- Instance name: `agro-staging-01`.
- Once running: **Networking → Attach static IP** so the IP survives reboots.
- **Networking → Firewall**, open the following:

  | Port | Purpose |
  | :---: | :--- |
  | 22 | SSH |
  | 80 | Let's Encrypt HTTP-01 challenge (Caddy redirects to 443) |
  | 443 | HTTPS API |
  | 8883 | MQTTS from hardware |

- Note the static IP. From now on `<STATIC_IP>` refers to this address, and `<IP_DASHES>` is the same IP with dots replaced by dashes (used for sslip.io).

## Step 2 — Base OS setup (10 min)

SSH in:

```bash
ssh -i ~/.ssh/agro_lightsail.pem ubuntu@<STATIC_IP>
```

Base packages + Docker + UFW:

```bash
sudo hostnamectl set-hostname agro-staging-01
sudo apt update && sudo apt upgrade -y
sudo apt install -y curl ca-certificates gnupg jq ufw fail2ban git
curl -fsSL https://get.docker.com | sudo bash
sudo usermod -aG docker $USER
newgrp docker

sudo ufw default deny incoming
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8883
sudo ufw enable

sudo systemctl enable --now fail2ban
```

## Step 3 — Clone + configure (5 min)

```bash
cd ~
git clone <your-fork-url> agro_backend
cd agro_backend
cp .env.example .env
```

Edit `.env` — the fields that matter for staging:

```dotenv
APP_ENV=staging
APP_VERSION=0.0.1

# Postgres — generate a strong password; do NOT reuse dev's
POSTGRES_USER=agro
POSTGRES_PASSWORD=<generated>
POSTGRES_DB=agro
DATABASE_URL=postgresql+asyncpg://agro:<generated>@postgres:5432/agro
DATABASE_URL_SYNC=postgresql://agro:<generated>@postgres:5432/agro

# JWT — 32+ random bytes, never CHANGE_ME
AUTH_JWT_SECRET=<openssl rand -hex 32>

# MQTT — Main Node credential; will be provisioned below
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=8883
MQTT_BROKER_USER=main-node-001
MQTT_BROKER_PASSWORD=<generated>
MQTT_USE_TLS=true
MQTT_TLS_CA_PATH=/etc/ssl/certs/ca-certificates.crt

# Hardware bench: rules OFF until sensors are calibrated
CALIBRATION_MODE=true

# Anthropic (optional at this stage; compose_advisory only runs post-Round 13)
ANTHROPIC_API_KEY=<sk-ant-...>
```

## Step 4 — Render the Caddyfile for sslip.io (2 min)

```bash
make caddyfile-prod IP=<STATIC_IP>
```

This produces `deploy/caddy/Caddyfile.prod` with `api-<IP_DASHES>.sslip.io` as the API host. sslip.io serves that hostname as an A-record to `<STATIC_IP>` automatically — no DNS registrar needed.

If `mqtts-<IP_DASHES>.sslip.io` isn't already in the template, add a second block that terminates TLS on `:8883` and reverse-proxies to the mosquitto container. (For port-8883 pass-through TLS, Caddy needs the `caddy-l4` layer-4 plugin; alternatively let mosquitto handle TLS directly with a Let's Encrypt cert bind-mounted in.)

## Step 5 — Start the stack (5 min)

```bash
docker compose -f docker-compose.prod.yml up -d
docker compose -f docker-compose.prod.yml logs -f app | head -40
```

You should see:

```
{"event":"app.startup","env":"staging","calibration_mode":true, ...}
{"event":"ingest_startup.started","host":"mosquitto","port":8883,"tls":true, ...}
{"event":"ingest_broker.started", ...}
{"event":"ingest_broker.subscribed","topic":"agro/v2/+/+/+/telemetry","qos":1}
```

If any of those are missing, `Ctrl-C` and inspect logs — the broker may be crash-looping on missing TLS certs.

## Step 6 — Migrate + seed (2 min)

```bash
docker compose -f docker-compose.prod.yml exec app alembic upgrade head
docker compose -f docker-compose.prod.yml exec -e PILOT_PHONE=+91XXXXXXXXXX \
    app python scripts/dev/seed_pilot.py
```

Save the Main Node ID (`AGR-MN-0001`) and Sub Node IDs (`AGR-SN-0001`, `AGR-SN-0002`) that get printed.

## Step 7 — Provision the Main Node's MQTT credential (2 min)

```bash
./scripts/dev/provision_mqtt_credential.sh main-node-001 <STRONG_PASSWORD>
docker compose -f docker-compose.prod.yml restart mosquitto
```

The same password goes into `.env` as `MQTT_BROKER_PASSWORD` **and** into the Main Node firmware's config. The backend and firmware use the *same* credential — the backend is a subscriber, the firmware is a publisher, but Mosquitto's ACL grants read+write on `agro/v2/#` to the shared user for simplicity in staging.

## Step 8 — Smoke test (5 min)

From your laptop, run `mosquitto_pub` with the minimal payload from `docs/HARDWARE_WIRE_CONTRACT.md` §7.1, aimed at the staging broker over TLS:

```bash
mosquitto_pub \
  -h mqtts-<IP_DASHES>.sslip.io -p 8883 \
  --capath /etc/ssl/certs \
  -u main-node-001 -P '<STRONG_PASSWORD>' \
  -t 'agro/v2/11111111-1111-1111-1111-111111111111/bbbbbbbb-2222-2222-2222-222222222222/AGR-SN-0001/telemetry' \
  -m '{"$schema":"agro-guardian/telemetry/v2","tenant_id":"11111111-1111-1111-1111-111111111111","farmer_id":"aaaaaaaa-1111-1111-1111-111111111111","farm_id":"bbbbbbbb-2222-2222-2222-222222222222","plot_id":"PLOT_PILOT_001","node_id":"AGR-SN-0001","recorded_at":"2026-07-21T13:12:00+00:00","received_at_master":"2026-07-21T13:12:00+00:00","transmission_type":"lora","soil_moisture_avg_pct":42.15}'
```

In another terminal, tail the ingest events:

```bash
docker compose -f docker-compose.prod.yml logs -f app | python scripts/dev/tail_ingest.py
```

Look for:

```
ingest_broker.subscribed topic='agro/v2/+/+/+/telemetry'
```

...followed by an event confirming the row landed. Check the database:

```bash
docker compose -f docker-compose.prod.yml exec postgres \
    psql -U agro -d agro -c \
    "SELECT node_id, plot_id, recorded_at, soil_moisture_avg_pct FROM node_sensor_readings ORDER BY recorded_at DESC LIMIT 5;"
```

## Step 9 — Point the Main Node at staging (firmware round)

Firmware config:

```
MQTT_HOST     = "mqtts-<IP_DASHES>.sslip.io"
MQTT_PORT     = 8883
MQTT_USER     = "main-node-001"
MQTT_PASSWORD = "<STRONG_PASSWORD>"
MQTT_USE_TLS  = true
```

The firmware skeleton (PlatformIO C++) ships in the follow-up bootstrap.

## What's NOT included in this trimmed staging (add for full Round 15)

- Coolify (a UI over docker-compose — nice, not necessary).
- Nightly `pg_dump | zstd | aws s3 cp` to Cloudflare R2. Add before real farmer data flows.
- Tailscale for private `/metrics`. Add before the pilot is publicly announced.
- A real domain (right now sslip.io serves the IP verbatim).
- Sentry DSN + BetterStack Uptime pinger.

Everything above is a `docker compose` restart or a single script — add it after hardware validates.
__AGRO_HW_EOF_9__

chmod +x scripts/dev/provision_mqtt_credential.sh
chmod +x scripts/dev/tail_ingest.py

echo ""
echo "============================================================"
echo "Hardware Enablement bootstrap: DONE"
echo "============================================================"
echo ""
echo "Files installed:"
echo "  app/main.py                            (lifespan spawns IngestBroker)"
echo "  app/config.py                          (adds CALIBRATION_MODE flag)"
echo "  app/application/evaluate_rules.py       (calibration short-circuit)"
echo "  app/jobs/ingest_startup.py             (NEW)"
echo "  scripts/dev/seed_pilot.py              (Main + 2 Sub Nodes + 4 plots)"
echo "  scripts/dev/provision_mqtt_credential.sh (NEW)"
echo "  scripts/dev/tail_ingest.py             (NEW)"
echo "  docs/HARDWARE_WIRE_CONTRACT.md         (NEW)"
echo "  deploy/staging/README.md               (NEW)"
echo ""
echo "Next steps (in this order):"
echo "  1. Add CALIBRATION_MODE=true to .env"
echo "  2. Re-seed pilot data:"
echo "       set -a; source .env; set +a"
echo "       export DATABASE_URL_SYNC=\"postgresql://agro:\$POSTGRES_PASSWORD@localhost:5433/agro\""
echo "       python scripts/dev/seed_pilot.py"
echo "  3. Restart backend:"
echo "       uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo "     Look for: ingest_broker.started + ingest_broker.subscribed"
echo "  4. Local smoke test (from another shell on the Mac):"
echo "       python scripts/dev/fake_main_node.py --tenant-id 11111111-1111-1111-1111-111111111111 \\"
echo "         --farmer-id aaaaaaaa-1111-1111-1111-111111111111 \\"
echo "         --farm-id   bbbbbbbb-2222-2222-2222-222222222222 \\"
echo "         --plot-id   PLOT_PILOT_001 --node-id AGR-SN-0001 --rate 1.0 --duration 30"
echo "  5. Then follow deploy/staging/README.md for the Lightsail bring-up."
echo ""

