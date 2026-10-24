"""Port for persisting anomaly-engine findings (Round-3 R3.4)."""

from __future__ import annotations

import datetime as _dt
from typing import Protocol, runtime_checkable

from app.domain.anomalies import AnomalyFinding


@runtime_checkable
class AnomalyRepo(Protocol):
    async def record_run(
        self, run_id: str, created_at: _dt.datetime, findings: list[AnomalyFinding]
    ) -> None:
        """Persist all findings of one detection run (best-effort caller).

        A run with no findings still records nothing — the Anomalies page treats
        "no rows for the latest run_id" as all-clear via the job_run ledger."""
        ...

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        """Delete rows older than ``cutoff``; return the number removed."""
        ...
