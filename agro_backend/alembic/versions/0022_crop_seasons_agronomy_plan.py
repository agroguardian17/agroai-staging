"""0022 crop_seasons agronomy-plan columns (Phase 2.2, part 1).

Adds the per-season agronomy PLAN / milestone facts the Ginger KB reads and the
schema had no home for: land prep (deep ploughing, solarization, planting
layout, bed/furrow dims), earthing-up + mulch stage milestones, the N/P/K
nutrient plan (target + applied + split dates), and bio-inputs (FYM, trichoderma,
neem cake, micronutrient sprays, hot-water/biofumigation/azospirillum, marigold).

All columns are:
* nullable (plan data arrives via the Data Entry page, often partial), and
* named **identically** to their kb_farm_brain_fields name, so build_farm_brain
  wires them 1:1.

These are one-value-per-season facts (fixed cardinality) — hence columns on
crop_seasons rather than an event log. Dated/variable operations (daily
irrigation, repeated sprays) go to a farm_operations log; observations go to
crop_scouting — both follow-up units. Enum columns carry a CHECK matching the
KB enum exactly. Reversible; no backfill.

Revision ID: 0022
Revises: 0021
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS deep_ploughing_done                BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS solarization_done                  BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS solarization_weeks                 NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS planting_layout                    TEXT CHECK (planting_layout IN ('flat_bed', 'ridge_furrow', 'broad_ridge'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS bed_height_cm                      NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS bed_width_cm                       NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS furrow_width_cm                    NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS plants_per_acre                    INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS planting_depth_cm                  NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS earthing_up_date                   DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS earthing_up_2_date                 DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS mulch_stage_1_done                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS mulch_stage_2_done                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS mulch_stage_3_done                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS n_target_kg_per_acre               NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS p_target_kg_per_acre               NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS k_target_kg_per_acre               NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS n_applied_kg_per_acre              NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS p_applied_kg_per_acre              NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS k_applied_kg_per_acre              NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS n_split_1_date                     DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS n_split_2_date                     DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS k_late_split_1_date                DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS k_late_split_2_date                DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS fym_t_per_acre                     NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS fym_fully_decomposed               BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS trichoderma_kg_per_acre            NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS neem_cake_basal_kg_per_acre        NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS neem_cake_earthing_kg_per_acre     NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS micronutrient_basal_done           BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS micronutrient_spray_1_done         BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS micronutrient_spray_2_done         BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS hot_water_treatment_done           BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS biofumigation_done                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS azospirillum_psb_done              BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS marigold_planted                   BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS target_product                     TEXT CHECK (target_product IN ('green_ginger', 'dry_ginger', 'seed_rhizome'));
"""

DOWNGRADE_SQL = r"""
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS deep_ploughing_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS solarization_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS solarization_weeks;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS planting_layout;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS bed_height_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS bed_width_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS furrow_width_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS plants_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS planting_depth_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS earthing_up_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS earthing_up_2_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS mulch_stage_1_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS mulch_stage_2_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS mulch_stage_3_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS n_target_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS p_target_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS k_target_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS n_applied_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS p_applied_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS k_applied_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS n_split_1_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS n_split_2_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS k_late_split_1_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS k_late_split_2_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS fym_t_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS fym_fully_decomposed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS trichoderma_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS neem_cake_basal_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS neem_cake_earthing_kg_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS micronutrient_basal_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS micronutrient_spray_1_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS micronutrient_spray_2_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS hot_water_treatment_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS biofumigation_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS azospirillum_psb_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS marigold_planted;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS target_product;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
