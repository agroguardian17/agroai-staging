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
    """One day of a daily forecast (or past actual) at a point."""

    forecast_for_date: datetime.date
    temp_min_c: float | None
    temp_max_c: float | None
    rain_mm_expected: float | None
    rain_probability_pct: float | None
    wind_speed_kmh: float | None
    # Phase-3 weather additions: reference ET (pan-evap proxy) + daily shortwave.
    et0_mm: float | None = None
    solar_radiation_mj_m2: float | None = None
    # From hourly RH+temp: mean nighttime (22:00-06:00) VPD, and a fog flag
    # (nighttime RH at/above saturation) - both computed in the adapter.
    vpd_night_mean_kpa: float | None = None
    fog_observed: bool | None = None


class ForecastError(Exception):
    """The provider could not return a forecast (network / bad shape / rate limit)."""


@runtime_checkable
class ForecastProvider(Protocol):
    async def daily_forecast(
        self, *, lat: float, lng: float, days: int, past_days: int = 0
    ) -> list[DailyForecast]:
        """Return ``past_days`` of actuals + ``days`` days of forecast for the point.

        Implementations raise :class:`ForecastError` on failure so the caller
        can skip one farm without aborting the whole nightly sweep.
        """
        ...


__all__ = ["DailyForecast", "ForecastError", "ForecastProvider"]
