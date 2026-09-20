"""0021 lab_soil_tests — soil-lab chemistry results (Phase-2 KB storage).

The Ginger KB's D02/D04/D10 nutrient rules read soil-test chemistry the schema
had no home for: organic carbon, EC, free lime, and micronutrients (Zn/Fe/Ca/
Mg/S). Sensor NPK is unreliable (agronomy team, 2026-08), so the authoritative
source for soil composition is the lab report — this table is its landing zone.

Design:

* One row per soil test (farm-, optionally plot-scoped), time-series — a farm
  is re-tested across seasons and each result is kept.
* Columns consumed by the KB are named **identically** to their
  ``kb_farm_brain_fields`` name (``soil_oc_pct``, ``soil_ec``,
  ``soil_free_lime_pct``, ``soil_zn_ppm`` …) so ``build_farm_brain`` wires them
  1:1. ``soil_test_available`` is *derived* (a row exists) — not stored.
* Extra standard lab outputs (lab pH, N/P/K kg/ha, boron, sand/silt/clay %) are
  stored too — not KB fields today, but the future soil-composition engine and
  the USDA-triangle texture upgrade will read them. Named descriptively.

Reversible. No data backfill (rows arrive via the Data Entry page / lab intake).

Revision ID: 0021
Revises: 0020
Create Date: 2026-09-20
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS lab_soil_tests (
    lab_test_id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id            UUID        NOT NULL REFERENCES tenants(id),
    farm_id              UUID        NOT NULL REFERENCES farms(farm_id) ON DELETE CASCADE,
    -- Nullable: most soil tests are farm/field-level, not plot-specific.
    plot_id              TEXT        REFERENCES plots(plot_id) ON DELETE SET NULL,

    sample_date          DATE        NOT NULL,
    lab_name             TEXT,
    report_reference     TEXT,       -- lab report id / object-storage URL

    -- ---- KB-consumed chemistry: names MATCH kb_farm_brain_fields ----------
    soil_oc_pct          NUMERIC,    -- organic carbon %
    soil_ec              NUMERIC,    -- soil-test EC, dS/m (distinct from sensor ec_current)
    soil_free_lime_pct   NUMERIC,    -- free CaCO3 %
    soil_zn_ppm          NUMERIC,
    soil_fe_ppm          NUMERIC,
    soil_ca_ppm          NUMERIC,
    soil_mg_ppm          NUMERIC,
    soil_s_ppm           NUMERIC,

    -- ---- Standard lab outputs (not KB fields yet; soil-composition engine) -
    soil_ph_lab          NUMERIC,
    soil_n_kg_per_ha     NUMERIC,
    soil_p_kg_per_ha     NUMERIC,
    soil_k_kg_per_ha     NUMERIC,
    soil_b_ppm           NUMERIC,
    sand_pct             NUMERIC,
    silt_pct             NUMERIC,
    clay_pct             NUMERIC,

    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Latest-test-for-farm / for-plot lookups (build_farm_brain reads the newest).
CREATE INDEX IF NOT EXISTS lab_soil_tests_farm_recent
    ON lab_soil_tests (farm_id, sample_date DESC);
CREATE INDEX IF NOT EXISTS lab_soil_tests_plot_recent
    ON lab_soil_tests (plot_id, sample_date DESC)
    WHERE plot_id IS NOT NULL;
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS lab_soil_tests_plot_recent;
DROP INDEX IF EXISTS lab_soil_tests_farm_recent;
DROP TABLE IF EXISTS lab_soil_tests;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
