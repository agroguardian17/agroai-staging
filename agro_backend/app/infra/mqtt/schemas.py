"""Pydantic v2 schemas at the MQTT boundary.


Round 5 ships only the **telemetry** message - it's what the Fast Path
prototype (per Roadmap §0.6 / Days 4-6) needs to demo end-to-end. The
other message types from Roadmap §1.10 (weather / heartbeat / alert /
health) ship in later rounds when downstream consumers need them; the
:func:`parse_inbound` dispatcher already routes by topic-suffix so adding
them is one new model + one ``elif`` branch.


Per ``.cursorrules`` #12 the *domain* layer is pure - pydantic lives only
in infra. The :class:`TelemetryIn` model is the *wire format*; its
:meth:`to_domain` method is the boundary that produces a pure
:class:`~app.domain.sensor.Reading` for the application layer to consume.


The wire format itself is JSON, per Roadmap §1.10. Numeric measurements
arrive as floats over MQTT and are converted to :class:`~decimal.Decimal`
via ``Decimal(str(value))`` to dodge float-precision drift before any
domain code touches the value (.cursorrules #3 - never float for
measurements).
"""


from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from app.domain.device_calibration import (
    DeviceCalibration,
    calibrate_battery_v,
    calibrate_flow_lpm,
    calibrate_npk_moisture_pct,
    calibrate_npk_ph,
    calibrate_npk_temp_c,
    calibrate_pressure_bar,
    calibrate_soil_moisture_pct,
    npk_ec_ms_cm,
)
from app.domain.sensor import CadenceMode, Reading, TransmissionType

# Canonical $schema discriminator. Producers (Sub Node firmware via the
# Main Node 4G uplink) write this string; the parser dispatches on the
# topic suffix and validates the $schema field as a final guard.
SCHEMA_TELEMETRY_V2: str = "agro-guardian/telemetry/v2"

# Round 16 raw-values variant. Firmware `viraai-*-1.0.0-raw` sends raw ADC
# counts, pulse counts, and Modbus register integers; the Main Node adds
# tenant/farm/timestamp + its own weather-station master_readings block.
# Server applies per-device calibration from the device_calibration table
# (Alembic migration 0012) before constructing the domain Reading.
SCHEMA_TELEMETRY_V2_RAW: str = "agro-guardian/telemetry/v2-raw"




# ---------------------------------------------------------------------------
# Decimal-safe coercion for incoming numeric fields.
#
# Sub Node firmware emits JSON numbers. ``json.loads`` parses them as Python
# floats. We never let a float reach the domain layer (.cursorrules #3), so
# every numeric field is wrapped in this BeforeValidator that converts
# float / int / str to Decimal via the *string* representation - which is
# the only way to avoid binary-float artefacts like 7.2 -> 7.199999... .
# ---------------------------------------------------------------------------
def _to_decimal(v: Any) -> Decimal | None:
    # Pydantic v2 only wraps ValueError / AssertionError raised inside a
    # BeforeValidator into a clean ValidationError. TypeError and
    # decimal.InvalidOperation would otherwise escape to the caller as
    # raw exceptions, so we re-raise both as ValueError for uniform error
    # handling at the MQTT boundary (.cursorrules #4 - never silently
    # swallow; convert to a domain-shaped exception).
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, bool):
        # bool is an int subclass; reject it explicitly so a boolean field
        # mis-typed as decimal surfaces as a validation error rather than
        # silently storing Decimal(0) or Decimal(1).
        raise ValueError("bool is not a valid Decimal source")
    if isinstance(v, int | float | str):
        try:
            return Decimal(str(v))
        except InvalidOperation as exc:
            raise ValueError(f"cannot parse {v!r} as Decimal") from exc
    raise ValueError(f"cannot coerce {type(v).__name__} to Decimal")




SafeDecimal = Annotated[Decimal | None, BeforeValidator(_to_decimal)]




