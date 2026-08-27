"""ORM model for the ``device_calibration`` table (migration 0012).

Per-Sub-Node calibration constants used by the raw-payload ingest path
(`agro-guardian/telemetry/v2-raw`). The table + trigger are created by
Alembic 0012; this ORM model exists so `Base.metadata.tables` reflects
the full schema for tests and introspection tools.
"""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class DeviceCalibration(Base):
    """Per-device calibration constants; composite PK ``(tenant_id, device_id)``."""

    __tablename__ = "device_calibration"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        primary_key=True,
    )
    device_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("device_registry.device_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Soil moisture (ADC counts)
    soil_dry_adc: Mapped[int] = mapped_column(Integer, nullable=False)
    soil_wet_adc: Mapped[int] = mapped_column(Integer, nullable=False)

    # Battery voltage
    battery_vref_v: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    battery_divider_ratio: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)

    # Pressure transducer
    pressure_offset_v: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    pressure_scale_bar_per_v: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)

    # Flow sensor
    flow_pulses_per_litre: Mapped[Decimal] = mapped_column(Numeric(8, 3), nullable=False)
    flow_window_seconds: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)

    # NPK register scaling
    npk_temp_divisor: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    npk_moisture_divisor: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)
    npk_ph_divisor: Mapped[Decimal] = mapped_column(Numeric(6, 3), nullable=False)

    # Audit
    calibration_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_by: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
