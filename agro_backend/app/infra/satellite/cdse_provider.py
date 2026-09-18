"""Copernicus Data Space Ecosystem (CDSE) Sentinel Hub adapter.

Fetches per-polygon vegetation indices (Sentinel-2 L2A) and radar backscatter
(Sentinel-1 GRD) via the Sentinel Hub **Statistical API**. The indices are
computed server-side by an evalscript, so the response is per-time-interval
aggregate statistics over the plot polygon — no raster is ever downloaded.

Auth is OAuth2 client-credentials against the CDSE identity server; the bearer
token is cached until shortly before it expires. Every failure is surfaced as
:class:`SatelliteError` so the sweep skips one plot rather than aborting.

Not exercised against the live API in CI (that needs a CDSE OAuth client);
the token flow and response parsing are unit-tested with a mocked transport.
Verify end-to-end against staging once ``COPERNICUS_CLIENT_ID/SECRET`` are set.
"""

from __future__ import annotations

import datetime
import time
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.application.ports.satellite_provider import (
    OpticalObservation,
    SarObservation,
    SatelliteError,
)

log = structlog.get_logger(__name__)

_CRS_4326 = "http://www.opengis.net/def/crs/EPSG/0/4326"
# resx/resy are in the bounds-CRS units (degrees for EPSG:4326). ~10 m at the
# pilot's latitude is ~9e-5 degrees; this samples the plot at Sentinel
# resolution instead of collapsing it to a single coarse pixel.
_RES_DEG = 0.00009

