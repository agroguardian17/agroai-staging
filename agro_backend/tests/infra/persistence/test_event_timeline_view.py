"""Integration test for the event_timeline view (R3.2) against the real schema.

The view (migration 0072) UNIONs seven source tables; a wrong column name or a
type mismatch between branches would make the migration's CREATE VIEW — or a
SELECT from it — fail. This is the CI guard (runs on the postgis service) that
proves every branch lines up with the migrated schema. It asserts shape, not
data, so it passes on an empty DB.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_EXPECTED_COLS = {
    "ts",
    "event_kind",
    "event_type",
    "level",
    "entity",
    "summary",
    "source_table",
    "source_id",
}


async def test_view_exists_and_has_expected_shape(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        # A bad column name in any UNION branch raises here.
        result = await s.execute(text("SELECT * FROM event_timeline LIMIT 1"))
        assert _EXPECTED_COLS.issubset(set(result.keys()))


async def test_view_is_filterable_by_kind_and_time(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    async with sessionmaker() as s:
        rows = await s.execute(
            text(
                "SELECT event_kind, count(*) FROM event_timeline "
                "WHERE ts >= now() - make_interval(hours => :h) "
                "AND event_kind = ANY(:kinds) GROUP BY event_kind"
            ),
            {"h": 24, "kinds": ["ingest", "alert", "anomaly", "job"]},
        )
        # Shape/validity only — any row count (including zero) is fine.
        for kind, n in rows.all():
            assert kind in {"ingest", "alert", "anomaly", "job"}
            assert n >= 0