class TelemetryIn(BaseModel):
    """Sub Node telemetry as transmitted on the MQTT topic
    ``agro/v2/<tenant>/<farm>/<node>/telemetry``.


    Field names match the wire format exactly and the ``node_sensor_readings``
    columns 1:1 - the only renames live on ``device_registry`` for SQL
    identifiers that begin with a digit (per ``SCHEMA_DECISIONS.md`` #11b).
    """


    # ``ConfigDict`` is the pydantic-v2 way; no ``class Config`` (.cursorrules #1).
    # ``strict`` is False because the wire format mixes int + float for the
    # same field across producer versions; we want safe coercion.
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


    # --- Discriminator ---
    schema_id: Literal["agro-guardian/telemetry/v2"] = Field(
        alias="$schema",
        description="Canonical schema identifier; rejected if unknown.",
    )


    # --- Identity ---
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=64)


    # --- Timing (.cursorrules #2: must be timezone-aware) ---
    recorded_at: datetime
    received_at_master: datetime


    # --- Transport ---
    transmission_type: TransmissionType
    signal_rssi_dbm: int | None = Field(default=None, ge=-150, le=20)


    # --- Battery ---
    battery_voltage_v: SafeDecimal = None
    battery_percent: SafeDecimal = None
    solar_charging: bool | None = None
    low_battery_flag: bool = False


    # --- Soil moisture ---
    soil_moisture_1_pct: SafeDecimal = None
    soil_moisture_2_pct: SafeDecimal = None
    soil_moisture_avg_pct: SafeDecimal = None


    # --- Soil temperature ---
    soil_temp_c: SafeDecimal = None
    soil_temp_rootzone_c: SafeDecimal = None


    # --- Soil chemistry ---
    soil_ph: SafeDecimal = None
    soil_ec_ms_cm: SafeDecimal = None
    soil_n_mg_kg: SafeDecimal = None
    soil_p_mg_kg: SafeDecimal = None
    soil_k_mg_kg: SafeDecimal = None
    soil_n_bucket: int | None = Field(default=None, ge=0, le=63)
    soil_p_bucket: int | None = Field(default=None, ge=0, le=63)
    soil_k_bucket: int | None = Field(default=None, ge=0, le=63)
    npk_sensor_raw_hex: str | None = None


    # --- Water / pump (VIRAAI v1.0 Sub Node emits flow + pressure) ---
    # These map 1:1 to the identically-named columns on
    # ``node_sensor_readings``. Added 2026-08-04 so the Sub Node's flow
    # (pulse-counted) and pressure sensor readings actually reach the DB.
    water_flow_lpm: SafeDecimal = None
    water_pressure_bar: SafeDecimal = None

    # --- Diagnostics ---
    tamper_detected: bool | None = None
    enclosure_temp_c: SafeDecimal = None
    fault_flags: str | None = None
    sensor_health_json: dict[str, Any] = Field(default_factory=dict)
    firmware_version: str | None = None
    uptime_seconds: int | None = Field(default=None, ge=0)


    # --- v3 cadence + ingest flags ---
    cadence_mode: CadenceMode | None = None
    backlog_pending: bool = False
    validation_warn: bool = False


    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("recorded_at", "received_at_master")
    @classmethod
    def _must_be_aware(cls, dt: datetime) -> datetime:
        # Naive datetimes are a CLASS of bug (.cursorrules #2); reject at
        # the boundary so the application layer never sees one.
        if dt.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (RFC 3339 with offset)")
        return dt.astimezone(UTC)


    # ------------------------------------------------------------------
    # Boundary -> domain
    # ------------------------------------------------------------------
    def to_domain(self) -> Reading:
        """Project this wire-format model into the pure domain :class:`Reading`.


        This is the only place an :class:`MQTT model becomes a domain
        object`. Every field maps 1:1; pydantic has already done the
        type-safe coercion.
        """
        return Reading(
            tenant_id=self.tenant_id,
            farmer_id=self.farmer_id,
            farm_id=self.farm_id,
            plot_id=self.plot_id,
            node_id=self.node_id,
            recorded_at=self.recorded_at,
            received_at_master=self.received_at_master,
            transmission_type=self.transmission_type,
            signal_rssi_dbm=self.signal_rssi_dbm,
            battery_voltage_v=self.battery_voltage_v,
            battery_percent=self.battery_percent,
            solar_charging=self.solar_charging,
            low_battery_flag=self.low_battery_flag,
            soil_moisture_1_pct=self.soil_moisture_1_pct,
            soil_moisture_2_pct=self.soil_moisture_2_pct,
            soil_moisture_avg_pct=self.soil_moisture_avg_pct,
            soil_temp_c=self.soil_temp_c,
            soil_temp_rootzone_c=self.soil_temp_rootzone_c,
            soil_ph=self.soil_ph,
            soil_ec_ms_cm=self.soil_ec_ms_cm,
            soil_n_mg_kg=self.soil_n_mg_kg,
            soil_p_mg_kg=self.soil_p_mg_kg,
            soil_k_mg_kg=self.soil_k_mg_kg,
            soil_n_bucket=self.soil_n_bucket,
            soil_p_bucket=self.soil_p_bucket,
            soil_k_bucket=self.soil_k_bucket,
            npk_sensor_raw_hex=self.npk_sensor_raw_hex,
            water_flow_lpm=self.water_flow_lpm,
            water_pressure_bar=self.water_pressure_bar,
            tamper_detected=self.tamper_detected,
            enclosure_temp_c=self.enclosure_temp_c,
            fault_flags=self.fault_flags,
            sensor_health_json=dict(self.sensor_health_json),
            firmware_version=self.firmware_version,
            uptime_seconds=self.uptime_seconds,
            cadence_mode=self.cadence_mode,
            backlog_pending=self.backlog_pending,
            validation_warn=self.validation_warn,
        )