# Sentinel-2 L2A: NDVI, NDRE, NDMI, EVI, SAVI, NBR over cloud-masked pixels.
# Output "data" carries the six indices (B0..B5). The "dataMask" output sets
# cloudy/nodata pixels to 0 so the Statistical API counts them as noDataCount
# (the valid fraction is derived from sampleCount/noDataCount, not a separate
# returned band).
_S2_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["B02","B04","B05","B08","B11","B12","SCL","dataMask"] }],
    output: [
      { id: "data", bands: 6, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function evaluatePixel(s) {
  var valid = s.dataMask;
  // SCL: 3 cloud shadow, 8/9 cloud med/high, 10 thin cirrus, 11 snow — drop.
  if (s.SCL == 3 || s.SCL == 8 || s.SCL == 9 || s.SCL == 10 || s.SCL == 11) valid = 0;
  var ndvi = (s.B08 - s.B04) / (s.B08 + s.B04);
  var ndre = (s.B08 - s.B05) / (s.B08 + s.B05);
  var ndmi = (s.B08 - s.B11) / (s.B08 + s.B11);
  var evi = 2.5 * (s.B08 - s.B04) / (s.B08 + 6.0 * s.B04 - 7.5 * s.B02 + 1.0);
  var savi = 1.5 * (s.B08 - s.B04) / (s.B08 + s.B04 + 0.5);
  var nbr = (s.B08 - s.B12) / (s.B08 + s.B12);
  return { data: [ndvi, ndre, ndmi, evi, savi, nbr], dataMask: [valid] };
}
"""

# Sentinel-1 GRD: VV/VH sigma-nought converted to dB.
_S1_EVALSCRIPT = """//VERSION=3
function setup() {
  return {
    input: [{ bands: ["VV","VH","dataMask"] }],
    output: [
      { id: "data", bands: 2, sampleType: "FLOAT32" },
      { id: "dataMask", bands: 1 }
    ]
  };
}
function toDb(x) { return x > 0 ? 10.0 * Math.log(x) / Math.LN10 : -30.0; }
function evaluatePixel(s) {
  return { data: [toDb(s.VV), toDb(s.VH)], dataMask: [s.dataMask] };
}
"""


@dataclass(frozen=True, slots=True)
class CdseSettings:
    client_id: str
    client_secret: str
    base_url: str = "https://sh.dataspace.copernicus.eu"
    token_url: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    timeout_seconds: float = 30.0


def _bounds(geometry: dict[str, Any]) -> dict[str, Any]:
    return {"geometry": geometry, "properties": {"crs": _CRS_4326}}


def _iso(d: datetime.date) -> str:
    return f"{d.isoformat()}T00:00:00Z"


def _num(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # Drop NaN (all-nodata interval): NaN is the only value not equal to itself.
    return None if f != f else f


class CdseSentinelHubProvider:
    """Concrete :class:`SatelliteProvider` against CDSE Sentinel Hub."""

    def __init__(self, settings: CdseSettings, *, client: httpx.AsyncClient | None = None) -> None:
        self._s = settings
        self._client = client
        self._token: str | None = None
        self._token_exp: float = 0.0

    def _http(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(timeout=self._s.timeout_seconds)

    async def _access_token(self) -> str:
        # Reuse the cached token until 60 s before expiry.
        if self._token is not None and time.time() < self._token_exp - 60:
            return self._token
        client = self._http()
        try:
            resp = await client.post(
                self._s.token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._s.client_id,
                    "client_secret": self._s.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SatelliteError(f"CDSE token request failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
        raw = body.get("access_token")
        if not raw:
            raise SatelliteError("CDSE token response missing access_token")
        token = str(raw)
        self._token = token
        self._token_exp = time.time() + float(body.get("expires_in", 600))
        return token

    async def _statistics(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        token = await self._access_token()
        client = self._http()
        try:
            resp = await client.post(
                f"{self._s.base_url}/api/v1/statistics",
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise SatelliteError(f"CDSE statistics request failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
        data = body.get("data")
        if not isinstance(data, list):
            raise SatelliteError("CDSE statistics response missing 'data' list")
        return data

    def _payload(
        self,
        *,
        data_type: str,
        data_filter: dict[str, Any],
        evalscript: str,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
        processing: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data_block: dict[str, Any] = {"type": data_type, "dataFilter": data_filter}
        if processing:
            data_block["processing"] = processing
        return {
            "input": {"bounds": _bounds(geometry), "data": [data_block]},
            "aggregation": {
                "timeRange": {"from": _iso(date_from), "to": _iso(date_to)},
                "aggregationInterval": {"of": "P5D"},
                "evalscript": evalscript,
                "resx": _RES_DEG,
                "resy": _RES_DEG,
            },
            "calculations": {"default": {}},
        }

    async def optical(
        self,
        *,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[OpticalObservation]:
        payload = self._payload(
            data_type="sentinel-2-l2a",
            data_filter={"mosaickingOrder": "leastCC"},
            evalscript=_S2_EVALSCRIPT,
            geometry=geometry,
            date_from=date_from,
            date_to=date_to,
        )
        out: list[OpticalObservation] = []
        for item in await self._statistics(payload):
            parsed = _parse_optical(item)
            if parsed is not None:
                out.append(parsed)
        return out

    async def sar(
        self,
        *,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[SarObservation]:
        payload = self._payload(
            data_type="sentinel-1-grd",
            data_filter={"acquisitionMode": "IW", "polarization": "DV"},
            evalscript=_S1_EVALSCRIPT,
            geometry=geometry,
            date_from=date_from,
            date_to=date_to,
            processing={"backCoeff": "SIGMA0_ELLIPSOID", "orthorectify": True},
        )
        out: list[SarObservation] = []
        for item in await self._statistics(payload):
            parsed = _parse_sar(item)
            if parsed is not None:
                out.append(parsed)
        return out


def _interval_date(item: dict[str, Any]) -> datetime.date | None:
    frm = item.get("interval", {}).get("from")
    if not isinstance(frm, str):
        return None
    try:
        return datetime.date.fromisoformat(frm[:10])
    except ValueError:
        return None


def _bands(item: dict[str, Any], output: str) -> dict[str, Any] | None:
    outputs = item.get("outputs")
    if not isinstance(outputs, dict):
        return None
    block = outputs.get(output)
    if not isinstance(block, dict):
        return None
    bands = block.get("bands")
    return bands if isinstance(bands, dict) else None


def _mean(bands: dict[str, Any], key: str) -> float | None:
    band = bands.get(key)
    if not isinstance(band, dict):
        return None
    return _num(band.get("stats", {}).get("mean"))


def _std(bands: dict[str, Any], key: str) -> float | None:
    band = bands.get(key)
    if not isinstance(band, dict):
        return None
    return _num(band.get("stats", {}).get("stDev"))


def _valid_fraction(item: dict[str, Any]) -> float | None:
    """Clear-pixel fraction from a band's sampleCount / noDataCount.

    The Statistical API does not return the evalscript's ``dataMask`` output as
    a separate stats block; instead every band's stats carry ``sampleCount``
    (total pixels sampled) and ``noDataCount`` (masked, incl. cloud + NaN). The
    valid fraction is ``(sampleCount - noDataCount) / sampleCount``.
    """
    data = _bands(item, "data")
    if data is None:
        return None
    b0 = data.get("B0")
    if not isinstance(b0, dict):
        return None
    stats = b0.get("stats", {})
    sc = stats.get("sampleCount")
    nd = stats.get("noDataCount")
    if not isinstance(sc, int | float) or not isinstance(nd, int | float) or sc <= 0:
        return None
    return max(0.0, min(1.0, (sc - nd) / sc))


def _parse_optical(item: dict[str, Any]) -> OpticalObservation | None:
    d = _interval_date(item)
    data = _bands(item, "data")
    if d is None or data is None:
        return None
    valid = _valid_fraction(item)
    if valid is not None and valid <= 0:
        return None  # fully clouded / empty interval
    valid_pct = None if valid is None else round(valid * 100, 2)
    cloud_pct = None if valid is None else round((1 - valid) * 100, 2)
    return OpticalObservation(
        image_date=d,
        ndvi_mean=_mean(data, "B0"),
        ndvi_std=_std(data, "B0"),
        ndre_mean=_mean(data, "B1"),
        ndmi_mean=_mean(data, "B2"),
        evi_mean=_mean(data, "B3"),
        savi_mean=_mean(data, "B4"),
        nbr_value=_mean(data, "B5"),
        cloud_cover_pct=cloud_pct,
        valid_pixel_pct=valid_pct,
    )


def _parse_sar(item: dict[str, Any]) -> SarObservation | None:
    d = _interval_date(item)
    data = _bands(item, "data")
    if d is None or data is None:
        return None
    valid = _valid_fraction(item)
    if valid is not None and valid <= 0:
        return None
    return SarObservation(image_date=d, sar_vv_db=_mean(data, "B0"), sar_vh_db=_mean(data, "B1"))


__all__ = ["CdseSentinelHubProvider", "CdseSettings"]
