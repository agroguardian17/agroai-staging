"""USGS M2M LST adapter — pure helpers + the M2M JSON flow (mocked transport).

The rasterio polygon read (``_polygon_mean_lst``) needs a real COG + credentials
so it is stubbed here; live end-to-end is verified on staging.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from pathlib import Path

import httpx
import numpy as np
import pytest

from app.application.ports.lst_provider import LstError
from app.infra.lst.usgs_m2m import (
    UsgsM2mLstProvider,
    UsgsM2mSettings,
    _bbox,
    _mean_lst,
    _reduce_lst_band,
    st_dn_to_celsius,
)

# ST_B10 digital number that scales to ~300 K (26.85 C).
_DN_300K = (300.0 - 149.0) / 0.00341802

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


# --- raster reduction (no network, no credentials) --------------------------


def test_reduce_lst_band_means_valid_pixels_excluding_nodata() -> None:
    # One 0 (fill/nodata) pixel must not drag the mean down.
    arr = np.array([[[_DN_300K, _DN_300K], [0.0, _DN_300K]]])
    assert _reduce_lst_band(arr) == round(300.0 - 273.15, 2)  # 26.85


def test_reduce_lst_band_all_nodata_returns_none() -> None:
    assert _reduce_lst_band(np.zeros((1, 3, 3))) is None


def test_mean_lst_reads_local_geotiff(tmp_path: Path) -> None:
    """The full open -> mask -> mean path against a real GeoTIFF (no network)."""
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds

    data = np.full((4, 4), _DN_300K, dtype="float32")
    data[0, 0] = 0.0  # a nodata corner the mean must ignore
    minx, miny, maxx, maxy = 75.20, 20.10, 75.24, 20.14
    path = tmp_path / "ST_B10.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=4,
        width=4,
        count=1,
        dtype="float32",
        crs="EPSG:4326",
        transform=from_bounds(minx, miny, maxx, maxy, 4, 4),
    ) as dst:
        dst.write(data, 1)

    geom = {
        "type": "Polygon",
        "coordinates": [
            [
                [75.205, 20.105],
                [75.235, 20.105],
                [75.235, 20.135],
                [75.205, 20.135],
                [75.205, 20.105],
            ]
        ],
    }
    out = _mean_lst(str(path), geom)
    assert out is not None
    assert abs(out - (300.0 - 273.15)) < 0.5


def test_mean_lst_reprojects_latlon_polygon_onto_utm_raster(tmp_path: Path) -> None:
    """Regression: a lon/lat (EPSG:4326) polygon must be reprojected onto a UTM
    Landsat raster before masking. Without the reprojection rasterio raises
    'Input shapes do not overlap raster' and LST is silently lost."""
    rasterio = pytest.importorskip("rasterio")
    from rasterio.transform import from_bounds
    from rasterio.warp import transform_bounds

    # A lon/lat plot near Kannad, Marathwada (UTM zone 43N / EPSG:32643).
    lonlat = {
        "type": "Polygon",
        "coordinates": [
            [
                [75.083, 20.140],
                [75.085, 20.140],
                [75.085, 20.142],
                [75.083, 20.142],
                [75.083, 20.140],
            ]
        ],
    }
    # Build a UTM raster whose extent covers that polygon (bounds in metres).
    minx, miny, maxx, maxy = transform_bounds(
        "EPSG:4326", "EPSG:32643", 75.082, 20.139, 75.086, 20.143
    )
    data = np.full((8, 8), _DN_300K, dtype="float32")
    path = tmp_path / "ST_B10_utm.tif"
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=8,
        width=8,
        count=1,
        dtype="float32",
        crs="EPSG:32643",
        transform=from_bounds(minx, miny, maxx, maxy, 8, 8),
    ) as dst:
        dst.write(data, 1)

    out = _mean_lst(str(path), lonlat)  # lon/lat polygon vs UTM raster
    assert out is not None
    assert abs(out - (300.0 - 273.15)) < 0.5


def test_mean_lst_raises_on_unreadable_source() -> None:
    pytest.importorskip("rasterio")
    with pytest.raises(LstError, match="raster_read_failed"):
        _mean_lst(
            "/vsicurl/https://example.invalid/missing.tif", {"type": "Polygon", "coordinates": []}
        )


# --- M2M JSON edge paths (mocked transport) ---------------------------------


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_post_raises_on_error_code() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"data": None, "errorCode": "AUTH_ERROR", "errorMessage": "bad token"}
        )

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    with pytest.raises(LstError, match="login-token_error"):
        await prov._login()
    await client.aclose()


@pytest.mark.asyncio
async def test_login_empty_key_raises() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": "", "errorCode": None})

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    with pytest.raises(LstError, match="login_no_key"):
        await prov._login()
    await client.aclose()


@pytest.mark.asyncio
async def test_resolve_st_url_none_when_product_staging() -> None:
    # download-options has the product but it is not yet 'available' -> None (retry later).
    def handler(request: httpx.Request) -> httpx.Response:
        ep = request.url.path.rsplit("/", 1)[-1]
        if ep == "login-token":
            return httpx.Response(200, json={"data": "K", "errorCode": None})
        if ep == "download-options":
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "P", "available": False, "productName": "ST_B10"}],
                    "errorCode": None,
                },
            )
        return httpx.Response(200, json={"data": {}, "errorCode": None})

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    key = await prov._login()
    assert await prov._resolve_st_url("E1", key) is None
    await client.aclose()


@pytest.mark.asyncio
async def test_resolve_st_url_uses_secondary_st_b10_download() -> None:
    """Real USGS shape: products are generic; ST_B10 lives in secondaryDownloads.

    This is the regression guard for the bug where the resolver only matched the
    top-level product name (always generic) and so never found the band —
    silently yielding zero LST. We also assert the download-request targets the
    *secondary* file's own entityId + id, and that a non-B10 band is ignored.
    """
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        ep = request.url.path.rsplit("/", 1)[-1]
        if ep == "login-token":
            return httpx.Response(200, json={"data": "K", "errorCode": None})
        if ep == "download-options":
            return httpx.Response(
                200,
                json={
                    "data": [
                        {
                            "id": "BUNDLE",
                            "available": False,
                            "productName": "Landsat Collection 2 Level-2 Product Bundle",
                            "displayId": "LC09_..._02_T1",
                            "secondaryDownloads": [
                                {
                                    "id": "QA_ID",
                                    "available": True,
                                    "productName": "Landsat Collection 2 Level-2 Band File",
                                    "displayId": "LC09_..._02_T1_ST_QA.TIF",
                                    "entityId": "L2ST_..._ST_QA_TIF",
                                },
                                {
                                    "id": "B10_ID",
                                    "available": True,
                                    "productName": "Landsat Collection 2 Level-2 Band File",
                                    "displayId": "LC09_..._02_T1_ST_B10.TIF",
                                    "entityId": "L2ST_..._ST_B10_TIF",
                                },
                            ],
                        }
                    ],
                    "errorCode": None,
                },
            )
        if ep == "download-request":
            captured["body"] = request.read().decode()
            return httpx.Response(
                200,
                json={
                    "data": {"availableDownloads": [{"url": "https://dds/ST_B10.TIF"}]},
                    "errorCode": None,
                },
            )
        return httpx.Response(404, json={"errorCode": "x", "errorMessage": ep})

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    key = await prov._login()
    url = await prov._resolve_st_url("SCENE1", key)
    await client.aclose()
    assert url == "https://dds/ST_B10.TIF"
    # download-request must target the ST_B10 secondary file's own ids, not QA / the scene.
    assert '"productId": "B10_ID"' in str(captured["body"])
    assert "L2ST_..._ST_B10_TIF" in str(captured["body"])
    assert "QA_ID" not in str(captured["body"])


@pytest.mark.asyncio
async def test_resolve_st_url_none_when_no_download_url() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        ep = request.url.path.rsplit("/", 1)[-1]
        if ep == "login-token":
            return httpx.Response(200, json={"data": "K", "errorCode": None})
        if ep == "download-options":
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "P", "available": True, "productName": "ST_B10"}],
                    "errorCode": None,
                },
            )
        if ep == "download-request":
            return httpx.Response(200, json={"data": {"availableDownloads": []}, "errorCode": None})
        return httpx.Response(404, json={"errorCode": "x", "errorMessage": ep})

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    key = await prov._login()
    assert await prov._resolve_st_url("E1", key) is None
    await client.aclose()


@pytest.mark.asyncio
async def test_lst_for_polygon_skips_staging_scene() -> None:
    # A scene is found but its ST product is still staging -> the scene is skipped.
    def handler(request: httpx.Request) -> httpx.Response:
        ep = request.url.path.rsplit("/", 1)[-1]
        if ep == "login-token":
            return httpx.Response(200, json={"data": "K", "errorCode": None})
        if ep == "scene-search":
            return httpx.Response(
                200,
                json={
                    "data": {
                        "results": [
                            {
                                "entityId": "E1",
                                "cloudCover": 5,
                                "temporalCoverage": {"startDate": "2026-07-30"},
                            }
                        ]
                    },
                    "errorCode": None,
                },
            )
        if ep == "download-options":
            return httpx.Response(
                200,
                json={
                    "data": [{"id": "P", "available": False, "productName": "ST_B10"}],
                    "errorCode": None,
                },
            )
        return httpx.Response(200, json={"data": {}, "errorCode": None})

    client = _client(handler)
    prov = UsgsM2mLstProvider(UsgsM2mSettings(username="u", token="t"), client=client)
    out = await prov.lst_for_polygon(
        geometry=_GEOM, date_from=datetime.date(2026, 7, 20), date_to=datetime.date(2026, 8, 3)
    )
    await client.aclose()
    assert out == []
