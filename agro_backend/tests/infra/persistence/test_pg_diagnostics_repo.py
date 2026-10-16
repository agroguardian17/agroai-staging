"""Integration test for PgDiagnosticsRepo against the diagnostics_result table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.diagnostics import CheckResult
from app.infra.persistence.pg_diagnostics_repo import PgDiagnosticsRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_record_run_and_purge(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgDiagnosticsRepo(sessionmaker)
    now = datetime.now(UTC)
    run_id = str(uuid.uuid4())
    results = [
        CheckResult("readings_fresh", "freshness", "ok", observed="1.0h old", expected="<= 6h"),
        CheckResult("no_duplicate_advisories", "invariant", "fail", observed="2", expected="0"),
    ]
    await repo.record_run(run_id, now, results)
    try:
        async with sessionmaker() as s:
            rows = (
                await s.execute(
                    text(
                        "SELECT check_id, status FROM diagnostics_result "
                        "WHERE run_id = :r ORDER BY check_id"
                    ),
                    {"r": run_id},
                )
            ).all()
        got = {r.check_id: r.status for r in rows}
        assert got == {"no_duplicate_advisories": "fail", "readings_fresh": "ok"}

        async with sessionmaker() as s, s.begin():
            await s.execute(
                text("UPDATE diagnostics_result SET created_at = :c WHERE run_id = :r"),
                {"c": now - timedelta(days=40), "r": run_id},
            )
        removed = await repo.purge_older_than(now - timedelta(days=30))
        assert removed >= 2
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM diagnostics_result WHERE run_id = :r"), {"r": run_id})
