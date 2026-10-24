"""0071 anomaly_finding — persist the anomaly engine's typed findings (R3.4).

The Round-3 anomaly engine runs nightly and writes one row per finding (a
device that stopped reporting, a stuck sensor, a rule firing on nearly every
reading, an advisory-volume spike/drop) so the dashboard "Anomalies" page and
Daily Health can surface "the system pointing out issues itself". A run with no
findings writes no rows; the latest run is identified via the job_run ledger.

Revision ID: 0071
Revises: 0070
Create Date: 2026-10-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0071"
down_revision: str | None = "0070"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
CREATE TABLE IF NOT EXISTS anomaly_finding (
    id            UUID PRIMARY KEY,
    run_id        UUID NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    anomaly_type  TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('info', 'warn', 'critical')),
    entity_type   TEXT NOT NULL,
    entity_id     TEXT,
    observed      TEXT,
    expected      TEXT,
    detail        TEXT
);
CREATE INDEX IF NOT EXISTS ix_anomaly_finding_run ON anomaly_finding (run_id);
CREATE INDEX IF NOT EXISTS ix_anomaly_finding_recent
    ON anomaly_finding (created_at DESC, anomaly_type);
"""

DOWNGRADE_SQL = r"""
DROP TABLE IF EXISTS anomaly_finding;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
