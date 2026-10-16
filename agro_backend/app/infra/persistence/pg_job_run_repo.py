"""Postgres adapter for
:class:`~app.application.ports.job_run_repo.JobRunRepo`."""

from __future__ import annotations

import datetime as _dt
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.job_run_repo import JobRun

_INSERT = text(
    """
    INSERT INTO job_run (
        id, job_name, started_at, finished_at, duration_ms, status,
        summary, error_type, error_message
    ) VALUES (
        :id, :job_name, :started_at, :finished_at, :duration_ms, :status,
        CAST(:summary AS JSONB), :error_type, :error_message
    )
    ON CONFLICT (id) DO NOTHING
    """
)


class PgJobRunRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, run: JobRun) -> None:
        params = {
            "id": run.id,
            "job_name": run.job_name,
            "started_at": run.started_at,
            "finished_at": run.finished_at,
            "duration_ms": run.duration_ms,
            "status": run.status,
            "summary": json.dumps(run.summary, default=str),
            "error_type": run.error_type,
            "error_message": run.error_message,
        }
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, params)

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        async with self._sm() as session, session.begin():
            result = await session.execute(
                text("DELETE FROM job_run WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        return int(getattr(result, "rowcount", 0) or 0)
