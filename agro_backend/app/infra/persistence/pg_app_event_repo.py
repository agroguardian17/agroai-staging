"""Postgres adapter for
:class:`~app.application.ports.app_event_repo.AppEventRepo` (Round-3 R3.5)."""

from __future__ import annotations

import datetime as _dt
import json
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.app_event_repo import AppEvent

_INSERT = text(
    """
    INSERT INTO app_event (id, created_at, level, source, event, entity, detail)
    VALUES (:id, now(), :level, :source, :event, :entity, CAST(:detail AS JSONB))
    """
)


class PgAppEventRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, event: AppEvent) -> None:
        params = {
            "id": str(uuid4()),
            "level": event.level,
            "source": event.source,
            "event": event.event,
            "entity": event.entity,
            "detail": json.dumps(event.detail, default=str),
        }
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, params)

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        async with self._sm() as session, session.begin():
            result = await session.execute(
                text("DELETE FROM app_event WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        return int(getattr(result, "rowcount", 0) or 0)
