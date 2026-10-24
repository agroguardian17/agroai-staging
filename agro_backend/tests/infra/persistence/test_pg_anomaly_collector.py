"""Integration test for PgAnomalyCollector against the real schema.

Validates that every probe's SQL is valid against the migrated database — the
guard that would have caught the ``:now``-inferred-as-interval bug (asyncpg
typed a bare ``:now`` bind as interval inside ``:now - make_interval(...)``, so
``timestamptz > interval`` failed and the probe silently returned nothing).

The collector swallows probe errors by design, so "ran but returned empty" and
"raised and was swallowed" look the same through ``collect()``. We therefore
execute each probe's raw SQL directly here (a bad query raises and fails the
test), then also call ``collect()`` and assert the always-answerable scalar
probe returned a concrete value.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.anomaly.pg_collector import (
    _ADVISORY_BASELINE_SQL,
    _ADVISORY_TODAY_SQL,
    _DEVICE_GAP_SQL,
    _RULE_FIRE_RATE_SQL,
    _STUCK_FIELDS,
    PgAnomalyCollector,
    _stuck_sql,
)

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_every_probe_sql_is_valid(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    now = datetime.now(UTC)
    async with sessionmaker() as s:
        await s.execute(text(_DEVICE_GAP_SQL), {"now": now})
        await s.execute(text(_RULE_FIRE_RATE_SQL), {"now": now, "win": 7})
        await s.execute(text(_ADVISORY_TODAY_SQL), {"now": now})
        await s.execute(text(_ADVISORY_BASELINE_SQL), {"now": now, "win": 14})
        for field in _STUCK_FIELDS:
            # A bad column name or a type-inference bug raises here.
            await s.execute(text(_stuck_sql(field)), {"now": now, "n": 12})


async def test_collect_runs_and_counts(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    collector = PgAnomalyCollector(sessionmaker)
    inputs = await collector.collect(
        datetime.now(UTC),
        data_gap_minutes=180,
        stuck_min_readings=12,
        rule_always_rate=0.95,
        rule_min_samples=20,
        advisory_spike_factor=3.0,
        advisory_baseline_days=14,
        trace_window_days=7,
    )
    # count(*) is always answerable on a migrated DB; None here would mean the
    # advisory_today probe raised and was swallowed.
    assert inputs.advisory_today is not None
    assert inputs.advisory_today >= 0
    # Signal lists are always concrete lists (empty is fine on a sparse test DB).
    assert isinstance(inputs.device_gaps, list)
    assert isinstance(inputs.stuck_sensors, list)
    assert isinstance(inputs.rule_fire_rates, list)
