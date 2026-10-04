"""Postgres adapter for
:class:`~app.application.ports.plot_run_trace_repo.PlotRunTraceRepo`."""

from __future__ import annotations

import datetime as _dt
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.plot_run_trace_repo import PlotRunTrace

_INSERT = text(
    """
    INSERT INTO plot_run_trace (
        trace_id, created_at, plot_id, season_id, run_date, tenant_id, farm_id,
        advisories_written, coverage, derived, engine, stages, validations, overall, error
    ) VALUES (
        :trace_id, :created_at, :plot_id, :season_id, :run_date, :tenant_id, :farm_id,
        :advisories_written, CAST(:coverage AS JSONB), CAST(:derived AS JSONB),
        CAST(:engine AS JSONB), CAST(:stages AS JSONB), CAST(:validations AS JSONB),
        :overall, :error
    )
    ON CONFLICT (trace_id) DO NOTHING
    """
)


class PgPlotRunTraceRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, trace: PlotRunTrace) -> None:
        params = {
            "trace_id": trace.trace_id,
            "created_at": trace.created_at,
            "plot_id": trace.plot_id,
            "season_id": trace.season_id,
            "run_date": trace.run_date,
            "tenant_id": trace.tenant_id,
            "farm_id": trace.farm_id,
            "advisories_written": trace.advisories_written,
            "coverage": json.dumps(trace.coverage, default=str),
            "derived": json.dumps(trace.derived, default=str),
            "engine": json.dumps(trace.engine, default=str),
            "stages": json.dumps(trace.stages, default=str),
            "validations": json.dumps(trace.validations, default=str),
            "overall": trace.overall,
            "error": trace.error,
        }
        async with self._sm() as session, session.begin():
            await session.execute(_INSERT, params)

    async def purge_older_than(self, cutoff: _dt.datetime) -> int:
        async with self._sm() as session, session.begin():
            result = await session.execute(
                text("DELETE FROM plot_run_trace WHERE created_at < :cutoff"),
                {"cutoff": cutoff},
            )
        return int(getattr(result, "rowcount", 0) or 0)
