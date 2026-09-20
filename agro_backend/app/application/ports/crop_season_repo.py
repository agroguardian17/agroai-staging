"""Port: read-side crop season lookup.

The Round-11 advisory composer needs to know which crop is on which
plot RIGHT NOW so the prompt can be crop-stage-aware ("cotton, week 6
post-sowing"). A full CropSeason entity in the domain layer is
overkill for this use case; we surface a thin view here in the port.

Future rounds that need a richer model — sowing date, expected harvest,
variety details — can either extend :class:`CropSeasonView` or graduate
it to a domain entity. For Round 11 the view is enough.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CropSeasonView:
    """Read-side projection of an active crop_seasons row."""

    season_id: uuid.UUID
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str
    crop_name_english: str
    crop_name_marathi: str
    crop_category: str
    crop_variety: str
    sowing_date: datetime.date
    expected_harvest_date: datetime.date
    current_growth_stage: str | None
    crop_age_days_today: int | None
    # Extra season facts consumed by the ginger KB (Phase-1 field wiring).
    # Nullable: back-fill / farmer-declared, absent on many rows.
    actual_harvest_date: datetime.date | None = None
    seed_cost_per_kg: Decimal | None = None
    target_yield_qtl_per_acre: Decimal | None = None
    actual_yield_qtl_per_acre: Decimal | None = None
    # Agronomy-plan facts (migration 0022) — named to match the KB fields.
    deep_ploughing_done: bool | None = None
    solarization_done: bool | None = None
    solarization_weeks: Decimal | None = None
    planting_layout: str | None = None
    bed_height_cm: Decimal | None = None
    bed_width_cm: Decimal | None = None
    furrow_width_cm: Decimal | None = None
    plants_per_acre: int | None = None
    planting_depth_cm: Decimal | None = None
    earthing_up_date: datetime.date | None = None
    earthing_up_2_date: datetime.date | None = None
    mulch_stage_1_done: bool | None = None
    mulch_stage_2_done: bool | None = None
    mulch_stage_3_done: bool | None = None
    n_target_kg_per_acre: Decimal | None = None
    p_target_kg_per_acre: Decimal | None = None
    k_target_kg_per_acre: Decimal | None = None
    n_applied_kg_per_acre: Decimal | None = None
    p_applied_kg_per_acre: Decimal | None = None
    k_applied_kg_per_acre: Decimal | None = None
    n_split_1_date: datetime.date | None = None
    n_split_2_date: datetime.date | None = None
    k_late_split_1_date: datetime.date | None = None
    k_late_split_2_date: datetime.date | None = None
    fym_t_per_acre: Decimal | None = None
    fym_fully_decomposed: bool | None = None
    trichoderma_kg_per_acre: Decimal | None = None
    neem_cake_basal_kg_per_acre: Decimal | None = None
    neem_cake_earthing_kg_per_acre: Decimal | None = None
    micronutrient_basal_done: bool | None = None
    micronutrient_spray_1_done: bool | None = None
    micronutrient_spray_2_done: bool | None = None
    hot_water_treatment_done: bool | None = None
    biofumigation_done: bool | None = None
    azospirillum_psb_done: bool | None = None
    marigold_planted: bool | None = None
    target_product: str | None = None


@runtime_checkable
class CropSeasonRepo(Protocol):
    """Read-only crop season repo for prompt context + dashboards."""

    async def find_active_for_plot(self, plot_id: str) -> CropSeasonView | None:
        """Return the active (season_status='active') season for this plot,
        or None if there is no active season yet (post-harvest gap).
        """
        ...

    async def list_active_by_crop(self, crop_name_english: str) -> list[CropSeasonView]:
        """Every active season where ``crop_name_english`` matches, newest first.

        Used by the daily ginger job to iterate all ginger plots at once
        without loading every plot from every tenant. Returns an empty list
        if nothing matches.
        """
        ...


__all__ = ["CropSeasonRepo", "CropSeasonView"]
