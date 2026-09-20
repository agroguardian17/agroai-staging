"""USGS M2M LST adapter — pure helpers + the M2M JSON flow (mocked transport).

The rasterio polygon read (``_polygon_mean_lst``) needs a real COG + credentials
so it is stubbed here; live end-to-end is verified on staging.
"""

from __future__ import annotations

import datetime

import httpx
import pytest

from app.infra.lst.usgs_m2m import UsgsM2mLstProvider, UsgsM2mSettings, _bbox, st_dn_to_celsius

_GEOM = {
    "type": "Polygon",
    "coordinates": [[[75.20, 20.10], [75.22, 20.10], [75.22, 20.12], [75.20, 20.10]]],
}


def test_st_dn_to_celsius() -> None:
    # 0 K offset check: DN such that Kelvin ~ 300 -> ~26.85 C
    dn = (300.0 - 149.0) / 0.00341802
    assert abs(st_dn_to_celsius(dn) - (300.0 - 273.15)) < 0.01


def test_bbox_from_polygon() -> None:
    assert _bbox(_GEOM) == (75.20, 20.10, 75.22, 20.12)


@pytest.mark.asyncio
async def test_lst_for_polygon_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        ep = request.url.path.rsplit("/", 1)[-1]
        if ep == "login-token":
            return httpx.Response(200, json={"data": "APIKEY", "errorCode": None})
        if ep == "scene-search":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "results": [
                            {
                                "entityId": "E1",
                                "cloudCover": 12,
                                "temporalCoverage": {"startDate": "2026-07-30"},
                            },
                        ]
                    },
                    "errorCode": None,
                },
            )
        if ep == "download-options":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {"id": "P_ST", "available": True, "productName": "ST_B10 surface temp"},
                    ],
                    "errorCode": None,
                },
            )
        if ep == "download-request":
            return httpx.Response(
                200,
                json={
                    "data": {"availableDownloads": [{"url": "https://example/ST_B10.TIF"}]},
                    "errorCode": None,
                },
            )
        return httpx.Response(404, json={"errorCode": "x", "errorMessage": ep})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    # Stub the raster read (no network / rasterio in the unit test).
    monkeypatch.setattr(prov, "_polygon_mean_lst", lambda url, geom: 31.4)
    out = await prov.lst_for_polygon(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 20), date_to=datetime.date(2026, 8, 3)
    )
    await client.aclose()
    assert len(out) == 1
    assert out[0].image_date == datetime.date(2026, 7, 30)
    assert out[0].lst_c == 31.4
    assert out[0].cloud_cover_pct == 12.0
