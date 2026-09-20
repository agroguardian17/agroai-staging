"""Port: read-side season_operations lookup for the ginger farm-brain."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable  # noqa: F401


@dataclass(frozen=True, slots=True)
class SeasonOperationsView:
    """Read-side projection of the season_operations row (KB-consumed columns)."""

    season_id: uuid.UUID
    basal_k_kg_per_acre: Decimal | None = None
    basal_p_kg_per_acre: Decimal | None = None
    castor_bait_prepared_date: datetime.date | None = None
    castor_bait_units_per_acre: int | None = None
    drip_runtime_min: Decimal | None = None
    ethephon_spray_count: int | None = None
    fertigation_active: bool | None = None
    fertigation_last_ec_response: Decimal | None = None
    herbicide_post_emergent_date: datetime.date | None = None
    herbicide_pre_emergent_date: datetime.date | None = None
    irrigation_applied_litres_today: Decimal | None = None
    kulav_passes: int | None = None
    last_fungicide_date: datetime.date | None = None
    last_fungicide_group: str | None = None
    last_insecticide_date: datetime.date | None = None
    last_insecticide_group: str | None = None
    metarhizium_kg_per_acre: Decimal | None = None
    naa_spray_count: int | None = None
    weeding_count: int | None = None


@runtime_checkable
class SeasonOperationsRepo(Protocol):
    async def for_season(self, season_id: uuid.UUID) -> SeasonOperationsView | None:
        """The season_operations row for this season, or None."""
        ...


__all__ = ["SeasonOperationsRepo", "SeasonOperationsView"]
