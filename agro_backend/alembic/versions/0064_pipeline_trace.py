"""0064 pipeline_trace — per-message ingest observability (Pipeline Inspector).

One row per ingest message describing its journey through the server-side stages
(receive → validate → raw snapshot → calibrate → clock-skew → persist →
device-rules), with the raw-vs-calibrated values and a validation checklist. This
is **observability only** — it is written best-effort by the broker when
``PIPELINE_TRACE_ENABLED`` is set, and nothing in the system reads it except the
dashboard's Pipeline Inspector page. Additive; forward-only (downgrade drops it).

Bounded by a retention sweep (PIPELINE_TRACE_RETENTION_DAYS) to be added with the
retention job.

Revision ID: 0064
Revises: 0063
Create Date: 2026-10-04
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0064"
down_revision: str | None = "0063"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS pipeline_trace (
    trace_id     UUID PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    topic        TEXT NOT NULL,
    schema_id    TEXT,
    node_id      TEXT,
    plot_id      TEXT,
    tenant_id    TEXT,
    recorded_at  TIMESTAMPTZ,
    raw_payload  JSONB NOT NULL DEFAULT '{}'::jsonb,
    calibrated   JSONB NOT NULL DEFAULT '{}'::jsonb,
    stages       JSONB NOT NULL DEFAULT '{}'::jsonb,
    validations  JSONB NOT NULL DEFAULT '[]'::jsonb,
    overall      TEXT NOT NULL CHECK (overall IN ('ok', 'warn', 'fail')),
    drop_reason  TEXT
);
CREATE INDEX IF NOT EXISTS ix_pipeline_trace_node_created
    ON pipeline_trace (node_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_pipeline_trace_overall_created
    ON pipeline_trace (overall, created_at DESC);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS pipeline_trace;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
