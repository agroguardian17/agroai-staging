"""0043 ai_suggestions.rule_id — link a delivered advisory to its KB rule.

D12 build, PR 4. The advisory-QA workflow (D12_QA_WORKFLOW §5.1) classifies each
delivered advisory as a true/false positive *per rule*, and the weekly digest
aggregates by ``rule_id``. The delivered advisory lives in ``ai_suggestions``
(farmer/plot/time) but did not record which KB rule produced it — the daily job
renders the engine message to text and drops ``msg.rule_id``. This adds the
column so ``classify_advisory`` can read plot/farmer/rule/fired_at from one row.

Nullable + additive: rows written before this change keep ``rule_id`` NULL (they
predate rule-level QA). The daily job populates it going forward.

Revision ID: 0043
Revises: 0042
Create Date: 2026-09-23
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0043"
down_revision: str | None = "0042"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE ai_suggestions ADD COLUMN IF NOT EXISTS rule_id TEXT;
CREATE INDEX IF NOT EXISTS ai_suggestions_rule_idx
    ON ai_suggestions (rule_id) WHERE rule_id IS NOT NULL;
"""

DOWNGRADE_SQL = """
DROP INDEX IF EXISTS ai_suggestions_rule_idx;
ALTER TABLE ai_suggestions DROP COLUMN IF EXISTS rule_id;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
