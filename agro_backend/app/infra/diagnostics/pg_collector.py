"""Postgres data source for the diagnostics battery.

Implements :class:`~app.application.ports.diagnostics_data.DiagnosticsDataSource`.
Each observed value is read by its own small, **best-effort** query: if a probe
raises (table missing, transient DB error) its field is left ``None`` and the
matching check degrades to ``skip`` rather than failing the whole battery.
"""

from __future__ import annotations

import datetime as _dt
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.diagnostics import DiagnosticsInputs

log = structlog.get_logger(__name__)

# EXISTS() over the partition children: true iff node_sensor_readings has a
# DEFAULT catch-all partition (migration 0067).
_DEFAULT_PARTITION_SQL = """
SELECT EXISTS (
    SELECT 1
    FROM pg_inherits i
    JOIN pg_class parent ON parent.oid = i.inhparent
    JOIN pg_class child ON child.oid = i.inhrelid
    WHERE parent.relname = 'node_sensor_readings'
      AND pg_get_expr(child.relpartbound, child.oid) = 'DEFAULT'
)
"""

# Count of (plot, UTC-day, rule) groups with more than one ginger-engine
# advisory — should be 0 since the daily-unique index (migration 0066).
_DUPLICATE_ADVISORY_SQL = """
SELECT count(*) FROM (
    SELECT plot_id, (generated_at AT TIME ZONE 'UTC')::date AS day, rule_id
    FROM ai_suggestions
    WHERE ai_model_version = 'ginger-engine/v1.0' AND rule_id IS NOT NULL
    GROUP BY 1, 2, 3
    HAVING count(*) > 1
) dups
"""


class PgDiagnosticsCollector:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def _scalar(self, sql: str, params: dict[str, Any] | None = None) -> Any:
        try:
            async with self._sm() as session:
                result = await session.execute(text(sql), params or {})
                return result.scalar()
        except Exception:  # best-effort: a failed probe → None → check skips
            log.debug("diagnostics_collector.probe_failed", sql=sql.strip()[:60])
            return None

    async def collect(
        self,
        now: _dt.datetime,
        *,
        readings_max_age_hours: int,
        satellite_enabled: bool,
        satellite_max_age_days: int,
    ) -> DiagnosticsInputs:
        latest_reading_at = await self._scalar("SELECT max(recorded_at) FROM node_sensor_readings")
        latest_forecast = await self._scalar("SELECT max(forecast_for_date) FROM weather_forecasts")
        latest_satellite = (
            await self._scalar("SELECT max(image_date) FROM satellite_data")
            if satellite_enabled
            else None
        )
        has_default_partition = await self._scalar(_DEFAULT_PARTITION_SQL)
        dup_groups = await self._scalar(_DUPLICATE_ADVISORY_SQL)
        last_forecast_job = await self._scalar(
            "SELECT max(started_at) FROM job_run "
            "WHERE job_name = 'weather_forecast' AND status = 'ok'"
        )

        return DiagnosticsInputs(
            now=now,
            readings_max_age_hours=readings_max_age_hours,
            satellite_max_age_days=satellite_max_age_days,
            satellite_enabled=satellite_enabled,
            latest_reading_at=latest_reading_at,
            latest_forecast_for_date=latest_forecast,
            latest_satellite_image_date=latest_satellite,
            has_default_partition=(
                bool(has_default_partition) if has_default_partition is not None else None
            ),
            duplicate_advisory_groups=(int(dup_groups) if dup_groups is not None else None),
            last_forecast_job_ok_at=last_forecast_job,
        )
