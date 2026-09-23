"""Postgres adapter for
:class:`~app.application.ports.advisory_audit_repo.AdvisoryAuditRepo`.

Insert-only: the ``advisory_audit`` table's trigger blocks UPDATE/DELETE, so
this adapter offers no mutation path.
"""

from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_audit_repo import AdvisoryAuditRow

_INSERT_SQL = text(
    """
    INSERT INTO advisory_audit (
        suggestion_id, rule_id, rule_version, model_version, confidence,
        gate_results, inputs
    ) VALUES (
        :suggestion_id, :rule_id, :rule_version, :model_version, :confidence,
        CAST(:gate_results AS JSONB), CAST(:inputs AS JSONB)
    )
    """
)


class PgAdvisoryAuditRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, row: AdvisoryAuditRow) -> None:
        params = {
            "suggestion_id": row.suggestion_id,
            "rule_id": row.rule_id,
            "rule_version": row.rule_version,
            "model_version": row.model_version,
            "confidence": row.confidence,
            "gate_results": json.dumps(row.gate_results or {}),
            "inputs": json.dumps(row.inputs or {}),
        }
        async with self._sm() as session:
            await session.execute(_INSERT_SQL, params)
            await session.commit()


__all__ = ["PgAdvisoryAuditRepo"]