# ===========================================================================
# Round 16 — raw-values telemetry (`agro-guardian/telemetry/v2-raw`)
# ===========================================================================
# Firmware sends raw sensor outputs; server applies per-device calibration
# from the ``device_calibration`` table. The wire format has two nested
# blocks:
#   * ``raw_readings``   — everything the Sub Node measured (CSV over LoRa,
#                          then JSON'd by the Main Node)
#   * ``master_readings`` — everything the Main Node measured itself
#                          (weather station + LoRa link quality)
#
# All three models are ``extra="forbid"`` so an unknown field is a hard
# validation error — no silent field drops between firmware and server.
# ---------------------------------------------------------------------------


class RawReadings(BaseModel):
    """Raw Sub Node measurements, keyed exactly as the firmware emits them."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    # ADC counts (10-bit)
    soil_adc: int = Field(ge=0, le=1023)
    battery_adc: int = Field(ge=0, le=1023)
    pressure_adc: int = Field(ge=0, le=1023)

    # Pulse counters (flow sensor, hall-effect)
    flow_pulses_window: int = Field(ge=0)
    flow_pulses_total: int = Field(ge=0)

    # DS18B20 emits °C directly (sensor's own calibration is in the chip);
    # nullable because the firmware reports None as JSON null when the
    # DS18B20 is disconnected.
    ds18b20_temp_c: SafeDecimal = None

    # NPK Modbus block. `npk_ok=False` means this cycle's read failed CRC
    # or timed out; the raw fields below should be treated as stale.
    npk_ok: bool
    npk_temp_raw: int          # register (°C x10, backend divides)
    npk_moisture_raw: int      # register (% x10, backend divides)
    npk_ec_us_cm: int          # sensor-native µS/cm
    npk_ph_raw: int            # register (pH x100, backend divides)
    npk_nitrogen_mg_kg: int    # sensor-native mg/kg
    npk_phosphorus_mg_kg: int
    npk_potassium_mg_kg: int

    sub_node_fw: str = Field(min_length=1, max_length=64)


class MasterReadings(BaseModel):
    """Main Node's own sensor readings, bundled with each Sub Node telemetry.

    Backend writes these to ``weather_station_readings`` in a follow-up round
    (Round 17); today they're carried on the payload and dropped at the
    ingest boundary so the field team can watch them via ``mosquitto_sub``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    bme280_temp_c: SafeDecimal = None
    bme280_humidity_pct: SafeDecimal = None
    bme280_pressure_pa: SafeDecimal = None
    ina219_bus_v: SafeDecimal = None
    ina219_current_ma: SafeDecimal = None
    rain_pulses_window: int = Field(default=0, ge=0)
    wind_pulses_window: int = Field(default=0, ge=0)
    wind_dir_adc: int = Field(default=0, ge=0, le=4095)  # ESP32 12-bit ADC
    lora_rssi_dbm: int = Field(ge=-150, le=20)
    lora_snr_db: SafeDecimal = None


