"""0034 reload KB for step-2 additions (rule D07-CY-WX-001 + 2 fields).

Step 2 adds one new rule (D07-CY-WX-001) plus two new farm-brain fields
(rainfall_24h_mm, wind_gust_kmph) to the unified build. This migration reloads
the regenerated unified SQL so those additions land.

Why a truncate-and-reload (not a bare re-execute)
-------------------------------------------------
The generated SQL uses ``INSERT ... ON CONFLICT DO NOTHING`` for the reference
and child tables, but the ``kb_rules`` inserts have NO conflict clause (rule-id
uniqueness is a build-time invariant, enforced at load by the primary key). So
re-executing the file against a database that already holds the rules — which is
exactly the state after 0032 — collides on the first ``kb_rules`` row. We
therefore rebuild the ``kb_*`` REFERENCE tables from the unified file using the
same FK-safe dance as 0032, preserving the runtime/user-state tables
(``advisory_log``, ``engine_state``, ``kb_overrides``, ``kb_override_audit``).

Because 0032 and this migration read the same file at runtime, on a fresh chain
0032 already loads the step-2 content and this reload is redundant-but-clean; on
a database whose 0032 predates step-2, this reload is what applies the additions.
Either way it is a safe idempotent rebuild.

Forward-only (the KB is derived data); downgrade is a no-op.

Revision ID: 0034
Revises: 0033
Create Date: 2026-09-22
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

# Reference tables rebuilt from the unified file. Runtime/user-state tables
# (advisory_log, engine_state, kb_overrides, kb_override_audit) are preserved.
# Mirrors 0032._REFERENCE_TABLES.
_REFERENCE_TABLES = (
    "kb_rules",
    "kb_rule_fields",
    "kb_golden_tests",
    "kb_rule_references",
    "kb_rule_dependencies",
    "kb_duplication_members",
    "kb_duplication_groups",
    "kb_precedence",
    "kb_rule_categories",
    "kb_farm_brain_fields",
    "kb_domains",
    "kb_stages",
    "kb_source_classes",
    "kb_source_tiers",
    "kb_open_items",
)


def upgrade() -> None:
    if not _SQL_PATH.exists():
        raise RuntimeError(f"Unified ginger KB SQL not found at {_SQL_PATH}.")
    sql = _SQL_PATH.read_text(encoding="utf-8")
    # Strip the file's own transaction wrapper so the whole reload is atomic
    # inside Alembic's migration transaction.
    sql = re.sub(r"(?m)^\s*BEGIN;\s*$", "", sql, count=1)
    sql = re.sub(r"(?m)^\s*COMMIT;\s*$", "", sql, count=1)

    # 1. Drop the two preserved-table FKs that point into kb_rules so the
    #    reference tables can be truncated without cascading into runtime state.
    op.execute("ALTER TABLE advisory_log DROP CONSTRAINT IF EXISTS advisory_log_rule_id_fkey")
    op.execute("ALTER TABLE kb_overrides DROP CONSTRAINT IF EXISTS kb_overrides_rule_id_fkey")

    # 2. Clear the reference tables. CASCADE covers inter-kb FKs; the two
    #    preserved tables no longer reference kb_rules, so they are untouched.
    op.execute(f"TRUNCATE {', '.join(_REFERENCE_TABLES)} CASCADE")

    # 3. Reload from the unified build (idempotent DDL + fresh INSERTs).
    op.execute(sql)

    # 4. Re-add the FKs (every referenced rule_id was restored by the reload).
    op.execute(
        "ALTER TABLE advisory_log ADD CONSTRAINT advisory_log_rule_id_fkey "
        "FOREIGN KEY (rule_id) REFERENCES kb_rules(rule_id)"
    )
    op.execute(
        "ALTER TABLE kb_overrides ADD CONSTRAINT kb_overrides_rule_id_fkey "
        "FOREIGN KEY (rule_id) REFERENCES kb_rules(rule_id)"
    )


def downgrade() -> None:
    """No-op: the KB is derived data and the reload is forward-only."""
