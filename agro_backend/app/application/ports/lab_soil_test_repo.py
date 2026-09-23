"""Port: read-side soil-lab test lookup for the ginger farm-brain.

The KB's nutrient rules read soil chemistry (organic carbon, EC, free lime,
micronutrients) that only a lab report provides. This thin view surfaces the
latest test's KB-consumed columns; ``build_farm_brain`` maps them 1:1.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class LabSoilTestView:
    """Read-side projection of a ``lab_soil_tests`` row (KB-consumed columns)."""

    lab_test_id: uuid.UUID
    farm_id: uuid.UUID
    sample_date: datetime.date
    soil_oc_pct: Decimal | None = None
    soil_ec: Decimal | None = None
    soil_free_lime_pct: Decimal | None = None
    soil_zn_ppm: Decimal | None = None
    soil_fe_ppm: Decimal | None = None
    soil_ca_ppm: Decimal | None = None
    soil_mg_ppm: Decimal | None = None
    soil_s_ppm: Decimal | None = None
    # Particle-size fractions (migration 0021) — feed the USDA-triangle texture
    # override of the soil-type-derived ``soil_texture_class``.
    sand_pct: Decimal | None = None
    silt_pct: Decimal | None = None
    clay_pct: Decimal | None = None


@runtime_checkable
class LabSoilTestRepo(Protocol):
    """Read-only soil-lab test repo for the farm-brain builder."""

    async def latest_for_farm(self, farm_id: uuid.UUID) -> LabSoilTestView | None:
        """Most-recent soil test for the farm (any plot), or None."""
        ...


__all__ = ["LabSoilTestRepo", "LabSoilTestView"]
