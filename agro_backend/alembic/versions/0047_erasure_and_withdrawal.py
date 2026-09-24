"""0047 DPDP erasure request + consent withdrawal (A3.4, A3.5).

Completes the data-principal rights from LEGAL_COMPLIANCE_CERTIFICATE §3.1:

- ``farmer_consent.withdrawn_at`` records the last consent withdrawal (§3.2:
  withdrawing research/third-party consent must not stop the advisory service —
  enforced in the ``withdraw_consent`` use-case, per-scope).
- ``erasure_request`` is the 30-day-SLA erasure workflow (A3.4). Each request
  carries a ``due_at`` (requested_at + 30 days) the retention/purge job acts on.
  A partial unique index allows at most one ``pending`` request per farmer.

Additive; reversible.

Revision ID: 0047
Revises: 0046
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0047"
down_revision: str | None = "0046"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE farmer_consent ADD COLUMN IF NOT EXISTS withdrawn_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS erasure_request (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    farmer_id     UUID NOT NULL REFERENCES farmers(farmer_id) ON DELETE CASCADE,
    requested_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at        TIMESTAMPTZ NOT NULL,      -- requested_at + 30 days (§3.1 SLA)
    status        TEXT NOT NULL DEFAULT 'pending'
                    CHECK (status IN ('pending', 'completed', 'rejected')),
    method        TEXT,                       -- e.g. 'db_and_backups'
    actor         TEXT,
    completed_at  TIMESTAMPTZ,
    note          TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS erasure_request_one_pending
    ON erasure_request (farmer_id) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS erasure_request_due_idx
    ON erasure_request (due_at) WHERE status = 'pending';
"""

DOWNGRADE_SQL = """
DROP TABLE IF EXISTS erasure_request;
ALTER TABLE farmer_consent DROP COLUMN IF EXISTS withdrawn_at;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
