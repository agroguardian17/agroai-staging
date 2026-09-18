"""CDSE Sentinel Hub adapter tests (mocked transport, no network)."""

from __future__ import annotations

import datetime
import json

import httpx
import pytest

from app.application.ports.satellite_provider import SatelliteError
from app.infra.satellite.cdse_provider import CdseSentinelHubProvider, CdseSettings

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[75.2, 20.1], [75.21, 20.1], [75.21, 20.11], [75.2, 20.1]]],
}

# Real Statistical API shape: no separate dataMask output; each band's stats
# carry sampleCount/noDataCount, and cloudy pixels come back as "NaN" strings.
def _stat(mean, sample=10, nodata=0, std=0.0):
    return {"stats": {"mean": mean, "stDev": std, "sampleCount": sample, "noDataCount": nodata}}


_OPTICAL_RESP = {
    "data": [
        {
            # clear scene, 2 of 10 pixels masked → 80% valid
            "interval": {"from": "2026-07-01T00:00:00Z", "to": "2026-07-06T00:00:00Z"},
            "outputs": {
                "data": {
                    "bands": {
                        "B0": _stat(0.55, nodata=2, std=0.05),
                        "B1": _stat(0.30, nodata=2),
                        "B2": _stat(0.40, nodata=2),
                        "B3": _stat(1.20, nodata=2),
                        "B4": _stat(0.50, nodata=2),
                        "B5": _stat(0.20, nodata=2),
                    }
                }
            },
        },
        # fully-clouded interval → all NaN, noDataCount == sampleCount → skipped
        {
            "interval": {"from": "2026-07-06T00:00:00Z", "to": "2026-07-11T00:00:00Z"},
            "outputs": {"data": {"bands": {"B0": _stat("NaN", sample=10, nodata=10)}}},
        },
    ]
}

_SAR_RESP = {
    "data": [
        {
            "interval": {"from": "2026-07-02T00:00:00Z", "to": "2026-07-07T00:00:00Z"},
            "outputs": {"data": {"bands": {"B0": _stat(-9.5), "B1": _stat(-15.2)}}},
        }
    ]
}


def _provider(handler) -> CdseSentinelHubProvider:
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    return CdseSentinelHubProvider(
        CdseSettings(client_id="cid", client_secret="secret"), client=client
    )


def _ok_handler(stats_body: dict) -> object:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 600})
        if request.url.path.endswith("/api/v1/statistics"):
            return httpx.Response(200, json=stats_body)
        return httpx.Response(404)

    return handler


@pytest.mark.asyncio
async def test_optical_parses_indices_and_valid_pixels() -> None:
    provider = _provider(_ok_handler(_OPTICAL_RESP))
    obs = await provider.optical(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 20)
    )
    assert len(obs) == 1  # the all-NaN interval is dropped
    o = obs[0]
    assert o.image_date == datetime.date(2026, 7, 1)
    assert o.ndvi_mean == 0.55
    assert o.ndvi_std == 0.05
    assert o.ndre_mean == 0.30
    assert o.valid_pixel_pct == 80.0  # (10 - 2) / 10
    assert o.cloud_cover_pct == 20.0


@pytest.mark.asyncio
async def test_sar_parses_vv_vh_db() -> None:
    provider = _provider(_ok_handler(_SAR_RESP))
    obs = await provider.sar(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 20)
    )
    assert len(obs) == 1
    assert obs[0].sar_vv_db == -9.5
    assert obs[0].sar_vh_db == -15.2


@pytest.mark.asyncio
async def test_token_failure_raises_satellite_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            return httpx.Response(401, json={"error": "invalid_client"})
        return httpx.Response(200, json={})

    provider = _provider(handler)
    with pytest.raises(SatelliteError):
        await provider.optical(
            geometry=_GEOM, date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 20)
        )


@pytest.mark.asyncio
async def test_token_is_reused_across_calls() -> None:
    calls = {"token": 0, "stats": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/token"):
            calls["token"] += 1
            return httpx.Response(200, json={"access_token": "tok", "expires_in": 600})
        calls["stats"] += 1
        return httpx.Response(200, json=json.loads(json.dumps(_SAR_RESP)))

    provider = _provider(handler)
    await provider.sar(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 20)
    )
    await provider.sar(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 1), date_to=datetime.date(2026, 7, 20)
    )
    assert calls["token"] == 1  # cached
    assert calls["stats"] == 2
