"""Start/stop the nightly diagnostics battery (debug hardening, Round 1).

Runs after the ginger job (default 07:15 IST) so it sees the day's rows. Gathers
freshness + invariant observations from the DB, evaluates the pure checks, and
writes one ``diagnostics_result`` row per check for the dashboard's System
Diagnostics / Daily Health pages. Read-only + best-effort; skipped when
``DIAGNOSTICS_ENABLED`` is false. Wrapped in ``instrument_job`` so it also lands
in the job-run ledger and Prometheus like every other scheduler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.run_diagnostics import run_diagnostics
from app.domain import diagnostics
from app.infra.diagnostics.dependency_checks import run_dependency_checks
from app.infra.diagnostics.pg_collector import PgDiagnosticsCollector
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_diagnostics_repo import PgDiagnosticsRepo
from app.jobs._instrument import instrument_job
from app.lib.metrics import diagnostics_checks
from app.lib.time import now_utc

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_diagnostics_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.DIAGNOSTICS_ENABLED:
        log.info("diagnostics_scheduler.disabled", reason="DIAGNOSTICS_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    collector = PgDiagnosticsCollector(sm)
    repo = PgDiagnosticsRepo(sm)
    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        async with instrument_job(settings, "diagnostics_battery") as rec:
            now = now_utc()
            results = await run_diagnostics(
                collector,
                now=now,
                readings_max_age_hours=settings.DIAGNOSTICS_READINGS_MAX_AGE_HOURS,
                satellite_enabled=settings.SATELLITE_JOB_ENABLED,
                satellite_max_age_days=settings.DIAGNOSTICS_SATELLITE_MAX_AGE_DAYS,
            )
            results += await run_dependency_checks(settings)
            run_id = str(uuid4())
            await repo.record_run(run_id, now, results)
            counts = diagnostics.summarize(results)
            for status, n in counts.items():
                diagnostics_checks.labels(status=status).set(n)
            rec.ok(run_id=run_id, overall=diagnostics.worst_status(results), **counts)

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.DIAGNOSTICS_JOB_HOUR,
            minute=settings.DIAGNOSTICS_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="diagnostics_battery",
        name="Nightly diagnostics battery",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "diagnostics_scheduler.started",
        hour=settings.DIAGNOSTICS_JOB_HOUR,
        minute=settings.DIAGNOSTICS_JOB_MINUTE,
    )
    return scheduler


async def stop_diagnostics_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("diagnostics_scheduler.stopped")


__all__ = ["build_and_start_diagnostics_scheduler", "stop_diagnostics_scheduler"]
