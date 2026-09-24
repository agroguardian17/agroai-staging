"""0048 reload KB for VNMKV B1.5 — D02-LY-001 CONDITIONAL → BLOCKING.

VNMKV compliance certificate §8.1: flat-layout planting on Marathwada vertisol
produced 35–50% yield loss + 3× soft-rot vs BBF, so D02-LY-001
(vertisol + drip + not-broad-ridge) is certified to move from CONDITIONAL to
BLOCKING. In this KB, "blocking" is a ``severity`` enum value (SQL CHECK
severity IN info/yellow/red/blocking), so the JSON rule's ``severity`` went
red → blocking; this reloads the regenerated SQL so the change lands.

Same FK-safe truncate-and-reload as 0034/0036/0037 (kb_rules inserts have no
ON CONFLICT); runtime/user-state tables preserved. Forward-only; downgrade no-op.

Revision ID: 0048
Revises: 0047
Create Date: 2026-09-24
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0048"
down_revision: str | None = "0047"
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
