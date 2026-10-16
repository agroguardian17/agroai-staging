"""0068 job_run — scheduler job-run ledger (debug hardening, Round 1).

One row per scheduler tick: when it started/finished, its terminal status
(ok|failed|skipped), a small summary dict, and the error type/message on
failure. Written **best-effort** by ``instrument_job`` when
``JOB_RUN_LEDGER_ENABLED`` is set; nothing in the system reads it except the
dashboard's Scheduler Health page. Additive + forward-only (downgrade drops it).

Turns a silently-failing nightly job from "invisible in the logs for weeks"
into "red on the dashboard the next morning". Bounded by the retention sweep
(OBSERVABILITY_RETENTION_DAYS) in the retention job.

Revision ID: 0068
Revises: 0067
Create Date: 2026-10-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0068"
down_revision: str | None = "0067"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS job_run (
    id            UUID PRIMARY KEY,
    job_name      TEXT NOT NULL,
    started_at    TIMESTAMPTZ NOT NULL,
    finished_at   TIMESTAMPTZ NOT NULL,
    duration_ms   INTEGER,
    status        TEXT NOT NULL CHECK (status IN ('ok', 'failed', 'skipped')),
    summary       JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_type    TEXT,
    error_message TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_job_run_job_started
    ON job_run (job_name, started_at DESC);
CREATE INDEX IF NOT EXISTS ix_job_run_status_started
    ON job_run (status, started_at DESC);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS job_run;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
