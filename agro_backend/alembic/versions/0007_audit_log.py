"""0007 audit log: trigger function + triggers on master tables.

``audit_trigger_fn`` reads ``app.current_user_role`` / ``app.current_user_id``
session GUCs, captures TG_OP + OLD/NEW as JSONB, and writes to ``audit_log``.
The row's primary-key column name is passed as a trigger argument so a single
generic function serves tables with differently-named PKs.

Master tables (roadmap Part 8 #8): farmers, farms, plots, crop_seasons,
device_registry, subscriptions_billing, users, tenants, calibration_history.

Revision ID: 0007
Revises: 0006
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (table_name, primary_key_column)
_AUDITED: tuple[tuple[str, str], ...] = (
    ("farmers", "farmer_id"),
    ("farms", "farm_id"),
    ("plots", "plot_id"),
    ("crop_seasons", "season_id"),
    ("device_registry", "device_id"),
    ("subscriptions_billing", "subscription_id"),
    ("users", "user_id"),
    ("tenants", "id"),
    ("calibration_history", "id"),
)


_FN_SQL = r"""
CREATE OR REPLACE FUNCTION audit_trigger_fn() RETURNS TRIGGER AS $$
DECLARE
    v_role   TEXT  := current_setting('app.current_user_role', true);
    v_user   TEXT  := current_setting('app.current_user_id', true);
    v_pk_col TEXT  := TG_ARGV[0];
    v_old    JSONB;
    v_new    JSONB;
    v_rowpk  JSONB;
BEGIN
    IF TG_OP = 'DELETE' THEN
        v_old   := to_jsonb(OLD);
        v_new   := NULL;
        v_rowpk := jsonb_build_object(v_pk_col, v_old -> v_pk_col);
    ELSIF TG_OP = 'INSERT' THEN
        v_old   := NULL;
        v_new   := to_jsonb(NEW);
        v_rowpk := jsonb_build_object(v_pk_col, v_new -> v_pk_col);
    ELSE
        v_old   := to_jsonb(OLD);
        v_new   := to_jsonb(NEW);
        v_rowpk := jsonb_build_object(v_pk_col, v_new -> v_pk_col);
    END IF;

    INSERT INTO audit_log
        (actor_type, actor_id, table_name, row_pk, operation, old_data, new_data)
    VALUES
        (COALESCE(v_role, 'system'), v_user, TG_TABLE_NAME, v_rowpk, TG_OP, v_old, v_new);

    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade() -> None:
    op.execute(_FN_SQL)
    for table, pk in _AUDITED:
        op.execute(
            f"CREATE TRIGGER {table}_audit_trg "
            f"AFTER INSERT OR UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION audit_trigger_fn('{pk}');"
        )


def downgrade() -> None:
    for table, _pk in _AUDITED:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_audit_trg ON {table};")
    op.execute("DROP FUNCTION IF EXISTS audit_trigger_fn();")
