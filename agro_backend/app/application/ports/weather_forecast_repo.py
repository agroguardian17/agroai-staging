"""Port: persistence for fetched weather forecasts (``weather_forecasts``)."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ForecastRow:
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    fetched_at: datetime.datetime
    forecast_for_date: datetime.date
    source_api: str
    temp_min_c: float | None
    temp_max_c: float | None
    rain_mm_expected: float | None
    rain_probability_pct: float | None
    wind_speed_kmh: float | None
    et0_mm: float | None = None
    solar_radiation_mj_m2: float | None = None


@runtime_checkable
class WeatherForecastRepo(Protocol):
    async def save_daily(self, rows: list[ForecastRow]) -> int:
        """Insert daily forecast rows; return how many were written."""
        ...

    async def window_for_farm(
        self, farm_id: uuid.UUID, date_from: datetime.date, date_to: datetime.date
    ) -> list[ForecastRow]:
        """Rows for the farm with ``forecast_for_date`` in [from, to], one per
        date (the most recently fetched), ordered by date ascending."""
        ...


__all__ = ["ForecastRow", "WeatherForecastRepo"]
