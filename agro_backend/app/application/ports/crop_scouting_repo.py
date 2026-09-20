"""Port: read-side crop-scouting lookup for the ginger farm-brain.

The KB's D05/D06 pest and disease rules read per-visit field observations
(incidence %, plant/rhizome/stem condition). This view surfaces the latest
scouting row's KB-consumed columns; ``build_farm_brain`` maps them 1:1 and
derives ``pest_scouting_date`` from ``scouting_date``.
"""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class CropScoutingView:
    """Read-side projection of the latest ``crop_scouting`` row for a plot."""

    scouting_id: uuid.UUID
    plot_id: str
    scouting_date: datetime.date
    emergence_started: bool | None = None
    establishment_pct: Decimal | None = None
    tillers_per_plant: Decimal | None = None
    flowering_observed: bool | None = None
    central_shoot_dead: bool | None = None
    seed_sprouts_visible: bool | None = None
    shoot_borer_incidence_pct: Decimal | None = None
    leaf_roller_incidence_pct: Decimal | None = None
    rhizome_fly_incidence_pct: Decimal | None = None
    white_grub_suspected: bool | None = None
    nematode_suspected: bool | None = None
    leaf_caterpillar_observed: bool | None = None
    light_trap_installed: bool | None = None
    light_trap_count_nightly: int | None = None
    straight_line_holes_in_whorl: bool | None = None
    stem_hole_with_webbing: bool | None = None
    exposed_rhizomes_observed: bool | None = None
    rot_incidence_pct: Decimal | None = None
    wilt_incidence_pct: Decimal | None = None
    leaf_spot_incidence_pct: Decimal | None = None
    wilt_while_green: bool | None = None
    leaf_spot_rings_visible: bool | None = None
    ooze_test_result: str | None = None
    rhizome_texture: str | None = None
    rhizome_smell: str | None = None
    stem_cut_colour: str | None = None
    stem_ooze_type: str | None = None
    soft_rhizome_found: bool | None = None
    plant_pulls_easily: bool | None = None
    shoot_pulls_out_easily: bool | None = None
    leaf_yellowing_pattern: str | None = None
    skin_scrape_result: str | None = None
    sample_dig_120_done: bool | None = None
    sample_dig_180_done: bool | None = None
    standing_water_hours_observed: Decimal | None = None
    harvest_injury_observed: bool | None = None
    moisture_pct_final: Decimal | None = None


@runtime_checkable
class CropScoutingRepo(Protocol):
    """Read-only crop-scouting repo for the farm-brain builder."""

    async def latest_for_plot(self, plot_id: str) -> CropScoutingView | None:
        """Most-recent scouting row for the plot, or None."""
        ...


__all__ = ["CropScoutingRepo", "CropScoutingView"]
