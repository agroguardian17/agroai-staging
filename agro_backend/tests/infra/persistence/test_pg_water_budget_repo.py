"""Integration tests for PgWaterBudgetRepo against the seeded variety table."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.persistence.pg_water_budget_repo import PgWaterBudgetRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_targets_for_dap_matches_stage_window(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    # DAP 100 falls in Mahima's G3 window (91-150); loose variety match on "Mahima".
    t = await repo.targets_for_dap("Mahima", 100)
    assert t is not None
    assert t.stage == "G3"
    assert float(t.stage_target_l_high) == 110.0
    assert float(t.max_l_per_event) == 4.0
    # DAP 50 falls in G2 (36-90).
    t2 = await repo.targets_for_dap("Mahima", 50)
    assert t2 is not None and t2.stage == "G2"


async def test_lifecycle_high(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    assert float(await repo.lifecycle_high("Mahima")) == 250.0
    assert await repo.lifecycle_high("NoSuchVariety") is None


async def test_flow_and_last_irrigation_none_when_no_readings(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    since = datetime(2020, 1, 1, tzinfo=UTC)
    assert await repo.flow_litres_since("PLOT_DOES_NOT_EXIST", since) is None
    assert await repo.last_irrigation_at("PLOT_DOES_NOT_EXIST") is None


async def test_targets_none_for_unknown_variety(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    assert await repo.targets_for_dap("NoSuchVariety", 100) is None
