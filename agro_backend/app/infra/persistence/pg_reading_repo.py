"""Postgres adapter for :class:`~app.application.ports.reading_repo.ReadingRepo`.


Implements the 5 methods declared in Round 4's Protocol against the
``node_sensor_readings`` partitioned table from migration 0005.


Three things this implementation enforces that the Protocol can't:


1. **Idempotent INSERTs** via ``ON CONFLICT (node_id, recorded_at) DO NOTHING
   RETURNING reading_id``. The composite unique constraint
   ``node_sensor_readings_idem`` is the schema-level guarantee; ``RETURNING``
   gives us "did I actually insert?" in one round trip. A return of ``None``
   from ``save()`` means duplicate - the caller treats it as success
   (the row exists) but increments ``metrics.ingest.duplicate``.


2. **SQL-injection guard on history column names.** The validation gate
   passes a field name string; we whitelist against
   :data:`~app.application.ports.reading_repo.ALLOWED_HISTORY_FIELDS`
   before interpolating into the SQL. Round 4's allowlist is the only
   acceptable source of column names.


3. **Decimal <-> Double conversion at the storage boundary.** The
   schema stores numeric sensor values as ``Double`` (the PDF's choice).
   SQLAlchemy converts Decimal parameters to float and back; our domain
   stores Decimal end-to-end. Reads go ``Float -> Decimal(str(value))``
   to keep precision contracts intact.
"""


from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.reading_repo import ALLOWED_HISTORY_FIELDS
from app.domain.sensor import CadenceMode, Reading, TransmissionType, ValveStatus

# ---------------------------------------------------------------------------
# Column ordering for INSERT / SELECT. Defined once so the two SQL templates
# stay in lockstep when a new Reading field lands.
# ---------------------------------------------------------------------------
_INSERT_COLUMNS: tuple[str, ...] = (
    "tenant_id",
    "node_id",
    "farm_id",
    "plot_id",
    "farmer_id",
    "recorded_at",
    "received_at_master",
    "transmission_type",
    "signal_rssi_dbm",
    "battery_voltage_v",
    "battery_percent",
    "solar_charging",
    "low_battery_flag",
    "soil_moisture_1_pct",
    "soil_moisture_2_pct",
    "soil_moisture_avg_pct",
    "soil_temp_c",
    "soil_temp_rootzone_c",
    "soil_ph",
    "soil_ec_ms_cm",
    "soil_n_mg_kg",
    "soil_p_mg_kg",
    "soil_k_mg_kg",
    "soil_n_bucket",
    "soil_p_bucket",
    "soil_k_bucket",
    "npk_sensor_raw_hex",
    "tamper_detected",
    "enclosure_temp_c",
    "fault_flags",
    "sensor_health_json",
    "firmware_version",
    "uptime_seconds",
    "cadence_mode",
    "backlog_pending",
    "validation_warn",
    "valve_status",
    "pump_running",
    "pump_current_amps",
    "pump_runtime_minutes_today",
    "dry_run_detected",
    "water_flow_lpm",
    "water_volume_liters_session",
    "water_volume_liters_cumulative",
    "water_pressure_bar",
)




def _insert_sql() -> str:
    cols = ", ".join(_INSERT_COLUMNS)
    placeholders = ", ".join(
        # sensor_health_json is JSONB; we bind a JSON-encoded string and use
        # SQL-standard ``CAST(... AS jsonb)`` rather than Postgres' ``::jsonb``.
        # SQLAlchemy's ``text()`` parameter parser treats ``:name`` as a bind
        # variable but then chokes on the trailing ``::`` cast operator
        # (it leaves the literal ``:sensor_health_json::jsonb`` in the SQL,
        # which asyncpg rejects as a syntax error). ``CAST(... AS jsonb)``
        # is unambiguous and works on every dialect we care about.
        "CAST(:sensor_health_json AS jsonb)" if c == "sensor_health_json" else f":{c}"
        for c in _INSERT_COLUMNS
    )
    return (
        f"INSERT INTO node_sensor_readings ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT (node_id, recorded_at) DO NOTHING "
        "RETURNING reading_id"
    )




_SELECT_COLUMNS = "reading_id, " + ", ".join(_INSERT_COLUMNS)




