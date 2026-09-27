"""0055 reload KB for Batch 1b — layout gate/prompt split + stage-transition rule.

Resolves the two Batch-1 rules held from 0054 (agronomy confirmations 27 Sep):

* D02-LY-001 (BLOCKING, ONCE_UNTIL_RESOLVED) — the #87 flat/bad-layout-on-vertisol
  gate, now with an explicit trigger:
  ``soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout IS NOT NULL
  AND planting_layout != 'broad_ridge'``
* D02-LY-004 (NEW, yellow, ONCE_UNTIL_RESOLVED) — the unset-layout pre-planting
  prompt (split from D02-LY-001; the sheet's proposed id D02-LY-002 was already
  taken, so the next free LY id, 004, was assigned):
  ``soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout IS NULL
  AND dap IS NULL``
* D03-SB-003 (EVENT, info) — stage-transition marker, using a new derived field
  ``previous_stage`` (declared in Domain 3 schema; the mapper persists last-run
  stage): ``current_stage != previous_stage AND previous_stage IS NOT NULL``

Also adds 2 precedence edges (D02-LY-004 SEQUENCES D02-LY-001; D02-ST-002
SEQUENCES D02-LY-001). Drift + golden gates pass (243 rules / 613 golden tests).

``previous_stage`` is declared so the rule parses and gate-checks; it stays
UNKNOWN (rule dormant, safe) until the mapper persists last-run stage — a
follow-up app change.

Same FK-safe truncate-and-reload as 0048/0054. Forward-only; downgrade no-op.

Revision ID: 0055
Revises: 0054
Create Date: 2026-09-27
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0055"
down_revision: str | None = "0054"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)

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
