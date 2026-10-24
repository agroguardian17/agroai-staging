"""Pure unit tests for the diagnostics evaluators (no DB)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from app.domain import diagnostics
from app.domain.diagnostics import CheckResult, DiagnosticsInputs

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


def _by_id(results: list[CheckResult]) -> dict[str, CheckResult]:
    return {r.check_id: r for r in results}


def test_readings_freshness_ok_fail_empty() -> None:
    fresh = diagnostics.evaluate(
        DiagnosticsInputs(
            now=NOW, readings_max_age_hours=6, latest_reading_at=NOW - timedelta(hours=1)
        )
    )
    assert _by_id(fresh)["readings_fresh"].status == "ok"

    stale = diagnostics.evaluate(
        DiagnosticsInputs(
            now=NOW, readings_max_age_hours=6, latest_reading_at=NOW - timedelta(hours=10)
        )
    )
    assert _by_id(stale)["readings_fresh"].status == "fail"

    empty = diagnostics.evaluate(DiagnosticsInputs(now=NOW, latest_reading_at=None))
    assert _by_id(empty)["readings_fresh"].status == "fail"


def test_forecast_coverage() -> None:
    covers = diagnostics.evaluate(
        DiagnosticsInputs(now=NOW, latest_forecast_for_date=date(2026, 10, 18))
    )
    assert _by_id(covers)["forecast_coverage"].status == "ok"

    behind = diagnostics.evaluate(
        DiagnosticsInputs(now=NOW, latest_forecast_for_date=date(2026, 10, 10))
    )
    assert _by_id(behind)["forecast_coverage"].status == "fail"


def test_satellite_skip_warn_ok() -> None:
    off = _by_id(diagnostics.evaluate(DiagnosticsInputs(now=NOW, satellite_enabled=False)))
    assert off["satellite_fresh"].status == "skip"

    none = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(now=NOW, satellite_enabled=True, latest_satellite_image_date=None)
        )
    )
    assert none["satellite_fresh"].status == "warn"

    fresh = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(
                now=NOW,
                satellite_enabled=True,
                satellite_max_age_days=14,
                latest_satellite_image_date=date(2026, 10, 10),
            )
        )
    )
    assert fresh["satellite_fresh"].status == "ok"

    old = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(
                now=NOW,
                satellite_enabled=True,
                satellite_max_age_days=14,
                latest_satellite_image_date=date(2026, 9, 1),
            )
        )
    )
    assert old["satellite_fresh"].status == "warn"


def test_partition_and_duplicate_invariants() -> None:
    good = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(now=NOW, has_default_partition=True, duplicate_advisory_groups=0)
        )
    )
    assert good["partition_default_present"].status == "ok"
    assert good["no_duplicate_advisories"].status == "ok"

    bad = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(now=NOW, has_default_partition=False, duplicate_advisory_groups=3)
        )
    )
    assert bad["partition_default_present"].status == "fail"
    assert bad["no_duplicate_advisories"].status == "fail"

    unknown = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(now=NOW, has_default_partition=None, duplicate_advisory_groups=None)
        )
    )
    assert unknown["partition_default_present"].status == "skip"
    assert unknown["no_duplicate_advisories"].status == "skip"


def test_summarize_and_worst_status() -> None:
    all_ok = diagnostics.evaluate(
        DiagnosticsInputs(
            now=NOW,
            latest_reading_at=NOW,
            latest_forecast_for_date=date(2026, 10, 16),
            has_default_partition=True,
            duplicate_advisory_groups=0,
        )
    )
    counts = diagnostics.summarize(all_ok)
    assert set(counts) == {"ok", "warn", "fail", "skip"}
    assert counts["fail"] == 0
    # readings/forecast/partition/dup ok, satellite skip -> overall ok
    assert diagnostics.worst_status(all_ok) == "ok"

    failing = diagnostics.evaluate(DiagnosticsInputs(now=NOW, latest_reading_at=None))
    assert diagnostics.worst_status(failing) == "fail"


def test_forecast_job_recent() -> None:
    # A6: catch a dead forecast job even when coverage would still pass.
    none = _by_id(diagnostics.evaluate(DiagnosticsInputs(now=NOW, last_forecast_job_ok_at=None)))
    assert none["forecast_job_recent"].status == "skip"

    recent = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(
                now=NOW,
                last_forecast_job_ok_at=NOW - timedelta(hours=2),
                forecast_job_max_age_hours=26,
            )
        )
    )
    assert recent["forecast_job_recent"].status == "ok"

    stale = _by_id(
        diagnostics.evaluate(
            DiagnosticsInputs(
                now=NOW,
                # a run 2 days ago while forecast_coverage would still be green
                latest_forecast_for_date=date(2026, 10, 18),
                last_forecast_job_ok_at=NOW - timedelta(hours=48),
                forecast_job_max_age_hours=26,
            )
        )
    )
    assert stale["forecast_job_recent"].status == "fail"
