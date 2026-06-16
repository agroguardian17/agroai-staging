"""AI models: ai_suggestions, ai_learning_log, chat_messages."""

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
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class AiSuggestion(Base):
    __tablename__ = "ai_suggestions"

    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
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
    generated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    suggestion_type: Mapped[str] = mapped_column(String, nullable=False)
    crop_age_days: Mapped[int | None] = mapped_column(Integer)
    crop_stage: Mapped[str | None] = mapped_column(Text)
    soil_moisture_at_time: Mapped[float | None] = mapped_column(Double)
    ndvi_at_time: Mapped[float | None] = mapped_column(Double)
    weather_summary_json: Mapped[Any | None] = mapped_column(JSONB)
    electricity_window_json: Mapped[Any | None] = mapped_column(JSONB)
    water_source_status: Mapped[str | None] = mapped_column(Text)
    water_action: Mapped[str | None] = mapped_column(Text)
    water_liters_suggested: Mapped[float | None] = mapped_column(Double)
    water_time_suggested: Mapped[str | None] = mapped_column(Text)
    water_reason: Mapped[str | None] = mapped_column(Text)
    fertilizer_needed: Mapped[bool | None] = mapped_column(Boolean)
    fertilizer_product: Mapped[str | None] = mapped_column(Text)
    fertilizer_qty_kg_per_acre: Mapped[float | None] = mapped_column(Double)
    fertilizer_timing: Mapped[str | None] = mapped_column(Text)
    fertilizer_reason: Mapped[str | None] = mapped_column(Text)
    micronutrient_deficiency: Mapped[str | None] = mapped_column(Text)
    micronutrient_product: Mapped[str | None] = mapped_column(Text)
    micronutrient_qty: Mapped[str | None] = mapped_column(Text)
    micronutrient_reason: Mapped[str | None] = mapped_column(Text)
    pesticide_spray_today: Mapped[bool | None] = mapped_column(Boolean)
    pesticide_product: Mapped[str | None] = mapped_column(Text)
    pesticide_dose: Mapped[str | None] = mapped_column(Text)
    pesticide_reason: Mapped[str | None] = mapped_column(Text)
    tomorrow_plan: Mapped[str | None] = mapped_column(Text)
    weekly_tip: Mapped[str | None] = mapped_column(Text)
    full_message_marathi: Mapped[str | None] = mapped_column(Text)
    whatsapp_sent: Mapped[bool | None] = mapped_column(Boolean)
    whatsapp_sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    ai_model_version: Mapped[str | None] = mapped_column(Text)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    generation_time_ms: Mapped[int | None] = mapped_column(Integer)
    # v3 (0002)
    prompt_template_version: Mapped[str | None] = mapped_column(Text)
    llm_cost_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    confidence_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    confidence_band: Mapped[str | None] = mapped_column(String)
    review_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'none'")
    )
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.user_id")
    )
    reviewed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[str | None] = mapped_column(Text)


class AiLearningLog(Base):
    __tablename__ = "ai_learning_log"

    learning_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    season_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("crop_seasons.season_id"), nullable=False
    )
    suggestion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_suggestions.suggestion_id"), nullable=False
    )
    action_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("farmer_actions.action_id")
    )
    learning_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    suggestion_type: Mapped[str | None] = mapped_column(Text)
    ai_suggested_liters: Mapped[float | None] = mapped_column(Double)
    farmer_gave_liters: Mapped[float | None] = mapped_column(Double)
    water_variance_liters: Mapped[float | None] = mapped_column(Double)
    ndvi_before: Mapped[float | None] = mapped_column(Double)
    ndvi_7days_after: Mapped[float | None] = mapped_column(Double)
    ndvi_change: Mapped[float | None] = mapped_column(Double)
    moisture_before: Mapped[float | None] = mapped_column(Double)
    moisture_3days_after: Mapped[float | None] = mapped_column(Double)
    crop_health_improved: Mapped[bool | None] = mapped_column(Boolean)
    suggestion_accuracy: Mapped[str | None] = mapped_column(String)
    soil_type: Mapped[str | None] = mapped_column(Text)
    crop_stage: Mapped[str | None] = mapped_column(Text)
    weather_pattern: Mapped[str | None] = mapped_column(Text)
    water_coefficient_adjusted: Mapped[float | None] = mapped_column(Double)
    notes: Mapped[str | None] = mapped_column(Text)
    learning_applied_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int | None] = mapped_column(Integer)
    llm_cost_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    context: Mapped[Any | None] = mapped_column(JSONB)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
