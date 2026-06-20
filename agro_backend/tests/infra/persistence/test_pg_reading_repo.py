"""Integration tests for :class:`~app.infra.persistence.pg_reading_repo.PgReadingRepo`.


Requires a reachable Postgres with all migrations applied. Auto-skip path
is in ``conftest.py``.
"""


from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import (
    CadenceMode,
    Reading,
    TransmissionType,
)
from app.infra.persistence.pg_reading_repo import PgReadingRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)




# ---------------------------------------------------------------------------
# Seed helpers - create the master rows the FK constraints need.
# ---------------------------------------------------------------------------
def _seed_master_data(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str, str]:
    """Insert tenant (already exists) + farmer + farm + plot + device.


    Returns (farmer_id, farm_id, plot_id, device_id). All entities are
    keyed off the test run id so tests don't collide.
    """
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
def seed(
    sync_engine: Engine, clean_telemetry: None
) -> Iterator[tuple[uuid.UUID, uuid.UUID, str, str]]:
    """Insert the master data needed by every test, then clean up afterwards.


    ``clean_telemetry`` is requested too so each test starts with empty
    reading tables. The seed runs after the truncate.
    """
    farmer_id, farm_id, plot_id, device_id = _seed_master_data(sync_engine)
    yield farmer_id, farm_id, plot_id, device_id
    # Clean up to leave the DB usable for the next test module. Order
    # matters: rows that REFERENCE device_registry/farms/farmers must be
    # removed before the rows they point at. node_sensor_readings and
    # alerts_notifications both FK onto device_registry, so truncate them
    # before deleting the device.
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




