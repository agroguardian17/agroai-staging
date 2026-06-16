"""Farm-domain models: farmers, farms, plots, crop_seasons."""

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
    LargeBinary,
    Numeric,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class Farmer(Base):
    __tablename__ = "farmers"

    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    marathi_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone_primary: Mapped[str] = mapped_column(Text, nullable=False)
    phone_secondary: Mapped[str | None] = mapped_column(Text)
    whatsapp_number: Mapped[str] = mapped_column(Text, nullable=False)
    language_preference: Mapped[str] = mapped_column(String, nullable=False)
    village: Mapped[str] = mapped_column(Text, nullable=False)
    taluka: Mapped[str] = mapped_column(Text, nullable=False)
    district: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False)
    pin_code: Mapped[str | None] = mapped_column(Text)
    aadhar_number: Mapped[str | None] = mapped_column(Text)
    farmer_id_govt: Mapped[str | None] = mapped_column(Text)
    education_level: Mapped[str | None] = mapped_column(String)
    age_years: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String)
    account_created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    account_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'active'")
    )
    subscription_tier: Mapped[str] = mapped_column(String, nullable=False)
    subscription_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    subscription_end: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    payment_status: Mapped[str] = mapped_column(String, nullable=False)
    referred_by: Mapped[str | None] = mapped_column(Text)
    dealer_id: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    # v3 (0002)
    phone_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    phone_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)


class Farm(Base):
    __tablename__ = "farms"

    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    farm_name: Mapped[str | None] = mapped_column(Text)
    survey_number: Mapped[str | None] = mapped_column(Text)
    total_area_acre: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gps_lat_center: Mapped[float] = mapped_column(Double, nullable=False)
    gps_lng_center: Mapped[float] = mapped_column(Double, nullable=False)
    gps_boundary_geojson: Mapped[Any | None] = mapped_column(JSONB)
    soil_type: Mapped[str] = mapped_column(String, nullable=False)
    soil_texture: Mapped[str | None] = mapped_column(Text)
    soil_depth_cm: Mapped[int | None] = mapped_column(Integer)
    soil_organic_carbon_pct: Mapped[float | None] = mapped_column(Double)
    water_holding_capacity: Mapped[str | None] = mapped_column(String)
    terrain_type: Mapped[str | None] = mapped_column(String)
    elevation_m: Mapped[float | None] = mapped_column(Double)
    water_source_primary: Mapped[str] = mapped_column(String, nullable=False)
    water_source_secondary: Mapped[str | None] = mapped_column(String)
    well_depth_ft: Mapped[int | None] = mapped_column(Integer)
    borewell_depth_ft: Mapped[int | None] = mapped_column(Integer)
    borewell_yield_lpm: Mapped[float | None] = mapped_column(Double)
    farm_pond_capacity_liters: Mapped[float | None] = mapped_column(Double)
    irrigation_type: Mapped[str] = mapped_column(String, nullable=False)
    drip_emitter_lph: Mapped[float | None] = mapped_column(Double)
    irrigation_area_acre: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    electricity_source: Mapped[str] = mapped_column(String, nullable=False)
    solar_pump_hp: Mapped[float | None] = mapped_column(Double)
    generator_fuel: Mapped[str | None] = mapped_column(String)
    electricity_feeder_name: Mapped[str | None] = mapped_column(Text)
    electricity_schedule_known: Mapped[bool | None] = mapped_column(Boolean)
    electricity_schedule_json: Mapped[Any | None] = mapped_column(JSONB)
    road_access: Mapped[bool | None] = mapped_column(Boolean)
    mobile_network_quality: Mapped[str | None] = mapped_column(String)
    nearest_town_km: Mapped[float | None] = mapped_column(Double)
    previous_crops_json: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Plot(Base):
    __tablename__ = "plots"

    plot_id: Mapped[str] = mapped_column(Text, primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_number: Mapped[int] = mapped_column(Integer, nullable=False)
    plot_name: Mapped[str | None] = mapped_column(Text)
    area_acre: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    gps_lat: Mapped[float] = mapped_column(Double, nullable=False)
    gps_lng: Mapped[float] = mapped_column(Double, nullable=False)
    gps_boundary_geojson: Mapped[Any | None] = mapped_column(JSONB)
    node_id: Mapped[str | None] = mapped_column(Text, ForeignKey("device_registry.device_id"))
    soil_type_override: Mapped[str | None] = mapped_column(String)
    crop_current_season_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_seasons.season_id")
    )
    irrigation_valve_id: Mapped[str] = mapped_column(Text, nullable=False)
    drip_line_count: Mapped[int | None] = mapped_column(Integer)
    plot_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'active'")
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # v3 (0004); maintained by the plots_set_data_tier trigger.
    data_tier: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'satellite_only'")
    )


class CropSeason(Base):
    __tablename__ = "crop_seasons"

    season_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str] = mapped_column(Text, ForeignKey("plots.plot_id"), nullable=False)
    season_name: Mapped[str] = mapped_column(Text, nullable=False)
    season_type: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_name_marathi: Mapped[str] = mapped_column(Text, nullable=False)
    crop_name_english: Mapped[str] = mapped_column(Text, nullable=False)
    crop_variety: Mapped[str] = mapped_column(Text, nullable=False)
    crop_category: Mapped[str] = mapped_column(String, nullable=False)
    sowing_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    transplanting_date: Mapped[datetime.date | None] = mapped_column(Date)
    expected_harvest_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    actual_harvest_date: Mapped[datetime.date | None] = mapped_column(Date)
    seed_rate_kg_per_acre: Mapped[float | None] = mapped_column(Double)
    seed_cost_per_kg: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    base_fertilizer_at_sowing: Mapped[str | None] = mapped_column(Text)
    crop_age_days_today: Mapped[int | None] = mapped_column(Integer)
    current_growth_stage: Mapped[str | None] = mapped_column(Text)
    days_to_harvest: Mapped[int | None] = mapped_column(Integer)
    target_yield_qtl_per_acre: Mapped[float | None] = mapped_column(Double)
    actual_yield_qtl_per_acre: Mapped[float | None] = mapped_column(Double)
    total_water_used_liters: Mapped[float | None] = mapped_column(Double)
    total_fertilizer_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    total_pesticide_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    season_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'active'")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # v3 (0002)
    sowing_date_inferred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
