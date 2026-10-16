"""Integration test for PgJobRunRepo against the job_run table."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.job_run_repo import JobRun
from app.infra.persistence.pg_job_run_repo import PgJobRunRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_JOB = "test_job_run_ledger"


def _run(rid: str, started: datetime, status: str = "ok") -> JobRun:
    return JobRun(
        id=rid,
        job_name=_JOB,
        started_at=started,
        finished_at=started + timedelta(seconds=2),
        duration_ms=2000,
        status=status,
        summary={"written": 5},
        error_type=None if status == "ok" else "RuntimeError",
        error_message=None if status == "ok" else "boom",
    )


async def test_record_and_purge(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgJobRunRepo(sessionmaker)
    now = datetime.now(UTC)
    new_id, old_id = str(uuid.uuid4()), str(uuid.uuid4())
    await repo.record(_run(new_id, now))
    await repo.record(_run(old_id, now - timedelta(days=40), status="failed"))
    try:
        async with sessionmaker() as s:
            row = (
                await s.execute(
                    text(
                        "SELECT status, duration_ms, summary->>'written' AS written "
                        "FROM job_run WHERE id = :i"
                    ),
                    {"i": new_id},
                )
            ).one()
        assert row.status == "ok"
        assert row.duration_ms == 2000
        assert row.written == "5"

        # Age the old row (created_at defaults to insert time) then purge by it.
        async with sessionmaker() as s, s.begin():
            await s.execute(
                text("UPDATE job_run SET created_at = :c WHERE id = :i"),
                {"c": now - timedelta(days=40), "i": old_id},
            )
        removed = await repo.purge_older_than(now - timedelta(days=30))
        assert removed >= 1

        async with sessionmaker() as s:
            remaining = {
                str(x)
                for x in (
                    await s.execute(text("SELECT id FROM job_run WHERE job_name = :j"), {"j": _JOB})
                )
                .scalars()
                .all()
            }
        assert old_id not in remaining and new_id in remaining
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM job_run WHERE job_name = :j"), {"j": _JOB})
