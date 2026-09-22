"""0036 reload KB for the D05 blocklist-detection rule (D05-CH-008).

Step 3-followup: authors the runtime counterpart to the D05-CH-001 emission
guard. The farm-brain mapper already raises ``phi_blocklist_hit`` (and the
``blocklist_reason`` / ``blocklist_source_ref`` / ``farmer_alert_type`` trace
fields) when a recorded spray is on the crop input blocklist, but no KB rule
consumed them. ``D05-CH-008`` (severity red, ONCE_UNTIL_RESOLVED) fires on
``phi_blocklist_hit IS TRUE`` and warns the farmer that no valid pre-harvest
interval exists for a blocklisted input. This migration reloads the regenerated
unified SQL so the new rule + its golden tests + its reference rows land.

Why a truncate-and-reload (not a bare re-execute)
-------------------------------------------------
The generated SQL uses ``INSERT ... ON CONFLICT DO NOTHING`` for the reference
and child tables, but the ``kb_rules`` inserts have NO conflict clause, so
re-executing the file against a database that already holds the rules collides
on the first ``kb_rules`` row. We therefore rebuild the ``kb_*`` reference
tables from the unified file using the same FK-safe dance as 0032/0034,
preserving the runtime/user-state tables (``advisory_log``, ``engine_state``,
``kb_overrides``, ``kb_override_audit``). ``kb_rule_references`` already has its
structured shape from 0035, so — unlike 0035 — it is truncated in place here
rather than dropped.

Forward-only (the KB is derived data); downgrade is a no-op.

Revision ID: 0036
Revises: 0035
Create Date: 2026-09-22
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

# Reference tables rebuilt from the unified file. Runtime/user-state tables
# (advisory_log, engine_state, kb_overrides, kb_override_audit) are preserved.
# Mirrors 0032/0034._REFERENCE_TABLES (kb_rule_references is back in the set now
# that 0035 has given it its structured shape).
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
