"""Start/stop the nightly anomaly engine (Round-3 observability, R3.4).

Runs shortly after the diagnostics battery (default 07:25 IST) so it sees the
day's rows and the diagnostics have already landed. Gathers signals from the DB
(per-device reading gaps, stuck sensors, per-rule fire rates from the R3.1
pipeline traces, advisory volume vs a trailing baseline), evaluates the pure
detector, and writes one ``anomaly_finding`` row per finding for the dashboard's
Anomalies / Daily Health pages. Read-only + best-effort; skipped when
``ANOMALY_DETECTION_ENABLED`` is false. Wrapped in ``instrument_job`` so the run
also lands in the job-run ledger and Prometheus like every other scheduler.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import uuid4

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.run_anomaly_detection import run_anomaly_detection
from app.domain import anomalies
from app.infra.anomaly.pg_collector import PgAnomalyCollector
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_anomaly_repo import PgAnomalyRepo
from app.jobs._instrument import instrument_job
from app.lib.metrics import anomaly_findings
from app.lib.time import now_utc

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_anomaly_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.ANOMALY_DETECTION_ENABLED:
        log.info("anomaly_scheduler.disabled", reason="ANOMALY_DETECTION_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    collector = PgAnomalyCollector(sm)
    repo = PgAnomalyRepo(sm)
    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        async with instrument_job(settings, "anomaly_engine") as rec:
            now = now_utc()
            findings = await run_anomaly_detection(
                collector,
                now=now,
                data_gap_minutes=settings.ANOMALY_DATA_GAP_MINUTES,
                stuck_min_readings=settings.ANOMALY_STUCK_MIN_READINGS,
                rule_always_rate=settings.ANOMALY_RULE_ALWAYS_RATE,
                rule_min_samples=settings.ANOMALY_RULE_MIN_SAMPLES,
                advisory_spike_factor=settings.ANOMALY_ADVISORY_SPIKE_FACTOR,
                advisory_baseline_days=settings.ANOMALY_ADVISORY_BASELINE_DAYS,
                trace_window_days=settings.ANOMALY_TRACE_WINDOW_DAYS,
            )
            run_id = str(uuid4())
            await repo.record_run(run_id, now, findings)
            counts = anomalies.summarize(findings)
            for severity, n in counts.items():
                anomaly_findings.labels(severity=severity).set(n)
            rec.ok(
                run_id=run_id,
                overall=anomalies.worst_severity(findings),
                total=len(findings),
                **counts,
            )

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.ANOMALY_JOB_HOUR,
            minute=settings.ANOMALY_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="anomaly_engine",
        name="Nightly anomaly engine",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "anomaly_scheduler.started",
        hour=settings.ANOMALY_JOB_HOUR,
        minute=settings.ANOMALY_JOB_MINUTE,
    )
    return scheduler


async def stop_anomaly_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("anomaly_scheduler.stopped")


__all__ = ["build_and_start_anomaly_scheduler", "stop_anomaly_scheduler"]
