"""Port: farm lookups needed by background jobs.

Round 18's forecast sweep needs each farm's centre coordinates + tenant. Kept
minimal (no domain Farm entity yet) — a small read-side dataclass, mirroring
``farmer_repo``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FarmLocation:
    farm_id: uuid.UUID
    tenant_id: uuid.UUID
    lat: float
    lng: float


@dataclass(frozen=True, slots=True)
class FarmFacts:
    """Farm-level facts the ginger KB reads (Phase-1 field wiring).

    A thin read-side projection of the ``farms`` columns the engine's
    farm-brain needs. All nullable — onboarding data, often absent.
    """

    farm_id: uuid.UUID
    soil_type: str | None = None
    soil_depth_cm: Decimal | None = None
    soil_organic_carbon_pct: Decimal | None = None
    water_source_primary: str | None = None
    irrigation_type: str | None = None
    drip_emitter_lph: Decimal | None = None
    previous_crops_json: Any | None = None


@runtime_checkable
class FarmRepo(Protocol):
    async def list_with_location(self) -> list[FarmLocation]:
        """Every farm with its centre coordinates (for per-farm forecasts)."""
        ...

    async def find_facts(self, farm_id: uuid.UUID) -> FarmFacts | None:
        """Farm-brain facts for one farm, or None if the farm is unknown."""
        ...


__all__ = ["FarmFacts", "FarmLocation", "FarmRepo"]
