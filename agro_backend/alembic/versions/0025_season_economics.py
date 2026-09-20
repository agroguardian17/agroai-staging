"""0025 season_economics - per-season economics (D13): costs, prices, grades, returns, finance (Phase 2.4).

1:1 with season (``season_id`` UNIQUE) upsert table. KB-consumed columns are named
identically to their kb_farm_brain_fields name so build_farm_brain maps them 1:1;
enum columns carry a CHECK matching the KB enum. Reversible, no backfill.

Revision ID: 0025
Revises: 0024
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS season_economics (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    season_id            UUID        NOT NULL UNIQUE REFERENCES crop_seasons(season_id) ON DELETE CASCADE,

    breakeven_price_per_quintal        NUMERIC,
    breakeven_yield_quintal            NUMERIC,
    cash_flow_gap_months               NUMERIC,
    cash_outflow_to_date               NUMERIC,
    ceiling_quintal_per_acre           NUMERIC,
    cost_drainage                      NUMERIC,
    cost_earthing_labour               NUMERIC,
    cost_harvest_transport             NUMERIC,
    cost_micronutrients                NUMERIC,
    cost_mulch                         NUMERIC,
    cost_seed                          NUMERIC,
    cost_seed_treatment_planting       NUMERIC,
    crop_loan_taken                    BOOLEAN,
    drip_annual_share                  NUMERIC,
    drip_capital_cost                  NUMERIC,
    drip_life_years                    NUMERIC,
    grade_a_pct                        NUMERIC,
    grade_b_pct                        NUMERIC,
    grade_c_pct                        NUMERIC,
    graded_separately                  BOOLEAN,
    intercrop_revenue                  NUMERIC,
    interest_cost                      NUMERIC,
    land_rent_or_opportunity           NUMERIC,
    mulch_material_price_per_tonne     NUMERIC,
    mulch_quantity_t_per_acre          NUMERIC,
    net_return_per_acre                NUMERIC,
    sale_market                        TEXT,
    sale_price_per_quintal             NUMERIC,
    seed_opportunity_cost              NUMERIC,
    seed_retained_or_purchased         TEXT CHECK (seed_retained_or_purchased IN ('retained', 'purchased', 'mixed')),
    total_cost_per_acre                NUMERIC,
    transport_cost_per_quintal         NUMERIC,

    notes                TEXT,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS season_economics;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
