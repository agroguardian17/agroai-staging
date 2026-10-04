"""0065 plot_run_trace — downstream (daily-run) pipeline observability.

One row per plot per daily ginger run: farm-brain field coverage, the key
derived KB fields, which rules the engine fired, how many advisories were
written, a per-stage checklist (farm-brain → KB engine → advisory) and a
validation checklist. Companion to ``pipeline_trace`` (ingest). Observability
only — written best-effort by the daily job when ``PIPELINE_TRACE_ENABLED`` is
on; bounded by the retention worker. Additive; forward-only.

Revision ID: 0065
Revises: 0064
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0065"
down_revision: str | None = "0064"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS plot_run_trace (
    trace_id            UUID PRIMARY KEY,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    plot_id             TEXT NOT NULL,
    season_id           TEXT,
    run_date            DATE NOT NULL,
    tenant_id           TEXT,
    farm_id             TEXT,
    advisories_written  INTEGER NOT NULL DEFAULT 0,
    coverage            JSONB NOT NULL DEFAULT '{}'::jsonb,
    derived             JSONB NOT NULL DEFAULT '{}'::jsonb,
    engine              JSONB NOT NULL DEFAULT '{}'::jsonb,
    stages              JSONB NOT NULL DEFAULT '{}'::jsonb,
    validations         JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall             TEXT NOT NULL CHECK (overall IN ('ok', 'warn', 'fail')),
    error               TEXT
);
CREATE INDEX IF NOT EXISTS ix_plot_run_trace_plot_created
    ON plot_run_trace (plot_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_plot_run_trace_rundate
    ON plot_run_trace (run_date DESC);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS plot_run_trace;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
