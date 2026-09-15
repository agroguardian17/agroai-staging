"""0014 advisory_status — Round 13 advisory-subscriber state machine.

The Round 13 advisory subscriber (``app/jobs/advisory_subscriber.py``) consumes
``alert.created`` events (Postgres ``LISTEN agro_events``) and drives
``compose_advisory`` to produce one Marathi advisory per alert. Because
``pg_notify`` is fire-and-forget (an event published while no listener is
connected is lost) and can redeliver, each alert carries a *compose* state
machine so processing is idempotent and recoverable:

    pending → in_flight → { composed | skipped | failed_transient | failed_permanent }
                    ↘ (transient) → pending (with backoff)
                    ↘ (reaper: stale in_flight) → pending

This is a distinct axis from the existing ``dispatch_status`` (the WhatsApp
*send* state, migration 0002). Columns added here:

* ``advisory_status``     — the compose state (CHECK-constrained).
* ``advisory_attempts``   — transient-failure counter (drives backoff).
* ``advisory_next_retry_at`` — earliest time a pending row is due again.
* ``advisory_claimed_at`` — when the row entered ``in_flight`` (reaper input).
* ``advisory_last_error`` — last error / skip reason for ops triage.

Idempotent (``ADD COLUMN IF NOT EXISTS``). Reversible.

Revision ID: 0014
Revises: 0013
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE alerts_notifications
    ADD COLUMN IF NOT EXISTS advisory_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (advisory_status IN (
            'pending', 'in_flight', 'composed', 'skipped',
            'failed_transient', 'failed_permanent'
        )),
    ADD COLUMN IF NOT EXISTS advisory_attempts     INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS advisory_next_retry_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS advisory_claimed_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS advisory_last_error   TEXT;

-- The subscriber's reconciliation sweep scans for due pending rows; a partial
-- index keeps that scan cheap as the alerts table grows.
CREATE INDEX IF NOT EXISTS alerts_notifications_advisory_pending
    ON alerts_notifications (advisory_next_retry_at, triggered_at)
    WHERE advisory_status = 'pending';
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS alerts_notifications_advisory_pending;
ALTER TABLE alerts_notifications
    DROP COLUMN IF EXISTS advisory_last_error,
    DROP COLUMN IF EXISTS advisory_claimed_at,
    DROP COLUMN IF EXISTS advisory_next_retry_at,
    DROP COLUMN IF EXISTS advisory_attempts,
    DROP COLUMN IF EXISTS advisory_status;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
