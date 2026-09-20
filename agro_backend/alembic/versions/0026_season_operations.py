"""0026 season_operations - per-season field operations (D03/D05/D06/D08): sprays, fertigation, weeding (Phase 2.4).

1:1 with season (``season_id`` UNIQUE) upsert table. KB-consumed columns are named
identically to their kb_farm_brain_fields name so build_farm_brain maps them 1:1;
enum columns carry a CHECK matching the KB enum. Reversible, no backfill.

Revision ID: 0026
Revises: 0025
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS season_operations (
    id                   UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    season_id            UUID        NOT NULL UNIQUE REFERENCES crop_seasons(season_id) ON DELETE CASCADE,

    basal_k_kg_per_acre                NUMERIC,
    basal_p_kg_per_acre                NUMERIC,
    castor_bait_prepared_date          DATE,
    castor_bait_units_per_acre         INTEGER,
    drip_runtime_min                   NUMERIC,
    ethephon_spray_count               INTEGER,
    fertigation_active                 BOOLEAN,
    fertigation_last_ec_response       NUMERIC,
    herbicide_post_emergent_date       DATE,
    herbicide_pre_emergent_date        DATE,
    irrigation_applied_litres_today    NUMERIC,
    kulav_passes                       INTEGER,
    last_fungicide_date                DATE,
    last_fungicide_group               TEXT,
    last_insecticide_date              DATE,
    last_insecticide_group             TEXT,
    metarhizium_kg_per_acre            NUMERIC,
    naa_spray_count                    INTEGER,
    weeding_count                      INTEGER,

    notes                TEXT,
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS season_operations;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
