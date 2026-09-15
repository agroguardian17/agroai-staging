"""Port: external weather-forecast provider.

Round 18. A nightly job fetches a short-range daily forecast per farm and stores
it in ``weather_forecasts``; the ginger engine + advisory composer read it for
rain/frost/heat awareness. The default adapter is Open-Meteo (free, no API key).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class DailyForecast:
    """One day of a daily forecast at a point."""

    forecast_for_date: datetime.date
    temp_min_c: float | None
    temp_max_c: float | None
    rain_mm_expected: float | None
    rain_probability_pct: float | None
    wind_speed_kmh: float | None


class ForecastError(Exception):
    """The provider could not return a forecast (network / bad shape / rate limit)."""


@runtime_checkable
class ForecastProvider(Protocol):
    async def daily_forecast(self, *, lat: float, lng: float, days: int) -> list[DailyForecast]:
        """Return ``days`` days of daily forecast for the point.

        Implementations raise :class:`ForecastError` on failure so the caller
        can skip one farm without aborting the whole nightly sweep.
        """
        ...


__all__ = ["DailyForecast", "ForecastError", "ForecastProvider"]
