"""Event models: irrigation_events, electricity_schedule_log,
water_source_status, farmer_actions.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
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
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"

    irrigation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str] = mapped_column(Text, ForeignKey("plots.plot_id"), nullable=False)
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_seasons.season_id"), nullable=False
    )
    started_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    water_liters: Mapped[float | None] = mapped_column(Double)
    flow_rate_lpm_avg: Mapped[float | None] = mapped_column(Double)
    trigger_type: Mapped[str] = mapped_column(String, nullable=False)
    ai_suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_suggestions.suggestion_id")
    )
    soil_moisture_before: Mapped[float | None] = mapped_column(Double)
    soil_moisture_after: Mapped[float | None] = mapped_column(Double)
    valve_id: Mapped[str | None] = mapped_column(Text)
    pump_id: Mapped[str | None] = mapped_column(Text)
    water_source_used: Mapped[str | None] = mapped_column(String)
    electricity_available: Mapped[bool | None] = mapped_column(Boolean)
    weather_at_irrigation: Mapped[Any | None] = mapped_column(JSONB)
    crop_stage_at_time: Mapped[str | None] = mapped_column(Text)
    ai_recommended_liters: Mapped[float | None] = mapped_column(Double)
    variance_liters: Mapped[float | None] = mapped_column(Double)
    dry_run_event: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)


class ElectricityScheduleLog(Base):
    __tablename__ = "electricity_schedule_log"

    elec_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    electricity_on_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    electricity_off_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    detection_method: Mapped[str | None] = mapped_column(String)
    pump_used_during: Mapped[bool | None] = mapped_column(Boolean)
    pattern_confidence_pct: Mapped[float | None] = mapped_column(Double)
    detected_schedule_json: Mapped[Any | None] = mapped_column(JSONB)
    schedule_changed_flag: Mapped[bool | None] = mapped_column(Boolean)
    last_schedule_change_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    ai_irrigation_adapted: Mapped[bool | None] = mapped_column(Boolean)
    notes: Mapped[str | None] = mapped_column(Text)


class WaterSourceStatus(Base):
    __tablename__ = "water_source_status"

    source_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    water_level_cm: Mapped[float | None] = mapped_column(Double)
    water_level_pct: Mapped[float | None] = mapped_column(Double)
    water_level_liters_estimate: Mapped[float | None] = mapped_column(Double)
    level_status: Mapped[str | None] = mapped_column(String)
    turbidity_ntu: Mapped[float | None] = mapped_column(Double)
    water_temp_c: Mapped[float | None] = mapped_column(Double)
    water_ph: Mapped[float | None] = mapped_column(Double)
    water_ec_ms_cm: Mapped[float | None] = mapped_column(Double)
    pump_drawdown_cm: Mapped[float | None] = mapped_column(Double)
    recovery_rate_cm_per_hour: Mapped[float | None] = mapped_column(Double)
    recharge_status: Mapped[str | None] = mapped_column(String)
    alert_sent: Mapped[bool | None] = mapped_column(Boolean)
    sensor_id: Mapped[str | None] = mapped_column(Text)


class FarmerAction(Base):
    __tablename__ = "farmer_actions"

    action_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    plot_id: Mapped[str | None] = mapped_column(Text, ForeignKey("plots.plot_id"))
    season_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_seasons.season_id"), nullable=False
    )
    action_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    action_time: Mapped[datetime.time | None] = mapped_column(Time)
    action_type: Mapped[str] = mapped_column(String, nullable=False)
    ai_suggestion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_suggestions.suggestion_id")
    )
    ai_suggested: Mapped[bool | None] = mapped_column(Boolean)
    farmer_followed_ai: Mapped[bool | None] = mapped_column(Boolean)
    water_liters: Mapped[float | None] = mapped_column(Double)
    fertilizer_name: Mapped[str | None] = mapped_column(Text)
    fertilizer_qty_kg: Mapped[float | None] = mapped_column(Double)
    fertilizer_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pesticide_name: Mapped[str | None] = mapped_column(Text)
    pesticide_qty_ml_or_g: Mapped[float | None] = mapped_column(Double)
    pesticide_area_acre: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pesticide_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    labour_cost_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    equipment_used: Mapped[str | None] = mapped_column(Text)
    weather_at_action: Mapped[Any | None] = mapped_column(JSONB)
    farmer_note: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String, nullable=False)
    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
