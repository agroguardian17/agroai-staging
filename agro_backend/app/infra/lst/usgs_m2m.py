"""USGS Machine-to-Machine (M2M) Landsat Collection-2 L2 LST adapter.

Fetches per-plot land-surface temperature from Landsat-8/9 Collection-2 Level-2
(the ``ST_B10`` surface-temperature band) via the USGS M2M API:

  login-token -> scene-search (dataset landsat_ot_c2_l2, plot bbox + date range)
  -> download-options / download-request (resolve the ST_B10 GeoTIFF URL)
  -> rasterio: mask the COG to the plot polygon, mean the valid pixels, scale
     the DN to Celsius (ST_B10 * 0.00341802 + 149.0 - 273.15).

Auth needs a USGS ERS account + an M2M application token
(``USGS_M2M_USERNAME`` / ``USGS_M2M_TOKEN``). Not exercised against the live API
in CI (that needs credentials + a real scene); the login/search/parse paths are
unit-tested with a mocked transport, and the raster + download-staging steps
must be verified against staging once credentials are set (mirrors the CDSE
adapter). Every failure surfaces as :class:`LstError` so a sweep skips one plot.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from app.application.ports.lst_provider import LstError, LstObservation

log = structlog.get_logger(__name__)

# Landsat C2 L2 ST_B10 DN -> Kelvin -> Celsius.
_ST_SCALE = 0.00341802
_ST_OFFSET = 149.0
_KELVIN = 273.15


def st_dn_to_celsius(dn: float) -> float:
    """Convert a Landsat C2 L2 ST_B10 digital number to degrees Celsius."""
    return dn * _ST_SCALE + _ST_OFFSET - _KELVIN


@dataclass(frozen=True, slots=True)
class UsgsM2mSettings:
    username: str
    token: str
    base_url: str = "https://m2m.cr.usgs.gov/api/api/json/stable"
    dataset: str = "landsat_ot_c2_l2"
    timeout_seconds: float = 60.0
    max_cloud_pct: float = 70.0


def _bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    """(min_lng, min_lat, max_lng, max_lat) of a GeoJSON Polygon's outer ring."""
    coords = geometry.get("coordinates") if isinstance(geometry, dict) else None
    if not coords or not isinstance(coords, list):
        raise LstError("bad_geometry")
    ring = coords[0]
    xs = [p[0] for p in ring if isinstance(p, list | tuple) and len(p) >= 2]
    ys = [p[1] for p in ring if isinstance(p, list | tuple) and len(p) >= 2]
    if not xs or not ys:
        raise LstError("bad_geometry")
    return min(xs), min(ys), max(xs), max(ys)


