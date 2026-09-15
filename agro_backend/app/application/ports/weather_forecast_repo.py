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


@runtime_checkable
class WeatherForecastRepo(Protocol):
    async def save_daily(self, rows: list[ForecastRow]) -> int:
        """Insert daily forecast rows; return how many were written."""
        ...


__all__ = ["ForecastRow", "WeatherForecastRepo"]
