"""Postgres adapter for :class:`~app.application.ports.crop_scouting_repo.CropScoutingRepo`."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.crop_scouting_repo import CropScoutingView

_SELECT_COLS = (
    "scouting_id, plot_id, scouting_date, "
    "emergence_started, establishment_pct, tillers_per_plant, flowering_observed, central_shoot_dead, seed_sprouts_visible, shoot_borer_incidence_pct, leaf_roller_incidence_pct, rhizome_fly_incidence_pct, white_grub_suspected, nematode_suspected, leaf_caterpillar_observed, light_trap_installed, light_trap_count_nightly, straight_line_holes_in_whorl, stem_hole_with_webbing, exposed_rhizomes_observed, rot_incidence_pct, wilt_incidence_pct, leaf_spot_incidence_pct, wilt_while_green, leaf_spot_rings_visible, ooze_test_result, rhizome_texture, rhizome_smell, stem_cut_colour, stem_ooze_type, soft_rhizome_found, plant_pulls_easily, shoot_pulls_out_easily, leaf_yellowing_pattern, skin_scrape_result, sample_dig_120_done, sample_dig_180_done, standing_water_hours_observed, harvest_injury_observed, moisture_pct_final"
)


def _row_to_view(row: object) -> CropScoutingView:
    r: Any = row
    return CropScoutingView(
        scouting_id=r.scouting_id,
        plot_id=r.plot_id,
        scouting_date=r.scouting_date,
        emergence_started=r.emergence_started,
        establishment_pct=r.establishment_pct,
        tillers_per_plant=r.tillers_per_plant,
        flowering_observed=r.flowering_observed,
        central_shoot_dead=r.central_shoot_dead,
        seed_sprouts_visible=r.seed_sprouts_visible,
        shoot_borer_incidence_pct=r.shoot_borer_incidence_pct,
        leaf_roller_incidence_pct=r.leaf_roller_incidence_pct,
        rhizome_fly_incidence_pct=r.rhizome_fly_incidence_pct,
        white_grub_suspected=r.white_grub_suspected,
        nematode_suspected=r.nematode_suspected,
        leaf_caterpillar_observed=r.leaf_caterpillar_observed,
        light_trap_installed=r.light_trap_installed,
        light_trap_count_nightly=r.light_trap_count_nightly,
        straight_line_holes_in_whorl=r.straight_line_holes_in_whorl,
        stem_hole_with_webbing=r.stem_hole_with_webbing,
        exposed_rhizomes_observed=r.exposed_rhizomes_observed,
        rot_incidence_pct=r.rot_incidence_pct,
        wilt_incidence_pct=r.wilt_incidence_pct,
        leaf_spot_incidence_pct=r.leaf_spot_incidence_pct,
        wilt_while_green=r.wilt_while_green,
        leaf_spot_rings_visible=r.leaf_spot_rings_visible,
        ooze_test_result=r.ooze_test_result,
        rhizome_texture=r.rhizome_texture,
        rhizome_smell=r.rhizome_smell,
        stem_cut_colour=r.stem_cut_colour,
        stem_ooze_type=r.stem_ooze_type,
        soft_rhizome_found=r.soft_rhizome_found,
        plant_pulls_easily=r.plant_pulls_easily,
        shoot_pulls_out_easily=r.shoot_pulls_out_easily,
        leaf_yellowing_pattern=r.leaf_yellowing_pattern,
        skin_scrape_result=r.skin_scrape_result,
        sample_dig_120_done=r.sample_dig_120_done,
        sample_dig_180_done=r.sample_dig_180_done,
        standing_water_hours_observed=r.standing_water_hours_observed,
        harvest_injury_observed=r.harvest_injury_observed,
        moisture_pct_final=r.moisture_pct_final,
    )


class PgCropScoutingRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def latest_for_plot(self, plot_id: str) -> CropScoutingView | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_scouting "
            "WHERE plot_id = :plot_id ORDER BY scouting_date DESC LIMIT 1"
        )
        async with self._sm() as session:
            row = (await session.execute(stmt, {"plot_id": plot_id})).first()
        return None if row is None else _row_to_view(row)


__all__ = ["PgCropScoutingRepo"]
