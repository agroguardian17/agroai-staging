"""Postgres adapter for
:class:`~app.application.ports.erasure_request_repo.ErasureRequestRepo`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.erasure_request_repo import ErasureRequest

# ON CONFLICT on the partial unique index (one pending per farmer) → no dup.
_CREATE_SQL = text(
    """
    INSERT INTO erasure_request (farmer_id, due_at, method, actor)
    VALUES (:farmer_id, :due_at, :method, :actor)
    ON CONFLICT (farmer_id) WHERE status = 'pending' DO NOTHING
    RETURNING id
    """
)

_PENDING_SQL = text(
    """
    SELECT id, farmer_id, requested_at, due_at, status, method, actor
    FROM erasure_request
    WHERE farmer_id = :farmer_id AND status = 'pending'
    ORDER BY requested_at DESC LIMIT 1
    """
)


class PgErasureRequestRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def create(
        self,
        *,
        farmer_id: uuid.UUID,
        due_at: datetime,
        method: str | None,
        actor: str | None,
    ) -> bool:
        params = {"farmer_id": farmer_id, "due_at": due_at, "method": method, "actor": actor}
        async with self._sm() as session:
            res = await session.execute(_CREATE_SQL, params)
            row = res.first()
            await session.commit()
        return row is not None

    async def pending_for(self, farmer_id: uuid.UUID) -> ErasureRequest | None:
        async with self._sm() as session:
            row = (await session.execute(_PENDING_SQL, {"farmer_id": farmer_id})).first()
        if row is None:
            return None
        r: Any = row
        return ErasureRequest(
            id=r.id,
            farmer_id=r.farmer_id,
            requested_at=r.requested_at,
            due_at=r.due_at,
            status=r.status,
            method=r.method,
            actor=r.actor,
        )


__all__ = ["PgErasureRequestRepo"]
