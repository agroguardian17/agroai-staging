"""Alert models: alerts_notifications, notification_dispatch_log, notification_dlq."""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Double,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class AlertNotification(Base):
    __tablename__ = "alerts_notifications"

    alert_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farms.farm_id"), nullable=False
    )
    farmer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("farmers.farmer_id"), nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(Text, ForeignKey("device_registry.device_id"))
    alert_type: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    alert_message_marathi: Mapped[str] = mapped_column(Text, nullable=False)
    alert_value: Mapped[float | None] = mapped_column(Double)
    alert_threshold: Mapped[float | None] = mapped_column(Double)
    triggered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    whatsapp_sent: Mapped[bool | None] = mapped_column(Boolean)
    whatsapp_sent_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    sms_sent: Mapped[bool | None] = mapped_column(Boolean)
    auto_action_taken: Mapped[str | None] = mapped_column(Text)
    farmer_acknowledged: Mapped[bool | None] = mapped_column(Boolean)
    acknowledged_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    resolved: Mapped[bool | None] = mapped_column(Boolean)
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    resolution_note: Mapped[str | None] = mapped_column(Text)
    # v3 (0002)
    dispatch_status: Mapped[str] = mapped_column(
        String, nullable=False, server_default=text("'pending'")
    )


class NotificationDispatchLog(Base):
    __tablename__ = "notification_dispatch_log"
    __table_args__ = (UniqueConstraint("alert_id", "channel", name="notification_dispatch_log_uq"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    alert_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("alerts_notifications.alert_id"), nullable=False
    )
    channel: Mapped[str] = mapped_column(String, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, nullable=False)
    error_code: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    dispatched_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class NotificationDlq(Base):
    __tablename__ = "notification_dlq"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    alert_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("alerts_notifications.alert_id")
    )
    channels: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    last_error: Mapped[str | None] = mapped_column(Text)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    moved_to_dlq_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
