"""Integration test for PgAppEventRepo against the real schema (R3.5)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.app_event_repo import AppEvent
from app.infra.persistence.pg_app_event_repo import PgAppEventRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_record_then_read_and_purge(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgAppEventRepo(sessionmaker)
    marker = f"test-{datetime.now(UTC).timestamp()}"
    await repo.record(
        AppEvent(
            level="error",
            source="pytest",
            event=marker,
            entity="agro/v2/t/f/n/telemetry",
            detail={"error_type": "RuntimeError", "error": "boom"},
        )
    )

    async with sessionmaker() as s:
        row = (
            await s.execute(
                text(
                    "SELECT level, source, entity, detail->>'error_type' AS et "
                    "FROM app_event WHERE event = :m"
                ),
                {"m": marker},
            )
        ).one()
    assert row.level == "error"
    assert row.source == "pytest"
    assert row.et == "RuntimeError"

    # purge_older_than with a future cutoff removes our fresh row.
    removed = await repo.purge_older_than(datetime.now(UTC) + timedelta(minutes=1))
    assert removed >= 1
    async with sessionmaker() as s:
        gone = (
            await s.execute(text("SELECT count(*) FROM app_event WHERE event = :m"), {"m": marker})
        ).scalar()
    assert gone == 0
