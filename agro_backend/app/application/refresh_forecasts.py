"""Use case: refresh the daily weather forecast for every farm.

Round 18. The nightly job calls this: for each farm, fetch a short-range daily
forecast from the provider and persist it to ``weather_forecasts`` (one row per
day). One farm's failure never aborts the sweep.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.ports.farm_repo import FarmRepo
from app.application.ports.forecast_provider import ForecastError, ForecastProvider
from app.application.ports.weather_forecast_repo import ForecastRow, WeatherForecastRepo


@dataclass(frozen=True, slots=True)
class RefreshForecastsDeps:
    farm_repo: FarmRepo
    forecast_provider: ForecastProvider
    forecast_repo: WeatherForecastRepo
    source_api: str = "open-meteo"
    days: int = 7


@dataclass(frozen=True, slots=True)
class RefreshForecastsResult:
    farms: int
    rows_written: int
    failed_farms: int


async def execute(*, deps: RefreshForecastsDeps, now: datetime) -> RefreshForecastsResult:
    farms = await deps.farm_repo.list_with_location()
    rows_written = 0
    failed = 0
    for farm in farms:
        try:
            daily = await deps.forecast_provider.daily_forecast(
                lat=farm.lat, lng=farm.lng, days=deps.days
            )
        except ForecastError:
            failed += 1
            continue
        except Exception:
            # Defensive: any provider surprise skips one farm, not the sweep.
            failed += 1
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
            )
            for d in daily
        ]
        if rows:
            rows_written += await deps.forecast_repo.save_daily(rows)

    return RefreshForecastsResult(farms=len(farms), rows_written=rows_written, failed_farms=failed)


__all__ = ["RefreshForecastsDeps", "RefreshForecastsResult", "execute"]
