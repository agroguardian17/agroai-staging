"""Port for persisting diagnostics battery results (debug hardening, Round 1)."""

from __future__ import annotations

import datetime as _dt
from typing import Protocol, runtime_checkable

from app.domain.diagnostics import CheckResult


@runtime_checkable
class DiagnosticsRepo(Protocol):
    async def record_run(
        self, run_id: str, created_at: _dt.datetime, results: list[CheckResult]
    ) -> None:
        """Persist all check results of one battery run (best-effort caller)."""
        ...

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        """Delete rows older than ``cutoff``; return the number removed."""
        ...
