"""``instrument_job`` — uniform observability wrapper for scheduler ticks.

Every cron scheduler's job body is wrapped in ``async with instrument_job(...)``.
The wrapper gives each tick, for free and identically:

* structured ``{job}.tick_ok`` / ``{job}.tick_skipped`` / ``{job}.tick_failed``
  logs (the failed one with the traceback);
* Prometheus metrics — ``agro_job_runs_total{job,status}``,
  ``agro_job_run_duration_seconds{job}`` and, on success,
  ``agro_job_last_success_timestamp_seconds{job}``;
* a best-effort ``job_run`` ledger row (when ``JOB_RUN_LEDGER_ENABLED`` is on).

It is **behaviour-preserving**: a raised exception is logged and *swallowed*,
exactly as the previous per-scheduler ``try/except`` did — so a failing tick
never crashes the scheduler, and the ledger/metrics can never affect the job.

Usage::

    async def _job() -> None:
        async with instrument_job(settings, "satellite_fetch") as rec:
            res = await refresh_satellite.execute(...)
            rec.ok(plots=res.plots, scenes=res.optical_scenes)
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

import structlog

from app.application.ports.job_run_repo import JobRun
from app.infra.http.deps import _ensure_engine
from app.infra.persistence.pg_job_run_repo import PgJobRunRepo
from app.lib.metrics import (
    job_last_success_timestamp,
    job_run_duration_seconds,
    job_runs_total,
)
from app.lib.time import now_utc

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from app.config import Settings

log = structlog.get_logger(__name__)

_MAX_ERR_LEN = 2000


@dataclass
class JobRecorder:
    """Handed to the ``async with`` body so the job can attach a summary.

    Call :meth:`ok` to add fields to the success summary, or :meth:`skipped`
    to mark the tick as a no-op (e.g. nothing was due). An unhandled exception
    overrides either and records a failure.
    """

    status: str = "ok"
    summary: dict[str, Any] = field(default_factory=dict)

    def ok(self, **fields: Any) -> None:
        self.summary.update(fields)

    def skipped(self, **fields: Any) -> None:
        self.status = "skipped"
        self.summary.update(fields)


def _observe(job_name: str, status: str, dur_ms: int) -> None:
    try:
        job_runs_total.labels(job=job_name, status=status).inc()
        job_run_duration_seconds.labels(job=job_name).observe(dur_ms / 1000.0)
        if status == "ok":
            job_last_success_timestamp.labels(job=job_name).set(now_utc().timestamp())
    except Exception:  # metrics must never break a job
        log.debug("instrument_job.metrics_failed", job=job_name)


async def _record(
    settings: Settings,
    job_name: str,
    started: Any,
    finished: Any,
    dur_ms: int,
    status: str,
    summary: dict[str, Any],
    exc: BaseException | None,
) -> None:
    if not settings.JOB_RUN_LEDGER_ENABLED:
        return
    try:
        repo = PgJobRunRepo(_ensure_engine(settings))
        await repo.record(
            JobRun(
                id=str(uuid4()),
                job_name=job_name,
                started_at=started,
                finished_at=finished,
                duration_ms=dur_ms,
                status=status,
                summary=summary,
                error_type=type(exc).__name__ if exc is not None else None,
                error_message=(str(exc)[:_MAX_ERR_LEN] if exc is not None else None),
            )
        )
    except Exception:  # ledger write must never break a job
        log.exception("instrument_job.ledger_write_failed", job=job_name)


@asynccontextmanager
async def instrument_job(settings: Settings, job_name: str) -> AsyncIterator[JobRecorder]:
    """Wrap one scheduler tick with logging, metrics and the job-run ledger.

    Exceptions raised inside the ``with`` body are logged (with traceback) and
    swallowed, matching the previous per-scheduler behaviour.
    """
    rec = JobRecorder()
    started = now_utc()
    try:
        yield rec
    except Exception as exc:
        finished = now_utc()
        dur_ms = int((finished - started).total_seconds() * 1000)
        log.exception(f"{job_name}.tick_failed", duration_ms=dur_ms)
        _observe(job_name, "failed", dur_ms)
        await _record(settings, job_name, started, finished, dur_ms, "failed", {}, exc)
        return  # swallow — behaviour-preserving
    finished = now_utc()
    dur_ms = int((finished - started).total_seconds() * 1000)
    event = "tick_skipped" if rec.status == "skipped" else "tick_ok"
    log.info(f"{job_name}.{event}", duration_ms=dur_ms, **rec.summary)
    _observe(job_name, rec.status, dur_ms)
    await _record(settings, job_name, started, finished, dur_ms, rec.status, rec.summary, None)


__all__ = ["JobRecorder", "instrument_job"]
