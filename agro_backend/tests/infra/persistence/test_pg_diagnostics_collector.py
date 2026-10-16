"""Integration test for PgDiagnosticsCollector against the real schema.

Validates that every probe's SQL is valid against the migrated database (this is
the guard that would have caught a wrong column name like the k_source bug). It
does not assert specific data values — only that the probes run and the always-
answerable ones (partition state, duplicate count) return a concrete value.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.diagnostics.pg_collector import PgDiagnosticsCollector

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_collect_runs_all_probes(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    collector = PgDiagnosticsCollector(sessionmaker)
    now = datetime.now(UTC)
    inputs = await collector.collect(
        now, readings_max_age_hours=6, satellite_enabled=False, satellite_max_age_days=14
    )
    assert inputs.now == now
    # Always answerable on a migrated DB — if the SQL were wrong these would be None.
    assert inputs.has_default_partition is not None
    assert inputs.duplicate_advisory_groups is not None
    assert inputs.duplicate_advisory_groups >= 0
    # Satellite feed disabled -> probe skipped, so no image date gathered.
    assert inputs.latest_satellite_image_date is None
