"""0040 D11 yield_prediction_log v1 columns (D11_YIELD_MODEL_v1 §6.4).

D11 yield-model build, PR 4b (the full switch). The mapper now predicts with the
v1 model (Y_var x SI x factors, bootstrap CI), so the prediction log gains the
spec's v1 fields. Additive and nullable, so any in-flight writes keep working;
the new orchestration populates them.

- y_potential / y_process / epsilon_ml / y_point : the pipeline stages (§5).
- y_low_90 / y_high_90                          : the bootstrap 90% band (§4).
- unexplained_pct                              : residual gap not attributed.
- missing_factors INT[]                        : factor_ids with no measurable signal.
- as_of_date                                   : the prediction's as-of date.

Reversible.

Revision ID: 0040
Revises: 0039
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0040"
down_revision: str | None = "0039"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE yield_prediction_log
    ADD COLUMN IF NOT EXISTS y_potential      NUMERIC,
    ADD COLUMN IF NOT EXISTS y_process        NUMERIC,
    ADD COLUMN IF NOT EXISTS epsilon_ml       NUMERIC,
    ADD COLUMN IF NOT EXISTS y_point          NUMERIC,
    ADD COLUMN IF NOT EXISTS y_low_90         NUMERIC,
    ADD COLUMN IF NOT EXISTS y_high_90        NUMERIC,
    ADD COLUMN IF NOT EXISTS unexplained_pct  NUMERIC,
    ADD COLUMN IF NOT EXISTS missing_factors  INT[],
    ADD COLUMN IF NOT EXISTS as_of_date       DATE;
"""

DOWNGRADE_SQL = """
ALTER TABLE yield_prediction_log
    DROP COLUMN IF EXISTS y_potential,
    DROP COLUMN IF EXISTS y_process,
    DROP COLUMN IF EXISTS epsilon_ml,
    DROP COLUMN IF EXISTS y_point,
    DROP COLUMN IF EXISTS y_low_90,
    DROP COLUMN IF EXISTS y_high_90,
    DROP COLUMN IF EXISTS unexplained_pct,
    DROP COLUMN IF EXISTS missing_factors,
    DROP COLUMN IF EXISTS as_of_date;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
