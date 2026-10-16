"""Job-run ledger repository port (scheduler observability).

One row per scheduler tick recording start/finish, terminal status, a small
summary dict, and the error on failure. Written best-effort by
``app.jobs._instrument.instrument_job`` when ``JOB_RUN_LEDGER_ENABLED`` is on;
read only by the dashboard's Scheduler Health page.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class JobRun:
    id: str
    job_name: str
    started_at: _dt.datetime
    finished_at: _dt.datetime
    duration_ms: int
    status: str  # ok | failed | skipped
    summary: dict[str, Any] = field(default_factory=dict)
    error_type: str | None = None
    error_message: str | None = None


@runtime_checkable
class JobRunRepo(Protocol):
    async def record(self, run: JobRun) -> None:
        """Persist one job-run row (best-effort caller)."""
        ...

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        """Delete rows older than ``cutoff``; return the number removed."""
        ...
