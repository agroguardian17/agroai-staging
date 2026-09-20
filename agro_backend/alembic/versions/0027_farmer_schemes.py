"""0027 farmer_schemes - per-farmer govt scheme / subsidy / eligibility state (D10) (Phase 2.4).

1:1 with farmer (``farmer_id`` UNIQUE) upsert table. KB-consumed columns are named
identically to their kb_farm_brain_fields name so build_farm_brain maps them 1:1;
enum columns carry a CHECK matching the KB enum. Reversible, no backfill.

Revision ID: 0027
Revises: 0026
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS farmer_schemes (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    farmer_id            UUID        NOT NULL UNIQUE REFERENCES farmers(farmer_id) ON DELETE CASCADE,

    cgwb_block_category                TEXT CHECK (cgwb_block_category IN ('safe', 'semi_critical', 'critical', 'over_exploited', 'unverified')),
    cibrc_list_checked_date            DATE,
    data_review_due                    DATE,
    drip_subsidy_pct_applicable        NUMERIC,
    drought_prone_listed               TEXT CHECK (drought_prone_listed IN ('yes', 'no', 'unverified')),
    farm_pond_planned                  BOOLEAN,
    farmer_category                    TEXT CHECK (farmer_category IN ('small_marginal', 'other', 'unverified')),
    geo_tagging_done                   BOOLEAN,
    kvk_contacted                      BOOLEAN,
    pmfby_notified_for_ginger          TEXT CHECK (pmfby_notified_for_ginger IN ('yes', 'no', 'unverified')),
    pre_sanction_date                  DATE,
    pre_sanction_received              BOOLEAN,
    priority_category                  TEXT CHECK (priority_category IN ('martyr_family', 'suicide_affected', 'bpl', 'widow_or_deserted', 'small_marginal', 'other')),
    research_centre_contacted          BOOLEAN,
    scale_of_finance_per_acre          NUMERIC,
    seed_supplier_identified           BOOLEAN,
    soil_lab_selected                  TEXT,
    subsidy_applied_date               DATE,
    subsidy_documents_ready            BOOLEAN,
    subsidy_lottery_result             TEXT CHECK (subsidy_lottery_result IN ('pending', 'selected', 'not_selected', 'not_applied')),
    subsidy_scheme_applied             TEXT,

    notes                TEXT,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS farmer_schemes;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
