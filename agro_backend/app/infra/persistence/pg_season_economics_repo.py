"""Postgres adapter for the SeasonEconomicsRepo port."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.season_economics_repo import SeasonEconomicsView

_SELECT_COLS = "season_id, breakeven_price_per_quintal, breakeven_yield_quintal, cash_flow_gap_months, cash_outflow_to_date, ceiling_quintal_per_acre, cost_drainage, cost_earthing_labour, cost_harvest_transport, cost_micronutrients, cost_mulch, cost_seed, cost_seed_treatment_planting, crop_loan_taken, drip_annual_share, drip_capital_cost, drip_life_years, grade_a_pct, grade_b_pct, grade_c_pct, graded_separately, intercrop_revenue, interest_cost, land_rent_or_opportunity, mulch_material_price_per_tonne, mulch_quantity_t_per_acre, net_return_per_acre, sale_market, sale_price_per_quintal, seed_opportunity_cost, seed_retained_or_purchased, total_cost_per_acre, transport_cost_per_quintal"


def _row_to_view(row: object) -> SeasonEconomicsView:
    r: Any = row
    return SeasonEconomicsView(
        season_id=r.season_id,
        breakeven_price_per_quintal=r.breakeven_price_per_quintal,
        breakeven_yield_quintal=r.breakeven_yield_quintal,
        cash_flow_gap_months=r.cash_flow_gap_months,
        cash_outflow_to_date=r.cash_outflow_to_date,
        ceiling_quintal_per_acre=r.ceiling_quintal_per_acre,
        cost_drainage=r.cost_drainage,
        cost_earthing_labour=r.cost_earthing_labour,
        cost_harvest_transport=r.cost_harvest_transport,
        cost_micronutrients=r.cost_micronutrients,
        cost_mulch=r.cost_mulch,
        cost_seed=r.cost_seed,
        cost_seed_treatment_planting=r.cost_seed_treatment_planting,
        crop_loan_taken=r.crop_loan_taken,
        drip_annual_share=r.drip_annual_share,
        drip_capital_cost=r.drip_capital_cost,
        drip_life_years=r.drip_life_years,
        grade_a_pct=r.grade_a_pct,
        grade_b_pct=r.grade_b_pct,
        grade_c_pct=r.grade_c_pct,
        graded_separately=r.graded_separately,
        intercrop_revenue=r.intercrop_revenue,
        interest_cost=r.interest_cost,
        land_rent_or_opportunity=r.land_rent_or_opportunity,
        mulch_material_price_per_tonne=r.mulch_material_price_per_tonne,
        mulch_quantity_t_per_acre=r.mulch_quantity_t_per_acre,
        net_return_per_acre=r.net_return_per_acre,
        sale_market=r.sale_market,
        sale_price_per_quintal=r.sale_price_per_quintal,
        seed_opportunity_cost=r.seed_opportunity_cost,
        seed_retained_or_purchased=r.seed_retained_or_purchased,
        total_cost_per_acre=r.total_cost_per_acre,
        transport_cost_per_quintal=r.transport_cost_per_quintal,
    )


class PgSeasonEconomicsRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def for_season(self, season_id: uuid.UUID) -> SeasonEconomicsView | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM season_economics WHERE season_id = :k")
        async with self._sm() as session:
            row = (await session.execute(stmt, {"k": season_id})).first()
        return None if row is None else _row_to_view(row)


__all__ = ["PgSeasonEconomicsRepo"]
