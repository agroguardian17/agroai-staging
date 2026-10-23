"""Integration test for PgQaDigestRepo.save_digest (fix A2 — durable digests)."""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.infra.persistence.pg_qa_digest_repo import PgQaDigestRepo

from .conftest import DB_SKIP_REASON, db_available

pytestmark = [
    pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON),
    pytest.mark.asyncio,
]

_WEEK = date(2099, 1, 4)  # far-future week — never clashes with real data


async def test_save_digest_upserts(sessionmaker: async_sessionmaker[AsyncSession]) -> None:
    repo = PgQaDigestRepo(sessionmaker)
    await repo.save_digest(_WEEK, "weekly_report", "wr.md", "v1")
    await repo.save_digest(_WEEK, "bias_digest", "bd.md", "bias")
    # Same (week_start, kind) overwrites filename + content — not a duplicate row.
    await repo.save_digest(_WEEK, "weekly_report", "wr2.md", "v2")
    try:
        async with sessionmaker() as s:
            rows = (
                await s.execute(
                    text(
                        "SELECT kind, filename, content FROM qa_digest "
                        "WHERE week_start = :w ORDER BY kind"
                    ),
                    {"w": _WEEK},
                )
            ).all()
        got = {r.kind: (r.filename, r.content) for r in rows}
        assert len(rows) == 2
        assert got["weekly_report"] == ("wr2.md", "v2")  # overwritten by the upsert
        assert got["bias_digest"] == ("bd.md", "bias")
    finally:
        async with sessionmaker() as s, s.begin():
            await s.execute(text("DELETE FROM qa_digest WHERE week_start = :w"), {"w": _WEEK})
