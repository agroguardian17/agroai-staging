"""Postgres adapter for
:class:`~app.application.ports.qa_counters_repo.QaCountersRepo`.

One query with four correlated sub-counts, so a plot with no QA activity yet
returns all zeros (never NULL) in a single round trip.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.qa_counters_repo import QaCounters

_COUNTS_SQL = text(
    """
    SELECT
        (SELECT count(*) FROM advisory_classification
             WHERE plot_id = :plot_id AND classification = 'confirmed_true_positive') AS true_alarm,
        (SELECT count(*) FROM advisory_classification
             WHERE plot_id = :plot_id AND classification = 'false_positive') AS false_alarm,
        (SELECT count(*) FROM farmer_photos WHERE plot_id = :plot_id) AS photo_uploaded,
        (SELECT count(*) FROM photo_label WHERE plot_id = :plot_id) AS photo_labelled
    """
)


class PgQaCountersRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def counts_for_plot(self, plot_id: str) -> QaCounters:
        async with self._sm() as session:
            row = (await session.execute(_COUNTS_SQL, {"plot_id": plot_id})).one()
        r: Any = row
        return QaCounters(
            true_alarm_count=int(r.true_alarm),
            false_alarm_count=int(r.false_alarm),
            photo_uploaded_count=int(r.photo_uploaded),
            photo_labelled_count=int(r.photo_labelled),
        )


__all__ = ["PgQaCountersRepo"]
