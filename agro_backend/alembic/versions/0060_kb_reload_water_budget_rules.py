"""0060 reload KB for the water-budget engine rules (9 net-new, dormant).

Adds the water-budget rule layer, now that live single-pipe flow lands in
node_sensor_readings.water_flow_lpm (blocker resolved). Nine net-new rules in
Domain 3 (new categories WB + ST):

* D03-WB-001 moderate deficit -> irrigate (WINDOW, yellow)
* D03-WB-002 severe stage deficit -> RED (WINDOW, red)
* D03-WB-003 over-irrigation warning (EVENT, yellow)
* D03-WB-004 under-irrigation correction (EVENT, yellow)
* D03-WB-005 daily cumulative silent D11 feeder (SILENT_GUARD, info)
* D03-WB-006 flow-sensor gap alert (EVENT, red)
* D03-WB-007 season over-irrigation flag (ONCE_UNTIL_RESOLVED, yellow)
* D03-WB-008 pre-planting geometry gate (ONCE_UNTIL_RESOLVED, blocking)
* D03-ST-001 water-deficit stress log -> D11 factor-7 (SILENT_GUARD, info)

DORMANT by design: the triggers fire on DERIVED ratio/dose fields
(stage_water_deficit_ratio, per_plant_dose_l_last_event, variety_min/max_per_event_l,
per_plant_cumulative_vs_lifecycle_ratio, vwc_status, days_since_last_*,
planting_geometry_incomplete, ...) that a compute_water_budget() layer must
produce from water_flow_lpm + planting geometry + variety_stage_water_target.
Until that engine + geometry capture exist, the derived fields are UNKNOWN and
these rules do not fire (three-valued logic) - safe.

v1.2 discipline applied: no confidence-gate DSL (three-valued logic handles
absence), no FEEDS/push/urgency. The DSL has no arithmetic, so thresholds are
expressed as pre-computed ratio fields compared to constants. 13 new farm-brain
fields declared; 5 precedence edges added (D03-MN-002 SUPPRESSES WB-001/002/004;
WB-002 ESCALATES WB-001; WB-001 BUNDLES D03-MN-004). Triggers in a new authoring
wave (triggers_wave7_water_budget.py). Drift + golden gates pass (294 rules /
716 golden tests).

Deferred: D03-WB-006 SUSPENDS the flow-dependent WB rules and SUPPRESSES D03-MN-*
are not single formal edges (operational scope) — handled at the compute layer.

Same FK-safe truncate-and-reload as 0048/0059. Forward-only; downgrade no-op.

Revision ID: 0060
Revises: 0059
Create Date: 2026-09-30
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0060"
down_revision: str | None = "0059"
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
