"""ORM model for ``main_node_readings`` (migration 0013).

The table stores Main Node heartbeat payloads emitted with
``agro-guardian/telemetry/v2-master``. These rows are infrastructure-level
readings, keyed by Main Node + timestamp rather than by plot.
"""

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
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.persistence.base import Base


class MainNodeReading(Base):
    """Main Node heartbeat/weather/power/liveness history."""

    __tablename__ = "main_node_readings"
    __table_args__ = (
        UniqueConstraint("main_node_id", "recorded_at", name="main_node_readings_idem"),
    )

    reading_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id"),
        nullable=False,
    )
    farm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("farms.farm_id"),
        nullable=False,
    )
    main_node_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("device_registry.device_id", ondelete="CASCADE"),
        nullable=False,
    )

    recorded_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    received_at_master: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    time_source: Mapped[str | None] = mapped_column(Text)

    sub_node_online: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("TRUE"),
    )
    sub_node_silence_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        server_default=text("0"),
    )

    bme280_temp_c: Mapped[float | None] = mapped_column(Double)
    bme280_humidity_pct: Mapped[float | None] = mapped_column(Double)
    bme280_pressure_pa: Mapped[float | None] = mapped_column(Double)

    ina219_bus_v: Mapped[float | None] = mapped_column(Double)
    ina219_current_ma: Mapped[float | None] = mapped_column(Double)

    rain_pulses_window: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    wind_pulses_window: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    wind_dir_adc: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )

    firmware_version: Mapped[str | None] = mapped_column(Text)
    inserted_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("NOW()"),
    )
