"""0059 reload KB for Batches 3-9 — the remaining 36 firing-intent rules (dormant-safe).

Wires the final 36 trigger-less firing-intent rules from agronomy Batches 3-9
(28 Sep), completing all 48. Every rule is dormant until its field(s) get a data
source (farmer_app / ops / derived / engine-composer flag), so none fires yet —
safe by three-valued logic.

Rules by domain: D04 (BI-002, DG-002, SN-001), D05 (CH-002, IP-001, PC-001,
SC-002), D10 (ACT-002, APP-001, CROP-002, REG-001), D11 (GA-001/002/003,
RC-002/003, SC-001/002/003), D09 (DR-001/002/003, PW-001, SL-003, ST-002,
YD-002/003/004), D12 (AL-001/002, IMG-001, LOG-002, VOC-002), D01 (PH-005),
D03 (SB-004, WS-002).

Declares 52 new farm-brain fields across the domain schemas; adds 6 precedence
edges (D04-SN-001→D04-NS-003, D05-CH-002→D10-REG-001, D08-WD-001 BUNDLES
D10-REG-001, D09-YD-002/004→D11-GA-001, D11-GA-001→D11-GA-003). Triggers live in
a new authoring wave (triggers_wave6_firing_intent.py). Drift + golden gates pass
(285 rules / 698 golden tests).

Deferred (not expressible as one edge): D03-SB-004 SUPPRESSES D03-MN-* (a wildcard
over all VWC rules) — needs enumerated targets or app-level handling.

Same FK-safe truncate-and-reload as 0048/0058. Forward-only; downgrade no-op.

Revision ID: 0059
Revises: 0058
Create Date: 2026-09-29
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0059"
down_revision: str | None = "0058"
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
