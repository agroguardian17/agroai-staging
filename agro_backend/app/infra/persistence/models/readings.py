"""Reading models: node_sensor_readings, weather_station_readings,
weather_forecasts, satellite_data.

The first three are range-partitioned in the database (0005). Their composite
primary keys include the partition key, and ``postgresql_partition_by`` is set
so the mapping reflects the physical table.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Double,
    Float,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class NodeSensorReading(Base):
    __tablename__ = "node_sensor_readings"
    __table_args__ = (
        UniqueConstraint("node_id", "recorded_at", name="node_sensor_readings_idem"),
        {"postgresql_partition_by": "RANGE (recorded_at)"},
    )

    reading_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("device_registry.device_id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str] = mapped_column(Text, ForeignKey("plots.plot_id"), nullable=False)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    received_at_master: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    transmission_type: Mapped[str] = mapped_column(String, nullable=False)
    signal_rssi_dbm: Mapped[int | None] = mapped_column(Integer)
    battery_voltage_v: Mapped[float | None] = mapped_column(Double)
    battery_percent: Mapped[float | None] = mapped_column(Double)
    solar_charging: Mapped[bool | None] = mapped_column(Boolean)
    soil_moisture_1_pct: Mapped[float | None] = mapped_column(Double)
    soil_moisture_2_pct: Mapped[float | None] = mapped_column(Double)
    soil_moisture_avg_pct: Mapped[float | None] = mapped_column(Double)
    soil_temp_c: Mapped[float | None] = mapped_column(Double)
    soil_temp_rootzone_c: Mapped[float | None] = mapped_column(Float)
    soil_ph: Mapped[float | None] = mapped_column(Double)
    soil_ec_ms_cm: Mapped[float | None] = mapped_column(Double)
    soil_n_mg_kg: Mapped[float | None] = mapped_column(Double)
    soil_p_mg_kg: Mapped[float | None] = mapped_column(Double)
    soil_k_mg_kg: Mapped[float | None] = mapped_column(Double)
    soil_n_bucket: Mapped[int | None] = mapped_column(SmallInteger)
    soil_p_bucket: Mapped[int | None] = mapped_column(SmallInteger)
    soil_k_bucket: Mapped[int | None] = mapped_column(SmallInteger)
    npk_sensor_raw_hex: Mapped[str | None] = mapped_column(Text)
    water_flow_lpm: Mapped[float | None] = mapped_column(Double)
    water_volume_liters_session: Mapped[float | None] = mapped_column(Double)
    water_volume_liters_cumulative: Mapped[float | None] = mapped_column(Double)
    valve_status: Mapped[str | None] = mapped_column(String)
    pump_running: Mapped[bool | None] = mapped_column(Boolean)
    pump_current_amps: Mapped[float | None] = mapped_column(Double)
    pump_runtime_minutes_today: Mapped[int | None] = mapped_column(Integer)
    dry_run_detected: Mapped[bool | None] = mapped_column(Boolean)
    tamper_detected: Mapped[bool | None] = mapped_column(Boolean)
    enclosure_temp_c: Mapped[float | None] = mapped_column(Double)
    fault_flags: Mapped[str | None] = mapped_column(Text)
    sensor_health_json: Mapped[Any | None] = mapped_column(JSONB)
    firmware_version: Mapped[str | None] = mapped_column(Text)
    uptime_seconds: Mapped[int | None] = mapped_column(Integer)
    # v3 (0005)
    cadence_mode: Mapped[str | None] = mapped_column(String)
    backlog_pending: Mapped[bool | None] = mapped_column(Boolean)
    validation_warn: Mapped[bool | None] = mapped_column(Boolean)
    low_battery_flag: Mapped[bool | None] = mapped_column(Boolean)


class WeatherStationReading(Base):
    __tablename__ = "weather_station_readings"
    __table_args__ = (
        UniqueConstraint("master_node_id", "recorded_at", name="weather_station_readings_idem"),
        {"postgresql_partition_by": "RANGE (recorded_at)"},
    )

    weather_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    master_node_id: Mapped[str] = mapped_column(
        Text, ForeignKey("device_registry.device_id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    air_temp_c: Mapped[float | None] = mapped_column(Double)
    air_temp_min_c: Mapped[float | None] = mapped_column(Double)
    air_temp_max_c: Mapped[float | None] = mapped_column(Double)
    humidity_pct: Mapped[float | None] = mapped_column(Double)
    dew_point_c: Mapped[float | None] = mapped_column(Double)
    atmospheric_pressure_hpa: Mapped[float | None] = mapped_column(Double)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Double)
    wind_speed_max_gust_kmh: Mapped[float | None] = mapped_column(Double)
    wind_direction_degrees: Mapped[float | None] = mapped_column(Double)
    wind_direction_cardinal: Mapped[str | None] = mapped_column(Text)
    rain_mm_current_hour: Mapped[float | None] = mapped_column(Double)
    rain_mm_today: Mapped[float | None] = mapped_column(Double)
    rain_mm_last_7_days: Mapped[float | None] = mapped_column(Double)
    rain_mm_this_season: Mapped[float | None] = mapped_column(Double)
    light_intensity_lux: Mapped[float | None] = mapped_column(Double)
    uv_index: Mapped[float | None] = mapped_column(Double)
    leaf_wetness_pct: Mapped[float | None] = mapped_column(Double)
    fog_detected: Mapped[bool | None] = mapped_column(Boolean)
    fog_intensity: Mapped[str | None] = mapped_column(String)
    frost_risk: Mapped[bool | None] = mapped_column(Boolean)
    heat_stress_index: Mapped[float | None] = mapped_column(Double)
    evapotranspiration_mm: Mapped[float | None] = mapped_column(Double)
    weather_station_battery_v: Mapped[float | None] = mapped_column(Double)
    anemometer_fault: Mapped[bool | None] = mapped_column(Boolean)
    rain_gauge_fault: Mapped[bool | None] = mapped_column(Boolean)


class WeatherForecast(Base):
    __tablename__ = "weather_forecasts"
    __table_args__ = ({"postgresql_partition_by": "RANGE (fetched_at)"},)

    forecast_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fetched_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    forecast_for_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    forecast_hour: Mapped[int | None] = mapped_column(Integer)
    source_api: Mapped[str] = mapped_column(Text, nullable=False)
    temp_c: Mapped[float | None] = mapped_column(Double)
    temp_min_c: Mapped[float | None] = mapped_column(Double)
    temp_max_c: Mapped[float | None] = mapped_column(Double)
    humidity_pct: Mapped[float | None] = mapped_column(Double)
    rain_probability_pct: Mapped[float | None] = mapped_column(Double)
    rain_mm_expected: Mapped[float | None] = mapped_column(Double)
    wind_speed_kmh: Mapped[float | None] = mapped_column(Double)
    wind_direction: Mapped[str | None] = mapped_column(Text)
    fog_probability_pct: Mapped[float | None] = mapped_column(Double)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Double)
    spray_suitability: Mapped[str | None] = mapped_column(String)
    irrigation_recommendation: Mapped[str | None] = mapped_column(String)
    frost_risk: Mapped[bool | None] = mapped_column(Boolean)
    heat_wave_risk: Mapped[bool | None] = mapped_column(Boolean)


class SatelliteData(Base):
    __tablename__ = "satellite_data"

    sat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str | None] = mapped_column(Text, ForeignKey("plots.plot_id"))
    satellite_source: Mapped[str] = mapped_column(String, nullable=False)
    image_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Double)
    resolution_m: Mapped[float | None] = mapped_column(Double)
    ndvi_value: Mapped[float | None] = mapped_column(Double)
    ndvi_min: Mapped[float | None] = mapped_column(Double)
    ndvi_max: Mapped[float | None] = mapped_column(Double)
    ndvi_status: Mapped[str | None] = mapped_column(String)
    ndre_value: Mapped[float | None] = mapped_column(Double)
    evi_value: Mapped[float | None] = mapped_column(Double)
    savi_value: Mapped[float | None] = mapped_column(Double)
    ndwi_value: Mapped[float | None] = mapped_column(Double)
    ndwi_status: Mapped[str | None] = mapped_column(String)
    ndmi_value: Mapped[float | None] = mapped_column(Double)
    soil_moisture_index: Mapped[float | None] = mapped_column(Double)
    soil_moisture_source: Mapped[str | None] = mapped_column(String)
    chlorophyll_index: Mapped[float | None] = mapped_column(Double)
    lai_value: Mapped[float | None] = mapped_column(Double)
    crop_health_score: Mapped[float | None] = mapped_column(Double)
    stressed_area_pct: Mapped[float | None] = mapped_column(Double)
    stressed_zone_geojson: Mapped[Any | None] = mapped_column(JSONB)
    pest_risk_index: Mapped[float | None] = mapped_column(Double)
    disease_risk_index: Mapped[float | None] = mapped_column(Double)
    yield_prediction_qtl: Mapped[float | None] = mapped_column(Double)
    raw_image_url: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    gee_task_id: Mapped[str | None] = mapped_column(Text)
