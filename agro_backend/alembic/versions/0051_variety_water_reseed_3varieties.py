"""0051 variety_stage_water_target re-seed — 3 varieties + DAP bands (VIRAAI deliverables 25 Sep 2026).

Re-seeds ``variety_stage_water_target`` from the agronomy team's authoritative
CSV (``VIRAAI_Agronomy_Deliverables_25Sep2026/01_WATER_BUDGET_CORE/
variety_stage_water_target.csv``), superseding migration 0050's Mahima-only
foundation seed.

Changes vs 0050:
* Adds ``dap_start`` / ``dap_end`` (the stage's DAP window — the water-budget
  engine maps DAP -> stage through these) and a ``notes`` provenance column.
* Adds a ``G0`` pre-plant bed-prep row per variety (not counted in LIFECYCLE).
* Seeds all three Season-1 Kannad varieties: IISR-Mahima (L3 VNMKV OFT
  indicative), IISR-Varada (-10% demand) and Nadia-local (-15% demand).
* Renames the Mahima key from "IISR Mahima" (space, 0050) to "IISR-Mahima"
  (hyphen) to match the CSV's canonical variety key.

Values stay source_tier L3 (indicative) — Season 1 field data re-calibrates them
(a later data-only migration). G5 per-event and max are 0 (irrigation stops for
skin cure); LIFECYCLE rows carry the season total only (no daily/per-event/max).

Additive schema + full re-seed; reversible (downgrade drops the new columns and
restores 0050's Mahima-only seed).

Revision ID: 0051
Revises: 0050
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0051"
down_revision: str | None = "0050"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE variety_stage_water_target
    ADD COLUMN IF NOT EXISTS dap_start INTEGER,
    ADD COLUMN IF NOT EXISTS dap_end   INTEGER,
    ADD COLUMN IF NOT EXISTS notes     TEXT;

-- Full re-seed: clear 0050's Mahima-only ("IISR Mahima") rows and load the
-- three-variety CSV (canonical hyphenated keys).
DELETE FROM variety_stage_water_target;

INSERT INTO variety_stage_water_target (
    variety, stage, dap_start, dap_end,
    stage_target_l_low, stage_target_l_high,
    daily_l_low, daily_l_high, per_event_l_low, per_event_l_high, max_l_per_event,
    source_tier, notes
) VALUES
    -- IISR-Mahima (240-day; L3 VNMKV OFT indicative)
    ('IISR-Mahima', 'G0',        -15,   0,   0,   3,  0,   0.2, 0,   0,   0.5, 'L3', 'Pre-plant bed prep water only; not counted in lifecycle'),
    ('IISR-Mahima', 'G1',          1,  35,  18,  22,  0.5, 0.7, 0.5, 0.8, 1.5, 'L3', 'Establishment; small frequent doses; sensitive to over-water at emergence'),
    ('IISR-Mahima', 'G2',         36,  90,  55,  70,  1.0, 1.4, 1.5, 2.0, 3.0, 'L3', 'Vegetative tiller and pseudostem build'),
    ('IISR-Mahima', 'G3',         91, 150,  90, 110,  1.5, 2.0, 2.0, 2.8, 4.0, 'L3', 'Peak rhizome-initiation; highest water sensitivity window'),
    ('IISR-Mahima', 'G4',        151, 210,  30,  40,  0.5, 0.7, 1.5, 2.0, 3.0, 'L3', 'Rhizome bulking; taper frequency but maintain per-event dose'),
    ('IISR-Mahima', 'G5',        211, 240,   3,   6,  0.1, 0.2, 0,   0,   0,   'L3', 'Senescence; stop irrigation 15-20 days before harvest for skin cure'),
    ('IISR-Mahima', 'LIFECYCLE',   0, 240, 200, 250, NULL,NULL,NULL,NULL,NULL,  'L3', 'Full-season total; use for pond capacity planning'),

    -- IISR-Varada (~10% lower demand than Mahima; shorter duration)
    ('IISR-Varada', 'G0',        -15,   0,   0,   3,  0,   0.2, 0,   0,   0.5, 'L3', 'Same as Mahima'),
    ('IISR-Varada', 'G1',          1,  35,  16,  20,  0.5, 0.6, 0.5, 0.7, 1.4, 'L3', '-10% vs Mahima; shorter duration variety'),
    ('IISR-Varada', 'G2',         36,  90,  50,  63,  0.9, 1.3, 1.4, 1.8, 2.7, 'L3', '-10% vs Mahima'),
    ('IISR-Varada', 'G3',         91, 150,  80, 100,  1.4, 1.8, 1.8, 2.5, 3.6, 'L3', '-10% vs Mahima'),
    ('IISR-Varada', 'G4',        151, 210,  27,  36,  0.5, 0.6, 1.4, 1.8, 2.7, 'L3', '-10% vs Mahima'),
    ('IISR-Varada', 'G5',        211, 240,   3,   5,  0.1, 0.2, 0,   0,   0,   'L3', '-10% vs Mahima'),
    ('IISR-Varada', 'LIFECYCLE',   0, 240, 180, 225, NULL,NULL,NULL,NULL,NULL,  'L3', 'Full-season total (Varada ~10% lower demand)'),

    -- Nadia-local (~15% lower demand; drought-tolerant landrace)
    ('Nadia-local', 'G0',        -15,   0,   0,   3,  0,   0.2, 0,   0,   0.5, 'L3', 'Local Kannad landrace'),
    ('Nadia-local', 'G1',          1,  35,  15,  19,  0.4, 0.6, 0.5, 0.7, 1.3, 'L3', '-15% vs Mahima; drought-tolerant landrace'),
    ('Nadia-local', 'G2',         36,  90,  47,  60,  0.9, 1.2, 1.3, 1.7, 2.6, 'L3', '-15% vs Mahima'),
    ('Nadia-local', 'G3',         91, 150,  77,  94,  1.3, 1.7, 1.7, 2.4, 3.4, 'L3', '-15% vs Mahima'),
    ('Nadia-local', 'G4',        151, 210,  26,  34,  0.4, 0.6, 1.3, 1.7, 2.6, 'L3', '-15% vs Mahima'),
    ('Nadia-local', 'G5',        211, 240,   3,   5,  0.1, 0.2, 0,   0,   0,   'L3', '-15% vs Mahima'),
    ('Nadia-local', 'LIFECYCLE',   0, 240, 170, 212, NULL,NULL,NULL,NULL,NULL,  'L3', 'Full-season total (Nadia ~15% lower demand)');
"""

