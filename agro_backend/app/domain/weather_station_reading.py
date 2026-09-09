"""Weather station reading — pure domain type (Round 17).

The Main Node bundles its own weather sensor readings (BME280 + INA219 +
rain-gauge + anemometer + wind vane) with every Sub Node telemetry payload
(as ``master_readings``) *and* with every v2-master heartbeat.

Round 16 carried the block through ``Reading.sensor_health_json`` as a
JSONB blob — queryable but awkward. Round 17 promotes it to its own
Main-Node-keyed table (``weather_station_readings``, migration 0001 +
partitioning in 0005). This module is the pure in-memory shape.

PURE module — stdlib + ``Decimal`` + ``uuid`` + ``datetime`` only.
Enforced by ``tests/domain/test_domain_purity.py``.

Design notes:

* Immutable frozen dataclass. ``with_(...)`` helper mirrors ``Reading``
  and ``MainNodeReading`` for the broker-side clock-skew normaliser.
* All numeric measurements are ``Decimal | None`` — never ``float``
  (.cursorrules #3).
* Includes derived buckets (temp min/max) as optional fields; the
  ingest boundary leaves them as ``None`` and a rollup job (Round 18)
  fills them from windowed queries.
* The v2.1 firmware (2026-09-05) added ``wind_gust_pulses_max``; the
  domain field is ``wind_gust_pulses_max`` (raw pulses; km/h conversion
  is a downstream rollup).
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any


@dataclass(frozen=True, slots=True)
class WeatherStationReading:
    """One row of ``weather_station_readings``. Immutable, all-Decimal."""

    tenant_id: uuid.UUID
    master_node_id: str
    farm_id: uuid.UUID
    recorded_at: datetime

    # BME280 weather block
    air_temp_c: Decimal | None = None
    humidity_pct: Decimal | None = None
    atmospheric_pressure_hpa: Decimal | None = None
    # Filled by the daily rollup job (Round 18), not by the ingest boundary.
    air_temp_min_c: Decimal | None = None
    air_temp_max_c: Decimal | None = None
    dew_point_c: Decimal | None = None
    heat_stress_index: Decimal | None = None
    evapotranspiration_mm: Decimal | None = None

    # Wind block. Direction stored as degrees (calibrated on the backend
    # from raw ADC) + cardinal string. Speed as km/h from pulse-window
    # rate; gust from the v2.1 max-pulse bucket.
    wind_speed_kmh: Decimal | None = None
    wind_speed_max_gust_kmh: Decimal | None = None
    wind_direction_degrees: Decimal | None = None
    wind_direction_cardinal: str | None = None

    # Rain — instant + rolling windows (rolling filled by rollup job).
    rain_mm_current_hour: Decimal | None = None
    rain_mm_today: Decimal | None = None
    rain_mm_last_7_days: Decimal | None = None
    rain_mm_this_season: Decimal | None = None

    # Optional / not on pilot Main Node.
    light_intensity_lux: Decimal | None = None
    uv_index: Decimal | None = None
    leaf_wetness_pct: Decimal | None = None
    fog_detected: bool | None = None
    fog_intensity: str | None = None
    frost_risk: bool | None = None

    # Power monitor.
    weather_station_battery_v: Decimal | None = None

    # Long-run zero-count fault detection (filled by rollup job).
    anemometer_fault: bool | None = None
    rain_gauge_fault: bool | None = None

    # Free-form audit fields; broker adds clock-skew metadata here if it
    # rewrote timestamps. Mirrors Reading / MainNodeReading pattern.
    sensor_health_json: dict[str, Any] = field(default_factory=dict)
    validation_warn: bool = False

    def with_(self, **updates: Any) -> WeatherStationReading:
        """Frozen-dataclass copy helper. Matches ``Reading.with_()`` idiom."""
        return dataclasses.replace(self, **updates)


__all__ = ["WeatherStationReading"]
