"""0024 crop_seasons agronomy-plan columns part 2 (Phase 2.4).

Adds the remaining per-season config the KB reads: drip design (flow, spacing,
shifts, drippers/acre, efficiency), water plan (available water, requirement,
plan basis), VWC thresholds, seed handling, harvest/processing plan, land/bed
config, drainage, and a few observed/history flags. All nullable, named to
match kb_farm_brain_fields; enum columns carry a CHECK matching the KB enum.

Companion to 0022 (part 1). One value per season -> columns. Reversible.

Revision ID: 0024
Revises: 0023
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS affected_plants_removed            BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS bed_former_arranged                BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS bud_orientation_instructed         BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS calibration_date                   DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS calibration_done                   BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS crop_coefficient_kc                NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drainage_levels_present            INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drainage_outlet_present            BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drip_efficiency_measured           NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drip_flow_lph_per_acre             NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drip_lateral_spacing_ft            NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drip_shifts_per_day                INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS dripper_spacing_cm                 NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drippers_per_acre                  INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS dry_recovery_pct_actual            NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drying_method                      TEXT CHECK (drying_method IN ('none', 'simple_sun', 'malabar_lime_sulphur', 'soda_khar', 'powder'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS drying_space_ready                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS field_history_rot                  BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS field_history_wilt                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS gap_filling_done                   BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS harvest_route                      TEXT CHECK (harvest_route IN ('green_early', 'green_full', 'dry_ginger_immediate', 'dry_ginger_stored', 'seed_rhizome'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS intercrop_selected                 TEXT;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS limiting_nutrient                  TEXT CHECK (limiting_nutrient IN ('N', 'P', 'K', 'S', 'Zn', 'Fe', 'B', 'Mg', 'none'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS main_drain_connected               BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS moisture_probe_depth_cm            NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS pan_coefficient_kp                 NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS perennial_weeds_removed            BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS ppe_available                      BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS processing_trained_operator        BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS produce_washed                     BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS rows_per_bed                       INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS season_water_plan_basis            TEXT CHECK (season_water_plan_basis IN ('poor_year', 'average_year', 'good_year'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seasonal_water_requirement_litres  NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_at_planting_kg                NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_buds_per_piece                INTEGER;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_piece_weight_g                NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_storage_loss_pct              NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_storage_method                TEXT CHECK (seed_storage_method IN ('pit', 'shade_heap', 'cold_store', 'purchased_fresh'));
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS seed_stored_kg                     NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS shade_pct                          NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS so2_treatment_used                 BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS storage_loss_monthly_pct           NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS vwc_field_capacity                 NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS vwc_saturation                     NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS vwc_stress_threshold               NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS water_available_oct_feb_litres     NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS water_stress_after_earthing_done   BOOLEAN;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS water_withdrawal_pct               NUMERIC;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS water_withdrawal_start_date        DATE;
ALTER TABLE crop_seasons ADD COLUMN IF NOT EXISTS water_withdrawal_started           BOOLEAN;
"""

DOWNGRADE_SQL = r"""
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS affected_plants_removed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS bed_former_arranged;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS bud_orientation_instructed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS calibration_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS calibration_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS crop_coefficient_kc;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drainage_levels_present;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drainage_outlet_present;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drip_efficiency_measured;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drip_flow_lph_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drip_lateral_spacing_ft;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drip_shifts_per_day;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS dripper_spacing_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drippers_per_acre;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS dry_recovery_pct_actual;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drying_method;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS drying_space_ready;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS field_history_rot;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS field_history_wilt;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS gap_filling_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS harvest_route;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS intercrop_selected;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS limiting_nutrient;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS main_drain_connected;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS moisture_probe_depth_cm;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS pan_coefficient_kp;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS perennial_weeds_removed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS ppe_available;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS processing_trained_operator;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS produce_washed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS rows_per_bed;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS season_water_plan_basis;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seasonal_water_requirement_litres;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_at_planting_kg;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_buds_per_piece;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_piece_weight_g;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_storage_loss_pct;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_storage_method;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS seed_stored_kg;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS shade_pct;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS so2_treatment_used;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS storage_loss_monthly_pct;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS vwc_field_capacity;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS vwc_saturation;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS vwc_stress_threshold;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS water_available_oct_feb_litres;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS water_stress_after_earthing_done;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS water_withdrawal_pct;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS water_withdrawal_start_date;
ALTER TABLE crop_seasons DROP COLUMN IF EXISTS water_withdrawal_started;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
