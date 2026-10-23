"""0070 qa_digest — persist the weekly D12 digests to the DB (fix A2).

The weekly QA/bias digests were written only to a container directory
(``QA_DIGEST_DIR``), which (a) fails with ``PermissionError`` when that path
isn't writable in the image and (b) is ephemeral — lost on every redeploy.
This table makes the rendered digests durable + queryable + dashboard-viewable;
the filesystem write becomes best-effort. Upsert on ``(week_start, kind)`` since
a digest is regenerable.

Revision ID: 0070
Revises: 0069
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0070"
down_revision: str | None = "0069"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS qa_digest (
    id            UUID PRIMARY KEY,
    week_start    DATE NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('weekly_report', 'bias_digest')),
    filename      TEXT NOT NULL,
    content       TEXT NOT NULL,
    generated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (week_start, kind)
);
CREATE INDEX IF NOT EXISTS ix_qa_digest_week ON qa_digest (week_start DESC, kind);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS qa_digest;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
