"""Port for the diagnostics data source (debug hardening, Round 1).

The nightly diagnostics battery needs observed values from the DB (latest
reading time, latest forecast date, partition state, duplicate-advisory count).
That gathering is infra (SQL); the orchestration (`run_diagnostics`) depends on
this Protocol so it stays framework-free and testable with a fake source.
"""

from __future__ import annotations

import datetime as _dt
from typing import Protocol, runtime_checkable

from app.domain.diagnostics import DiagnosticsInputs


@runtime_checkable
class DiagnosticsDataSource(Protocol):
    async def collect(
        self,
        now: _dt.datetime,
        *,
        readings_max_age_hours: int,
        satellite_enabled: bool,
        satellite_max_age_days: int,
    ) -> DiagnosticsInputs:
        """Gather observed values into a pure :class:`DiagnosticsInputs`.

        Each probe is best-effort: a failed query leaves its field ``None`` so
        the corresponding check degrades to ``skip`` rather than crashing.
        """
        ...
