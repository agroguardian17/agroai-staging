"""Integration test for PgPlotRunTraceRepo against the plot_run_trace table."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.plot_run_trace_repo import PlotRunTrace
from app.infra.persistence.pg_plot_run_trace_repo import PgPlotRunTraceRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_PLOT = "PLOT_RUN_TRACE_TEST"


def _trace(tid: str, created: datetime, overall: str = "ok") -> PlotRunTrace:
    return PlotRunTrace(
        trace_id=tid,
        plot_id=_PLOT,
        run_date=date(2026, 10, 4),
        overall=overall,
        created_at=created,
        advisories_written=2,
        coverage={"filled": 70, "unknown": 10, "coverage_pct": 0.875},
        derived={"dap": 100},
        engine={"messages": 2, "rule_ids": ["D03-WB-001", "D04-MC-005"]},
        stages={"s9_kb_engine": {"rules_fired": 2}},
        validations=[],
    )


async def test_record_and_purge(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgPlotRunTraceRepo(sessionmaker)
    now = datetime.now(UTC)
    new_id, old_id = str(uuid.uuid4()), str(uuid.uuid4())
    await repo.record(_trace(new_id, now))
    await repo.record(_trace(old_id, now - timedelta(days=40)))
    try:
        async with sessionmaker() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT overall, advisories_written, coverage->>'filled' AS filled, "
                        "engine->>'messages' AS msgs FROM plot_run_trace WHERE trace_id = :t"
                    ),
                    {"t": new_id},
                )
            ).one()
        assert row.overall == "ok"
        assert row.advisories_written == 2
        assert row.filled == "70"
        assert row.msgs == "2"

        removed = await repo.purge_older_than(now - timedelta(days=30))
        assert removed >= 1
        async with sessionmaker() as s:
            remaining = {
                str(x)
                for x in (
                    await s.execute(
                        text("SELECT trace_id FROM plot_run_trace WHERE plot_id = :p"), {"p": _PLOT}
                    )
                )
                .scalars()
                .all()
            }
        assert old_id not in remaining and new_id in remaining
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM plot_run_trace WHERE plot_id = :p"), {"p": _PLOT})
