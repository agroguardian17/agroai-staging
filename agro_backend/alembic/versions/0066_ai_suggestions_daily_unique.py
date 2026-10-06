"""0066 daily-advisory idempotency — partial unique index on ai_suggestions.

The daily ginger job writes one ``ai_suggestions`` row per fired rule, but had
no idempotency key: a re-run, or the engine's notification-policy replay after a
KB-version (STATE_VERSION) reset, inserted duplicate rows for the same
(plot, run-day, rule). This adds a partial UNIQUE index so the write (now
``ON CONFLICT DO NOTHING``) is idempotent, matching the guarantee the engine's
own ``advisory_log`` already has via its ``(plot_id, day, rule_id)`` PK.

Non-destructive by design. Existing duplicate rows are NOT removed: their
``advisory_audit`` children are append-only (an immutable BEFORE UPDATE OR DELETE
trigger, migration 0045) and other tables FK to ``ai_suggestions`` with no
cascade, so historical duplicates cannot be deleted or repointed. Instead the
index carries a forward cutoff (``generated_at >= start of tomorrow``) so it
only governs future run-days and never trips over the dirty history. Scope is
the ginger-engine daily rows only (``ai_model_version = 'ginger-engine/v1.0'``
with a non-null ``rule_id``); alert rows (a different model tag) are excluded and
keep their current behaviour.

Revision ID: 0066
Revises: 0065
Create Date: 2026-10-07
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0066"
down_revision: str | None = "0065"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# ``date_trunc('day', now()) + 1 day`` is strictly greater than every existing
# daily row's ``generated_at`` (which is UTC-midnight of an IST run-day) and <=
# the next run-day's value, so the partial index excludes all current rows
# (dirty or not) and covers every future daily write. ``IF NOT EXISTS`` keeps
# the migration re-runnable.
UPGRADE_SQL = r"""
DO $$
DECLARE
    cutoff timestamptz := date_trunc('day', now()) + interval '1 day';
BEGIN
    EXECUTE format(
        'CREATE UNIQUE INDEX IF NOT EXISTS ai_suggestions_ginger_daily_uniq '
        'ON ai_suggestions (plot_id, (generated_at::date), rule_id) '
        'WHERE ai_model_version = %L AND rule_id IS NOT NULL AND generated_at >= %L',
        'ginger-engine/v1.0', cutoff
    );
END
$$;
"""

DOWNGRADE_SQL = r"""
DROP INDEX IF EXISTS ai_suggestions_ginger_daily_uniq;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
