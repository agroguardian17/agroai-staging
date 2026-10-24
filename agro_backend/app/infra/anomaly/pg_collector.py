"""Postgres data source for the anomaly engine (Round-3 R3.4).

Implements :class:`~app.application.ports.anomaly_data.AnomalyDataSource`. Each
signal is read by its own small, **best-effort** query: if a probe raises
(table missing, transient DB error) that signal is left empty and the matching
detector simply emits no finding rather than failing the whole run.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.anomalies import (
    AnomalyInputs,
    DeviceGap,
    RuleFireRate,
    StuckSensor,
)

log = structlog.get_logger(__name__)

# Numeric reading fields worth a stuck-sensor check (one probe each). These are
# the calibrated engineering columns most likely to flag a disconnected/frozen
# probe; adding a field here is a one-line change.
_STUCK_FIELDS: tuple[str, ...] = (
    "soil_moisture_avg_pct",
    "soil_temp_c",
    "soil_ph",
    "soil_ec_ms_cm",
    "battery_voltage_v",
    "water_flow_lpm",
)

# Minutes since each device's last reading. Only devices that have ever reported.
_DEVICE_GAP_SQL = """
SELECT node_id, EXTRACT(EPOCH FROM (:now - max(recorded_at))) / 60.0 AS mins
FROM node_sensor_readings
GROUP BY node_id
"""

# Per-rule fire rate from the R3.1 pipeline traces' s7_rules.evaluations JSON.
_RULE_FIRE_RATE_SQL = """
WITH ev AS (
    SELECT (e->>'rule_id') AS rule_id, (e->>'fired')::boolean AS fired
    FROM pipeline_trace t,
         LATERAL jsonb_array_elements(
             COALESCE(t.stages->'s7_rules'->'evaluations', '[]'::jsonb)
         ) AS e
    WHERE t.created_at > :now - make_interval(days => :win)
      AND t.drop_reason IS NULL
)
SELECT rule_id, count(*) AS samples, count(*) FILTER (WHERE fired) AS fires
FROM ev
WHERE rule_id IS NOT NULL
GROUP BY rule_id
"""

_ADVISORY_TODAY_SQL = """
SELECT count(*) FROM ai_suggestions
WHERE ai_model_version = 'ginger-engine/v1.0'
  AND (generated_at AT TIME ZONE 'UTC')::date = (:now AT TIME ZONE 'UTC')::date
"""

# Mean advisories/day over the trailing window, excluding today.
_ADVISORY_BASELINE_SQL = """
SELECT avg(c)::float FROM (
    SELECT (generated_at AT TIME ZONE 'UTC')::date AS d, count(*) AS c
    FROM ai_suggestions
    WHERE ai_model_version = 'ginger-engine/v1.0'
      AND generated_at >= :now - make_interval(days => :win)
      AND (generated_at AT TIME ZONE 'UTC')::date < (:now AT TIME ZONE 'UTC')::date
    GROUP BY 1
) q
"""


class PgAnomalyCollector:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def _rows(self, sql: str, params: dict[str, Any] | None = None) -> list[Any]:
        try:
            async with self._sm() as session:
                result = await session.execute(text(sql), params or {})
                return list(result.all())
        except Exception:
            log.debug("anomaly_collector.probe_failed", sql=sql.strip()[:60])
            return []

    async def _scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with self._sm() as session:
                result = await session.execute(text(sql), params or {})
                return result.scalar()
        except Exception:
            log.debug("anomaly_collector.scalar_failed", sql=sql.strip()[:60])
            return None

    async def _stuck_for_field(self, field: str, *, now: _dt.datetime, n: int) -> list[StuckSensor]:
        # Last `n` non-null readings per device; stuck iff they're all identical.
        # The column is interpolated from a fixed allow-list (never user input).
        sql = f"""
        WITH recent AS (
            SELECT node_id, {field} AS v,
                   row_number() OVER (PARTITION BY node_id ORDER BY recorded_at DESC) AS rn
            FROM node_sensor_readings
            WHERE recorded_at > :now - make_interval(days => 2) AND {field} IS NOT NULL
        )
        SELECT node_id, count(*) AS n, max(v) AS val
        FROM recent
        WHERE rn <= :n
        GROUP BY node_id
        HAVING count(*) >= :n AND count(DISTINCT v) = 1
        """
        rows = await self._rows(sql, {"now": now, "n": n})
        return [
            StuckSensor(device_id=r.node_id, field=field, value=str(r.val), n_readings=int(r.n))
            for r in rows
        ]

    async def collect(
        self,
        now: _dt.datetime,
        *,
        data_gap_minutes: int,
        stuck_min_readings: int,
        rule_always_rate: float,
        rule_min_samples: int,
        advisory_spike_factor: float,
        advisory_baseline_days: int,
        trace_window_days: int,
    ) -> AnomalyInputs:
        gap_rows = await self._rows(_DEVICE_GAP_SQL, {"now": now})
        device_gaps = [
            DeviceGap(device_id=r.node_id, minutes_since_last=float(r.mins))
            for r in gap_rows
            if r.mins is not None
        ]

        stuck: list[StuckSensor] = []
        for fld in _STUCK_FIELDS:
            stuck += await self._stuck_for_field(fld, now=now, n=stuck_min_readings)

        rate_rows = await self._rows(_RULE_FIRE_RATE_SQL, {"now": now, "win": trace_window_days})
        rule_fire_rates = [
            RuleFireRate(rule_id=r.rule_id, samples=int(r.samples), fires=int(r.fires))
            for r in rate_rows
        ]

        advisory_today = await self._scalar(_ADVISORY_TODAY_SQL, {"now": now})
        advisory_baseline = await self._scalar(
            _ADVISORY_BASELINE_SQL, {"now": now, "win": advisory_baseline_days}
        )

        return AnomalyInputs(
            now=now,
            data_gap_minutes=data_gap_minutes,
            stuck_min_readings=stuck_min_readings,
            rule_always_rate=rule_always_rate,
            rule_min_samples=rule_min_samples,
            advisory_spike_factor=advisory_spike_factor,
            device_gaps=device_gaps,
            stuck_sensors=stuck,
            rule_fire_rates=rule_fire_rates,
            advisory_today=(int(advisory_today) if advisory_today is not None else None),
            advisory_baseline_avg=(
                float(advisory_baseline) if advisory_baseline is not None else None
            ),
        )
