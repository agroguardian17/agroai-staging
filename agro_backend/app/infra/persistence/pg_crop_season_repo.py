"""Postgres adapter for :class:`~app.application.ports.crop_season_repo.CropSeasonRepo`."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.crop_season_repo import CropSeasonView

_SELECT_COLS = (
    "season_id, tenant_id, farm_id, plot_id, "
    "crop_name_english, crop_name_marathi, crop_category, crop_variety, "
    "sowing_date, expected_harvest_date, current_growth_stage, "
    "crop_age_days_today, "
    "actual_harvest_date, seed_cost_per_kg, "
    "target_yield_qtl_per_acre, actual_yield_qtl_per_acre, "
    # Agronomy-plan columns (migration 0022).
    "deep_ploughing_done, solarization_done, solarization_weeks, planting_layout, "
    "bed_height_cm, bed_width_cm, furrow_width_cm, plants_per_acre, planting_depth_cm, "
    "earthing_up_date, earthing_up_2_date, "
    "mulch_stage_1_done, mulch_stage_2_done, mulch_stage_3_done, "
    "n_target_kg_per_acre, p_target_kg_per_acre, k_target_kg_per_acre, "
    "n_applied_kg_per_acre, p_applied_kg_per_acre, k_applied_kg_per_acre, "
    "n_split_1_date, n_split_2_date, k_late_split_1_date, k_late_split_2_date, "
    "fym_t_per_acre, fym_fully_decomposed, trichoderma_kg_per_acre, "
    "neem_cake_basal_kg_per_acre, neem_cake_earthing_kg_per_acre, "
    "micronutrient_basal_done, micronutrient_spray_1_done, micronutrient_spray_2_done, "
    "hot_water_treatment_done, biofumigation_done, azospirillum_psb_done, "
    "marigold_planted, target_product"
)


def _row_to_view(row: object) -> CropSeasonView:
    r: Any = row
    return CropSeasonView(
        season_id=r.season_id,
        tenant_id=r.tenant_id,
        farm_id=r.farm_id,
        plot_id=r.plot_id,
        crop_name_english=r.crop_name_english,
        crop_name_marathi=r.crop_name_marathi,
        crop_category=r.crop_category,
        crop_variety=r.crop_variety,
        sowing_date=r.sowing_date,
        expected_harvest_date=r.expected_harvest_date,
        current_growth_stage=r.current_growth_stage,
        crop_age_days_today=r.crop_age_days_today,
        actual_harvest_date=r.actual_harvest_date,
        seed_cost_per_kg=r.seed_cost_per_kg,
        target_yield_qtl_per_acre=r.target_yield_qtl_per_acre,
        actual_yield_qtl_per_acre=r.actual_yield_qtl_per_acre,
        deep_ploughing_done=r.deep_ploughing_done,
        solarization_done=r.solarization_done,
        solarization_weeks=r.solarization_weeks,
        planting_layout=r.planting_layout,
        bed_height_cm=r.bed_height_cm,
        bed_width_cm=r.bed_width_cm,
        furrow_width_cm=r.furrow_width_cm,
        plants_per_acre=r.plants_per_acre,
        planting_depth_cm=r.planting_depth_cm,
        earthing_up_date=r.earthing_up_date,
        earthing_up_2_date=r.earthing_up_2_date,
        mulch_stage_1_done=r.mulch_stage_1_done,
        mulch_stage_2_done=r.mulch_stage_2_done,
        mulch_stage_3_done=r.mulch_stage_3_done,
        n_target_kg_per_acre=r.n_target_kg_per_acre,
        p_target_kg_per_acre=r.p_target_kg_per_acre,
        k_target_kg_per_acre=r.k_target_kg_per_acre,
        n_applied_kg_per_acre=r.n_applied_kg_per_acre,
        p_applied_kg_per_acre=r.p_applied_kg_per_acre,
        k_applied_kg_per_acre=r.k_applied_kg_per_acre,
        n_split_1_date=r.n_split_1_date,
        n_split_2_date=r.n_split_2_date,
        k_late_split_1_date=r.k_late_split_1_date,
        k_late_split_2_date=r.k_late_split_2_date,
        fym_t_per_acre=r.fym_t_per_acre,
        fym_fully_decomposed=r.fym_fully_decomposed,
        trichoderma_kg_per_acre=r.trichoderma_kg_per_acre,
        neem_cake_basal_kg_per_acre=r.neem_cake_basal_kg_per_acre,
        neem_cake_earthing_kg_per_acre=r.neem_cake_earthing_kg_per_acre,
        micronutrient_basal_done=r.micronutrient_basal_done,
        micronutrient_spray_1_done=r.micronutrient_spray_1_done,
        micronutrient_spray_2_done=r.micronutrient_spray_2_done,
        hot_water_treatment_done=r.hot_water_treatment_done,
        biofumigation_done=r.biofumigation_done,
        azospirillum_psb_done=r.azospirillum_psb_done,
        marigold_planted=r.marigold_planted,
        target_product=r.target_product,
    )


class PgCropSeasonRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def find_active_for_plot(self, plot_id: str) -> CropSeasonView | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_seasons "
            "WHERE plot_id = :plot_id AND season_status = 'active' "
            "ORDER BY sowing_date DESC LIMIT 1"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id})
            row = res.first()
        return None if row is None else _row_to_view(row)

    async def list_active_by_crop(self, crop_name_english: str) -> list[CropSeasonView]:
        """All active seasons for a given crop, newest sowing_date first.

        Used by the daily ginger advisory job to iterate every ginger plot
        across every tenant in a single query.
        """
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_seasons "
            "WHERE crop_name_english = :crop AND season_status = 'active' "
            "ORDER BY sowing_date DESC"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"crop": crop_name_english})
            return [_row_to_view(r) for r in res.all()]


__all__ = ["PgCropSeasonRepo"]
