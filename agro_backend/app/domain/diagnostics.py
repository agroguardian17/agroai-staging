"""Pure diagnostics evaluators (debug hardening, Round 1).

The *logic* of the nightly diagnostics battery lives here — pure functions that
turn observed-vs-expected inputs into a list of :class:`CheckResult`. The data
gathering (SQL) lives in ``app/infra/diagnostics`` and the orchestration in
``app/application/run_diagnostics``; this module stays import-pure (stdlib only)
so it can be unit-tested without a database and reused by the `make diagnose`
CLI in Round 2.

Checks catch the "bad data / stale pipeline" class of bugs — a silently-dead
ingest (the k_source outage would show ``readings_fresh = fail``), a forecast
job that stopped covering today, a missing partition catch-all, or duplicate
advisories — automatically, instead of by manual dashboard review.

Severity convention: a missing *catch-all* / stale *core data* is ``fail``; a
stale optional feed (satellite revisit cadence is lumpy) is ``warn``; a check
whose inputs are unavailable or not applicable is ``skip`` (never a false fail).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

CATEGORY_FRESHNESS = "freshness"
CATEGORY_INVARIANT = "invariant"
CATEGORY_DEPENDENCY = "dependency"

_STATUSES = ("ok", "warn", "fail", "skip")


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    category: str
    status: str  # ok | warn | fail | skip
    observed: str | None = None
    expected: str | None = None
    detail: str | None = None


@dataclass(frozen=True)
class DiagnosticsInputs:
    """Plain data gathered by the collector; evaluated here with no I/O."""

    now: _dt.datetime
    readings_max_age_hours: int = 6
    satellite_max_age_days: int = 14
    satellite_enabled: bool = False
    latest_reading_at: _dt.datetime | None = None
    latest_forecast_for_date: _dt.date | None = None
    latest_satellite_image_date: _dt.date | None = None
    has_default_partition: bool | None = None
    duplicate_advisory_groups: int | None = None


def _age_hours(now: _dt.datetime, ts: _dt.datetime) -> float:
    return (now - ts).total_seconds() / 3600.0


def evaluate(inp: DiagnosticsInputs) -> list[CheckResult]:
    """Turn gathered inputs into an ordered list of check results (pure)."""
    results: list[CheckResult] = []

    # --- freshness: live sensor telemetry ---------------------------------
    if inp.latest_reading_at is None:
        results.append(
            CheckResult(
                "readings_fresh",
                CATEGORY_FRESHNESS,
                "fail",
                observed="no rows",
                expected=f"a reading within {inp.readings_max_age_hours}h",
                detail="node_sensor_readings is empty or unreadable",
            )
        )
    else:
        age = _age_hours(inp.now, inp.latest_reading_at)
        results.append(
            CheckResult(
                "readings_fresh",
                CATEGORY_FRESHNESS,
                "ok" if age <= inp.readings_max_age_hours else "fail",
                observed=f"{age:.1f}h old",
                expected=f"<= {inp.readings_max_age_hours}h",
            )
        )

    # --- freshness: weather forecast covers today -------------------------
    today = inp.now.date()
    if inp.latest_forecast_for_date is None:
        results.append(
            CheckResult(
                "forecast_coverage",
                CATEGORY_FRESHNESS,
                "fail",
                observed="no forecast rows",
                expected="a forecast covering today",
            )
        )
    else:
        results.append(
            CheckResult(
                "forecast_coverage",
                CATEGORY_FRESHNESS,
                "ok" if inp.latest_forecast_for_date >= today else "fail",
                observed=str(inp.latest_forecast_for_date),
                expected=f">= {today}",
            )
        )

    # --- freshness: satellite scenes (only when the feed is enabled) ------
    if not inp.satellite_enabled:
        results.append(
            CheckResult(
                "satellite_fresh",
                CATEGORY_FRESHNESS,
                "skip",
                detail="SATELLITE_JOB_ENABLED=false",
            )
        )
    elif inp.latest_satellite_image_date is None:
        results.append(
            CheckResult(
                "satellite_fresh",
                CATEGORY_FRESHNESS,
                "warn",
                observed="no scenes",
                expected=f"a scene within {inp.satellite_max_age_days}d",
            )
        )
    else:
        age_d = (today - inp.latest_satellite_image_date).days
        results.append(
            CheckResult(
                "satellite_fresh",
                CATEGORY_FRESHNESS,
                "ok" if age_d <= inp.satellite_max_age_days else "warn",
                observed=f"{age_d}d old",
                expected=f"<= {inp.satellite_max_age_days}d",
            )
        )

    # --- invariant: partition catch-all present ---------------------------
    if inp.has_default_partition is None:
        results.append(
            CheckResult(
                "partition_default_present",
                CATEGORY_INVARIANT,
                "skip",
                detail="partition state unavailable",
            )
        )
    else:
        results.append(
            CheckResult(
                "partition_default_present",
                CATEGORY_INVARIANT,
                "ok" if inp.has_default_partition else "fail",
                observed=str(inp.has_default_partition),
                expected="True (DEFAULT catch-all partition exists)",
            )
        )

    # --- invariant: no duplicate ginger advisories ------------------------
    if inp.duplicate_advisory_groups is None:
        results.append(
            CheckResult(
                "no_duplicate_advisories",
                CATEGORY_INVARIANT,
                "skip",
                detail="duplicate query unavailable",
            )
        )
    else:
        results.append(
            CheckResult(
                "no_duplicate_advisories",
                CATEGORY_INVARIANT,
                "ok" if inp.duplicate_advisory_groups == 0 else "fail",
                observed=f"{inp.duplicate_advisory_groups} duplicate group(s)",
                expected="0",
            )
        )

    return results


def summarize(results: list[CheckResult]) -> dict[str, int]:
    """Count results by status; always returns all four keys."""
    counts = dict.fromkeys(_STATUSES, 0)
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts


def worst_status(results: list[CheckResult]) -> str:
    """Overall status: fail > warn > ok (skip-only → ok)."""
    statuses = {r.status for r in results}
    if "fail" in statuses:
        return "fail"
    if "warn" in statuses:
        return "warn"
    return "ok"


__all__ = [
    "CATEGORY_DEPENDENCY",
    "CATEGORY_FRESHNESS",
    "CATEGORY_INVARIANT",
    "CheckResult",
    "DiagnosticsInputs",
    "evaluate",
    "summarize",
    "worst_status",
]
