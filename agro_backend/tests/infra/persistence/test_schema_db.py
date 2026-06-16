"""Database integration tests for the Phase 1 schema.

These require a reachable Postgres with all migrations applied
(``alembic upgrade head``). They are skipped automatically when no database is
reachable (e.g. on the Windows dev box without Docker) and run on the Mac dev
stack. See ``TRANSFER_ROUND_2/MACBOOK_SETUP.md``.

Covered: pilot tenant seed, extensions, partition count (=13), RLS tenant
isolation + farmer ownership, and the audit-log trigger.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import Connection

SYNC_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://agro:agro@localhost:5433/agro")
PILOT_TENANT = "11111111-1111-1111-1111-111111111111"


def _db_available() -> bool:
    try:
        eng = create_engine(SYNC_URL)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
    except Exception:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres not reachable; run on the Mac dev stack after `alembic upgrade head`.",
)


@pytest.fixture()
def engine() -> Iterator[Engine]:
    eng = create_engine(SYNC_URL, future=True)
    yield eng
    eng.dispose()


def _insert_farmer(conn: Connection, tenant_id: str, full_name: str) -> str:
    """Insert a minimal valid farmer (as table owner) and return its id."""
    farmer_id = str(uuid.uuid4())
    conn.execute(
        text(
            """
            INSERT INTO farmers (
                farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                whatsapp_number, language_preference, village, taluka, district,
                state, subscription_tier, subscription_start, subscription_end,
                payment_status
            ) VALUES (
                :id, :tenant, :name, :name, '+910000000000',
                '+910000000000', 'marathi', 'v', 't', 'd',
                'Maharashtra', 'basic', '2025-06-01', '2026-06-01',
                'paid'
            )
            """
        ),
        {"id": farmer_id, "tenant": tenant_id, "name": full_name},
    )
    return farmer_id


def _insert_farm_and_plot(conn: Connection, tenant_id: str, farmer_id: str, plot_id: str) -> str:
    farm_id = str(uuid.uuid4())
    conn.execute(
        text(
            """
            INSERT INTO farms (
                farm_id, tenant_id, farmer_id, total_area_acre,
                gps_lat_center, gps_lng_center, soil_type,
                water_source_primary, irrigation_type, electricity_source
            ) VALUES (
                :farm, :tenant, :farmer, 3.5, 19.9, 75.7, 'black',
                'well', 'drip', 'grid'
            )
            """
        ),
        {"farm": farm_id, "tenant": tenant_id, "farmer": farmer_id},
    )
    conn.execute(
        text(
            """
            INSERT INTO plots (
                plot_id, tenant_id, farm_id, plot_number, area_acre,
                gps_lat, gps_lng, irrigation_valve_id
            ) VALUES (
                :plot, :tenant, :farm, 1, 1.0, 19.9, 75.7, 'V1'
            )
            """
        ),
        {"plot": plot_id, "tenant": tenant_id, "farm": farm_id},
    )
    return farm_id


def test_pilot_tenant_seeded(engine: Engine) -> None:
    with engine.connect() as conn:
        tier = conn.execute(
            text("SELECT tier FROM tenants WHERE id = :id"), {"id": PILOT_TENANT}
        ).scalar_one()
    assert tier == "pilot_internal"


def test_core_extensions_present(engine: Engine) -> None:
    with engine.connect() as conn:
        names = {r[0] for r in conn.execute(text("SELECT extname FROM pg_extension")).all()}
    # uuid-ossp / postgis / pgcrypto are required; vector is best-effort.
    assert {"uuid-ossp", "postgis", "pgcrypto"}.issubset(names)


def test_node_readings_has_13_partitions(engine: Engine) -> None:
    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT count(*) FROM pg_inherits "
                "WHERE inhparent = 'node_sensor_readings'::regclass"
            )
        ).scalar_one()
    assert count == 13


def test_plots_data_tier_trigger(engine: Engine) -> None:
    """Inserting a plot with NULL node_id yields data_tier='satellite_only'."""
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            farmer_id = _insert_farmer(conn, PILOT_TENANT, "trigger test")
            plot_id = f"PLOT_TRG_{uuid.uuid4().hex[:8]}"
            _insert_farm_and_plot(conn, PILOT_TENANT, farmer_id, plot_id)
            tier = conn.execute(
                text("SELECT data_tier FROM plots WHERE plot_id = :p"), {"p": plot_id}
            ).scalar_one()
            assert tier == "satellite_only"
        finally:
            trans.rollback()


def test_rls_tenant_and_owner_isolation(engine: Engine) -> None:
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            farmer_a = _insert_farmer(conn, PILOT_TENANT, "Farmer A")
            plot_a = f"PLOT_A_{uuid.uuid4().hex[:8]}"
            _insert_farm_and_plot(conn, PILOT_TENANT, farmer_a, plot_a)

            # Act as farmer A within the pilot tenant.
            conn.execute(text("SET LOCAL ROLE authenticated_role"))
            conn.execute(text(f"SET LOCAL app.current_tenant_id = '{PILOT_TENANT}'"))
            conn.execute(text("SET LOCAL app.current_user_role = 'farmer'"))
            conn.execute(text(f"SET LOCAL app.current_farmer_id = '{farmer_a}'"))

            visible = conn.execute(
                text("SELECT plot_id FROM plots WHERE plot_id = :p"), {"p": plot_a}
            ).all()
            assert len(visible) == 1

            # Switch to a different tenant -> the row disappears.
            other_tenant = str(uuid.uuid4())
            conn.execute(text(f"SET LOCAL app.current_tenant_id = '{other_tenant}'"))
            hidden = conn.execute(
                text("SELECT plot_id FROM plots WHERE plot_id = :p"), {"p": plot_a}
            ).all()
            assert len(hidden) == 0
        finally:
            conn.execute(text("RESET ROLE"))
            trans.rollback()


def test_audit_log_records_farmer_update(engine: Engine) -> None:
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            actor = str(uuid.uuid4())
            conn.execute(text("SET LOCAL app.current_user_role = 'admin'"))
            conn.execute(text(f"SET LOCAL app.current_user_id = '{actor}'"))

            farmer_id = _insert_farmer(conn, PILOT_TENANT, "Before")
            conn.execute(
                text("UPDATE farmers SET full_name = 'After' WHERE farmer_id = :id"),
                {"id": farmer_id},
            )

            row = conn.execute(
                text(
                    "SELECT operation, new_data ->> 'full_name' AS name "
                    "FROM audit_log "
                    "WHERE table_name = 'farmers' AND operation = 'UPDATE' "
                    "  AND new_data ->> 'farmer_id' = :id "
                    "ORDER BY at DESC LIMIT 1"
                ),
                {"id": farmer_id},
            ).one()
            assert row.operation == "UPDATE"
            assert row.name == "After"
        finally:
            trans.rollback()


@pytest.mark.skipif(
    os.getenv("AGRO_RUN_DESTRUCTIVE") != "1",
    reason="Destructive migration round-trip; set AGRO_RUN_DESTRUCTIVE=1 to run.",
)
def test_migration_roundtrip() -> None:
    """upgrade head -> downgrade base -> upgrade head against the configured DB."""
    from alembic import command
    from alembic.config import Config

    cfg = Config("alembic.ini")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
