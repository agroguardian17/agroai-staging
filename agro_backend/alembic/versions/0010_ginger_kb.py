"""0010 ginger knowledge base — load teammate's compiled SQL.

This migration adds the Ginger Advisory Engine's schema and data:
19 ``kb_*`` reference tables plus 4 runtime tables (``engine_state``,
``advisory_log``, ``kb_overrides``, ``kb_override_audit``).

The SQL file at ``agro_backend/ginger/generated/agroguardian_ginger_kb.sql``
is the compiled output of ``json_to_sql.py`` over the 13 domain JSON files
(431 rules). Their engine reads from these tables at runtime via
``ginger.engine.runtime_loader.PostgresSource``.

The SQL uses ``CREATE TABLE IF NOT EXISTS`` and ``INSERT ... ON CONFLICT DO
NOTHING`` throughout so it is idempotent — re-running the migration is safe.

Downgrade drops the 23 tables plus one trigger in FK-safe order. No cross-
schema references to our existing tables exist, so this cannot orphan any
of our data.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-03
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Located at agro_backend/ginger/generated/agroguardian_ginger_kb.sql. This
# migration file lives at agro_backend/alembic/versions/0010_ginger_kb.py, so
# the SQL is two directories up and then down into ginger/generated/.
_SQL_PATH = (
    Path(__file__).resolve().parents[2] / "ginger" / "generated" / "agroguardian_ginger_kb.sql"
)


# Tables created by the ginger SQL. Listed here (not parsed from the SQL) so
# downgrade is deterministic and self-documenting. Order matters for downgrade:
# children before parents in the FK graph.
_GINGER_TABLES: tuple[str, ...] = (
    # Runtime tables (created last in the SQL, dropped first)
    "advisory_log",
    "engine_state",
    "kb_override_audit",
    "kb_overrides",
    # Knowledge base tables (children first)
    "kb_open_items",
    "kb_duplication_members",
    "kb_duplication_groups",
    "kb_precedence",
    "kb_rule_dependencies",
    "kb_rule_references",
    "kb_rule_fields",
    "kb_golden_tests",
    "kb_rules",
    "kb_rule_categories",
    "kb_farm_brain_fields",
    "kb_domains",
    "kb_stages",
    "kb_source_classes",
    "kb_source_tiers",
)


def upgrade() -> None:
    """Load the compiled ginger knowledge base into Postgres."""
    if not _SQL_PATH.exists():
        raise RuntimeError(
            f"Ginger KB SQL not found at {_SQL_PATH}. "
            "Ensure agro_backend/ginger/generated/agroguardian_ginger_kb.sql is present."
        )
    sql = _SQL_PATH.read_text(encoding="utf-8")
    # The SQL file wraps itself in BEGIN;/COMMIT; and includes DO $$ blocks for
    # the immutable-override trigger. execute() on the connection dispatches
    # multi-statement SQL fine because Postgres supports it and asyncpg is not
    # in play here (Alembic uses the sync driver).
    op.execute(sql)


def downgrade() -> None:
    """Drop every ginger table + the immutable-override trigger."""
    # Trigger lives on kb_overrides; drop before the table to avoid dependency
    # warnings.
    op.execute("DROP TRIGGER IF EXISTS trg_reject_immutable_override ON kb_overrides")
    op.execute("DROP FUNCTION IF EXISTS reject_immutable_override() CASCADE")

    for table in _GINGER_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")

    # Views created by the SQL. Belt-and-suspenders — CASCADE on the tables
    # already drops dependent views, but explicit is clearer.
    for view in (
        "v_u_values_deduplicated",
        "v_rules_by_stage",
        "v_executable_rules",
        "v_pending_triggers",
        "v_blocking",
        "v_immutable_rules",
        "v_active_overrides",
        "v_override_review",
        "v_compliance",
        "v_rule_effectiveness",
        "v_stale_plots",
        "v_unguarded_instructions",
        "v_unintended_duplicate_actions",
        "v_plot_latest_ginger_advisories",
    ):
        op.execute(f"DROP VIEW IF EXISTS {view} CASCADE")
