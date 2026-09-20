"""Open-Meteo daily-forecast adapter (free, no API key).

Calls ``GET {base}/forecast`` with the daily variables we store, parses the
column-oriented ``daily`` arrays into :class:`DailyForecast` rows. Any network
or shape problem is surfaced as :class:`ForecastError` so the sweep skips one
farm rather than aborting.
"""

from __future__ import annotations

import datetime
import math
from collections import defaultdict
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
    "et0_fao_evapotranspiration",
    "shortwave_radiation_sum",
)
_HOURLY_VARS = ("temperature_2m", "relative_humidity_2m")
# Nighttime window (local hours) for VPD/fog aggregation.
_NIGHT_HOURS = frozenset({22, 23, 0, 1, 2, 3, 4, 5})
_FOG_RH_PCT = 98.0


def _vpd_kpa(temp_c: float, rh_pct: float) -> float:
    svp = 0.6108 * math.exp(17.27 * temp_c / (temp_c + 237.3))
    return svp * (1.0 - rh_pct / 100.0)


def _night_aggregates(hourly: dict[str, Any]) -> dict[datetime.date, tuple[float | None, bool]]:
    """Per-date (mean nighttime VPD kPa, fog flag) from hourly temp + RH."""
    times = hourly.get("time")
    temps = hourly.get("temperature_2m")
    rhs = hourly.get("relative_humidity_2m")
    if not isinstance(times, list) or not isinstance(temps, list) or not isinstance(rhs, list):
        return {}
    vpds: dict[datetime.date, list[float]] = defaultdict(list)
    fog: dict[datetime.date, bool] = defaultdict(bool)
    for i, ts in enumerate(times):
        try:
            dt = datetime.datetime.fromisoformat(ts)
        except (ValueError, TypeError):
            continue
        if dt.hour not in _NIGHT_HOURS:
            continue
        t = temps[i] if i < len(temps) else None
        rh = rhs[i] if i < len(rhs) else None
        if t is None or rh is None:
            continue
        # Hours 00-05 belong to that calendar date's night; 22-23 to the same date.
        vpds[dt.date()].append(_vpd_kpa(float(t), float(rh)))
        if float(rh) >= _FOG_RH_PCT:
            fog[dt.date()] = True
    out: dict[datetime.date, tuple[float | None, bool]] = {}
    for d, vs in vpds.items():
        out[d] = (round(sum(vs) / len(vs), 3) if vs else None, fog.get(d, False))
    return out


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

    def _params(self, lat: float, lng: float, days: int, past_days: int) -> dict[str, Any]:
        return {
            "latitude": lat,
            "longitude": lng,
            "daily": ",".join(_DAILY_VARS),
            "hourly": ",".join(_HOURLY_VARS),
            "timezone": "auto",
            "forecast_days": max(1, min(days, 16)),  # Open-Meteo caps at 16
            "past_days": max(0, min(past_days, 92)),  # Open-Meteo caps at 92
        }

    async def daily_forecast(
        self, *, lat: float, lng: float, days: int, past_days: int = 0
    ) -> list[DailyForecast]:
        url = f"{self._s.base_url.rstrip('/')}/forecast"
        owns = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._s.timeout_seconds)
        try:
            resp = await client.get(url, params=self._params(lat, lng, days, past_days))
        except httpx.HTTPError as exc:
            raise ForecastError(f"network_error: {exc}") from exc
        finally:
            if owns:
                await client.aclose()

        if resp.status_code >= 400:
            raise ForecastError(f"http_{resp.status_code}: {resp.text[:200]}")
        try:
            body = resp.json()
            daily = body["daily"]
            dates = daily["time"]
        except Exception as exc:
            raise ForecastError(f"bad_shape: {exc}") from exc

        night = _night_aggregates(body.get("hourly", {}) if isinstance(body, dict) else {})
        out: list[DailyForecast] = []
        for i, day in enumerate(dates):
            d = datetime.date.fromisoformat(day)
            vpd_night, fog = night.get(d, (None, None))
            out.append(
                DailyForecast(
                    forecast_for_date=d,
                    temp_max_c=_f(_at(daily, "temperature_2m_max", i)),
                    temp_min_c=_f(_at(daily, "temperature_2m_min", i)),
                    rain_mm_expected=_f(_at(daily, "precipitation_sum", i)),
                    rain_probability_pct=_f(_at(daily, "precipitation_probability_max", i)),
                    wind_speed_kmh=_f(_at(daily, "wind_speed_10m_max", i)),
                    et0_mm=_f(_at(daily, "et0_fao_evapotranspiration", i)),
                    solar_radiation_mj_m2=_f(_at(daily, "shortwave_radiation_sum", i)),
                    vpd_night_mean_kpa=vpd_night,
                    fog_observed=fog,
                )
            )
        return out


def _at(daily: dict[str, Any], key: str, i: int) -> Any:
    seq = daily.get(key)
    if isinstance(seq, list) and i < len(seq):
        return seq[i]
    return None


__all__ = ["OpenMeteoForecastProvider", "OpenMeteoSettings"]