def _row_to_reading(row: Any) -> Reading:
    """Convert one SQLAlchemy Row to a domain Reading."""
    return Reading(
        tenant_id=row.tenant_id,
        farmer_id=row.farmer_id,
        farm_id=row.farm_id,
        plot_id=row.plot_id,
        node_id=row.node_id,
        recorded_at=row.recorded_at,
        received_at_master=row.received_at_master,
        transmission_type=TransmissionType(row.transmission_type),
        signal_rssi_dbm=row.signal_rssi_dbm,
        battery_voltage_v=_to_decimal(row.battery_voltage_v),
        battery_percent=_to_decimal(row.battery_percent),
        solar_charging=row.solar_charging,
        low_battery_flag=bool(row.low_battery_flag) if row.low_battery_flag is not None else False,
        soil_moisture_1_pct=_to_decimal(row.soil_moisture_1_pct),
        soil_moisture_2_pct=_to_decimal(row.soil_moisture_2_pct),
        soil_moisture_avg_pct=_to_decimal(row.soil_moisture_avg_pct),
        soil_temp_c=_to_decimal(row.soil_temp_c),
        soil_temp_rootzone_c=_to_decimal(row.soil_temp_rootzone_c),
        soil_ph=_to_decimal(row.soil_ph),
        soil_ec_ms_cm=_to_decimal(row.soil_ec_ms_cm),
        soil_n_mg_kg=_to_decimal(row.soil_n_mg_kg),
        soil_p_mg_kg=_to_decimal(row.soil_p_mg_kg),
        soil_k_mg_kg=_to_decimal(row.soil_k_mg_kg),
        soil_n_bucket=row.soil_n_bucket,
        soil_p_bucket=row.soil_p_bucket,
        soil_k_bucket=row.soil_k_bucket,
        npk_sensor_raw_hex=row.npk_sensor_raw_hex,
        tamper_detected=row.tamper_detected,
        enclosure_temp_c=_to_decimal(row.enclosure_temp_c),
        fault_flags=row.fault_flags,
        sensor_health_json=dict(row.sensor_health_json) if row.sensor_health_json else {},
        firmware_version=row.firmware_version,
        uptime_seconds=row.uptime_seconds,
        cadence_mode=CadenceMode(row.cadence_mode) if row.cadence_mode else None,
        backlog_pending=bool(row.backlog_pending) if row.backlog_pending is not None else False,
        validation_warn=bool(row.validation_warn) if row.validation_warn is not None else False,
        valve_status=ValveStatus(row.valve_status) if row.valve_status else None,
        pump_running=row.pump_running,
        pump_current_amps=_to_decimal(row.pump_current_amps),
        pump_runtime_minutes_today=row.pump_runtime_minutes_today,
        dry_run_detected=row.dry_run_detected,
        water_flow_lpm=_to_decimal(row.water_flow_lpm),
        water_volume_liters_session=_to_decimal(row.water_volume_liters_session),
        water_volume_liters_cumulative=_to_decimal(row.water_volume_liters_cumulative),
        water_pressure_bar=_to_decimal(row.water_pressure_bar),
    )




