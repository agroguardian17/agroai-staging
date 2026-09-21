"""0032 switch to the unified 14-domain KB build + reload (step-1 KB edits).

Background
----------
The backend previously loaded the knowledge base as two files: a 13-domain base
(migration 0010) plus a hand-extracted Domain-14 delta (migration 0018). The
authoring package (``new-docs/.../build/json_to_sql.py``) now emits a single
unified 14-domain build, which is the source of truth. This migration switches
the backend onto that unified file and, in doing so, applies the step-1 KB edits
(AGRONOMY_SIGNOFF / VJH-V1.0):

- rename farm-brain field ``cyclone_alert_active`` -> ``severe_weather_alert_active``
- ``prediction_stage`` enum -> ``[G0, G1, G2, G3, G4, G5, pre_harvest_observation]``
- ``soil_type`` enum gains ``red_loam``
- new fields: ``soil_texture_class_source``, ``phi_blocklist_hit``,
  ``blocklist_reason``, ``blocklist_source_ref``, ``farmer_alert_type``

Why a reload (not an idempotent re-run)
---------------------------------------
The generated SQL inserts with ``ON CONFLICT DO NOTHING``, so re-running it would
NOT apply renames or changed enum specs (the stale rows would linger). We instead
rebuild the ``kb_*`` REFERENCE tables from the unified file while PRESERVING the
runtime/user-state tables (``advisory_log``, ``engine_state``, ``kb_overrides``,
``kb_override_audit``). Every rule id is unchanged across the reload (same 601),
so the preserved tables' ``rule_id`` FKs re-validate.

``advisory_log`` and ``kb_overrides`` are the only preserved tables whose FK
points into ``kb_rules`` (the child ``kb_*`` tables cascade). We drop those two
FKs, TRUNCATE the reference tables, reload, and re-add the FKs.

The reload is forward-only (the KB is fully derived data, not user data), so
downgrade is a no-op.

Revision ID: 0032
Revises: 0031
Create Date: 2026-09-22
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

# Reference tables rebuilt from the unified file. Runtime/user-state tables
# (advisory_log, engine_state, kb_overrides, kb_override_audit) are preserved.
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
    """No-op: the KB is derived data and the reload is forward-only.

    The kb_* tables retain the unified content; migrations 0010/0018 remain in
    history but are superseded by this reload.
    """