class TelemetryInRaw(BaseModel):
    """Raw-values telemetry as emitted by ``viraai-*-1.0.0-raw`` firmware.

    Round 16 accepts this alongside the calibrated ``TelemetryIn``; the
    parser dispatches on the ``$schema`` field. ``to_domain(calibration)``
    applies per-device calibration constants to produce the same
    :class:`Reading` object that the calibrated path emits — the rest of
    the pipeline is untouched.
    """

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )

    # --- Discriminator ---
    schema_id: Literal["agro-guardian/telemetry/v2-raw"] = Field(
        alias="$schema",
        description="Raw-values schema; server applies calibration before Reading construction.",
    )

    # --- Identity ---
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    farm_id: uuid.UUID
    plot_id: str = Field(min_length=1, max_length=64)
    node_id: str = Field(min_length=1, max_length=64)

    # --- Timing ---
    recorded_at: datetime
    received_at_master: datetime

    # --- Transport ---
    transmission_type: TransmissionType

    # --- Sub Node's per-cycle sequence counter (survives reset by using
    # firmware bootcount too; on its own it's still useful for detecting
    # gaps and out-of-order delivery). ---
    seq: int = Field(default=0, ge=0)

    # --- Nested measurement blocks ---
    raw_readings: RawReadings
    master_readings: MasterReadings

    # --- Metadata ---
    firmware_version: str | None = Field(default=None, max_length=64)
    main_node_id: str | None = Field(default=None, max_length=64)

    @field_validator("recorded_at", "received_at_master")
    @classmethod
    def _must_be_aware(cls, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            raise ValueError("datetime must be timezone-aware (RFC 3339 with offset)")
        return dt.astimezone(UTC)

    # ------------------------------------------------------------------
    # Boundary -> domain (calibration required)
    # ------------------------------------------------------------------
    def to_domain(self, calibration: DeviceCalibration) -> Reading:
        """Apply per-device calibration and build the pure domain Reading.

        Every raw sensor field is converted here. Fields that the raw
        firmware doesn't send (valve, pump, tamper flags, cadence mode)
        are left as their Reading defaults. ``master_readings`` are
        not persisted to ``node_sensor_readings`` — they're carried on
        the payload for follow-up work in Round 17.
        """
        rr = self.raw_readings

        # DS18B20 already reports °C (sensor's own factory calibration).
        soil_temp_c: Decimal | None = rr.ds18b20_temp_c

        # NPK-derived values only trust the register set if this cycle's
        # Modbus read passed CRC. Otherwise leave them ``None`` so the
        # rule engine treats the fields as "no data" rather than "0".
        if rr.npk_ok:
            soil_ph = calibrate_npk_ph(rr.npk_ph_raw, calibration)
            soil_ec_ms_cm = npk_ec_ms_cm(rr.npk_ec_us_cm)
            soil_n_mg_kg = Decimal(rr.npk_nitrogen_mg_kg)
            soil_p_mg_kg = Decimal(rr.npk_phosphorus_mg_kg)
            soil_k_mg_kg = Decimal(rr.npk_potassium_mg_kg)
            soil_temp_rootzone_c = calibrate_npk_temp_c(rr.npk_temp_raw, calibration)
            npk_moist_pct = calibrate_npk_moisture_pct(rr.npk_moisture_raw, calibration)
        else:
            soil_ph = None
            soil_ec_ms_cm = None
            soil_n_mg_kg = None
            soil_p_mg_kg = None
            soil_k_mg_kg = None
            soil_temp_rootzone_c = None
            npk_moist_pct = None

        # Firmware version string on the reading — prefer the Sub Node's
        # own string (transmitted in raw_readings.sub_node_fw); fall back
        # to the top-level metadata field if the Sub Node string is empty.
        fw = rr.sub_node_fw or self.firmware_version

        # Carry the master_readings + calibration_version through
        # ``sensor_health_json`` so downstream tooling can inspect them
        # without a schema change. Round 17 will move these to their own
        # tables; until then this is the least surprising landing zone.
        sensor_health: dict[str, Any] = {
            "calibration_version": calibration.calibration_version,
            "seq": self.seq,
            "main_node_id": self.main_node_id,
            "master_readings": self.master_readings.model_dump(),
            "flow_pulses_total": rr.flow_pulses_total,
            "npk_ok": rr.npk_ok,
        }

        return Reading(
            tenant_id=self.tenant_id,
            farmer_id=self.farmer_id,
            farm_id=self.farm_id,
            plot_id=self.plot_id,
            node_id=self.node_id,
            recorded_at=self.recorded_at,
            received_at_master=self.received_at_master,
            transmission_type=self.transmission_type,
            signal_rssi_dbm=self.master_readings.lora_rssi_dbm,
            # Battery
            battery_voltage_v=calibrate_battery_v(rr.battery_adc, calibration),
            # Soil moisture — capacitive probe reading only. NPK probe's
            # own moisture reading is carried separately in soil_moisture_2
            # so the Farm Brain gets both signals.
            soil_moisture_1_pct=calibrate_soil_moisture_pct(rr.soil_adc, calibration),
            soil_moisture_2_pct=npk_moist_pct,
            soil_moisture_avg_pct=calibrate_soil_moisture_pct(rr.soil_adc, calibration),
            # Soil temperature — DS18B20 for the primary rootzone probe,
            # NPK register for rootzone reference.
            soil_temp_c=soil_temp_c,
            soil_temp_rootzone_c=soil_temp_rootzone_c,
            # Soil chemistry (NPK)
            soil_ph=soil_ph,
            soil_ec_ms_cm=soil_ec_ms_cm,
            soil_n_mg_kg=soil_n_mg_kg,
            soil_p_mg_kg=soil_p_mg_kg,
            soil_k_mg_kg=soil_k_mg_kg,
            # Water
            water_flow_lpm=calibrate_flow_lpm(rr.flow_pulses_window, calibration),
            water_pressure_bar=calibrate_pressure_bar(rr.pressure_adc, calibration),
            # Diagnostics
            sensor_health_json=sensor_health,
            firmware_version=fw,
        )


# ---------------------------------------------------------------------------
# Parse dispatcher
# ---------------------------------------------------------------------------
# Per Roadmap §1.10 / §2.2 the MQTT topic shape is
#   agro/v2/<tenant>/<farm>/<node>/<kind>
# where <kind> is one of: telemetry | weather | heartbeat | alert | health.
#
# Round 5 implements ``telemetry`` only. Adding the others is one new model
# class + one elif branch here; the topic-parsing logic doesn't change.


TOPIC_KIND_TELEMETRY: str = "telemetry"
"""The only message kind Round 5 routes. Other kinds (weather, heartbeat,
alert, health) raise :class:`UnknownTopicKindError` until their schemas
land in later rounds."""




class TopicParseError(ValueError):
    """The topic string did not match ``agro/v2/<tenant>/<farm>/<node>/<kind>``."""




class UnknownTopicKindError(ValueError):
    """The topic kind is well-formed but not yet implemented (e.g. weather)."""




def _split_topic(topic: str) -> tuple[str, str, str, str]:
    """Return (tenant, farm, node, kind) or raise :class:`TopicParseError`."""
    parts = topic.split("/")
    if len(parts) != 6 or parts[0] != "agro" or parts[1] != "v2":
        raise TopicParseError(
            f"expected topic 'agro/v2/<tenant>/<farm>/<node>/<kind>', got {topic!r}"
        )
    _, _, tenant, farm, node, kind = parts
    if not (tenant and farm and node and kind):
        raise TopicParseError(f"empty path segment in topic {topic!r}")
    return tenant, farm, node, kind




def parse_inbound(topic: str, raw: bytes) -> TelemetryIn | TelemetryInRaw:
    """Dispatch an MQTT payload to the right pydantic model.

    Two schemas are supported today:

    * ``agro-guardian/telemetry/v2``      → :class:`TelemetryIn` (calibrated
      fields; original wire format used by ``fake_main_node.py`` and any
      producer that does its own calibration).
    * ``agro-guardian/telemetry/v2-raw``  → :class:`TelemetryInRaw` (Round
      16; the ``viraai-*-1.0.0-raw`` firmware). Server applies per-device
      calibration before ``to_domain(...)`` is called by the broker.

    Caller (the ingest worker) handles the dispatcher's errors:

    * :class:`TopicParseError`             — malformed topic
    * :class:`UnknownTopicKindError`       — topic kind not implemented
    * :class:`pydantic.ValidationError`    — payload malformed
    * :class:`json.JSONDecodeError`        — payload not JSON
    * :class:`ValueError`                  — unknown ``$schema``

    On success the returned model is frozen and ready for ``to_domain()``.
    ``TelemetryInRaw.to_domain`` requires a ``DeviceCalibration`` argument
    that the broker fetches from the calibration repo.
    """
    _, _, _, kind = _split_topic(topic)
    if kind != TOPIC_KIND_TELEMETRY:
        raise UnknownTopicKindError(
            f"kind {kind!r} not implemented (only {TOPIC_KIND_TELEMETRY!r} today)"
        )
    # json.loads raises JSONDecodeError on bad payload; that subclasses
    # ValueError so the caller's broad except is enough.
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(
            f"MQTT payload must be a JSON object, got {type(payload).__name__}"
        )

    schema_id = payload.get("$schema")
    if schema_id == SCHEMA_TELEMETRY_V2:
        return TelemetryIn.model_validate(payload)
    if schema_id == SCHEMA_TELEMETRY_V2_RAW:
        return TelemetryInRaw.model_validate(payload)
    raise ValueError(
        f"unknown $schema {schema_id!r}; expected {SCHEMA_TELEMETRY_V2!r} "
        f"or {SCHEMA_TELEMETRY_V2_RAW!r}"
    )




__all__ = [
    "SCHEMA_TELEMETRY_V2",
    "SCHEMA_TELEMETRY_V2_RAW",
    "TOPIC_KIND_TELEMETRY",
    "MasterReadings",
    "RawReadings",
    "SafeDecimal",
    "TelemetryIn",
    "TelemetryInRaw",
    "TopicParseError",
    "UnknownTopicKindError",
    "parse_inbound",
]
