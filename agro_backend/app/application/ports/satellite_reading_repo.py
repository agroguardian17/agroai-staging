"""Port: persist and read per-scene satellite index rows.

The fetch job writes one ``satellite_data`` row per plot per scene (optical =
Sentinel-2, sar = Sentinel-1); the ginger farm-brain builder reads the most
recent scenes back to populate the Domain 14 fields. Idempotent on
``(plot_id, image_date, satellite_source)`` — a re-fetch of the same scene
upserts rather than duplicates.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

# Canonical satellite_source values. These must match the satellite_data
# CHECK constraint from migration 0001 (no hyphen): 'sentinel2'/'sentinel1'/…
SOURCE_OPTICAL = "sentinel2"
SOURCE_SAR = "sentinel1"


@dataclass(frozen=True, slots=True)
class SatelliteScene:
    """One plot's index panel for one satellite overpass. All-Decimal."""

    image_date: datetime.date
    satellite_source: str
    # Optical (Sentinel-2)
    ndvi_mean: Decimal | None = None
    ndvi_std: Decimal | None = None
    ndre_mean: Decimal | None = None
    ndmi_mean: Decimal | None = None
    evi_mean: Decimal | None = None
    savi_mean: Decimal | None = None
    nbr_value: Decimal | None = None
    cloud_cover_pct: Decimal | None = None
    valid_pixel_pct: Decimal | None = None
    # SAR (Sentinel-1)
    sar_vv_db: Decimal | None = None
    sar_vh_db: Decimal | None = None
    sar_rvi: Decimal | None = None
    sar_coherence: Decimal | None = None
    # Thermal (Landsat — Phase 2)
    lst_c: Decimal | None = None
    cwsi: Decimal | None = None
    pipeline_version: str | None = None


@runtime_checkable
class SatelliteReadingRepo(Protocol):
    """Persist and query per-scene satellite index rows."""

    async def save(
        self,
        *,
        tenant_id: uuid.UUID,
        farm_id: uuid.UUID,
        plot_id: str,
        scene: SatelliteScene,
    ) -> None:
        """Upsert one scene row (idempotent on plot_id, image_date, source)."""
        ...

    async def recent(
        self,
        plot_id: str,
        satellite_source: str,
        limit: int,
    ) -> list[SatelliteScene]:
        """Most-recent-first scenes for one plot and one source."""
        ...


__all__ = [
    "SOURCE_OPTICAL",
    "SOURCE_SAR",
    "SatelliteReadingRepo",
    "SatelliteScene",
]
