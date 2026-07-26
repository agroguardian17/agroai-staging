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
