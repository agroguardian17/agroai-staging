"""Postgres adapter for
:class:`~app.application.ports.advisory_metrics_repo.AdvisoryMetricsRepo`.

One aggregation query per season derives the Domain 12 compliance counters
from ``ai_suggestions`` (issued) joined against ``farmer_actions`` (completed).

Definitions (kept intentionally conservative so the numbers are defensible):

- **issued**: advisories for the season that actually reached the farmer
  (``whatsapp_sent IS TRUE``). Advice never delivered is not a "recommended
  action issued".
- **completed**: issued advisories with at least one ``farmer_actions`` row
  where ``farmer_followed_ai IS TRUE``.
- **completed on time**: completed advisories whose earliest following action
  was recorded no later than ``on_time_days`` after the advisory date.
- **action_compliance_rate**: ``100 * completed_on_time / issued`` (percent,
  one decimal), or ``NULL`` when nothing was issued.
"""

from __future__ import annotations

import uuid
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_metrics_repo import AdvisoryPerformance

_PERFORMANCE_SQL = text(
    """
    WITH issued AS (
        SELECT s.suggestion_id, s.generated_at::date AS issued_date
        FROM ai_suggestions s
        WHERE s.season_id = :season
          AND s.whatsapp_sent IS TRUE
    ),
    completed AS (
        SELECT i.suggestion_id,
               i.issued_date,
               MIN(fa.action_date) AS first_action_date
        FROM issued i
        JOIN farmer_actions fa
          ON fa.ai_suggestion_id = i.suggestion_id
         AND fa.farmer_followed_ai IS TRUE
        GROUP BY i.suggestion_id, i.issued_date
    )
    SELECT
        (SELECT count(*) FROM issued) AS issued_count,
        (SELECT count(*) FROM completed) AS completed_count,
        (SELECT count(*) FROM completed c
           WHERE c.first_action_date <= c.issued_date + CAST(:on_time_days AS integer)) AS on_time_count
    """
)


class PgAdvisoryMetricsRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def performance_for_season(
        self, season_id: uuid.UUID, *, on_time_days: int = 3
    ) -> AdvisoryPerformance:
        async with self._sm() as session:
            res = await session.execute(
                _PERFORMANCE_SQL, {"season": season_id, "on_time_days": on_time_days}
            )
            row = res.first()
        r: Any = row
        issued = int(r.issued_count or 0) if row is not None else 0
        completed = int(r.completed_count or 0) if row is not None else 0
        on_time = int(r.on_time_count or 0) if row is not None else 0
        rate: Decimal | None = None
        if issued > 0:
            rate = (Decimal(on_time) * Decimal(100) / Decimal(issued)).quantize(
                Decimal("0.1"), rounding=ROUND_HALF_UP
            )
        return AdvisoryPerformance(
            advisory_issued_count=issued,
            advisory_completed_count=completed,
            advisory_completed_on_time_count=on_time,
            action_compliance_rate=rate,
        )


__all__ = ["PgAdvisoryMetricsRepo"]
