"""Postgres adapter for
:class:`~app.application.ports.anomaly_repo.AnomalyRepo` (Round-3 R3.4)."""

from __future__ import annotations

import datetime as _dt
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.anomalies import AnomalyFinding

_INSERT = text(
    """
    INSERT INTO anomaly_finding (
        id, run_id, created_at, anomaly_type, severity,
        entity_type, entity_id, observed, expected, detail
    ) VALUES (
        :id, :run_id, :created_at, :anomaly_type, :severity,
        :entity_type, :entity_id, :observed, :expected, :detail
    )
    """
)


class PgAnomalyRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record_run(
        self, run_id: str, created_at: _dt.datetime, findings: list[AnomalyFinding]
    ) -> None:
        rows = [
            {
                "id": str(uuid4()),
                "run_id": run_id,
                "created_at": created_at,
                "anomaly_type": f.anomaly_type,
                "severity": f.severity,
                "entity_type": f.entity_type,
                "entity_id": f.entity_id,
                "observed": f.observed,
                "expected": f.expected,
                "detail": f.detail,
            }
            for f in findings
        ]
        if not rows:
            return
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, rows)

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        async with self._sm() as session, session.begin():
            result = await session.execute(
                text("DELETE FROM anomaly_finding WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        return int(getattr(result, "rowcount", 0) or 0)