def _to_decimal(v: float | int | Decimal | None) -> Decimal | None:
    """Storage -> domain Decimal conversion (via str to dodge float artefacts)."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))




def _bind_params(reading: Reading) -> dict[str, Any]:
    """Reading -> parameter dict for the INSERT statement."""
    return {
        "tenant_id": reading.tenant_id,
        "node_id": reading.node_id,
        "farm_id": reading.farm_id,
        "plot_id": reading.plot_id,
        "farmer_id": reading.farmer_id,
        "recorded_at": reading.recorded_at,
        "received_at_master": reading.received_at_master,
        "transmission_type": reading.transmission_type.value,
        "signal_rssi_dbm": reading.signal_rssi_dbm,
        "battery_voltage_v": _decimal_to_float(reading.battery_voltage_v),
        "battery_percent": _decimal_to_float(reading.battery_percent),
        "solar_charging": reading.solar_charging,
        "low_battery_flag": reading.low_battery_flag,
        "soil_moisture_1_pct": _decimal_to_float(reading.soil_moisture_1_pct),
        "soil_moisture_2_pct": _decimal_to_float(reading.soil_moisture_2_pct),
        "soil_moisture_avg_pct": _decimal_to_float(reading.soil_moisture_avg_pct),
        "soil_temp_c": _decimal_to_float(reading.soil_temp_c),
        "soil_temp_rootzone_c": _decimal_to_float(reading.soil_temp_rootzone_c),
        "soil_ph": _decimal_to_float(reading.soil_ph),
        "soil_ec_ms_cm": _decimal_to_float(reading.soil_ec_ms_cm),
        "soil_n_mg_kg": _decimal_to_float(reading.soil_n_mg_kg),
        "soil_p_mg_kg": _decimal_to_float(reading.soil_p_mg_kg),
        "soil_k_mg_kg": _decimal_to_float(reading.soil_k_mg_kg),
        "soil_n_bucket": reading.soil_n_bucket,
        "soil_p_bucket": reading.soil_p_bucket,
        "soil_k_bucket": reading.soil_k_bucket,
        "npk_sensor_raw_hex": reading.npk_sensor_raw_hex,
        "tamper_detected": reading.tamper_detected,
        "enclosure_temp_c": _decimal_to_float(reading.enclosure_temp_c),
        "fault_flags": reading.fault_flags,
        # JSONB - SQLAlchemy needs a JSON-encoded string here when binding
        # via text(); CAST in the SQL handles the rest.
        "sensor_health_json": _jsonb_param(reading.sensor_health_json),
        "firmware_version": reading.firmware_version,
        "uptime_seconds": reading.uptime_seconds,
        "cadence_mode": reading.cadence_mode.value if reading.cadence_mode else None,
        "backlog_pending": reading.backlog_pending,
        "validation_warn": reading.validation_warn,
        "valve_status": reading.valve_status.value if reading.valve_status else None,
        "pump_running": reading.pump_running,
        "pump_current_amps": _decimal_to_float(reading.pump_current_amps),
        "pump_runtime_minutes_today": reading.pump_runtime_minutes_today,
        "dry_run_detected": reading.dry_run_detected,
        "water_flow_lpm": _decimal_to_float(reading.water_flow_lpm),
        "water_volume_liters_session": _decimal_to_float(reading.water_volume_liters_session),
        "water_volume_liters_cumulative": _decimal_to_float(reading.water_volume_liters_cumulative),
        "water_pressure_bar": _decimal_to_float(reading.water_pressure_bar),
    }




def _decimal_to_float(v: Decimal | None) -> float | None:
    return None if v is None else float(v)




def _jsonb_param(d: dict[str, Any]) -> str:
    """JSONB parameter binding via CAST. ``json.dumps`` for stable encoding."""
    import json


    return json.dumps(d)




class PgReadingRepo:
    """Concrete :class:`ReadingRepo` against Postgres.


    Construct with the shared ``async_sessionmaker`` from
    :mod:`app.infra.persistence.engine`. Each public method opens its own
    short-lived session - simpler reasoning, no implicit shared state, easy
    cleanup. When a single use case needs to coordinate multiple repo calls
    transactionally (Phase 4+), it will adopt a unit-of-work wrapper; the
    repos themselves stay independent.
    """


    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    # ------------------------------------------------------------------
    # save - idempotent UPSERT
    # ------------------------------------------------------------------
    async def save(self, reading: Reading) -> int | None:
        stmt = text(_insert_sql())
        async with self._sm() as session:
            res = await session.execute(stmt, _bind_params(reading))
            row = res.first()
            await session.commit()
        if row is None:
            return None
        return int(row.reading_id)


    # ------------------------------------------------------------------
    # latest_for_plot
    # ------------------------------------------------------------------
    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS} FROM node_sensor_readings "
            "WHERE plot_id = :plot_id "
            "ORDER BY recorded_at DESC LIMIT :limit"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id, "limit": limit})
            return [_row_to_reading(r) for r in res.all()]


    # ------------------------------------------------------------------
    # recent_for_node
    # ------------------------------------------------------------------
    async def recent_for_node(self, node_id: str, since: datetime) -> list[Reading]:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS} FROM node_sensor_readings "
            "WHERE node_id = :node_id AND recorded_at >= :since "
            "ORDER BY recorded_at ASC"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"node_id": node_id, "since": since})
            return [_row_to_reading(r) for r in res.all()]


    # ------------------------------------------------------------------
    # history_for_stuck_check
    # ------------------------------------------------------------------
    async def history_for_stuck_check(
        self, node_id: str, field: str, minutes: int
    ) -> list[Decimal | None]:
        col = _assert_allowed_field(field)
        # Newest 6 rows in the trailing window, then reverse to
        # oldest -> newest (the Protocol's documented order).
        #
        # Why ``:minutes * interval '1 minute'`` and not the older
        # ``(:minutes::text || ' minutes')::interval``: SQLAlchemy's
        # ``text()`` bind parser treats the ``::`` cast operator immediately
        # after a ``:name`` as part of the bind variable name, which leaves
        # ``:minutes::text`` literally in the SQL and asyncpg rejects it as
        # a syntax error. Multiplying a bound integer by a literal interval
        # is syntactically cleaner and equivalent.
        stmt = text(
            f"SELECT {col} AS v FROM node_sensor_readings "
            "WHERE node_id = :node_id "
            "AND recorded_at >= NOW() - :minutes * interval '1 minute' "
            "ORDER BY recorded_at DESC LIMIT 6"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"node_id": node_id, "minutes": minutes})
            rows = list(res.all())
        # Reverse to oldest-first (matches the Protocol's docstring).
        rows.reverse()
        return [None if r.v is None else _to_decimal(r.v) for r in rows]


    # ------------------------------------------------------------------
    # history_for_mad_check
    # ------------------------------------------------------------------
    async def history_for_mad_check(self, node_id: str, field: str, hours: int) -> list[Decimal]:
        col = _assert_allowed_field(field)
        # See the note in history_for_stuck_check above for why this is
        # ``:hours * interval '1 hour'`` rather than a ``::`` cast.
        stmt = text(
            f"SELECT {col} AS v FROM node_sensor_readings "
            "WHERE node_id = :node_id "
            f"AND {col} IS NOT NULL "
            "AND recorded_at >= NOW() - :hours * interval '1 hour'"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"node_id": node_id, "hours": hours})
            rows = res.all()
        # All non-null by the WHERE clause; cast and return.
        return [Decimal(str(r.v)) for r in rows]




def _assert_allowed_field(field: str) -> str:
    """Validate a field name against the Round-4 allowlist (SQL-injection guard)."""
    if field not in ALLOWED_HISTORY_FIELDS:
        raise ValueError(
            f"history field {field!r} not in ALLOWED_HISTORY_FIELDS "
            "(SQL-injection guard; see app.application.ports.reading_repo)"
        )
    return field




__all__ = ["PgReadingRepo"]
