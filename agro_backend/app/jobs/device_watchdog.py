"""Start/stop the device-liveness watchdog.

A small AsyncIOScheduler with one interval job that sweeps the latest Main Node
heartbeats and raises DEVICE_OFFLINE alerts for stale/silent nodes
(``app.application.check_device_liveness``). DB-only read + alert write + a
``alert.created`` NOTIFY; no external calls here (delivery stays gated on the
WhatsApp pipeline like every other alert). Skipped when
``DEVICE_WATCHDOG_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.application.check_device_liveness import DeviceLivenessDeps, check_device_liveness
from app.infra.events.pg_notify_bus import PgNotifyEventBus
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_alert_repo import PgAlertRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo
from app.infra.persistence.pg_main_node_reading_repo import PgMainNodeReadingRepo
from app.infra.persistence.pg_plot_repo import PgPlotRepo
from app.lib.time import now_utc

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_device_watchdog(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.DEVICE_WATCHDOG_ENABLED:
        log.info("device_watchdog.disabled", reason="DEVICE_WATCHDOG_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    deps = DeviceLivenessDeps(
        heartbeat_repo=PgMainNodeReadingRepo(sm),
        alert_repo=PgAlertRepo(sm),
        farmer_repo=PgFarmerRepo(sm),
        plot_repo=PgPlotRepo(sm),
        event_bus=PgNotifyEventBus(sm),
        warn_minutes=settings.SUB_NODE_SILENCE_WARN_MINUTES,
        critical_minutes=settings.SUB_NODE_SILENCE_CRITICAL_MINUTES,
        cooldown_minutes=settings.DEVICE_OFFLINE_COOLDOWN_MINUTES,
    )

    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        try:
            raised = await check_device_liveness(deps, now=now_utc())
            log.info("device_watchdog.tick_ok", alerts_raised=raised)
        except Exception:
            log.exception("device_watchdog.tick_failed")

    scheduler.add_job(
        _job,
        trigger=IntervalTrigger(minutes=settings.DEVICE_WATCHDOG_INTERVAL_MINUTES),
        id="device_watchdog",
        name="Device-liveness watchdog",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=5 * 60,
    )
    scheduler.start()
    log.info(
        "device_watchdog.started",
        interval_minutes=settings.DEVICE_WATCHDOG_INTERVAL_MINUTES,
        warn_minutes=settings.SUB_NODE_SILENCE_WARN_MINUTES,
        critical_minutes=settings.SUB_NODE_SILENCE_CRITICAL_MINUTES,
    )
    return scheduler


async def stop_device_watchdog(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("device_watchdog.stopped")


__all__ = ["build_and_start_device_watchdog", "stop_device_watchdog"]
