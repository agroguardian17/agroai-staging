"""0057 reload KB for v1.2 cluster-2 (dormant-safe) — D01-PW-001 + D06-BW-001.

Applies the v1.2 deployed-aligned pack's cluster-2 changes that are safe to land
now (agronomy 28 Sep), per the "dormant-safe" decision:

* D01-PW-001 (yellow, EVENT) — rewritten from the unplanted-window BLOCKING rule
  to a late-planting warning: ``planting_doy > 158`` (7 June; the DSL has no DATE
  literal). ``planting_doy`` is a new mapper-derived field (day-of-year of
  sowing_date) — functional immediately.
* D06-BW-001 (red, ONCE_UNTIL_RESOLVED) — bacterial-wilt 5-year rotation gate
  wired: ``field_history_wilt IS TRUE AND years_since_last_wilt < 5``.
  ``years_since_last_wilt`` is a new farmer-app int (companion to the existing
  field_history_wilt boolean); the rule stays dormant (UNKNOWN) until that
  capture lands.

Also remaps two lookup ``source_tier`` values (0056) separately. Drift + golden
gates pass (244 rules / 614 golden tests).

Held from this batch (need agronomy input, flagged): D04-MC-005 (ZnSO4) — the
deployed mapper emits agro_climatic_zone as marathwada_central/western/eastern,
not 'western_scarcity', so the zone-vocab mapping must be confirmed first; and
D04-NS-003 / D08-WD-001 keep their deployed triggers (replacing them with
source-less versions would regress live coverage).

Same FK-safe truncate-and-reload as 0048/0054/0055. Forward-only; downgrade no-op.

Revision ID: 0057
Revises: 0056
Create Date: 2026-09-28
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0057"
down_revision: str | None = "0056"
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
