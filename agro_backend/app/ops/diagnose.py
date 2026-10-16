"""One-command diagnosis — ``python -m app.ops.diagnose`` (``make diagnose``).

Runs the full battery in one shot and prints a red/green report:
* freshness + invariant checks (against the DB),
* external dependency self-tests (CDSE / USGS / Anthropic / Meta),
* the pipeline self-test (pure, golden payloads).

Exits non-zero if any check **failed**, so it is usable locally, on the box, and
in CI. Warnings and skips do not fail the run. Read-only + side-effect-free.
"""

from __future__ import annotations

import asyncio
import sys

from app.application.run_diagnostics import run_diagnostics
from app.config import get_settings
from app.domain import diagnostics
from app.domain.diagnostics import CATEGORY_FRESHNESS, CATEGORY_INVARIANT, CheckResult
from app.infra.diagnostics.dependency_checks import run_dependency_checks
from app.infra.diagnostics.pg_collector import PgDiagnosticsCollector
from app.infra.http.deps import _ensure_engine, shutdown_engine
from app.infra.pipeline_selftest import run_self_test
from app.lib.time import now_utc

_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "⚪"}
_ORDER = {"fail": 0, "warn": 1, "skip": 2, "ok": 3}


async def gather_checks() -> list[CheckResult]:
    settings = get_settings()
    now = now_utc()
    results: list[CheckResult] = []

    # Freshness + invariants (needs the DB).
    try:
        collector = PgDiagnosticsCollector(_ensure_engine(settings))
        results += await run_diagnostics(
            collector,
            now=now,
            readings_max_age_hours=settings.DIAGNOSTICS_READINGS_MAX_AGE_HOURS,
            satellite_enabled=settings.SATELLITE_JOB_ENABLED,
            satellite_max_age_days=settings.DIAGNOSTICS_SATELLITE_MAX_AGE_DAYS,
        )
    except Exception as exc:
        results.append(
            CheckResult(
                "diagnostics_db",
                CATEGORY_FRESHNESS,
                "fail",
                detail=f"DB battery could not run: {type(exc).__name__}",
            )
        )
    finally:
        await shutdown_engine()

    # External dependency self-tests (network).
    results += await run_dependency_checks(settings)

    # Pipeline self-test (pure, no I/O).
    report = run_self_test()
    passed = sum(1 for c in report.cases if c.passed)
    results.append(
        CheckResult(
            "pipeline_self_test",
            CATEGORY_INVARIANT,
            "ok" if report.passed else "fail",
            observed=f"{passed}/{len(report.cases)} cases passed",
        )
    )
    return results


def _format(results: list[CheckResult]) -> str:
    lines = []
    for r in sorted(results, key=lambda r: (_ORDER[r.status], r.category, r.check_id)):
        parts = [p for p in (r.observed, r.detail) if p]
        if r.expected and r.status in ("fail", "warn"):
            parts.append(f"expected {r.expected}")
        suffix = f" — {'; '.join(parts)}" if parts else ""
        lines.append(f"{_ICON[r.status]} [{r.category}] {r.check_id}{suffix}")
    c = diagnostics.summarize(results)
    lines.append("")
    lines.append(f"{c['ok']} ok · {c['warn']} warn · {c['fail']} fail · {c['skip']} skip")
    return "\n".join(lines)


def main() -> int:
    results = asyncio.run(gather_checks())
    print(_format(results))
    return 1 if diagnostics.worst_status(results) == "fail" else 0


if __name__ == "__main__":
    sys.exit(main())
