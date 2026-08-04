"""Sensor-reading domain model.


PURE module: only stdlib + ``app.lib.time`` (a pure tz helper). No framework
imports - enforced by ``tests/domain/test_domain_purity.py``.


A :class:`Reading` is the validated, in-memory representation of a single
Sub Node telemetry row, sitting between the MQTT pydantic adapter (which
parses the wire format) and the Postgres repository (which inserts into
``node_sensor_readings``). The dataclass mirrors that table's columns 1:1,
with these intentional simplifications for the domain layer:


* All numeric measurements are ``Decimal | None`` rather than ``float | None``.
  Floats are a wire-format and SQL-storage concern; domain logic (validation
  gates, rule conditions) reasons in exact decimals to avoid pH=6.499999999
  classes of bug. The MQTT adapter does ``Decimal(str(value))`` at the boundary
  (.cursorrules #3 - never float for measurements either).
* Boolean flags default to ``False`` rather than ``None`` where the schema
  allows null - validated cleanly when constructing.
* The four mutually-exclusive enum-style columns (``transmission_type``,
  ``valve_status``, ``cadence_mode``, ``fault_flags``) are typed as StrEnums.


The :class:`Reading` is immutable (``frozen=True``); validation gates produce
a new instance via :func:`dataclasses.replace` rather than mutating.


Schema reference: ``app/infra/persistence/models/readings.py``
(``NodeSensorReading``) and migrations 0001 + 0005. Enum value lists are
copied verbatim from the schema CHECK constraints; any change here MUST be
mirrored in the migration and ``SCHEMA_DECISIONS.md``.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any


class CadenceMode(StrEnum):
    """Sub Node sampling cadence; mirrors ``node_sensor_readings.cadence_mode``.


    Values match the CHECK constraint in migration 0005. The Sub Node firmware
    selects a mode based on battery + ambient conditions; the ingest pipeline
    persists it for replay and analytics. Mode transitions are observable
    (the field appears in every reading) - the firmware does not push a
    separate "mode change" event.
    """

    NORMAL = "normal"
    RAPID = "rapid"
    LOW_POWER = "low_power"
    STORM = "storm"
    MAINTENANCE = "maintenance"


class TransmissionType(StrEnum):
    """Physical link a reading arrived over (``node_sensor_readings.transmission_type``)."""

    ESP_NOW = "esp_now"
    LORA = "lora"
    RS485 = "rs485"
    WIFI = "wifi"


class ValveStatus(StrEnum):
    """Pilot is advisory-only; valve fields stay null in V2 sensor rows.


    Reserved for the Standard/Pro tiers when irrigation actuation lands.
    """

    OPEN = "open"
    CLOSED = "closed"
    FAULT = "fault"


# Sentinels for moisture sensor disagreement / NPK probe failure - both come
# from the firmware's on-device validation. They live on the reading as
# transparent flags rather than as magic numbers in the value fields.


LOW_BATTERY_THRESHOLD_V: Decimal = Decimal("3.30")
"""Per-cell low-battery threshold used by the validation gate in Phase 2.


Co-located with the dataclass so the threshold travels with the type when
later layers need to enforce it (Phase 4's hot-rule HOT-001). The value is
the same one the firmware uses for its in-packet ``low_battery_flag``.
"""


@dataclass(frozen=True, slots=True)
class Reading:
    """A single validated Sub Node telemetry row.


    Fields are grouped as: identity / timing / signal / battery / soil /
    valve+pump (reserved) / diagnostics / v3 flags. Names match the
    ``node_sensor_readings`` columns exactly (Reading.soil_moisture_1_pct
    maps to ``soil_moisture_1_pct``); only the ``signal_4g_*`` renames
    (illegal SQL identifiers) live on the device-registry table, not here.


    Construction is via the MQTT adapter's ``to_domain()`` boundary or test
    fixtures. Validation gates (Phase 2 stage 2.3) return a *new* Reading
    via ``dataclasses.replace`` - never mutate the original.
    """

    # --- Identity ---
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str
    node_id: str

    # --- Timing (.cursorrules #2: timezone-aware datetime only) ---
    recorded_at: datetime
    received_at_master: datetime

    # --- Transport ---
    transmission_type: TransmissionType
    signal_rssi_dbm: int | None = None

    # --- Battery ---
    battery_voltage_v: Decimal | None = None
    battery_percent: Decimal | None = None
    solar_charging: bool | None = None
    low_battery_flag: bool = False  # v3 (0005)

    # --- Soil moisture (two sensors + computed avg, v3 buckets for LoRa packing) ---
    soil_moisture_1_pct: Decimal | None = None
    soil_moisture_2_pct: Decimal | None = None
    soil_moisture_avg_pct: Decimal | None = None

    # --- Soil temperature ---
    soil_temp_c: Decimal | None = None
    soil_temp_rootzone_c: Decimal | None = None  # v3 (0005)

    # --- Soil chemistry ---
    soil_ph: Decimal | None = None
    soil_ec_ms_cm: Decimal | None = None
    soil_n_mg_kg: Decimal | None = None
    soil_p_mg_kg: Decimal | None = None
    soil_k_mg_kg: Decimal | None = None
    soil_n_bucket: int | None = None  # v3 (0005) - 0..63 for LoRa packing
    soil_p_bucket: int | None = None
    soil_k_bucket: int | None = None
    npk_sensor_raw_hex: str | None = None

    # --- Water / pump (reserved for Standard tier; null in V2) ---
    water_flow_lpm: Decimal | None = None
    water_volume_liters_session: Decimal | None = None
    water_volume_liters_cumulative: Decimal | None = None
    valve_status: ValveStatus | None = None
    pump_running: bool | None = None
    pump_current_amps: Decimal | None = None
    pump_runtime_minutes_today: int | None = None
    dry_run_detected: bool | None = None

    # --- Diagnostics ---
    tamper_detected: bool | None = None
    enclosure_temp_c: Decimal | None = None
    fault_flags: str | None = None  # comma-separated freeform per PDF schema
    sensor_health_json: dict[str, Any] = field(default_factory=dict)
    firmware_version: str | None = None
    uptime_seconds: int | None = None

    # --- v3 mode + validation flags (0005) ---
    cadence_mode: CadenceMode | None = None
    backlog_pending: bool = False
    validation_warn: bool = False

    # ------------------------------------------------------------------
    # Construction helpers (still pure - no I/O)
    # ------------------------------------------------------------------
    def with_(
        self,
        **changes: object,
    ) -> Reading:
        """Return a new Reading with ``changes`` applied.


        Thin wrapper over :func:`dataclasses.replace` that exists so callers
        in the application layer don't need to import ``dataclasses`` just
        to evolve a Reading - reduces coupling and makes intent clearer.
        """
        return dataclasses.replace(self, **changes)  # type: ignore[arg-type]

    def is_satellite_only(self) -> bool:
        """``True`` when the reading carries no usable on-prem sensor data.


        A satellite-only plot still emits Reading rows (one per heartbeat)
        so the system has a heartbeat trail, but every moisture/temp/npk
        field is ``None``. This helper lets the application layer route
        such readings to the satellite-derived advisory path instead of
        the sensor-derived one (Phase 5).
        """
        return (
            self.soil_moisture_1_pct is None
            and self.soil_moisture_2_pct is None
            and self.soil_temp_rootzone_c is None
            and self.soil_n_mg_kg is None
        )


__all__ = [
    "LOW_BATTERY_THRESHOLD_V",
    "CadenceMode",
    "Reading",
    "TransmissionType",
    "ValveStatus",
]
