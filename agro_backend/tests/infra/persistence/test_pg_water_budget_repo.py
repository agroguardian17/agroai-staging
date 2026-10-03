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
    # Assert STRUCTURE, not the exact seeded magnitudes — the signed variety CSV
    # updates those values and must not break this repo test. We only require
    # that a DAP resolves to the stage whose window contains it, with sane bounds.
    t = await repo.targets_for_dap("Mahima", 100)
    assert t is not None
    assert t.dap_start is not None and t.dap_end is not None
    assert t.dap_start <= 100 <= t.dap_end
    assert t.stage not in (None, "LIFECYCLE")
    if t.stage_target_l_high is not None:
        assert t.stage_target_l_high > 0
    if t.max_l_per_event is not None:
        assert t.max_l_per_event > 0
    # A different DAP resolves to a different (earlier) stage window.
    t2 = await repo.targets_for_dap("Mahima", 50)
    assert t2 is not None and t2.dap_start <= 50 <= t2.dap_end
    assert t2.stage != t.stage


async def test_lifecycle_high(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    high = await repo.lifecycle_high("Mahima")
    assert high is not None and high > 0  # magnitude comes from the signed CSV
    assert await repo.lifecycle_high("NoSuchVariety") is None


async def test_flow_and_last_irrigation_none_when_no_readings(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    since = datetime(2020, 1, 1, tzinfo=UTC)
    assert await repo.flow_litres_since("PLOT_DOES_NOT_EXIST", since) is None
    assert await repo.last_irrigation_at("PLOT_DOES_NOT_EXIST") is None
    assert await repo.last_flow_at("PLOT_DOES_NOT_EXIST") is None


async def test_targets_none_for_unknown_variety(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgWaterBudgetRepo(sessionmaker)
    assert await repo.targets_for_dap("NoSuchVariety", 100) is None
