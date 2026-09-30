"""0063 reload KB for the 3 final-decision rules (Kuldip, 30 Sep).

Wires the buildable subset of Kuldip's "KB 7 Final Decisions":

* D04-MC-005 basal ZnSO4, marathwada_central pre-planting default (item 1;
  ONCE_UNTIL_RESOLVED, info) — fires until a basal dose is recorded.
* D06-BW-004 bacterial-wilt history-capture prompt (item 4; ONCE_UNTIL_RESOLVED,
  yellow) — his proposed D06-BW-002/003 ids were already taken, so authored as
  the next free BW id, 004. SEQUENCES D06-BW-001.
* item 5 precedence: D03-SB-004 SUPPRESSES D03-MN-002 (the only D03-MN rule that
  reads soil_moisture_vwc). D03-MN-004 held — it is a rain-gap dry-spell rule,
  not a VWC rule, so suppressing it is pending Kuldip's re-confirmation.

Two new farm-brain fields declared (Domain 4): plot_status
(enum pre_planting/growing/post_harvest, derived in the mapper from season
dates) and basal_znso4_applied_kg_acre. agro_climatic_zone + field_history_wilt
already declared and mapper-emitted.

Items 2/3/6/7 were "keep deployed" confirmations — no KB change. Drift + golden
gates pass (296 rules / 723 golden tests). Same FK-safe truncate-and-reload as
0048/0059/0060. Forward-only; downgrade no-op.

Revision ID: 0063
Revises: 0061
Create Date: 2026-10-01
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0063"
down_revision: str | None = "0061"
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
