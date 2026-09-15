"""0015 RLS for post-0008 tenant tables — device_calibration + main_node_readings.

Finding F-008. Migration 0008 enrolled every then-existing tenant-scoped table in
row-level security, but `device_calibration` (0012) and `main_node_readings`
(0013) landed later and were never enrolled. This migration brings them under the
same RESTRICTIVE-tenant-isolation + ownership model, and grants them to the two
0008 roles (0008's `GRANT ... TO service_role` ran before these tables existed, so
they had no role grants).

Ownership model (mirrors 0008 §11h):
* `main_node_readings` — **farm-owned**: staff, or the farmer whose farm owns the
  Main Node (`farm_id IN (SELECT farm_id FROM farms)`, itself RLS-narrowed).
* `device_calibration` — **staff-only**: ops/technician config; it has `tenant_id`
  + `device_id` but no `farm_id`/`farmer_id`, so farmers get no rows.

Like the rest of the schema, this is defense-in-depth: the app connects as the
table owner (which bypasses RLS); RLS bites only a future `authenticated_role`
session that sets the `app.current_*` GUCs (SCHEMA_DECISIONS §10). Adding it
therefore does not change current app behaviour.

Reversible.

Revision ID: 0015
Revises: 0014
Create Date: 2026-09-15
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_STAFF = "('admin','agronomist','service','technician')"
_WRITE = "('admin','technician')"
_TENANT = "current_setting('app.current_tenant_id', true)::uuid"
_ROLE = "current_setting('app.current_user_role', true)"

# main_node_readings: farm-owned. device_calibration: staff-only.
_MNR_OWN = f"{_ROLE} IN {_STAFF} OR farm_id IN (SELECT farm_id FROM farms)"
_CAL_OWN = f"{_ROLE} IN {_STAFF}"


def _policy_sql(table: str, own: str) -> str:
    return f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO authenticated_role;
GRANT ALL ON {table} TO service_role;
CREATE POLICY {table}_tenant_iso ON {table}
    AS RESTRICTIVE FOR ALL USING (tenant_id = {_TENANT});
CREATE POLICY {table}_read ON {table}
    AS PERMISSIVE FOR SELECT TO authenticated_role USING ({own});
CREATE POLICY {table}_ins ON {table}
    AS PERMISSIVE FOR INSERT TO authenticated_role WITH CHECK ({_ROLE} IN {_WRITE});
CREATE POLICY {table}_upd ON {table}
    AS PERMISSIVE FOR UPDATE TO authenticated_role
    USING ({_ROLE} IN {_WRITE}) WITH CHECK ({_ROLE} IN {_WRITE});
CREATE POLICY {table}_del ON {table}
    AS PERMISSIVE FOR DELETE TO authenticated_role USING ({_ROLE} IN {_WRITE});
"""


def _downgrade_sql(table: str) -> str:
    drops = "\n".join(
        f"DROP POLICY IF EXISTS {table}_{s} ON {table};"
        for s in ("tenant_iso", "read", "ins", "upd", "del")
    )
    return f"""
{drops}
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
REVOKE ALL ON {table} FROM authenticated_role;
REVOKE ALL ON {table} FROM service_role;
"""


def upgrade() -> None:
    op.execute(_policy_sql("main_node_readings", _MNR_OWN))
    op.execute(_policy_sql("device_calibration", _CAL_OWN))


def downgrade() -> None:
    op.execute(_downgrade_sql("device_calibration"))
    op.execute(_downgrade_sql("main_node_readings"))
