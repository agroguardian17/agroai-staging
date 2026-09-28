"""0058 reload KB for Batch 2 — D06 disease guardrails (5 rules, dormant-safe).

Wires five previously trigger-less D06 rules from agronomy Batch 2 (28 Sep),
all dormant until their new fields get a data source (farmer app / ops / engine
composer flag):

* D06-CH-002 (SILENT_GUARD, info) fungicide_option_about_to_be_shown IS TRUE
* D06-FH-001 (EVENT, yellow)      harvest_complete IS TRUE
* D06-FH-002 (WINDOW, red)        soft_rot_confirmed_in_cluster IS TRUE
* D06-ST-001 (WINDOW, yellow)     seed_treatment_planned IS TRUE AND dap < 0
* D06-ST-002 (WINDOW, yellow)     bio == chem seed-treatment date (same day)

Declares 6 new farm-brain fields (fungicide_option_about_to_be_shown,
harvest_complete, soft_rot_confirmed_in_cluster, seed_treatment_planned,
biological_seed_treatment_date, chemical_seed_treatment_date) and adds 3
precedence edges (D06-FH-001 SEQUENCES D06-BW-001; D06-FH-002 BUNDLES D06-CH-002;
D06-ST-001 SEQUENCES D06-ST-002). Batch 2 also re-set three severities per
agronomy (D06-CH-002 -> info, D06-FH-002 -> red, D06-ST-002 -> yellow).

(D06-BW-001 was already wired in 0057.) Drift + golden gates pass (249 rules /
626 golden tests).

Same FK-safe truncate-and-reload as 0048/0057. Forward-only; downgrade no-op.

Revision ID: 0058
Revises: 0057
Create Date: 2026-09-28
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0058"
down_revision: str | None = "0057"
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
