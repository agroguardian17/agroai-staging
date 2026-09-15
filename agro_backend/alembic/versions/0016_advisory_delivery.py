"""0016 advisory delivery — Round 14 WhatsApp delivery state machine.

Round 13 (migration 0014) added a *compose* state machine on
``alerts_notifications`` (``advisory_status``) that ends at ``composed`` — a
Marathi advisory row written to ``ai_suggestions``. Round 14 adds the next
step: **delivering** that advisory to the farmer over WhatsApp.

Delivery is its own retryable state machine, on ``ai_suggestions`` this time,
mirroring the 0014 shape. It is a distinct axis from the base schema's
``whatsapp_sent`` / ``whatsapp_sent_at`` flags (0001) — those remain the simple
"was it ever sent" markers, which this migration leaves untouched and the
delivery use case sets on success.

    pending → in_flight → { sent | skipped | failed_transient | failed_permanent }
                    ↘ (transient: rate-limit / 5xx / network) → pending (backoff)
                    ↘ (reaper: stale in_flight) → pending

Columns added:

* ``delivery_status``          — CHECK-constrained delivery state.
* ``delivery_attempts``        — transient-failure counter (drives backoff).
* ``delivery_next_retry_at``   — earliest time a pending row is due again.
* ``delivery_claimed_at``      — when the row entered ``in_flight`` (reaper input).
* ``delivery_last_error``      — last provider error / skip reason for ops triage.
* ``delivery_provider_message_id`` — Meta's message id, for webhook receipt
  correlation (Round 14 PR B).

Idempotent (``ADD COLUMN IF NOT EXISTS``). Reversible.

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


UPGRADE_SQL = r"""
ALTER TABLE ai_suggestions
    ADD COLUMN IF NOT EXISTS delivery_status TEXT NOT NULL DEFAULT 'pending'
        CHECK (delivery_status IN (
            'pending', 'in_flight', 'sent', 'skipped',
            'failed_transient', 'failed_permanent'
        )),
    ADD COLUMN IF NOT EXISTS delivery_attempts          INTEGER     NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS delivery_next_retry_at     TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivery_claimed_at        TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS delivery_last_error        TEXT,
    ADD COLUMN IF NOT EXISTS delivery_provider_message_id TEXT;

-- The delivery reconciler scans for due pending rows; a partial index keeps
-- that scan cheap as ai_suggestions grows.
CREATE INDEX IF NOT EXISTS ai_suggestions_delivery_pending
    ON ai_suggestions (delivery_next_retry_at, generated_at)
    WHERE delivery_status = 'pending';
"""


DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS ai_suggestions_delivery_pending;
ALTER TABLE ai_suggestions
    DROP COLUMN IF EXISTS delivery_provider_message_id,
    DROP COLUMN IF EXISTS delivery_last_error,
    DROP COLUMN IF EXISTS delivery_claimed_at,
    DROP COLUMN IF EXISTS delivery_next_retry_at,
    DROP COLUMN IF EXISTS delivery_attempts,
    DROP COLUMN IF EXISTS delivery_status;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
