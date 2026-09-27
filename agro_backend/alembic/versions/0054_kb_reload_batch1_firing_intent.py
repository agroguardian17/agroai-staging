"""0054 reload KB for Batch 1 firing-intent rules (3 triggers wired).

Wires three previously trigger-less "ready" rules from the firing-intent sheet
(agronomy confirmations, 27 Sep 2026 — no new fields, existing declared fields
only):

* D01-PH-004  (EVENT, yellow)  flowering_observed IS TRUE AND dap >= 150
* D02-DR-004  (WINDOW, yellow) percolation_class == 'poor' AND
                              planting_layout == 'broad_ridge' AND dap < 15
* D02-ST-002  (ONCE_UNTIL_RESOLVED, yellow) dap IS NULL AND
                              percolation_time_hours IS NULL

Each gained a ``trigger.expr`` + golden tests in the domain JSON, a matching
``authoring/triggers_wave*.py`` entry, and a ``notification_policy.DELIVERY``
class; the drift + golden gates pass (240 rules / 606 golden tests). This
migration reloads the regenerated ``agroguardian_ginger_kb.sql`` so the new
triggers + delivery classes land in the ``kb_*`` tables.

Same FK-safe truncate-and-reload as 0048. Forward-only; downgrade no-op (the KB
is derived data — roll back by reloading a prior build).

Revision ID: 0054
Revises: 0053
Create Date: 2026-09-27
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0054"
down_revision: str | None = "0053"
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
