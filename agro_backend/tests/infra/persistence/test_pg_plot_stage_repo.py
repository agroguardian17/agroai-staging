"""Integration tests for PgPlotStageRepo against the plot_stage_log table."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.persistence.pg_plot_stage_repo import PgPlotStageRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_PLOT = "PLOT_STAGE_TEST_001"


@pytest.fixture
async def _clean(sessionmaker: async_sessionmaker[AsyncSession]):
    async with sessionmaker() as s, s.begin():
        await s.execute(text("DELETE FROM plot_stage_log WHERE plot_id = :p"), {"p": _PLOT})
    yield
    async with sessionmaker() as s, s.begin():
        await s.execute(text("DELETE FROM plot_stage_log WHERE plot_id = :p"), {"p": _PLOT})


async def test_previous_stage_none_when_no_history(
    sessionmaker: async_sessionmaker[AsyncSession], _clean: None
) -> None:
    repo = PgPlotStageRepo(sessionmaker)
    assert await repo.previous_stage(_PLOT, date(2026, 8, 3)) is None


async def test_record_then_read_previous(
    sessionmaker: async_sessionmaker[AsyncSession], _clean: None
) -> None:
    repo = PgPlotStageRepo(sessionmaker)
    await repo.record_stage(_PLOT, date(2026, 8, 1), "G1")
    await repo.record_stage(_PLOT, date(2026, 8, 2), "G2")
    # Strictly-before: today's own row does not mask the previous one.
    assert await repo.previous_stage(_PLOT, date(2026, 8, 2)) == "G1"
    assert await repo.previous_stage(_PLOT, date(2026, 8, 3)) == "G2"


async def test_record_is_idempotent_upsert(
    sessionmaker: async_sessionmaker[AsyncSession], _clean: None
) -> None:
    repo = PgPlotStageRepo(sessionmaker)
    await repo.record_stage(_PLOT, date(2026, 8, 2), "G1")
    await repo.record_stage(_PLOT, date(2026, 8, 2), "G2")  # same day -> overwrite
    assert await repo.previous_stage(_PLOT, date(2026, 8, 3)) == "G2"
