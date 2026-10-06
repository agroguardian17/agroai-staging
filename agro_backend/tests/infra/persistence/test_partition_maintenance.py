"""Partition maintenance ensures current + N months-ahead children exist.

Guards the fix for the "monthly partitions run out → ingest rejected" latent
bug: ensure_partitions must create the forward window and be idempotent.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.jobs.partition_maintenance import _PARTITIONED_TABLES, ensure_partitions

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]


async def test_ensure_partitions_creates_forward_window_idempotently(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    # Two calls: the second must be a no-op, not an error (IF NOT EXISTS).
    await ensure_partitions(sessionmaker, 6)
    await ensure_partitions(sessionmaker, 6)

    async with sessionmaker() as s:
        # Compute the +6-month suffix with the DB's own clock so there is no
        # local-vs-session timezone / month-boundary flakiness.
        suffix = (
            await s.execute(
                text("SELECT to_char(date_trunc('month', now()) + interval '6 month', 'YYYYMM')")
            )
        ).scalar_one()
        for tbl in _PARTITIONED_TABLES:
            reg = (await s.execute(text(f"SELECT to_regclass('{tbl}_p{suffix}')"))).scalar_one()
            assert reg is not None, f"missing +6mo partition for {tbl} (p{suffix})"


async def test_default_partition_exists(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    # The DEFAULT catch-all from migration 0067 must be present.
    async with sessionmaker() as s:
        for tbl in _PARTITIONED_TABLES:
            reg = (await s.execute(text(f"SELECT to_regclass('{tbl}_pdefault')"))).scalar_one()
            assert reg is not None, f"missing DEFAULT partition for {tbl}"
