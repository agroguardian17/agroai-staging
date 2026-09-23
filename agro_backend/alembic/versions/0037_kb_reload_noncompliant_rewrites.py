"""0037 reload KB for the 8 NON_COMPLIANT rule rewrites (agronomy handoff §2.2).

Phase 1 item 4a. The agronomy team's compliance review returned 8 rules as
NON_COMPLIANT with specific rewrites (AGRONOMY_COMPLIANCE_v1 §2.2); all are now
rewritten in the JSON source and downgraded to CONDITIONAL (reviewed):

- D01-PH-004, D08-EU-002: fixed 12.5% yield penalty removed (u_value nulled),
  stage/earthing warning kept.
- D08-LY-001: local broad-ridge uplift claim kept, scoped to heavy black soil
  under drip (the trigger already gates soil+drip).
- D08-WD-001: blanket herbicide block scoped to non-selective/unregistered;
  ginger-labelled herbicides permitted at label timing.
- D03-WL-003, D07-CY-001: dropped the unsupported "more severe than monsoon"
  prose; retagged AGRO_GUARDIAN_CUSTOM; trigger kept.
- D14-SR-002: -4 dB SAR threshold flagged calibration-pending; kept.
- D03-DS-001: trigger now gates on soil_texture_class == 'heavy' so the
  heavy-soil drip prescription no longer misfires on light/medium soils
  (the one trigger change; wave file + golden tests updated in lock-step).

This reloads the regenerated unified SQL so the rewrites land. Same FK-safe
truncate-and-reload as 0034/0036 (kb_rules inserts have no ON CONFLICT, so a
bare re-execute would collide); runtime/user-state tables are preserved.

Forward-only (the KB is derived data); downgrade is a no-op.

Revision ID: 0037
Revises: 0036
Create Date: 2026-09-23
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

# Reference tables rebuilt from the unified file (mirrors 0034/0036). Runtime/
# user-state tables (advisory_log, engine_state, kb_overrides, kb_override_audit)
# are preserved.
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
    sql = re.sub(r"(?m)^\s*BEGIN;\s*$", "", sql, count=1)
    sql = re.sub(r"(?m)^\s*COMMIT;\s*$", "", sql, count=1)

    op.execute("ALTER TABLE advisory_log DROP CONSTRAINT IF EXISTS advisory_log_rule_id_fkey")
    op.execute("ALTER TABLE kb_overrides DROP CONSTRAINT IF EXISTS kb_overrides_rule_id_fkey")
    op.execute(f"TRUNCATE {', '.join(_REFERENCE_TABLES)} CASCADE")
    op.execute(sql)
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
