"""0056 variety lookup source_tier vocabulary fix — L3/L4 -> A/B/C (v1.2 §DR2).

Aligns the descriptive ``source_tier`` column on the two variety lookup tables
to the deployed evidence-tier vocabulary (A/B/C), per the agronomy v1.2 pack:

* variety_stage_water_target: L3 -> B (VNMKV OFT indicative)
* variety_n_ceiling:          L3 -> B (Mahima VNMKV baseline), L4 -> C
  (VIRAAI-derived Varada/Nadia ratios)

Note: the v1.2 CSV re-issue labelled the column ``source_class`` with B/C values,
but B/C are source *tiers* (source_class is a separate enum: SRC-Q/DERIVED/EST/…).
We therefore keep the column name ``source_tier`` and only remap the values.

Data-only; reversible.

Revision ID: 0056
Revises: 0055
Create Date: 2026-09-28
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0056"
down_revision: str | None = "0055"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
UPDATE variety_stage_water_target SET source_tier = 'B' WHERE source_tier = 'L3';
UPDATE variety_n_ceiling          SET source_tier = 'B' WHERE source_tier = 'L3';
UPDATE variety_n_ceiling          SET source_tier = 'C' WHERE source_tier = 'L4';
"""

DOWNGRADE_SQL = """
UPDATE variety_stage_water_target SET source_tier = 'L3' WHERE source_tier = 'B';
UPDATE variety_n_ceiling          SET source_tier = 'L3' WHERE source_tier = 'B';
UPDATE variety_n_ceiling          SET source_tier = 'L4' WHERE source_tier = 'C';
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
