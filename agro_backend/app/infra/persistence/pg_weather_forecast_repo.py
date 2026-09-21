"""Postgres adapter for
:class:`~app.application.ports.weather_forecast_repo.WeatherForecastRepo`.

Inserts daily rows into the partitioned ``weather_forecasts`` table (RANGE on
``fetched_at``). ``forecast_id`` is server-assigned.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.weather_forecast_repo import ForecastRow


class PgWeatherForecastRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def save_daily(self, rows: list[ForecastRow]) -> int:
        if not rows:
            return 0
        stmt = text(
            """
            INSERT INTO weather_forecasts (
                fetched_at, tenant_id, farm_id, forecast_for_date, source_api,
                temp_min_c, temp_max_c, rain_mm_expected,
                rain_probability_pct, wind_speed_kmh, et0_mm, solar_radiation_mj_m2,
                vpd_night_mean_kpa, fog_observed, wind_gust_kmph
            ) VALUES (
                :fetched_at, :tenant_id, :farm_id, :forecast_for_date, :source_api,
                :temp_min_c, :temp_max_c, :rain_mm_expected,
                :rain_probability_pct, :wind_speed_kmh, :et0_mm, :solar_radiation_mj_m2,
                :vpd_night_mean_kpa, :fog_observed, :wind_gust_kmph
            )
            """
        )
        params = [
            {
                "fetched_at": r.fetched_at,
                "tenant_id": r.tenant_id,
                "farm_id": r.farm_id,
                "forecast_for_date": r.forecast_for_date,
                "source_api": r.source_api,
                "temp_min_c": r.temp_min_c,
                "temp_max_c": r.temp_max_c,
                "rain_mm_expected": r.rain_mm_expected,
                "rain_probability_pct": r.rain_probability_pct,
                "wind_speed_kmh": r.wind_speed_kmh,
                "et0_mm": r.et0_mm,
                "solar_radiation_mj_m2": r.solar_radiation_mj_m2,
                "vpd_night_mean_kpa": r.vpd_night_mean_kpa,
                "fog_observed": r.fog_observed,
                "wind_gust_kmph": r.wind_gust_kmph,
            }
            for r in rows
        ]
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            await session.commit()
        # asyncpg reports rowcount == -1 for an executemany; the commit succeeded,
        # so every row we passed was inserted.
        rc = cast(Any, res).rowcount
        return len(rows) if rc is None or rc < 0 else int(rc)

    async def window_for_farm(
        self, farm_id: uuid.UUID, date_from: datetime.date, date_to: datetime.date
    ) -> list[ForecastRow]:
        # One row per forecast date — the most recently fetched for that date.
        stmt = text(
            """
            SELECT DISTINCT ON (forecast_for_date)
                   tenant_id, farm_id, fetched_at, forecast_for_date, source_api,
                   temp_min_c, temp_max_c, rain_mm_expected, rain_probability_pct,
                   wind_speed_kmh, et0_mm, solar_radiation_mj_m2,
                   vpd_night_mean_kpa, fog_observed, wind_gust_kmph
            FROM weather_forecasts
            WHERE farm_id = :farm_id
              AND forecast_for_date BETWEEN :date_from AND :date_to
            ORDER BY forecast_for_date, fetched_at DESC
            """
        )
        async with self._sm() as session:
            rows = (
                await session.execute(
                    stmt, {"farm_id": farm_id, "date_from": date_from, "date_to": date_to}
                )
            ).all()
        out: list[ForecastRow] = []
        for row in rows:
            r: Any = row
            out.append(
                ForecastRow(
                    tenant_id=r.tenant_id,
                    farm_id=r.farm_id,
                    fetched_at=r.fetched_at,
                    forecast_for_date=r.forecast_for_date,
                    source_api=r.source_api,
                    temp_min_c=r.temp_min_c,
                    temp_max_c=r.temp_max_c,
                    rain_mm_expected=r.rain_mm_expected,
                    rain_probability_pct=r.rain_probability_pct,
                    wind_speed_kmh=r.wind_speed_kmh,
                    et0_mm=r.et0_mm,
                    solar_radiation_mj_m2=r.solar_radiation_mj_m2,
                    vpd_night_mean_kpa=r.vpd_night_mean_kpa,
                    fog_observed=r.fog_observed,
                    wind_gust_kmph=r.wind_gust_kmph,
                )
            )
        return out


__all__ = ["PgWeatherForecastRepo"]
