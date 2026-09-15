"""Tests for OpenMeteoForecastProvider. Uses respx to mock the HTTP call."""

from __future__ import annotations

import datetime

import httpx
import pytest
import respx

from app.application.ports.forecast_provider import ForecastError
from app.infra.forecast.open_meteo import OpenMeteoForecastProvider, OpenMeteoSettings

BASE = "https://api.open-meteo.com/v1"
URL = f"{BASE}/forecast"

_SAMPLE = {
    "daily": {
        "time": ["2026-09-15", "2026-09-16"],
        "temperature_2m_max": [28.8, 29.7],
        "temperature_2m_min": [21.0, 21.2],
        "precipitation_sum": [0.3, 2.1],
        "precipitation_probability_max": [27, 83],
        "wind_speed_10m_max": [14.2, 9.6],
    }
}


def _provider(client: httpx.AsyncClient) -> OpenMeteoForecastProvider:
    return OpenMeteoForecastProvider(OpenMeteoSettings(base_url=BASE), client=client)


@pytest.mark.asyncio
@respx.mock
async def test_parses_daily_arrays() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json=_SAMPLE))
    async with httpx.AsyncClient() as client:
        out = await _provider(client).daily_forecast(lat=19.87, lng=75.34, days=2)

    assert [d.forecast_for_date for d in out] == [
        datetime.date(2026, 9, 15),
        datetime.date(2026, 9, 16),
    ]
    assert out[0].temp_max_c == 28.8
    assert out[0].temp_min_c == 21.0
    assert out[0].rain_mm_expected == 0.3
    assert out[1].rain_probability_pct == 83.0
    assert out[1].wind_speed_kmh == 9.6


@pytest.mark.asyncio
@respx.mock
async def test_forecast_days_is_clamped_to_16() -> None:
    route = respx.get(URL).mock(return_value=httpx.Response(200, json=_SAMPLE))
    async with httpx.AsyncClient() as client:
        await _provider(client).daily_forecast(lat=1.0, lng=2.0, days=99)
    assert route.calls.last.request.url.params["forecast_days"] == "16"


@pytest.mark.asyncio
@respx.mock
async def test_http_error_raises_forecast_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(500, text="upstream boom"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(ForecastError):
            await _provider(client).daily_forecast(lat=1.0, lng=2.0, days=3)


@pytest.mark.asyncio
@respx.mock
async def test_network_error_raises_forecast_error() -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectError("no route"))
    async with httpx.AsyncClient() as client:
        with pytest.raises(ForecastError):
            await _provider(client).daily_forecast(lat=1.0, lng=2.0, days=3)


@pytest.mark.asyncio
@respx.mock
async def test_bad_shape_raises_forecast_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    async with httpx.AsyncClient() as client:
        with pytest.raises(ForecastError):
            await _provider(client).daily_forecast(lat=1.0, lng=2.0, days=3)
