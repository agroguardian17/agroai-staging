"""Integration tests for :class:`~app.infra.persistence.pg_plot_repo.PgPlotRepo`."""


from __future__ import annotations

import uuid
from collections.abc import Iterator
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.plot_repo import PlotRepo
from app.domain.plot import DataTier, Plot, PlotStatus
from app.infra.persistence.pg_plot_repo import PgPlotRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)




def _seed_minimum(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str, str]:
    run = uuid.uuid4().hex[:8]
    farmer_id = uuid.uuid4()
    farm_id = uuid.uuid4()
    plot_id = f"PLOT_PG_{run}"
    device_id = f"AGR-PG-{run}"
    with eng.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :farmer, :tenant, 'Test Farmer', 'टेस्ट', '+910000000000',
                    '+910000000000', 'marathi', 'v', 't', 'd',
                    'Maharashtra', 'basic', '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"farmer": farmer_id, "tenant": PILOT_TENANT},
        )
        conn.execute(
            text(
                """
                INSERT INTO farms (
                    farm_id, tenant_id, farmer_id, total_area_acre,
                    gps_lat_center, gps_lng_center, soil_type,
                    water_source_primary, irrigation_type, electricity_source
                ) VALUES (
                    :farm, :tenant, :farmer, 2.0, 19.9, 75.7, 'black',
                    'well', 'drip', 'grid'
                )
                """
            ),
            {"farm": farm_id, "tenant": PILOT_TENANT, "farmer": farmer_id},
        )
        conn.execute(
            text(
                """
                INSERT INTO device_registry (
                    device_id, tenant_id, device_type, serial_number,
                    mac_address, qr_code_data, farm_id, device_tier,
                    installation_date, device_status
                ) VALUES (
                    :dev, :tenant, 'sub_node', :sn,
                    :mac, :qr, :farm, 'basic',
                    '2025-06-01', 'online'
                )
                """
            ),
            {
                "dev": device_id,
                "tenant": PILOT_TENANT,
                "sn": run,
                "mac": f"AA:BB:CC:{run[:2]}:{run[2:4]}:{run[4:6]}",
                "qr": f"QR_{run}",
                "farm": farm_id,
            },
        )
        conn.execute(
            text(
                """
                INSERT INTO plots (
                    plot_id, tenant_id, farm_id, plot_number, area_acre,
                    gps_lat, gps_lng, irrigation_valve_id, node_id
                ) VALUES (
                    :plot, :tenant, :farm, 1, 1.0, 19.9, 75.7, :valve, :dev
                )
                """
            ),
            {
                "plot": plot_id,
                "tenant": PILOT_TENANT,
                "farm": farm_id,
                "valve": f"V_{run}",
                "dev": device_id,
            },
        )
    return farmer_id, farm_id, plot_id, device_id




@pytest.fixture
def seed(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, uuid.UUID, str, str]]:
    farmer_id, farm_id, plot_id, device_id = _seed_minimum(sync_engine)
    yield farmer_id, farm_id, plot_id, device_id
    # Defensive: also clear telemetry/alerts so this fixture is safe to
    # mix with other test modules (e.g. a previously-failed run could
    # have left rows around).
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE node_sensor_readings, alerts_notifications RESTART IDENTITY CASCADE"
            )
        )
        conn.execute(text("DELETE FROM plots WHERE plot_id = :p"), {"p": plot_id})
        conn.execute(text("DELETE FROM device_registry WHERE device_id = :d"), {"d": device_id})
        conn.execute(text("DELETE FROM farms WHERE farm_id = :f"), {"f": farm_id})
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})




# ===========================================================================
# Protocol check
# ===========================================================================
async def test_pg_plot_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgPlotRepo(sessionmaker), PlotRepo)




# ===========================================================================
# find
# ===========================================================================
async def test_find_returns_plot_with_sub_node_tier(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, plot_id, device_id = seed
    repo = PgPlotRepo(sessionmaker)
    p = await repo.find(plot_id)
    assert p is not None
    assert isinstance(p, Plot)
    assert p.plot_id == plot_id
    assert p.node_id == device_id
    # plots_set_data_tier trigger should have set this to sub_node because
    # node_id is non-null in the seed.
    assert p.data_tier is DataTier.SUB_NODE
    assert p.has_sensor() is True
    assert isinstance(p.area_acre, Decimal)




async def test_find_returns_none_when_missing(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    repo = PgPlotRepo(sessionmaker)
    p = await repo.find("does-not-exist")
    assert p is None




# ===========================================================================
# for_farmer
# ===========================================================================
async def test_for_farmer_returns_only_owned_plots(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, _, plot_id, _ = seed
    repo = PgPlotRepo(sessionmaker)
    plots = await repo.for_farmer(farmer_id)
    assert any(p.plot_id == plot_id for p in plots)




async def test_for_farmer_empty_when_unknown_id(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    repo = PgPlotRepo(sessionmaker)
    plots = await repo.for_farmer(uuid.uuid4())
    assert plots == []




# ===========================================================================
# for_tenant
# ===========================================================================
async def test_for_tenant_includes_seeded_plot(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, plot_id, _ = seed
    repo = PgPlotRepo(sessionmaker)
    plots = await repo.for_tenant(uuid.UUID(PILOT_TENANT))
    assert any(p.plot_id == plot_id for p in plots)




# ===========================================================================
# update_data_tier
# ===========================================================================
async def test_update_data_tier_to_satellite_only_clears_node(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    _, _, plot_id, _ = seed
    repo = PgPlotRepo(sessionmaker)


    # Verify starting state.
    p = await repo.find(plot_id)
    assert p is not None
    assert p.data_tier is DataTier.SUB_NODE


    await repo.update_data_tier(plot_id, DataTier.SATELLITE_ONLY)


    p_after = await repo.find(plot_id)
    assert p_after is not None
    assert p_after.data_tier is DataTier.SATELLITE_ONLY
    assert p_after.node_id is None




async def test_update_data_tier_to_sub_node_not_implemented(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, plot_id, _ = seed
    repo = PgPlotRepo(sessionmaker)
    with pytest.raises(NotImplementedError, match="Round 9"):
        await repo.update_data_tier(plot_id, DataTier.SUB_NODE)




# ===========================================================================
# Plot status round-trip
# ===========================================================================
async def test_plot_status_decodes_to_enum(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, plot_id, _ = seed
    repo = PgPlotRepo(sessionmaker)
    p = await repo.find(plot_id)
    assert p is not None
    assert p.plot_status is PlotStatus.ACTIVE
    assert p.is_active() is True
