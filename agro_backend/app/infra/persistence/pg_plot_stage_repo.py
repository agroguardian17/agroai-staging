"""Postgres adapter for
:class:`~app.application.ports.plot_stage_repo.PlotStageRepo`."""

from __future__ import annotations

import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

# Most recent stage from a run BEFORE the given date (strict — excludes today,
# so recording today's stage never masks the previous one within the same run).
_PREV_SQL = text(
    """
    SELECT stage
    FROM plot_stage_log
    WHERE plot_id = :plot_id AND run_date < :before
    ORDER BY run_date DESC
    LIMIT 1
    """
)

_RECORD_SQL = text(
    """
    INSERT INTO plot_stage_log (plot_id, run_date, stage)
    VALUES (:plot_id, :run_date, :stage)
    ON CONFLICT (plot_id, run_date) DO UPDATE SET
        stage = EXCLUDED.stage,
        recorded_at = now()
    """
)


class PgPlotStageRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def previous_stage(self, plot_id: str, before: datetime.date) -> str | None:
        async with self._sm() as session:
            row = (
                await session.execute(_PREV_SQL, {"plot_id": plot_id, "before": before})
            ).one_or_none()
        return row.stage if row is not None else None

    async def record_stage(self, plot_id: str, run_date: datetime.date, stage: str) -> None:
        async with self._sm() as session, session.begin():
            await session.execute(
                _RECORD_SQL, {"plot_id": plot_id, "run_date": run_date, "stage": stage}
            )
