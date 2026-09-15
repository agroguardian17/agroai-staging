"""Tests for the Round 18 forecast sweep (refresh_forecasts.execute)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from app.application.ports.farm_repo import FarmLocation
from app.application.ports.forecast_provider import DailyForecast, ForecastError
from app.application.ports.weather_forecast_repo import ForecastRow
from app.application.refresh_forecasts import RefreshForecastsDeps, execute

NOW = datetime.datetime(2026, 9, 15, 21, 30, tzinfo=datetime.UTC)


def _farm(n: int) -> FarmLocation:
    return FarmLocation(
        farm_id=uuid.UUID(int=n),
        tenant_id=uuid.UUID(int=1000),
        lat=19.87 + n,
        lng=75.34 + n,
    )


def _day(offset: int) -> DailyForecast:
    return DailyForecast(
        forecast_for_date=datetime.date(2026, 9, 15) + datetime.timedelta(days=offset),
        temp_min_c=21.0,
        temp_max_c=29.0,
        rain_mm_expected=2.5,
        rain_probability_pct=60.0,
        wind_speed_kmh=12.0,
    )


class _FakeFarmRepo:
    def __init__(self, farms: list[FarmLocation]) -> None:
        self._farms = farms

    async def list_with_location(self) -> list[FarmLocation]:
        return self._farms


class _FakeProvider:
    def __init__(self, days: int = 3, fail_for: set[uuid.UUID] | None = None) -> None:
        self._days = days
        self._fail_for = fail_for or set()
        self.calls: list[tuple[float, float]] = []

    async def daily_forecast(self, *, lat: float, lng: float, days: int) -> list[DailyForecast]:
        self.calls.append((lat, lng))
        # identify the farm by coordinates for the fail set
        for fid in self._fail_for:
            f = _farm(fid.int)
            if abs(f.lat - lat) < 1e-9:
                raise ForecastError("boom")
        return [_day(i) for i in range(self._days)]


class _FakeForecastRepo:
    def __init__(self) -> None:
        self.saved: list[ForecastRow] = []

    async def save_daily(self, rows: list[ForecastRow]) -> int:
        self.saved.extend(rows)
        return len(rows)


def _deps(farm_repo: Any, provider: Any, repo: Any, *, days: int = 3) -> RefreshForecastsDeps:
    return RefreshForecastsDeps(
        farm_repo=cast(Any, farm_repo),
        forecast_provider=cast(Any, provider),
        forecast_repo=cast(Any, repo),
        source_api="open-meteo",
        days=days,
    )


async def test_writes_daily_rows_for_every_farm() -> None:
    farms = [_farm(1), _farm(2)]
    provider = _FakeProvider(days=3)
    repo = _FakeForecastRepo()
    out = await execute(deps=_deps(_FakeFarmRepo(farms), provider, repo, days=3), now=NOW)

    assert out.farms == 2
    assert out.failed_farms == 0
    assert out.rows_written == 6  # 2 farms x 3 days
    assert len(repo.saved) == 6
    # rows carry the farm's tenant + fetched_at = now + the source
    assert {r.farm_id for r in repo.saved} == {_farm(1).farm_id, _farm(2).farm_id}
    assert all(r.fetched_at == NOW and r.source_api == "open-meteo" for r in repo.saved)


async def test_one_farm_failure_does_not_abort_sweep() -> None:
    farms = [_farm(1), _farm(2), _farm(3)]
    provider = _FakeProvider(days=2, fail_for={_farm(2).farm_id})
    repo = _FakeForecastRepo()
    out = await execute(deps=_deps(_FakeFarmRepo(farms), provider, repo, days=2), now=NOW)

    assert out.farms == 3
    assert out.failed_farms == 1
    assert out.rows_written == 4  # farms 1 and 3, 2 days each
    assert _farm(2).farm_id not in {r.farm_id for r in repo.saved}


async def test_no_farms_is_a_clean_noop() -> None:
    repo = _FakeForecastRepo()
    out = await execute(deps=_deps(_FakeFarmRepo([]), _FakeProvider(), repo), now=NOW)
    assert out == type(out)(farms=0, rows_written=0, failed_farms=0)
    assert repo.saved == []
