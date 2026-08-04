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

from app.domain.sensor import CadenceMode, Reading, TransmissionType

# Canonical $schema discriminator. Producers (Sub Node firmware via the
# Main Node 4G uplink) write this string; the parser dispatches on the
# topic suffix and validates the $schema field as a final guard.
SCHEMA_TELEMETRY_V2: str = "agro-guardian/telemetry/v2"




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




def parse_inbound(topic: str, raw: bytes) -> TelemetryIn:
    """Dispatch an MQTT payload to the right pydantic model.


    Round 5 implements telemetry only. Caller (the ingest worker in
    Round 7) handles the dispatcher's errors:


    * :class:`TopicParseError`  -> log + drop (malformed topic; producer bug)
    * :class:`UnknownTopicKindError` -> log + drop (kind not implemented yet)
    * :class:`pydantic.ValidationError` -> log + drop (payload malformed)
    * :class:`json.JSONDecodeError` -> log + drop (payload not JSON)


    On success the returned model is frozen and ready for ``to_domain()``.
    """
    _, _, _, kind = _split_topic(topic)
    if kind != TOPIC_KIND_TELEMETRY:
        raise UnknownTopicKindError(
            f"kind {kind!r} not implemented in Round 5 (only {TOPIC_KIND_TELEMETRY!r} so far)"
        )
    # json.loads raises JSONDecodeError on bad payload; that subclasses
    # ValueError so the caller's broad except is enough.
    payload = json.loads(raw)
    return TelemetryIn.model_validate(payload)




__all__ = [
    "SCHEMA_TELEMETRY_V2",
    "TOPIC_KIND_TELEMETRY",
    "SafeDecimal",
    "TelemetryIn",
    "TopicParseError",
    "UnknownTopicKindError",
    "parse_inbound",
]
