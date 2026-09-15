"""Integration tests for :class:`~app.infra.persistence.pg_alert_repo.PgAlertRepo`."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.alert_repo import AlertRepo
from app.domain.alert import AlertCandidate, AlertType, Severity
from app.infra.persistence.pg_alert_repo import PgAlertRepo

from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)


def _seed(eng: Engine) -> tuple[uuid.UUID, uuid.UUID, str, str]:
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
                    :farmer, :tenant, 'A', 'अ', '+910000000000',
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
                    :farm, :tenant, :farmer, 1.0, 19.9, 75.7, 'black',
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
    farmer_id, farm_id, plot_id, device_id = _seed(sync_engine)
    yield farmer_id, farm_id, plot_id, device_id
    # Order matters: rows that REFERENCE device_registry/farms must be
    # removed first. The test created alerts that FK onto device_id.
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


def _make_candidate(
    farmer_id: uuid.UUID,
    farm_id: uuid.UUID,
    device_id: str,
    *,
    alert_type: AlertType = AlertType.LOW_BATTERY,
    triggered_at: datetime | None = None,
) -> AlertCandidate:
    return AlertCandidate(
        alert_type=alert_type,
        severity=Severity.WARNING,
        alert_message_marathi="बॅटरी कमी आहे.",
        tenant_id=uuid.UUID(PILOT_TENANT),
        farm_id=farm_id,
        farmer_id=farmer_id,
        triggered_at=triggered_at or datetime.now(UTC),
        device_id=device_id,
        alert_value=Decimal("3.10"),
        alert_threshold=Decimal("3.30"),
    )


# ===========================================================================
# Protocol check
# ===========================================================================
async def test_pg_alert_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgAlertRepo(sessionmaker), AlertRepo)


# ===========================================================================
# create - returns alert_id, dispatch_status='pending'
# ===========================================================================
async def test_create_returns_alert_id_and_pending_status(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    assert isinstance(aid, int)
    assert aid > 0
    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT dispatch_status, alert_type, severity FROM alerts_notifications "
                "WHERE alert_id = :id"
            ),
            {"id": aid},
        ).one()
    assert row.dispatch_status == "pending"
    assert row.alert_type == "low_battery"
    assert row.severity == "warning"


# ===========================================================================
# last_triggered_at
# ===========================================================================
async def test_last_triggered_at_returns_none_when_no_alerts(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    _, _, plot_id, _ = seed
    repo = PgAlertRepo(sessionmaker)
    out = await repo.last_triggered_at(plot_id, AlertType.LOW_BATTERY)
    assert out is None


async def test_last_triggered_at_returns_latest_for_alert_type(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    t1 = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=2)
    t2 = t1 + timedelta(minutes=30)
    await repo.create(_make_candidate(farmer_id, farm_id, device_id, triggered_at=t1))
    await repo.create(_make_candidate(farmer_id, farm_id, device_id, triggered_at=t2))
    out = await repo.last_triggered_at(plot_id, AlertType.LOW_BATTERY)
    assert out is not None
    assert out == t2


async def test_last_triggered_at_filters_by_alert_type(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, plot_id, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    # Create a TAMPER alert (more recent) and a LOW_BATTERY alert (older).
    t1 = datetime.now(UTC).replace(microsecond=0) - timedelta(hours=1)
    t2 = t1 + timedelta(minutes=30)
    await repo.create(
        _make_candidate(
            farmer_id, farm_id, device_id, alert_type=AlertType.LOW_BATTERY, triggered_at=t1
        )
    )
    await repo.create(
        _make_candidate(farmer_id, farm_id, device_id, alert_type=AlertType.TAMPER, triggered_at=t2)
    )
    # Asking about LOW_BATTERY should return t1, not t2.
    out = await repo.last_triggered_at(plot_id, AlertType.LOW_BATTERY)
    assert out == t1


# ===========================================================================
# resolve
# ===========================================================================
async def test_resolve_marks_row_resolved(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    await repo.resolve(aid, notes="battery replaced")
    with sync_engine.begin() as conn:
        row = conn.execute(
            text("SELECT resolved, resolution_note FROM alerts_notifications WHERE alert_id = :id"),
            {"id": aid},
        ).one()
    assert row.resolved is True
    assert row.resolution_note == "battery replaced"


# ===========================================================================
# Round 13 advisory state machine
# ===========================================================================
async def test_claim_for_advisory_is_atomic_and_single_winner(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    now = datetime.now(UTC)

    first = await repo.claim_for_advisory(aid, now)
    assert first == 0  # fresh alert, zero prior attempts

    # A second claim of the same (now in_flight) alert loses.
    second = await repo.claim_for_advisory(aid, now)
    assert second is None

    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT advisory_status, advisory_claimed_at FROM alerts_notifications "
                "WHERE alert_id = :id"
            ),
            {"id": aid},
        ).one()
    assert row.advisory_status == "in_flight"
    assert row.advisory_claimed_at is not None


async def test_set_advisory_outcome_writes_fields(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    await repo.claim_for_advisory(aid, datetime.now(UTC))
    await repo.set_advisory_outcome(aid, status="composed", attempts=0)

    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT advisory_status, advisory_next_retry_at, advisory_last_error "
                "FROM alerts_notifications WHERE alert_id = :id"
            ),
            {"id": aid},
        ).one()
    assert row.advisory_status == "composed"
    assert row.advisory_next_retry_at is None
    assert row.advisory_last_error is None


async def test_list_due_advisory_alerts_respects_state_and_retry_time(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    now = datetime.now(UTC)

    # Fresh 'pending' with no next_retry_at is due.
    assert aid in await repo.list_due_advisory_alerts(now)

    # Claiming it (→ in_flight) removes it from the due set.
    await repo.claim_for_advisory(aid, now)
    assert aid not in await repo.list_due_advisory_alerts(now)

    # Back to pending but with a future retry time → not yet due.
    await repo.set_advisory_outcome(
        aid, status="pending", attempts=1, next_retry_at=now + timedelta(hours=1)
    )
    assert aid not in await repo.list_due_advisory_alerts(now)
    # ...but due once that time passes.
    assert aid in await repo.list_due_advisory_alerts(now + timedelta(hours=2))


async def test_revert_stale_in_flight_reaps_only_old_claims(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed: tuple[uuid.UUID, uuid.UUID, str, str],
    sync_engine: Engine,
) -> None:
    farmer_id, farm_id, _, device_id = seed
    repo = PgAlertRepo(sessionmaker)
    aid = await repo.create(_make_candidate(farmer_id, farm_id, device_id))
    now = datetime.now(UTC)
    await repo.claim_for_advisory(aid, now)

    # A cutoff before the claim leaves it alone.
    assert await repo.revert_stale_in_flight(now - timedelta(minutes=1), now) == 0

    # A cutoff after the claim reaps it back to pending.
    reverted = await repo.revert_stale_in_flight(now + timedelta(minutes=1), now)
    assert reverted == 1
    with sync_engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT advisory_status, advisory_last_error FROM alerts_notifications "
                "WHERE alert_id = :id"
            ),
            {"id": aid},
        ).one()
    assert row.advisory_status == "pending"
    assert row.advisory_last_error == "stale_revert"
