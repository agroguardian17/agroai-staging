"""Port: external land-surface-temperature (LST) provider for Domain 14.

A cron job fetches per-polygon LST (Landsat Collection-2 Level-2 surface
temperature) for each pilot plot and stores it on the ``satellite_data``
``landsat8`` row; the farm-brain reads ``lst_c`` and derives ``cwsi``
(canopy - air temperature). The default adapter is the USGS M2M API.

Kept intentionally small: one call returning per-overpass polygon-mean LST in
Celsius. The adapter raises :class:`LstError` on any failure so a sweep skips
one plot rather than aborting.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LstObservation:
    """One Landsat overpass: polygon-mean land-surface temperature in Celsius."""

    image_date: datetime.date
    lst_c: float | None
    cloud_cover_pct: float | None = None


class LstError(Exception):
    """The provider could not return LST (auth / search / download / raster)."""


@runtime_checkable
class LstProvider(Protocol):
    async def lst_for_polygon(
        self,
        *,
        geometry: dict[str, Any],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[LstObservation]:
        """Return recent per-overpass polygon-mean LST for the plot boundary."""
        ...


__all__ = ["LstError", "LstObservation", "LstProvider"]
