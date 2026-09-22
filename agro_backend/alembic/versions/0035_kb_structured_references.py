"""0035 structured rule references — kb_rule_references gains ref_kind / institution / source_tier.

Step 3 (B7): the free-text ``kb_rule_references.reference`` is enriched with an
evidence-hierarchy view. Three columns are added:

- ``ref_kind``    — 'external' evidence vs 'internal' cross-reference
- ``institution`` — best-effort curated source name; NULL when not confident
- ``source_tier`` — the rule's tier (A/B/C) inherited onto its external refs;
  NULL for internal cross-references

The column ``reference`` is unchanged and keeps the full original citation
(lossless), so no information is dropped.

Why a drop-and-reload
---------------------
``kb_rule_references`` changes shape, and the generated SQL creates it with
``CREATE TABLE IF NOT EXISTS`` — a no-op against the existing 2-column table. So
the table is dropped first (nothing references it), then the standard FK-safe KB
reload (same dance as 0032/0034) recreates it in the new shape and repopulates
every reference table. Runtime/user-state tables (advisory_log, engine_state,
kb_overrides, kb_override_audit) are preserved.

Forward-only (the KB is derived data); downgrade is a no-op.

Revision ID: 0035
Revises: 0034
Create Date: 2026-09-22
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

# Reference tables rebuilt from the unified file (mirrors 0032/0034). Runtime/
# user-state tables are preserved. kb_rule_references is DROPPED separately below
# because its shape changes, so it is excluded from the TRUNCATE set.
_REFERENCE_TABLES = (
    "kb_rules",
    "kb_rule_fields",
    "kb_golden_tests",
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
    sql = re.sub(r"(?m)^\s*BEGIN;\s*$", "", sql, count=1)
    sql = re.sub(r"(?m)^\s*COMMIT;\s*$", "", sql, count=1)

    # 1. Drop the two preserved-table FKs into kb_rules so the reference tables
    #    can be truncated without cascading into runtime state.
    op.execute("ALTER TABLE advisory_log DROP CONSTRAINT IF EXISTS advisory_log_rule_id_fkey")
    op.execute("ALTER TABLE kb_overrides DROP CONSTRAINT IF EXISTS kb_overrides_rule_id_fkey")

    # 2. kb_rule_references changes shape; CREATE TABLE IF NOT EXISTS in the reload
    #    cannot alter the existing 2-column table, so drop it (no dependents) and
    #    let the reload recreate it with ref_kind / institution / source_tier.
    op.execute("DROP TABLE IF EXISTS kb_rule_references CASCADE")

    # 3. Clear the remaining reference tables (kb_rule_references no longer exists).
    op.execute(f"TRUNCATE {', '.join(_REFERENCE_TABLES)} CASCADE")

    # 4. Reload from the unified build (recreates kb_rule_references + repopulates).
    op.execute(sql)

    # 5. Re-add the FKs (every referenced rule_id was restored by the reload).
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
