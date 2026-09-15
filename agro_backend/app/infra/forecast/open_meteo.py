"""Open-Meteo daily-forecast adapter (free, no API key).

Calls ``GET {base}/forecast`` with the daily variables we store, parses the
column-oriented ``daily`` arrays into :class:`DailyForecast` rows. Any network
or shape problem is surfaced as :class:`ForecastError` so the sweep skips one
farm rather than aborting.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.application.ports.forecast_provider import DailyForecast, ForecastError

log = structlog.get_logger(__name__)

_DAILY_VARS = (
    "temperature_2m_max",
    "temperature_2m_min",
    "precipitation_sum",
    "precipitation_probability_max",
    "wind_speed_10m_max",
)


@dataclass(frozen=True, slots=True)
class OpenMeteoSettings:
    base_url: str = "https://api.open-meteo.com/v1"
    timeout_seconds: float = 10.0


def _f(value: Any) -> float | None:
    return None if value is None else float(value)


class OpenMeteoForecastProvider:
    def __init__(
        self, settings: OpenMeteoSettings | None = None, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._s = settings or OpenMeteoSettings()
        self._client = client

    def _params(self, lat: float, lng: float, days: int) -> dict[str, Any]:
        return {
            "latitude": lat,
            "longitude": lng,
            "daily": ",".join(_DAILY_VARS),
            "timezone": "auto",
            "forecast_days": max(1, min(days, 16)),  # Open-Meteo caps at 16
        }

    async def daily_forecast(self, *, lat: float, lng: float, days: int) -> list[DailyForecast]:
        url = f"{self._s.base_url.rstrip('/')}/forecast"
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._s.timeout_seconds)
        try:
            resp = await client.get(url, params=self._params(lat, lng, days))
        except httpx.HTTPError as exc:
            raise ForecastError(f"network_error: {exc}") from exc
        finally:
            if owns:
                await client.aclose()

        if resp.status_code >= 400:
            raise ForecastError(f"http_{resp.status_code}: {resp.text[:200]}")
        try:
            daily = resp.json()["daily"]
            dates = daily["time"]
        except Exception as exc:
            raise ForecastError(f"bad_shape: {exc}") from exc

        out: list[DailyForecast] = []
        for i, day in enumerate(dates):
            out.append(
                DailyForecast(
                    forecast_for_date=datetime.date.fromisoformat(day),
                    temp_max_c=_f(_at(daily, "temperature_2m_max", i)),
                    temp_min_c=_f(_at(daily, "temperature_2m_min", i)),
                    rain_mm_expected=_f(_at(daily, "precipitation_sum", i)),
                    rain_probability_pct=_f(_at(daily, "precipitation_probability_max", i)),
                    wind_speed_kmh=_f(_at(daily, "wind_speed_10m_max", i)),
                )
            )
        return out


def _at(daily: dict[str, Any], key: str, i: int) -> Any:
    seq = daily.get(key)
    if isinstance(seq, list) and i < len(seq):
        return seq[i]
    return None


__all__ = ["OpenMeteoForecastProvider", "OpenMeteoSettings"]
