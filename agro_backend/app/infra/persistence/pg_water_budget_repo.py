"""Postgres adapter for
:class:`~app.application.ports.water_budget_repo.WaterBudgetRepo`."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.water_budget import VarietyStageTargets

# Sub Node reports every 5 minutes; cumulative litres over a window is the sum of
# per-reading L/min times the cadence. (Approximate: exact per-reading windows
# vary +/-10-15%; refine with window_s when the dose engine needs it.)
_CADENCE_MIN = Decimal("5")

# Loose variety match: the season stores e.g. "Mahima" while the table keys
# "IISR-Mahima"; match on either containing the other, shortest name first.
_TARGETS_SQL = text(
    """
    SELECT stage, dap_start, dap_end,
           stage_target_l_low, stage_target_l_high,
           per_event_l_low, per_event_l_high, max_l_per_event
    FROM variety_stage_water_target
    WHERE (variety ILIKE ('%' || :variety || '%') OR :variety ILIKE ('%' || variety || '%'))
      AND stage <> 'LIFECYCLE'
      AND dap_start <= :dap AND dap_end >= :dap
    ORDER BY length(variety) ASC
    LIMIT 1
    """
)

_LIFECYCLE_SQL = text(
    """
    SELECT stage_target_l_high
    FROM variety_stage_water_target
    WHERE (variety ILIKE ('%' || :variety || '%') OR :variety ILIKE ('%' || variety || '%'))
      AND stage = 'LIFECYCLE'
    ORDER BY length(variety) ASC
    LIMIT 1
    """
)

_FLOW_SQL = text(
    """
    SELECT SUM(water_flow_lpm) AS lpm_sum
    FROM node_sensor_readings
    WHERE plot_id = :plot_id
      AND recorded_at >= :since
      AND water_flow_lpm IS NOT NULL
    """
)

_LAST_IRRIG_SQL = text(
    """
    SELECT MAX(recorded_at) AS last_at
    FROM node_sensor_readings
    WHERE plot_id = :plot_id
      AND water_flow_lpm > 0
    """
)


def _dec(v: object) -> Decimal | None:
    if v is None:
        return None
    return v if isinstance(v, Decimal) else Decimal(str(v))


class PgWaterBudgetRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def targets_for_dap(self, variety: str, dap: int) -> VarietyStageTargets | None:
        async with self._sm() as session:
            row = (
                await session.execute(_TARGETS_SQL, {"variety": variety, "dap": dap})
            ).one_or_none()
        if row is None:
            return None
        return VarietyStageTargets(
            stage=row.stage,
            dap_start=row.dap_start,
            dap_end=row.dap_end,
            stage_target_l_low=_dec(row.stage_target_l_low),
            stage_target_l_high=_dec(row.stage_target_l_high),
            per_event_l_low=_dec(row.per_event_l_low),
            per_event_l_high=_dec(row.per_event_l_high),
            max_l_per_event=_dec(row.max_l_per_event),
        )

    async def lifecycle_high(self, variety: str) -> Decimal | None:
        async with self._sm() as session:
            row = (await session.execute(_LIFECYCLE_SQL, {"variety": variety})).one_or_none()
        return _dec(row.stage_target_l_high) if row is not None else None

    async def flow_litres_since(self, plot_id: str, since: datetime) -> Decimal | None:
        async with self._sm() as session:
            row = (
                await session.execute(_FLOW_SQL, {"plot_id": plot_id, "since": since})
            ).one_or_none()
        lpm_sum = _dec(row.lpm_sum) if row is not None else None
        if lpm_sum is None:
            return None
        return (lpm_sum * _CADENCE_MIN).quantize(Decimal("0.01"))

    async def last_irrigation_at(self, plot_id: str) -> datetime | None:
        async with self._sm() as session:
            row = (await session.execute(_LAST_IRRIG_SQL, {"plot_id": plot_id})).one_or_none()
        return row.last_at if row is not None else None
