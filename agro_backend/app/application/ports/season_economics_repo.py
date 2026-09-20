"""Port: read-side season_economics lookup for the ginger farm-brain."""

from __future__ import annotations

import datetime  # noqa: F401
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable  # noqa: F401


@dataclass(frozen=True, slots=True)
class SeasonEconomicsView:
    """Read-side projection of the season_economics row (KB-consumed columns)."""

    season_id: uuid.UUID
    breakeven_price_per_quintal: Decimal | None = None
    breakeven_yield_quintal: Decimal | None = None
    cash_flow_gap_months: Decimal | None = None
    cash_outflow_to_date: Decimal | None = None
    ceiling_quintal_per_acre: Decimal | None = None
    cost_drainage: Decimal | None = None
    cost_earthing_labour: Decimal | None = None
    cost_harvest_transport: Decimal | None = None
    cost_micronutrients: Decimal | None = None
    cost_mulch: Decimal | None = None
    cost_seed: Decimal | None = None
    cost_seed_treatment_planting: Decimal | None = None
    crop_loan_taken: bool | None = None
    drip_annual_share: Decimal | None = None
    drip_capital_cost: Decimal | None = None
    drip_life_years: Decimal | None = None
    grade_a_pct: Decimal | None = None
    grade_b_pct: Decimal | None = None
    grade_c_pct: Decimal | None = None
    graded_separately: bool | None = None
    intercrop_revenue: Decimal | None = None
    interest_cost: Decimal | None = None
    land_rent_or_opportunity: Decimal | None = None
    mulch_material_price_per_tonne: Decimal | None = None
    mulch_quantity_t_per_acre: Decimal | None = None
    net_return_per_acre: Decimal | None = None
    sale_market: str | None = None
    sale_price_per_quintal: Decimal | None = None
    seed_opportunity_cost: Decimal | None = None
    seed_retained_or_purchased: str | None = None
    total_cost_per_acre: Decimal | None = None
    transport_cost_per_quintal: Decimal | None = None


@runtime_checkable
class SeasonEconomicsRepo(Protocol):
    async def for_season(self, season_id: uuid.UUID) -> SeasonEconomicsView | None:
        """The season_economics row for this season, or None."""
        ...


__all__ = ["SeasonEconomicsRepo", "SeasonEconomicsView"]