def _make_reading(
    farmer_id: uuid.UUID,
    farm_id: uuid.UUID,
    plot_id: str,
    device_id: str,
    *,
    recorded_at: datetime | None = None,
    **over: object,
) -> Reading:
    base: dict[str, object] = {
        "tenant_id": uuid.UUID(PILOT_TENANT),
        "farmer_id": farmer_id,
        "farm_id": farm_id,
        "plot_id": plot_id,
        "node_id": device_id,
        "recorded_at": recorded_at or datetime.now(UTC),
        "received_at_master": datetime.now(UTC),
        "transmission_type": TransmissionType.LORA,
        "soil_moisture_1_pct": Decimal("32.5"),
        "battery_voltage_v": Decimal("3.45"),
        "cadence_mode": CadenceMode.NORMAL,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




# ===========================================================================
# Protocol structural check
# ===========================================================================
async def test_pg_reading_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgReadingRepo(sessionmaker)
    assert isinstance(repo, ReadingRepo)




# ===========================================================================
# save - idempotency on (node_id, recorded_at)
# ===========================================================================
async def test_save_returns_reading_id_on_fresh_insert(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    r = _make_reading(farmer_id, farm_id, plot_id, device_id)
    rid = await repo.save(r)
    assert rid is not None
    assert isinstance(rid, int)
    assert rid > 0




async def test_save_returns_none_on_duplicate_node_time(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    t = datetime.now(UTC).replace(microsecond=0)
    r1 = _make_reading(farmer_id, farm_id, plot_id, device_id, recorded_at=t)
    r2 = _make_reading(
        farmer_id,
        farm_id,
        plot_id,
        device_id,
        recorded_at=t,
        soil_moisture_1_pct=Decimal("99.9"),  # different content, same key
    )
    rid1 = await repo.save(r1)
    rid2 = await repo.save(r2)
    assert rid1 is not None
    assert rid2 is None  # duplicate key -> DO NOTHING -> no row -> None




async def test_save_different_times_creates_two_rows(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    t1 = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=10)
    t2 = t1 + timedelta(minutes=1)
    rid1 = await repo.save(_make_reading(farmer_id, farm_id, plot_id, device_id, recorded_at=t1))
    rid2 = await repo.save(_make_reading(farmer_id, farm_id, plot_id, device_id, recorded_at=t2))
    assert rid1 is not None and rid2 is not None
    assert rid1 != rid2




# ===========================================================================
# latest_for_plot - newest-first
# ===========================================================================
async def test_latest_for_plot_returns_newest_first_with_limit(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
    for i in range(5):
        await repo.save(
            _make_reading(
                farmer_id,
                farm_id,
                plot_id,
                device_id,
                recorded_at=base + timedelta(minutes=i),
                soil_moisture_1_pct=Decimal(str(20 + i)),
            )
        )
    out = await repo.latest_for_plot(plot_id, limit=3)
    assert len(out) == 3
    # Newest first -> i=4, i=3, i=2 -> moistures 24, 23, 22
    assert out[0].soil_moisture_1_pct == Decimal("24")
    assert out[1].soil_moisture_1_pct == Decimal("23")
    assert out[2].soil_moisture_1_pct == Decimal("22")




# ===========================================================================
# recent_for_node - oldest-first within a window
# ===========================================================================
async def test_recent_for_node_filters_by_since(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    # 4 readings spaced 10 min apart.
    for i in range(4):
        await repo.save(
            _make_reading(
                farmer_id,
                farm_id,
                plot_id,
                device_id,
                recorded_at=base + timedelta(minutes=i * 10),
            )
        )
    since = base + timedelta(minutes=15)  # only readings 2 and 3 qualify
    out = await repo.recent_for_node(device_id, since)
    assert len(out) == 2




# ===========================================================================
# history_for_stuck_check - oldest-first, max 6, SQL-injection guard
# ===========================================================================
async def test_history_for_stuck_check_returns_oldest_first(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=30)
    for i in range(8):
        await repo.save(
            _make_reading(
                farmer_id,
                farm_id,
                plot_id,
                device_id,
                recorded_at=base + timedelta(minutes=i * 2),
                soil_moisture_1_pct=Decimal(str(30 + i)),
            )
        )
    hist = await repo.history_for_stuck_check(device_id, "soil_moisture_1_pct", minutes=90)
    # Repo caps the SELECT at 6 newest then reverses to oldest-first.
    assert len(hist) == 6
    first, last = hist[0], hist[-1]
    assert first is not None
    assert last is not None
    # Last value should be the most recent (i=7 -> moisture 37).
    assert last == Decimal("37")
    # First value should be older than the last.
    assert first < last




async def test_history_for_stuck_check_rejects_disallowed_field(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, _, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    with pytest.raises(ValueError, match="not in ALLOWED_HISTORY_FIELDS"):
        await repo.history_for_stuck_check(device_id, "drop table users", minutes=90)




# ===========================================================================
# history_for_mad_check - returns non-null Decimals only
# ===========================================================================
async def test_history_for_mad_check_returns_non_null_decimals(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    base = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    # 3 with values, 1 with None (sensor_health flag scenario).
    for i, v in enumerate([Decimal("30"), Decimal("31"), None, Decimal("32")]):
        await repo.save(
            _make_reading(
                farmer_id,
                farm_id,
                plot_id,
                device_id,
                recorded_at=base + timedelta(minutes=i),
                soil_moisture_1_pct=v,
            )
        )
    window = await repo.history_for_mad_check(device_id, "soil_moisture_1_pct", hours=24)
    assert len(window) == 3
    assert all(isinstance(v, Decimal) for v in window)




async def test_history_for_mad_check_rejects_disallowed_field(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, _, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    with pytest.raises(ValueError, match="not in ALLOWED_HISTORY_FIELDS"):
        await repo.history_for_mad_check(device_id, "tenant_id", hours=24)




# ===========================================================================
# Round-trip - save then read back
# ===========================================================================
async def test_round_trip_preserves_decimal_and_enums(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgReadingRepo(sessionmaker)
    original = _make_reading(
        farmer_id,
        farm_id,
        plot_id,
        device_id,
        soil_moisture_1_pct=Decimal("32.5"),
        soil_ph=Decimal("6.85"),
        cadence_mode=CadenceMode.RAPID,
    )
    await repo.save(original)
    out = await repo.latest_for_plot(plot_id, limit=1)
    assert len(out) == 1
    r = out[0]
    # Decimal preserved (storage is Double; values are well within
    # representable precision so the Decimal(str(float)) round-trip is
    # lossless at this precision).
    assert r.soil_moisture_1_pct == Decimal("32.5")
    assert r.soil_ph == Decimal("6.85")
    # Enum decoded from TEXT back to the StrEnum value.
    assert r.cadence_mode is CadenceMode.RAPID
    assert r.transmission_type is TransmissionType.LORA
