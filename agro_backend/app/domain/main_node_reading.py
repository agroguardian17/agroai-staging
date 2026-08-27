"""Main Node master-only heartbeat — pure domain type.

Round 17.5 (2026-08-27 v2 firmware): the Main Node publishes a heartbeat
every ``MASTER_HEARTBEAT_MS`` (5 min) on ``$schema=v2-master``. The
:class:`MainNodeReading` is the pure in-memory representation of one such
heartbeat row, sitting between the pydantic parse boundary
(``app.infra.mqtt.schemas.TelemetryMaster``) and the Postgres repository
(``app.infra.persistence.pg_main_node_reading_repo``).

PURE module — stdlib + ``Decimal`` + ``uuid`` + ``datetime`` only.
Enforced by ``tests/domain/test_domain_purity.py``.

Design notes:

* Immutable frozen dataclass — validation-style transformations
  (broker-side clock-skew normalization) produce a new instance via
  ``dataclasses.replace``.
* All numeric measurements are ``Decimal | None`` — never ``float``
  (.cursorrules #3).
* No plot_id / farmer_id — the heartbeat is Main-Node-level (see
  ``docs/SCHEMA_DECISIONS.md`` §13.2).

Schema reference: ``alembic/versions/0013_main_node_readings.py`` and
``app/infra/persistence/models/main_node.py``.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class MainNodeReading:
    """One row of ``main_node_readings``. Immutable, all-Decimal, no floats."""

    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    main_node_id: str

    # Timing — TZ-aware datetimes (.cursorrules #2).
    recorded_at: datetime
    received_at_master: datetime

    # Firmware v1 provenance ("ntp"/"rtc"/"none"/None-if-pre-v1).
    time_source: str | None = None

    # Sub Node liveness observed by the Main Node at heartbeat assembly.
    # False when last LoRa RX is older than SUB_NODE_SILENCE_THRESHOLD_MS.
    sub_node_online: bool = True
    sub_node_silence_ms: int = 0

    # BME280 weather block (all optional — nulls survive if the sensor
    # failed init on this boot).
    bme280_temp_c: Decimal | None = None
    bme280_humidity_pct: Decimal | None = None
    bme280_pressure_pa: Decimal | None = None

    # INA219 power monitor.
    ina219_bus_v: Decimal | None = None
    ina219_current_ma: Decimal | None = None

    # Rain gauge + anemometer (Main Node's own ISR-counted pulses).
    rain_pulses_window: int = 0
    wind_pulses_window: int = 0
    wind_dir_adc: int = 0

    firmware_version: str | None = None

    # Free-form audit fields (rare — kept off the wire, added by broker
    # if it needs to record "we corrected the timestamp" style flags).
    sensor_health_json: dict[str, Any] = field(default_factory=dict)

    # Flipped by the broker's ``_normalize_clock_skew`` when the incoming
    # timestamps were rewritten to server UTC. Mirrors the field on the
    # Sub Node :class:`Reading` so the clock-skew safety net has one
    # uniform hook across both wire schemas.
    validation_warn: bool = False

    def with_(self, **updates: Any) -> MainNodeReading:
        """Frozen-dataclass copy helper. Matches ``Reading.with_(...)`` idiom."""
        return dataclasses.replace(self, **updates)


__all__ = ["MainNodeReading"]
