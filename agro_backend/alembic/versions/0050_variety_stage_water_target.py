"""0050 variety_stage_water_target — water-budget engine foundation (handoff v1.3 §6.1).

Water Budget & Irrigation engine, foundation phase (dependency-free; signed off
in handoff v1.3 §7.2/§9). Holds the per-variety, per-stage water targets the
water-budget deficit/dose logic reads (`stage_water_target_L_per_plant`).

Seeded with IISR Mahima's VNMKV/ICAR L3-indicative values from §6.1 (the primary
Kannad Season-1 variety). Varada / Nadia rows are intentionally NOT seeded from
the doc's "reduce by 10%/15%" rule — Kuldip's signed CSV (target 5 Oct 2026)
carries the authoritative values and re-seeds the table; we do not manufacture
pseudo-precise figures for L3 data. Re-seed is a data-only migration.

Stage rows use G1–G5 plus a LIFECYCLE aggregate row (total per plant, no daily/
per-event columns). G5 per-event target is 0 (stop irrigation before harvest).

Additive; reversible.

Revision ID: 0050
Revises: 0049
Create Date: 2026-09-25
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0050"
down_revision: str | None = "0049"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
CREATE TABLE IF NOT EXISTS variety_stage_water_target (
    variety              TEXT NOT NULL,
    stage                TEXT NOT NULL,      -- G1..G5 | LIFECYCLE
    stage_target_l_low   NUMERIC(6,2) NOT NULL,
    stage_target_l_high  NUMERIC(6,2) NOT NULL,
    daily_l_low          NUMERIC(5,2),       -- NULL for LIFECYCLE
    daily_l_high         NUMERIC(5,2),
    per_event_l_low      NUMERIC(5,2),       -- 0 at G5 (stop); NULL for LIFECYCLE
    per_event_l_high     NUMERIC(5,2),
    max_l_per_event      NUMERIC(5,2),       -- NULL where not applicable
    source_tier          TEXT NOT NULL DEFAULT 'L3',
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (variety, stage)
);

-- IISR Mahima — verbatim §6.1 (L3, VNMKV OFT indicative). Season 1 re-seeds
-- from Kuldip's signed CSV; Varada/Nadia land with that CSV.
INSERT INTO variety_stage_water_target (
    variety, stage, stage_target_l_low, stage_target_l_high,
    daily_l_low, daily_l_high, per_event_l_low, per_event_l_high, max_l_per_event
) VALUES
    ('IISR Mahima', 'G1',         18,  22, 0.5, 0.7, 0.5, 0.8, 1.5),
    ('IISR Mahima', 'G2',         55,  70, 1.0, 1.4, 1.5, 2.0, 3.0),
    ('IISR Mahima', 'G3',         90, 110, 1.5, 2.0, 2.0, 2.8, 4.0),
    ('IISR Mahima', 'G4',         30,  40, 0.5, 0.7, 1.5, 2.0, 3.0),
    ('IISR Mahima', 'G5',          3,   6, 0.1, 0.2, 0.0, 0.0, NULL),
    ('IISR Mahima', 'LIFECYCLE', 200, 250, NULL, NULL, NULL, NULL, NULL)
ON CONFLICT (variety, stage) DO NOTHING;
"""

DOWNGRADE_SQL = "DROP TABLE IF EXISTS variety_stage_water_target;"


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