DOWNGRADE_SQL = """
DELETE FROM variety_stage_water_target;

-- Restore 0050's Mahima-only foundation seed (space-keyed).
INSERT INTO variety_stage_water_target (
    variety, stage, stage_target_l_low, stage_target_l_high,
    daily_l_low, daily_l_high, per_event_l_low, per_event_l_high, max_l_per_event
) VALUES
    ('IISR Mahima', 'G1',         18,  22, 0.5, 0.7, 0.5, 0.8, 1.5),
    ('IISR Mahima', 'G2',         55,  70, 1.0, 1.4, 1.5, 2.0, 3.0),
    ('IISR Mahima', 'G3',         90, 110, 1.5, 2.0, 2.0, 2.8, 4.0),
    ('IISR Mahima', 'G4',         30,  40, 0.5, 0.7, 1.5, 2.0, 3.0),
    ('IISR Mahima', 'G5',          3,   6, 0.1, 0.2, 0.0, 0.0, NULL),
    ('IISR Mahima', 'LIFECYCLE', 200, 250, NULL, NULL, NULL, NULL, NULL);

ALTER TABLE variety_stage_water_target
    DROP COLUMN IF EXISTS dap_start,
    DROP COLUMN IF EXISTS dap_end,
    DROP COLUMN IF EXISTS notes;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
