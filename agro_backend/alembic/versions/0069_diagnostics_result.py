"""0069 diagnostics_result — nightly diagnostics battery results (Round 1).

One row per check per battery run: a freshness or invariant check over the DB,
with its status (ok|warn|fail|skip) and the observed-vs-expected detail. Written
**best-effort** by the diagnostics job when ``DIAGNOSTICS_ENABLED`` is set; read
only by the dashboard's System Diagnostics page. Additive + forward-only.

Catches the "bad data / stale pipeline" class of bugs (e.g. the k_source outage,
crop-age drift, duplicate advisories, partition exhaustion) automatically instead
of by manual dashboard review. Bounded by the retention sweep
(OBSERVABILITY_RETENTION_DAYS) in the retention job.

Revision ID: 0069
Revises: 0068
Create Date: 2026-10-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0069"
down_revision: str | None = "0068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS diagnostics_result (
    id          UUID PRIMARY KEY,
    run_id      UUID NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    check_id    TEXT NOT NULL,
    category    TEXT NOT NULL CHECK (category IN ('freshness', 'invariant', 'dependency')),
    status      TEXT NOT NULL CHECK (status IN ('ok', 'warn', 'fail', 'skip')),
    observed    TEXT,
    expected    TEXT,
    detail      TEXT
);
CREATE INDEX IF NOT EXISTS ix_diagnostics_result_created
    ON diagnostics_result (created_at DESC);
CREATE INDEX IF NOT EXISTS ix_diagnostics_result_check_created
    ON diagnostics_result (check_id, created_at DESC);
CREATE INDEX IF NOT EXISTS ix_diagnostics_result_run
    ON diagnostics_result (run_id);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS diagnostics_result;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
