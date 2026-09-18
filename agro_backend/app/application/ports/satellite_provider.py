"""Port: external satellite index provider.

A cron job fetches per-scene vegetation indices (Sentinel-2 optical) and radar
backscatter (Sentinel-1 SAR) for each pilot plot's polygon and stores them in
``satellite_data``; the ginger farm-brain reads them back for the Domain 14
rules. The default adapter is the Copernicus Data Space Ecosystem (CDSE)
Sentinel Hub Statistical API — the indices are computed server-side by an
evalscript, so we only ever receive per-polygon statistics (no raster
download).
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class OpticalObservation:
    """One Sentinel-2 overpass: per-polygon index means + scene quality."""

    image_date: datetime.date
    ndvi_mean: float | None
    ndvi_std: float | None
    ndre_mean: float | None
    ndmi_mean: float | None
    evi_mean: float | None
    savi_mean: float | None
    nbr_value: float | None
    cloud_cover_pct: float | None
    valid_pixel_pct: float | None


@dataclass(frozen=True, slots=True)
class SarObservation:
    """One Sentinel-1 overpass: per-polygon VV/VH backscatter in dB."""

    image_date: datetime.date
    sar_vv_db: float | None
    sar_vh_db: float | None


class SatelliteError(Exception):
    """The provider could not return data (auth / network / bad shape / quota)."""


@runtime_checkable
class SatelliteProvider(Protocol):
    async def optical(
        self,
        *,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[OpticalObservation]:
        """Sentinel-2 index observations for the polygon over the date range.

        Raises :class:`SatelliteError` on failure so the sweep can skip one
        plot without aborting.
        """
        ...

    async def sar(
        self,
        *,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[SarObservation]:
        """Sentinel-1 VV/VH observations for the polygon over the date range."""
        ...


__all__ = [
    "OpticalObservation",
    "SarObservation",
    "SatelliteError",
    "SatelliteProvider",
]
