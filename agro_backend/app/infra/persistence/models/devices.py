"""Device-domain models: device_registry, component_inventory,
technician_installations, service_maintenance, calibration_history.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class DeviceRegistry(Base):
    __tablename__ = "device_registry"

    device_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    device_type: Mapped[str] = mapped_column(String, nullable=False)
    serial_number: Mapped[str] = mapped_column(Text, nullable=False)
    mac_address: Mapped[str] = mapped_column(Text, nullable=False)
    qr_code_data: Mapped[str] = mapped_column(Text, nullable=False)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str | None] = mapped_column(Text, ForeignKey("plots.plot_id"))
    device_tier: Mapped[str] = mapped_column(String, nullable=False)
    manufacture_date: Mapped[datetime.date | None] = mapped_column(Date)
    batch_number: Mapped[str | None] = mapped_column(Text)
    pcb_version: Mapped[str | None] = mapped_column(Text)
    firmware_version_installed: Mapped[str | None] = mapped_column(Text)
    firmware_version_latest: Mapped[str | None] = mapped_column(Text)
    ota_pending: Mapped[bool | None] = mapped_column(Boolean)
    last_ota_update: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    last_ota_result: Mapped[str | None] = mapped_column(String)
    installation_date: Mapped[datetime.date | None] = mapped_column(Date)
    installation_technician_id: Mapped[str | None] = mapped_column(Text)
    gps_installed_lat: Mapped[float | None] = mapped_column(Double)
    gps_installed_lng: Mapped[float | None] = mapped_column(Double)
    pole_height_ft: Mapped[float | None] = mapped_column(Double)
    enclosure_type: Mapped[str | None] = mapped_column(Text)
    sim_number: Mapped[str | None] = mapped_column(Text)
    sim_provider: Mapped[str | None] = mapped_column(String)
    signal_4g_strength: Mapped[str | None] = mapped_column(String)
    last_heartbeat_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    heartbeat_interval_min: Mapped[int | None] = mapped_column(Integer)
    device_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'offline'")
    )
    warranty_expiry: Mapped[datetime.date | None] = mapped_column(Date)
    total_uptime_hours: Mapped[float | None] = mapped_column(Double)
    total_downtime_hours: Mapped[float | None] = mapped_column(Double)
    fault_count: Mapped[int | None] = mapped_column(Integer)
    replacement_flag: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)
    # v3 (0002)
    broker_secret_hash: Mapped[str | None] = mapped_column(Text)
    calibration_json: Mapped[Any] = mapped_column(
        JSONB, nullable=False, server_default=text("'{}'")
    )


class ComponentInventory(Base):
    __tablename__ = "component_inventory"

    component_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        Text, ForeignKey("device_registry.device_id"), nullable=False
    )
    component_name: Mapped[str] = mapped_column(Text, nullable=False)
    component_category: Mapped[str] = mapped_column(String, nullable=False)
    manufacturer: Mapped[str | None] = mapped_column(Text)
    model_number: Mapped[str | None] = mapped_column(Text)
    serial_number: Mapped[str | None] = mapped_column(Text)
    purchase_date: Mapped[datetime.date | None] = mapped_column(Date)
    purchase_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    supplier: Mapped[str | None] = mapped_column(Text)
    warranty_months: Mapped[int | None] = mapped_column(Integer)
    installation_date: Mapped[datetime.date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String, nullable=False, server_default=text("'active'"))
    last_calibration_date: Mapped[datetime.date | None] = mapped_column(Date)
    next_calibration_due: Mapped[datetime.date | None] = mapped_column(Date)
    calibration_values_json: Mapped[Any | None] = mapped_column(JSONB)
    fault_history_json: Mapped[Any | None] = mapped_column(JSONB)
    replacement_component_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    notes: Mapped[str | None] = mapped_column(Text)


class TechnicianInstallation(Base):
    __tablename__ = "technician_installations"

    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    technician_id: Mapped[str] = mapped_column(Text, nullable=False)
    technician_name: Mapped[str] = mapped_column(Text, nullable=False)
    technician_phone: Mapped[str] = mapped_column(Text, nullable=False)
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    visit_type: Mapped[str] = mapped_column(String, nullable=False)
    visit_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    arrival_time: Mapped[datetime.time | None] = mapped_column(Time)
    departure_time: Mapped[datetime.time | None] = mapped_column(Time)
    duration_hours: Mapped[float | None] = mapped_column(Double)
    devices_installed_json: Mapped[Any | None] = mapped_column(JSONB)
    nodes_installed_count: Mapped[int | None] = mapped_column(Integer)
    solar_panels_installed: Mapped[int | None] = mapped_column(Integer)
    poles_installed: Mapped[int | None] = mapped_column(Integer)
    cable_meters_laid: Mapped[float | None] = mapped_column(Double)
    soil_type_observed: Mapped[str | None] = mapped_column(Text)
    moisture_at_install: Mapped[float | None] = mapped_column(Double)
    well_depth_measured_ft: Mapped[int | None] = mapped_column(Integer)
    borewell_yield_tested_lpm: Mapped[float | None] = mapped_column(Double)
    farm_pond_level_pct: Mapped[float | None] = mapped_column(Double)
    water_quality_check: Mapped[str | None] = mapped_column(Text)
    electricity_tested: Mapped[bool | None] = mapped_column(Boolean)
    signal_4g_tested: Mapped[bool | None] = mapped_column(Boolean)
    signal_4g_result: Mapped[str | None] = mapped_column(String)
    whatsapp_test_sent: Mapped[bool | None] = mapped_column(Boolean)
    sensors_calibrated: Mapped[bool | None] = mapped_column(Boolean)
    farmer_training_done: Mapped[bool | None] = mapped_column(Boolean)
    farmer_training_topics: Mapped[str | None] = mapped_column(Text)
    installation_photos_urls: Mapped[Any | None] = mapped_column(JSONB)
    issues_found: Mapped[str | None] = mapped_column(Text)
    issues_resolved: Mapped[str | None] = mapped_column(Text)
    pending_work: Mapped[str | None] = mapped_column(Text)
    farmer_signature_collected: Mapped[bool | None] = mapped_column(Boolean)
    installation_quality_score: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    next_service_due: Mapped[datetime.date | None] = mapped_column(Date)


class ServiceMaintenance(Base):
    __tablename__ = "service_maintenance"

    service_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        Text, ForeignKey("device_registry.device_id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    technician_id: Mapped[str | None] = mapped_column(Text)
    service_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    service_type: Mapped[str] = mapped_column(String, nullable=False)
    complaint_description: Mapped[str | None] = mapped_column(Text)
    root_cause: Mapped[str | None] = mapped_column(Text)
    action_taken: Mapped[str | None] = mapped_column(Text)
    components_replaced_json: Mapped[Any | None] = mapped_column(JSONB)
    spare_parts_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    labour_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    downtime_hours: Mapped[float | None] = mapped_column(Double)
    resolution_time_hours: Mapped[float | None] = mapped_column(Double)
    firmware_updated: Mapped[bool | None] = mapped_column(Boolean)
    new_firmware_version: Mapped[str | None] = mapped_column(Text)
    service_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'pending'")
    )
    farmer_satisfaction: Mapped[int | None] = mapped_column(Integer)
    warranty_claim: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)


class CalibrationHistory(Base):
    __tablename__ = "calibration_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    device_id: Mapped[str] = mapped_column(
        Text, ForeignKey("device_registry.device_id"), nullable=False
    )
    sensor: Mapped[str] = mapped_column(Text, nullable=False)
    slope: Mapped[Decimal | None] = mapped_column(Numeric)
    intercept: Mapped[Decimal | None] = mapped_column(Numeric)
    lab_id: Mapped[str | None] = mapped_column(Text)
    calibrated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
