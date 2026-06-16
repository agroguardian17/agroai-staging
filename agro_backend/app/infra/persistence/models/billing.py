"""Billing/BI models: subscriptions_billing, product_performance_bi."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Double,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class SubscriptionBilling(Base):
    __tablename__ = "subscriptions_billing"

    subscription_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    plan_type: Mapped[str] = mapped_column(String, nullable=False)
    plan_start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    plan_end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    hardware_price_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    monthly_fee_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    emi_amount_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    emi_months: Mapped[int | None] = mapped_column(Integer)
    payment_mode: Mapped[str | None] = mapped_column(String)
    govt_subsidy_scheme: Mapped[str | None] = mapped_column(Text)
    subsidy_amount_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    payment_gateway: Mapped[str | None] = mapped_column(Text)
    last_payment_date: Mapped[datetime.date | None] = mapped_column(Date)
    last_payment_amount_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    next_payment_due: Mapped[datetime.date | None] = mapped_column(Date)
    total_paid_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    outstanding_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    payment_status: Mapped[str] = mapped_column(String, nullable=False)
    auto_renewal: Mapped[bool | None] = mapped_column(Boolean)
    dealer_id: Mapped[str | None] = mapped_column(Text)
    dealer_commission_pct: Mapped[float | None] = mapped_column(Double)
    churn_risk: Mapped[str | None] = mapped_column(String)
    notes: Mapped[str | None] = mapped_column(Text)


class ProductPerformanceBi(Base):
    __tablename__ = "product_performance_bi"

    perf_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_seasons.season_id"), nullable=False
    )
    district: Mapped[str] = mapped_column(Text, nullable=False)
    period_month: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    water_saved_liters: Mapped[float | None] = mapped_column(Double)
    water_saved_pct: Mapped[float | None] = mapped_column(Double)
    fertilizer_saved_kg: Mapped[float | None] = mapped_column(Double)
    fertilizer_saved_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    pesticide_sprays_ai_recommended: Mapped[int | None] = mapped_column(Integer)
    pesticide_sprays_done: Mapped[int | None] = mapped_column(Integer)
    spray_saved_count: Mapped[int | None] = mapped_column(Integer)
    spray_saved_rs: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ndvi_avg_this_season: Mapped[float | None] = mapped_column(Double)
    ndvi_improvement_vs_last_season: Mapped[float | None] = mapped_column(Double)
    yield_actual_qtl: Mapped[float | None] = mapped_column(Double)
    yield_last_season_qtl: Mapped[float | None] = mapped_column(Double)
    yield_improvement_pct: Mapped[float | None] = mapped_column(Double)
    ai_suggestions_sent: Mapped[int | None] = mapped_column(Integer)
    ai_suggestions_followed: Mapped[int | None] = mapped_column(Integer)
    ai_follow_rate_pct: Mapped[float | None] = mapped_column(Double)
    device_uptime_pct: Mapped[float | None] = mapped_column(Double)
    alerts_sent: Mapped[int | None] = mapped_column(Integer)
    alerts_critical: Mapped[int | None] = mapped_column(Integer)
    farmer_satisfaction_score: Mapped[float | None] = mapped_column(Double)
    roi_estimate_rs: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    product_effective: Mapped[bool | None] = mapped_column(Boolean)
