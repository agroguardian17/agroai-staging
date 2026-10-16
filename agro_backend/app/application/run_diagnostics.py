"""Run the diagnostics battery (debug hardening, Round 1).

Thin orchestration: gather inputs via the data-source port, then evaluate them
with the pure domain evaluators. Framework-free (imports domain + ports only),
so it is reused by both the nightly ``diagnostics_scheduler`` and the Round-2
``make diagnose`` CLI.
"""

from __future__ import annotations

import datetime as _dt

from app.application.ports.diagnostics_data import DiagnosticsDataSource
from app.domain import diagnostics
from app.domain.diagnostics import CheckResult


async def run_diagnostics(
    source: DiagnosticsDataSource,
    *,
    now: _dt.datetime,
    readings_max_age_hours: int,
    satellite_enabled: bool,
    satellite_max_age_days: int,
) -> list[CheckResult]:
    inputs = await source.collect(
        now,
        readings_max_age_hours=readings_max_age_hours,
        satellite_enabled=satellite_enabled,
        satellite_max_age_days=satellite_max_age_days,
    )
    return diagnostics.evaluate(inputs)


__all__ = ["run_diagnostics"]
