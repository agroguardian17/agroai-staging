"""0044 advisory-audit columns on ai_suggestions (LEGAL_COMPLIANCE_CERTIFICATE §7.3, A4.1).

The advisory audit trail must record, per advisory, the rule's confidence and the
rule/ruleset version alongside the rule id (already added in 0043) and model
version (existing). This adds the two missing columns:

- ``confidence NUMERIC(3,2)`` — the engine already computes a per-rule
  ``reasoning.confidence_score`` but dropped it on persist; now captured.
- ``rule_version TEXT`` — the KB ruleset version the advisory was generated
  under (stamped by the daily job).

The remaining §7.3 requirements (validation-gate results, immutable/append-only
storage) land in the next migration's dedicated ``advisory_audit`` table.

Nullable + additive: pre-existing rows and the non-rule LLM path keep NULLs.

Revision ID: 0044
Revises: 0043
Create Date: 2026-09-24
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0044"
down_revision: str | None = "0043"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UPGRADE_SQL = """
ALTER TABLE ai_suggestions ADD COLUMN IF NOT EXISTS confidence NUMERIC(3,2);
ALTER TABLE ai_suggestions ADD COLUMN IF NOT EXISTS rule_version TEXT;
"""

DOWNGRADE_SQL = """
ALTER TABLE ai_suggestions DROP COLUMN IF EXISTS rule_version;
ALTER TABLE ai_suggestions DROP COLUMN IF EXISTS confidence;
"""


def upgrade() -> None:
    op.execute(UPGRADE_SQL)


def downgrade() -> None:
    op.execute(DOWNGRADE_SQL)
