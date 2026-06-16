"""0008 row-level security: roles, grants, policies, agronomist review guard.

Implements the roadmap's RLS model with three correctness fixes (documented in
docs/SCHEMA_DECISIONS.md §11h):

* ``tenant_iso`` is RESTRICTIVE (AND'd), not permissive.
* write access uses three command-specific policies (``FOR INSERT, UPDATE,
  DELETE`` in one policy is invalid SQL).
* ownership differs for farmer-owned vs farm-owned vs staff-only tables.

Roles: ``authenticated_role`` (RLS-subject) and ``service_role`` (BYPASSRLS for
ingest/cron). Both are granted to the current login role so the app can
``SET ROLE``.

Revision ID: 0008
Revises: 0007
Create Date: Phase 1
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tenant-scoped tables grouped by farmer-ownership semantics.
GROUP_FARMER: tuple[str, ...] = (
    "farmers", "farms", "node_sensor_readings", "irrigation_events",
    "ai_suggestions", "farmer_actions", "ai_learning_log",
    "technician_installations", "alerts_notifications", "subscriptions_billing",
    "product_performance_bi", "chat_messages", "wa_inbound_log",
)
GROUP_FARM: tuple[str, ...] = (
    "plots", "crop_seasons", "device_registry", "weather_station_readings",
    "satellite_data", "weather_forecasts", "electricity_schedule_log",
    "water_source_status", "service_maintenance",
)
GROUP_STAFF: tuple[str, ...] = (
    "component_inventory", "feature_flags", "notification_dispatch_log",
    "notification_dlq", "ingest_unmatched", "event_outbox",
    "calibration_history",
)
ALL_RLS_TABLES: tuple[str, ...] = GROUP_FARMER + GROUP_FARM + GROUP_STAFF

MATERIALIZED_VIEWS: tuple[str, ...] = (
    "node_readings_hourly", "node_readings_daily", "weather_hourly", "weather_daily",
)

_STAFF = "('admin','agronomist','service','technician')"
_WRITE = "('admin','technician')"
_TENANT = "current_setting('app.current_tenant_id', true)::uuid"
_ROLE = "current_setting('app.current_user_role', true)"
_FARMER = "current_setting('app.current_farmer_id', true)::uuid"


def _ownership(table: str) -> str:
    if table in GROUP_FARMER:
        return f"{_ROLE} IN {_STAFF} OR farmer_id = {_FARMER}"
    if table in GROUP_FARM:
        return f"{_ROLE} IN {_STAFF} OR farm_id IN (SELECT farm_id FROM farms)"
    return f"{_ROLE} IN {_STAFF}"


def _policy_sql(table: str) -> list[str]:
    own = _ownership(table)
    return [
        f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;",
        (
            f"CREATE POLICY {table}_tenant_iso ON {table} "
            f"AS RESTRICTIVE FOR ALL USING (tenant_id = {_TENANT});"
        ),
        (
            f"CREATE POLICY {table}_read ON {table} "
            f"AS PERMISSIVE FOR SELECT TO authenticated_role USING ({own});"
        ),
        (
            f"CREATE POLICY {table}_ins ON {table} "
            f"AS PERMISSIVE FOR INSERT TO authenticated_role "
            f"WITH CHECK ({_ROLE} IN {_WRITE});"
        ),
        (
            f"CREATE POLICY {table}_upd ON {table} "
            f"AS PERMISSIVE FOR UPDATE TO authenticated_role "
            f"USING ({_ROLE} IN {_WRITE}) WITH CHECK ({_ROLE} IN {_WRITE});"
        ),
        (
            f"CREATE POLICY {table}_del ON {table} "
            f"AS PERMISSIVE FOR DELETE TO authenticated_role "
            f"USING ({_ROLE} IN {_WRITE});"
        ),
    ]


_ROLES_SQL = r"""
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated_role') THEN
        CREATE ROLE authenticated_role NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        CREATE ROLE service_role NOLOGIN BYPASSRLS;
    END IF;
END
$$;

-- Let the app login role assume either role via SET ROLE.
GRANT authenticated_role TO CURRENT_USER;
GRANT service_role TO CURRENT_USER;

GRANT USAGE ON SCHEMA public TO authenticated_role, service_role;
"""

_REVIEW_GUARD_SQL = r"""
CREATE OR REPLACE FUNCTION ai_suggestions_review_guard() RETURNS TRIGGER AS $$
BEGIN
    IF current_setting('app.current_user_role', true) = 'agronomist' THEN
        IF (to_jsonb(NEW) - 'review_status' - 'reviewed_by' - 'reviewed_at' - 'review_notes')
           IS DISTINCT FROM
           (to_jsonb(OLD) - 'review_status' - 'reviewed_by' - 'reviewed_at' - 'review_notes')
        THEN
            RAISE EXCEPTION
                'agronomist may only modify review_* columns on ai_suggestions';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER ai_suggestions_review_guard_trg
    BEFORE UPDATE ON ai_suggestions
    FOR EACH ROW EXECUTE FUNCTION ai_suggestions_review_guard();
"""


def upgrade() -> None:
    op.execute(_ROLES_SQL)

    # Scoped grants: tenant tables to authenticated_role; everything to service_role.
    for table in ALL_RLS_TABLES:
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO authenticated_role;"
        )
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO service_role;")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO service_role;")
    for view in (*MATERIALIZED_VIEWS, "v_plot_latest_state"):
        op.execute(f"GRANT SELECT ON {view} TO authenticated_role, service_role;")

    for table in ALL_RLS_TABLES:
        for stmt in _policy_sql(table):
            op.execute(stmt)

    # ai_suggestions: agronomist may UPDATE (review columns only, enforced by trigger).
    op.execute(
        "CREATE POLICY ai_suggestions_review ON ai_suggestions "
        "AS PERMISSIVE FOR UPDATE TO authenticated_role "
        "USING (current_setting('app.current_user_role', true) = 'agronomist') "
        "WITH CHECK (current_setting('app.current_user_role', true) = 'agronomist');"
    )
    op.execute(_REVIEW_GUARD_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS ai_suggestions_review_guard_trg ON ai_suggestions;")
    op.execute("DROP FUNCTION IF EXISTS ai_suggestions_review_guard();")
    op.execute("DROP POLICY IF EXISTS ai_suggestions_review ON ai_suggestions;")

    for table in ALL_RLS_TABLES:
        for suffix in ("tenant_iso", "read", "ins", "upd", "del"):
            op.execute(f"DROP POLICY IF EXISTS {table}_{suffix} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    # Drop roles (DROP OWNED BY clears dependent grants first).
    op.execute(
        r"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated_role') THEN
                EXECUTE 'DROP OWNED BY authenticated_role';
                DROP ROLE authenticated_role;
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
                EXECUTE 'DROP OWNED BY service_role';
                DROP ROLE service_role;
            END IF;
        END
        $$;
        """
    )
