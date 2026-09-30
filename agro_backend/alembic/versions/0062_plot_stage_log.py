"""0062 plot_stage_log — per-plot growth-stage history for D03-SB-003.

The KB rule **D03-SB-003** detects a phenological transition
(``current_stage != previous_stage AND previous_stage IS NOT NULL``). The
mapper knows the current stage from the active season, but the *previous* run's
stage is history the backend must keep. The ginger engine's ``engine_state``
store only holds notifier/override bookkeeping, so this small log is the home
for stage-by-run-date.

One row per (plot, run day): the daily job upserts the stage each run and the
mapper reads the most recent earlier row to fill ``previous_stage``. Reversible;
no backfill (a plot simply has no "previous" until its second recorded run).

Revision ID: 0062
Revises: 0061
Create Date: 2026-09-30
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0062"
down_revision: str | None = "0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS plot_stage_log (
    plot_id     TEXT NOT NULL,
    run_date    DATE NOT NULL,
    stage       TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (plot_id, run_date)
);
CREATE INDEX IF NOT EXISTS ix_plot_stage_log_plot_date
    ON plot_stage_log (plot_id, run_date DESC);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS plot_stage_log;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
