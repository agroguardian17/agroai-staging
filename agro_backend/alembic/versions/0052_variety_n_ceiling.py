"""0052 variety_n_ceiling — per-variety nitrogen ceilings (VIRAAI deliverables 25 Sep 2026).

Lookup table backing rule D04-NS-003 (late-stage N-excess gate). Holds each
variety's total N ceiling and the VNMKV/AICRP split schedule, all in **kg N/acre**
(per the bundle's units convention 6b), plus the DAP-150 late-stage hard cutoff.

Seeded from ``VIRAAI_Agronomy_Deliverables_25Sep2026/03_N_TIMING_GATE/
variety_N_ceiling.csv``:
* IISR-Mahima 61 kg/acre (L3 — VNMKV PoP baseline 150 kg/ha exact conversion,
  no safety margin)
* IISR-Varada 55, Nadia-local 52 (L4 — VIRAAI-derived at -10% / -15% of Mahima,
  matching the variety water-demand ratios in variety_stage_water_target)

Variety keys match the canonical hyphenated keys used by variety_stage_water_target
(migration 0051). Data only re-calibrates from Season 1 field data later.

Additive; reversible (drops the table).

Revision ID: 0052
Revises: 0051
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0052"
down_revision: str | None = "0051"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS variety_n_ceiling (
    variety                        TEXT NOT NULL,
    total_n_ceiling_kg_per_acre    NUMERIC(5,2) NOT NULL,
    total_n_baseline_kg_per_ha     NUMERIC(6,2),
    basal_dap_0_kg_per_acre        NUMERIC(5,2),
    top_dress_45_dap_kg_per_acre   NUMERIC(5,2),
    top_dress_120_dap_kg_per_acre  NUMERIC(5,2),
    late_stage_n_cutoff_dap        INTEGER NOT NULL DEFAULT 150,
    g3_g4_excess_pct_threshold     NUMERIC(4,2) NOT NULL DEFAULT 0.00,
    source_tier                    TEXT NOT NULL,
    notes                          TEXT,
    updated_at                     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (variety)
);

INSERT INTO variety_n_ceiling (
    variety, total_n_ceiling_kg_per_acre, total_n_baseline_kg_per_ha,
    basal_dap_0_kg_per_acre, top_dress_45_dap_kg_per_acre, top_dress_120_dap_kg_per_acre,
    late_stage_n_cutoff_dap, g3_g4_excess_pct_threshold, source_tier, notes
) VALUES
    ('IISR-Mahima', 61, 150, 24, 20, 17, 150, 0.00, 'L3',
        'VNMKV PoP baseline 150 kg/ha = 60.7 kg/acre (rounded 61); exact baseline conversion, no safety margin'),
    ('IISR-Varada', 55, 135, 22, 18, 15, 150, 0.00, 'L4',
        'VIRAAI-derived: Mahima baseline x0.90 (matches Varada -10% water demand); shorter-duration, lower N'),
    ('Nadia-local', 52, 128, 21, 17, 14, 150, 0.00, 'L4',
        'VIRAAI-derived: Mahima baseline x0.85 (matches Nadia -15% water demand); drought-tolerant landrace')
ON CONFLICT (variety) DO NOTHING;
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS variety_n_ceiling;"


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
