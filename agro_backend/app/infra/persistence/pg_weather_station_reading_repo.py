"""Postgres adapter for :class:`WeatherStationReadingRepo` (Round 17).

Writes into ``weather_station_readings`` (created in migration 0001,
range-partitioned by ``recorded_at`` in migration 0005). Idempotent on
the composite unique constraint ``weather_station_readings_idem``.

Mirrors the shape + conventions of ``PgReadingRepo`` and
``PgMainNodeReadingRepo``: Decimal-safe conversion at the storage
boundary, ``ON CONFLICT DO NOTHING RETURNING`` for idempotent inserts,
short-lived sessions per call.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.weather_station_reading import WeatherStationReading

_INSERT_COLUMNS: tuple[str, ...] = (
    "tenant_id",
    "master_node_id",
    "farm_id",
    "recorded_at",
    "air_temp_c",
    "air_temp_min_c",
    "air_temp_max_c",
    "humidity_pct",
    "dew_point_c",
    "atmospheric_pressure_hpa",
    "wind_speed_kmh",
    "wind_speed_max_gust_kmh",
    "wind_direction_degrees",
    "wind_direction_cardinal",
    "rain_mm_current_hour",
    "rain_mm_today",
    "rain_mm_last_7_days",
    "rain_mm_this_season",
    "light_intensity_lux",
    "uv_index",
    "leaf_wetness_pct",
    "fog_detected",
    "fog_intensity",
    "frost_risk",
    "heat_stress_index",
    "evapotranspiration_mm",
    "weather_station_battery_v",
    "anemometer_fault",
    "rain_gauge_fault",
)


def _insert_sql() -> str:
    cols = ", ".join(_INSERT_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in _INSERT_COLUMNS)
    return (
        f"INSERT INTO weather_station_readings ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT (master_node_id, recorded_at) DO NOTHING "
        "RETURNING weather_id"
    )


_SELECT_COLUMNS = "weather_id, " + ", ".join(_INSERT_COLUMNS)


def _to_decimal(v: float | int | Decimal | None) -> Decimal | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _decimal_to_float(v: Decimal | None) -> float | None:
    return None if v is None else float(v)


def _bind_params(reading: WeatherStationReading) -> dict[str, Any]:
    return {
        "tenant_id": reading.tenant_id,
        "master_node_id": reading.master_node_id,
        "farm_id": reading.farm_id,
        "recorded_at": reading.recorded_at,
        "air_temp_c": _decimal_to_float(reading.air_temp_c),
        "air_temp_min_c": _decimal_to_float(reading.air_temp_min_c),
        "air_temp_max_c": _decimal_to_float(reading.air_temp_max_c),
        "humidity_pct": _decimal_to_float(reading.humidity_pct),
        "dew_point_c": _decimal_to_float(reading.dew_point_c),
        "atmospheric_pressure_hpa": _decimal_to_float(reading.atmospheric_pressure_hpa),
        "wind_speed_kmh": _decimal_to_float(reading.wind_speed_kmh),
        "wind_speed_max_gust_kmh": _decimal_to_float(reading.wind_speed_max_gust_kmh),
        "wind_direction_degrees": _decimal_to_float(reading.wind_direction_degrees),
        "wind_direction_cardinal": reading.wind_direction_cardinal,
        "rain_mm_current_hour": _decimal_to_float(reading.rain_mm_current_hour),
        "rain_mm_today": _decimal_to_float(reading.rain_mm_today),
        "rain_mm_last_7_days": _decimal_to_float(reading.rain_mm_last_7_days),
        "rain_mm_this_season": _decimal_to_float(reading.rain_mm_this_season),
        "light_intensity_lux": _decimal_to_float(reading.light_intensity_lux),
        "uv_index": _decimal_to_float(reading.uv_index),
        "leaf_wetness_pct": _decimal_to_float(reading.leaf_wetness_pct),
        "fog_detected": reading.fog_detected,
        "fog_intensity": reading.fog_intensity,
        "frost_risk": reading.frost_risk,
        "heat_stress_index": _decimal_to_float(reading.heat_stress_index),
        "evapotranspiration_mm": _decimal_to_float(reading.evapotranspiration_mm),
        "weather_station_battery_v": _decimal_to_float(reading.weather_station_battery_v),
        "anemometer_fault": reading.anemometer_fault,
        "rain_gauge_fault": reading.rain_gauge_fault,
    }


def _row_to_reading(row: Any) -> WeatherStationReading:
    return WeatherStationReading(
        tenant_id=row.tenant_id,
        master_node_id=row.master_node_id,
        farm_id=row.farm_id,
        recorded_at=row.recorded_at,
        air_temp_c=_to_decimal(row.air_temp_c),
        air_temp_min_c=_to_decimal(row.air_temp_min_c),
        air_temp_max_c=_to_decimal(row.air_temp_max_c),
        humidity_pct=_to_decimal(row.humidity_pct),
        dew_point_c=_to_decimal(row.dew_point_c),
        atmospheric_pressure_hpa=_to_decimal(row.atmospheric_pressure_hpa),
        wind_speed_kmh=_to_decimal(row.wind_speed_kmh),
        wind_speed_max_gust_kmh=_to_decimal(row.wind_speed_max_gust_kmh),
        wind_direction_degrees=_to_decimal(row.wind_direction_degrees),
        wind_direction_cardinal=row.wind_direction_cardinal,
        rain_mm_current_hour=_to_decimal(row.rain_mm_current_hour),
        rain_mm_today=_to_decimal(row.rain_mm_today),
        rain_mm_last_7_days=_to_decimal(row.rain_mm_last_7_days),
        rain_mm_this_season=_to_decimal(row.rain_mm_this_season),
        light_intensity_lux=_to_decimal(row.light_intensity_lux),
        uv_index=_to_decimal(row.uv_index),
        leaf_wetness_pct=_to_decimal(row.leaf_wetness_pct),
        fog_detected=row.fog_detected,
        fog_intensity=row.fog_intensity,
        frost_risk=row.frost_risk,
        heat_stress_index=_to_decimal(row.heat_stress_index),
        evapotranspiration_mm=_to_decimal(row.evapotranspiration_mm),
        weather_station_battery_v=_to_decimal(row.weather_station_battery_v),
        anemometer_fault=row.anemometer_fault,
        rain_gauge_fault=row.rain_gauge_fault,
    )


class PgWeatherStationReadingRepo:
    """Concrete :class:`WeatherStationReadingRepo` against Postgres."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def save(self, reading: WeatherStationReading) -> int | None:
        stmt = text(_insert_sql())
        async with self._sm() as session:
            res = await session.execute(stmt, _bind_params(reading))
            row = res.first()
            await session.commit()
        if row is None:
            return None
        return int(row.weather_id)

    async def latest_for_node(self, master_node_id: str, limit: int) -> list[WeatherStationReading]:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS} FROM weather_station_readings "
            "WHERE master_node_id = :master_node_id "
            "ORDER BY recorded_at DESC LIMIT :limit"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"master_node_id": master_node_id, "limit": limit})
            return [_row_to_reading(r) for r in res.all()]

    async def most_recent(self, master_node_id: str) -> WeatherStationReading | None:
        rows = await self.latest_for_node(master_node_id, limit=1)
        return rows[0] if rows else None


__all__ = ["PgWeatherStationReadingRepo"]