class UsgsM2mLstProvider:
    """Concrete :class:`LstProvider` against the USGS M2M API."""

    def __init__(
        self, settings: UsgsM2mSettings, *, client: httpx.AsyncClient | None = None
    ) -> None:
        self._s = settings
        self._client = client
        self._api_key: str | None = None

    def _http(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(timeout=self._s.timeout_seconds)

    async def _post(self, endpoint: str, payload: dict[str, Any], *, api_key: str | None) -> Any:
        client = self._http()
        headers = {"X-Auth-Token": api_key} if api_key else {}
        try:
            resp = await client.post(
                f"{self._s.base_url.rstrip('/')}/{endpoint}", json=payload, headers=headers
            )
            resp.raise_for_status()
            body = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise LstError(f"m2m_{endpoint}_failed: {exc}") from exc
        finally:
            if self._client is None:
                await client.aclose()
        if isinstance(body, dict) and body.get("errorCode"):
            raise LstError(
                f"m2m_{endpoint}_error: {body.get('errorCode')} {body.get('errorMessage')}"
            )
        return body.get("data") if isinstance(body, dict) else None

    async def _login(self) -> str:
        if self._api_key:
            return self._api_key
        data = await self._post(
            "login-token", {"username": self._s.username, "token": self._s.token}, api_key=None
        )
        if not isinstance(data, str) or not data:
            raise LstError("m2m_login_no_key")
        self._api_key = data
        return data

    async def _scene_search(
        self,
        bbox: tuple[float, float, float, float],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[dict[str, Any]]:
        api_key = await self._login()
        payload = {
            "datasetName": self._s.dataset,
            "sceneFilter": {
                "spatialFilter": {
                    "filterType": "mbr",
                    "lowerLeft": {"longitude": bbox[0], "latitude": bbox[1]},
                    "upperRight": {"longitude": bbox[2], "latitude": bbox[3]},
                },
                "acquisitionFilter": {"start": date_from.isoformat(), "end": date_to.isoformat()},
                "cloudCoverFilter": {"min": 0, "max": int(self._s.max_cloud_pct)},
            },
            "maxResults": 10,
            "sortDirection": "DESC",
        }
        data = await self._post("scene-search", payload, api_key=api_key)
        results = data.get("results", []) if isinstance(data, dict) else []
        return results if isinstance(results, list) else []

    def _polygon_mean_lst(self, band_url: str, geometry: dict[str, Any]) -> float | None:
        """Mask the ST_B10 COG to the polygon and return the mean LST in C.

        Uses a windowed read over HTTP (``/vsicurl/``); needs the raster to be
        reachable. Returns None when no valid pixels fall in the polygon.
        """
        try:
            import numpy as np
            import rasterio
            from rasterio.mask import mask as rio_mask
        except ImportError as exc:  # pragma: no cover
            raise LstError(f"raster_deps_missing: {exc}") from exc
        try:
            with rasterio.open(f"/vsicurl/{band_url}") as src:
                arr, _ = rio_mask(src, [geometry], crop=True, filled=False)
        except Exception as exc:
            raise LstError(f"raster_read_failed: {exc}") from exc
        band = np.ma.masked_equal(arr[0], 0)  # 0 = fill/nodata for ST_B10
        if band.count() == 0:
            return None
        return round(st_dn_to_celsius(float(band.mean())), 2)

    async def lst_for_polygon(
        self, *, geometry: dict[str, Any], date_from: datetime.date, date_to: datetime.date
    ) -> list[LstObservation]:
        results = await self._scene_search(_bbox(geometry), date_from, date_to)
        api_key = await self._login()
        out: list[LstObservation] = []
        for scene in results:
            entity_id = scene.get("entityId")
            acquired = scene.get("temporalCoverage", {}).get("startDate") or scene.get(
                "publishDate"
            )
            cloud = scene.get("cloudCover")
            if not entity_id or not isinstance(acquired, str):
                continue
            band_url = await self._resolve_st_url(entity_id, api_key)
            if band_url is None:
                continue
            lst_c = self._polygon_mean_lst(band_url, geometry)
            out.append(
                LstObservation(
                    image_date=datetime.date.fromisoformat(acquired[:10]),
                    lst_c=lst_c,
                    cloud_cover_pct=float(cloud) if cloud is not None else None,
                )
            )
        return out

    async def _resolve_st_url(self, entity_id: str, api_key: str) -> str | None:
        """Find the ST_B10 GeoTIFF download URL for a scene (secondary download).

        Returns None when the product is still staging (a later sweep retries).
        """
        opts = await self._post(
            "download-options",
            {"datasetName": self._s.dataset, "entityIds": [entity_id]},
            api_key=api_key,
        )
        products = opts if isinstance(opts, list) else []
        st = next(
            (
                p
                for p in products
                if p.get("available")
                and "ST_B10" in (str(p.get("productName", "")) + str(p.get("displayId", "")))
            ),
            None,
        )
        if st is None:
            return None
        req = await self._post(
            "download-request",
            {"downloads": [{"entityId": entity_id, "productId": st.get("id")}]},
            api_key=api_key,
        )
        avail = (req or {}).get("availableDownloads", []) if isinstance(req, dict) else []
        if avail and isinstance(avail, list):
            return avail[0].get("url")
        return None


__all__ = ["UsgsM2mLstProvider", "UsgsM2mSettings", "st_dn_to_celsius"]
