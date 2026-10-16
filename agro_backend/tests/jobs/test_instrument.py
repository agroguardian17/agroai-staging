"""Unit tests for instrument_job (no DB — ledger write gated off).

Verifies the behaviour-preserving contract: success/skip/failure set the right
status, a raised exception is **swallowed** (never propagates out of the
``async with``), and the job metrics move. The DB ledger write is covered by the
PgJobRunRepo integration test; here ``JOB_RUN_LEDGER_ENABLED`` is False so no DB
is touched.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.jobs._instrument import instrument_job
from app.lib import metrics


def _settings() -> SimpleNamespace:
    return SimpleNamespace(JOB_RUN_LEDGER_ENABLED=False)


def _runs(job: str, status: str) -> float:
    return metrics.job_runs_total.labels(job=job, status=status)._value.get()


async def test_ok_path_sets_summary_and_meters() -> None:
    before = _runs("t_ok", "ok")
    async with instrument_job(_settings(), "t_ok") as rec:
        rec.ok(written=3)
    assert rec.status == "ok"
    assert rec.summary == {"written": 3}
    assert _runs("t_ok", "ok") == before + 1


async def test_failure_is_swallowed_and_metered() -> None:
    before = _runs("t_fail", "failed")
    # The raised error must NOT escape the context manager.
    async with instrument_job(_settings(), "t_fail"):
        raise RuntimeError("boom")
    assert _runs("t_fail", "failed") == before + 1


async def test_skipped_status() -> None:
    before = _runs("t_skip", "skipped")
    async with instrument_job(_settings(), "t_skip") as rec:
        rec.skipped(reason="nothing due")
    assert rec.status == "skipped"
    assert _runs("t_skip", "skipped") == before + 1
