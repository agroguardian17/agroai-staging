"""0073 app_event — lightweight notable-events stream (R3.5).

A small additive table for structured notable events (errors, warnings, state
changes) that otherwise live only in ``docker logs`` — e.g. the ingest drain
loop's unexpected-error branch. NOT a full log-to-DB sink (that stays out of
scope); just enough that the dashboard's "Recent Errors & Warnings" page can
show these alongside the job_run ledger. Writes are best-effort from the app.

Revision ID: 0073
Revises: 0072
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0073"
down_revision: str | None = "0072"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS app_event (
    id          UUID PRIMARY KEY,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    level       TEXT NOT NULL CHECK (level IN ('error', 'warn', 'info')),
    source      TEXT NOT NULL,
    event       TEXT NOT NULL,
    entity      TEXT,
    detail      JSONB NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_app_event_recent ON app_event (created_at DESC, level);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS app_event;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
