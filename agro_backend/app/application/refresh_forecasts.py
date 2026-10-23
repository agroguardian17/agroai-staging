"""Use case: refresh the daily weather forecast for every farm.

Round 18. The nightly job calls this: for each farm, fetch a short-range daily
forecast from the provider and persist it to ``weather_forecasts`` (one row per
day). One farm's failure never aborts the sweep.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from app.application.ports.farm_repo import FarmRepo
from app.application.ports.forecast_provider import ForecastProvider
from app.application.ports.weather_forecast_repo import ForecastRow, WeatherForecastRepo


@dataclass(frozen=True, slots=True)
class RefreshForecastsDeps:
    farm_repo: FarmRepo
    forecast_provider: ForecastProvider
    forecast_repo: WeatherForecastRepo
    source_api: str = "open-meteo"
    days: int = 7
    # Days of past actuals to fetch alongside the forecast — feeds the KB's
    # rain-window fields (rain_gap_days, dry_spell_days, effective rainfall).
    past_days: int = 21
    # Retry a transient provider failure (timeout / 5xx) once before giving up
    # on a farm — Open-Meteo blips were silently dropping a night's forecast.
    max_attempts: int = 2
    retry_backoff_s: float = 2.0


@dataclass(frozen=True, slots=True)
class RefreshForecastsResult:
    farms: int
    rows_written: int
    failed_farms: int
    # Per-farm failure reasons ("farm <id>: <ErrorType>: <msg>") so the job
    # ledger/log shows WHY a farm failed instead of only a count.
    errors: list[str] = field(default_factory=list)


async def execute(*, deps: RefreshForecastsDeps, now: datetime) -> RefreshForecastsResult:
    farms = await deps.farm_repo.list_with_location()
    rows_written = 0
    failed = 0
    errors: list[str] = []
    for farm in farms:
        daily = None
        last_err: str | None = None
        for attempt in range(1, deps.max_attempts + 1):
            try:
                daily = await deps.forecast_provider.daily_forecast(
                    lat=farm.lat, lng=farm.lng, days=deps.days, past_days=deps.past_days
                )
                last_err = None
                break
            except Exception as exc:  # ForecastError or any provider surprise
                # One farm's failure (even repeated) never aborts the sweep.
                last_err = f"{type(exc).__name__}: {exc}"[:200]
                if attempt < deps.max_attempts:
                    await asyncio.sleep(deps.retry_backoff_s)
        if daily is None:
            failed += 1
            errors.append(f"farm {farm.farm_id}: {last_err}")
            continue

        rows = [
            ForecastRow(
                tenant_id=farm.tenant_id,
                farm_id=farm.farm_id,
                fetched_at=now,
                forecast_for_date=d.forecast_for_date,
                source_api=deps.source_api,
                temp_min_c=d.temp_min_c,
                temp_max_c=d.temp_max_c,
                rain_mm_expected=d.rain_mm_expected,
                rain_probability_pct=d.rain_probability_pct,
                wind_speed_kmh=d.wind_speed_kmh,
                et0_mm=d.et0_mm,
                solar_radiation_mj_m2=d.solar_radiation_mj_m2,
                vpd_night_mean_kpa=d.vpd_night_mean_kpa,
                fog_observed=d.fog_observed,
                wind_gust_kmph=d.wind_gust_kmph,
            )
            for d in daily
        ]
        if rows:
            rows_written += await deps.forecast_repo.save_daily(rows)

    return RefreshForecastsResult(
        farms=len(farms), rows_written=rows_written, failed_farms=failed, errors=errors
    )


__all__ = ["RefreshForecastsDeps", "RefreshForecastsResult", "execute"]
