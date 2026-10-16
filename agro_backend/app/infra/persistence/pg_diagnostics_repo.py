"""Postgres adapter for
:class:`~app.application.ports.diagnostics_repo.DiagnosticsRepo`."""

from __future__ import annotations

import datetime as _dt
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.diagnostics import CheckResult

_INSERT = text(
    """
    INSERT INTO diagnostics_result (
        id, run_id, created_at, check_id, category, status, observed, expected, detail
    ) VALUES (
        :id, :run_id, :created_at, :check_id, :category, :status, :observed, :expected, :detail
    )
    """
)


class PgDiagnosticsRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record_run(
        self, run_id: str, created_at: _dt.datetime, results: list[CheckResult]
    ) -> None:
        rows = [
            {
                "id": str(uuid4()),
                "run_id": run_id,
                "created_at": created_at,
                "check_id": r.check_id,
                "category": r.category,
                "status": r.status,
                "observed": r.observed,
                "expected": r.expected,
                "detail": r.detail,
            }
            for r in results
        ]
        if not rows:
            return
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, rows)

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        async with self._sm() as session, session.begin():
            result = await session.execute(
                text("DELETE FROM diagnostics_result WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        return int(getattr(result, "rowcount", 0) or 0)
