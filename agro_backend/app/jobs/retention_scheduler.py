"""Start/stop the DPDP erasure/retention worker (A4.3).

A small AsyncIOScheduler with one nightly cron that fulfils due erasure requests
(30-day SLA) by anonymising the farmer's identity in place. DB-only, no external
calls. Skipped when ``RETENTION_JOB_ENABLED`` is false (tests/CI).
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.application.fulfil_erasures import fulfil_erasures
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_anomaly_repo import PgAnomalyRepo
from app.infra.persistence.pg_diagnostics_repo import PgDiagnosticsRepo
from app.infra.persistence.pg_erasure_request_repo import PgErasureRequestRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo
from app.infra.persistence.pg_job_run_repo import PgJobRunRepo
from app.infra.persistence.pg_pipeline_trace_repo import PgPipelineTraceRepo
from app.infra.persistence.pg_plot_run_trace_repo import PgPlotRunTraceRepo
from app.jobs._instrument import instrument_job
from app.lib.time import now_utc

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)


async def build_and_start_retention_scheduler(settings: Settings) -> AsyncIOScheduler | None:
    if not settings.RETENTION_JOB_ENABLED:
        log.info("retention_scheduler.disabled", reason="RETENTION_JOB_ENABLED=false")
        return None

    sm = _ensure_engine(settings)
    erasure_repo = PgErasureRequestRepo(sm)
    farmer_repo = PgFarmerRepo(sm)
    trace_repo = PgPipelineTraceRepo(sm)
    run_trace_repo = PgPlotRunTraceRepo(sm)
    job_run_repo = PgJobRunRepo(sm)
    diagnostics_repo = PgDiagnosticsRepo(sm)
    anomaly_repo = PgAnomalyRepo(sm)
    scheduler = AsyncIOScheduler(timezone=settings.GINGER_JOB_TIMEZONE)

    async def _job() -> None:
        async with instrument_job(settings, "dpdp_retention_worker") as rec:
            res = await fulfil_erasures(
                erasure_repo=erasure_repo, farmer_repo=farmer_repo, now=now_utc()
            )
            rec.ok(processed=res.processed, anonymised=res.anonymised, missing=res.missing)
        # Bound the observability tables (best-effort, independent of erasure).
        try:
            cutoff = now_utc() - timedelta(days=settings.PIPELINE_TRACE_RETENTION_DAYS)
            purged = await trace_repo.purge_older_than(cutoff)
            run_purged = await run_trace_repo.purge_older_than(cutoff)
            obs_cutoff = now_utc() - timedelta(days=settings.OBSERVABILITY_RETENTION_DAYS)
            job_purged = await job_run_repo.purge_older_than(obs_cutoff)
            diag_purged = await diagnostics_repo.purge_older_than(obs_cutoff)
            anomaly_purged = await anomaly_repo.purge_older_than(obs_cutoff)
            if purged or run_purged or job_purged or diag_purged or anomaly_purged:
                log.info(
                    "retention_scheduler.observability_purged",
                    rows=purged,
                    run_rows=run_purged,
                    job_runs=job_purged,
                    diagnostics=diag_purged,
                    anomalies=anomaly_purged,
                )
        except Exception:
            log.exception("retention_scheduler.observability_purge_failed")

    scheduler.add_job(
        _job,
        trigger=CronTrigger(
            hour=settings.RETENTION_JOB_HOUR,
            minute=settings.RETENTION_JOB_MINUTE,
            timezone=settings.GINGER_JOB_TIMEZONE,
        ),
        id="dpdp_retention_worker",
        name="DPDP erasure/retention worker",
        max_instances=1,
        coalesce=True,
        misfire_grace_time=60 * 60,
    )
    scheduler.start()
    log.info(
        "retention_scheduler.started",
        hour=settings.RETENTION_JOB_HOUR,
        minute=settings.RETENTION_JOB_MINUTE,
    )
    return scheduler


async def stop_retention_scheduler(scheduler: AsyncIOScheduler) -> None:
    scheduler.shutdown(wait=False)
    log.info("retention_scheduler.stopped")


__all__ = ["build_and_start_retention_scheduler", "stop_retention_scheduler"]
