"""Postgres adapter for :class:`DeviceCalibrationRepo`.

Ingest calls this on every message that arrives with
``$schema=agro-guardian/telemetry/v2-raw``. Steady-state traffic is a
handful of Sub Nodes emitting once every ~16 s, so a small time-boxed
in-process cache keeps 99 % of lookups off the wire without introducing
a full connection pool. The cache is invalidated on TTL — no NOTIFY
plumbing required for the pilot's ~2-plot scope.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.domain.device_calibration import DeviceCalibration

CACHE_TTL_SECONDS: float = 60.0
"""How long a fetched calibration row is trusted before we re-query.

60 s is a compromise: field edits made in psql are visible within a
minute, but the ingest broker never touches Postgres more than once
per (device, minute) even at 1 Hz sensor cadence.
"""


@dataclass(slots=True)
class _CacheEntry:
    calibration: DeviceCalibration | None
    fetched_at: float


class PgDeviceCalibrationRepo:
    """Small-TTL cached lookup of ``device_calibration`` rows.

    Not thread-safe; the ingest broker is single-threaded (drain loop
    runs on the asyncio loop). Multiple broker instances would each
    keep their own cache — that's fine at pilot scale.
    """

    def __init__(
        self,
        sessionmaker: async_sessionmaker,
        *,
        ttl_seconds: float = CACHE_TTL_SECONDS,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._ttl = ttl_seconds
        self._cache: dict[tuple[str, str], _CacheEntry] = {}

    async def get_by_device(
        self,
        tenant_id: str,
        device_id: str,
    ) -> DeviceCalibration | None:
        key = (tenant_id, device_id)
        now = time.monotonic()

        cached = self._cache.get(key)
        if cached is not None and (now - cached.fetched_at) < self._ttl:
            return cached.calibration

        # Cache miss or stale — hit the DB.
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except (ValueError, TypeError):
            # Malformed tenant_id can never match a row; short-circuit + cache
            # the miss so we don't retry on every message.
            self._cache[key] = _CacheEntry(calibration=None, fetched_at=now)
            return None

        async with self._sessionmaker() as session:
            row = (
                await session.execute(
                    text(
                        """
                        SELECT
                            tenant_id::text        AS tenant_id,
                            device_id,
                            soil_dry_adc,
                            soil_wet_adc,
                            battery_vref_v,
                            battery_divider_ratio,
                            pressure_offset_v,
                            pressure_scale_bar_per_v,
                            flow_pulses_per_litre,
                            flow_window_seconds,
                            npk_temp_divisor,
                            npk_moisture_divisor,
                            npk_ph_divisor,
                            calibration_version
                        FROM device_calibration
                        WHERE tenant_id = CAST(:tenant AS uuid)
                          AND device_id = :device
                        """
                    ),
                    {"tenant": str(tenant_uuid), "device": device_id},
                )
            ).mappings().first()

        if row is None:
            self._cache[key] = _CacheEntry(calibration=None, fetched_at=now)
            return None

        calibration = DeviceCalibration(
            tenant_id=row["tenant_id"],
            device_id=row["device_id"],
            soil_dry_adc=int(row["soil_dry_adc"]),
            soil_wet_adc=int(row["soil_wet_adc"]),
            battery_vref_v=Decimal(str(row["battery_vref_v"])),
            battery_divider_ratio=Decimal(str(row["battery_divider_ratio"])),
            pressure_offset_v=Decimal(str(row["pressure_offset_v"])),
            pressure_scale_bar_per_v=Decimal(str(row["pressure_scale_bar_per_v"])),
            flow_pulses_per_litre=Decimal(str(row["flow_pulses_per_litre"])),
            flow_window_seconds=Decimal(str(row["flow_window_seconds"])),
            npk_temp_divisor=Decimal(str(row["npk_temp_divisor"])),
            npk_moisture_divisor=Decimal(str(row["npk_moisture_divisor"])),
            npk_ph_divisor=Decimal(str(row["npk_ph_divisor"])),
            calibration_version=int(row["calibration_version"]),
        )
        self._cache[key] = _CacheEntry(calibration=calibration, fetched_at=now)
        return calibration

    def invalidate(self, tenant_id: str, device_id: str) -> None:
        """Drop the cached entry for ``(tenant_id, device_id)``.

        Called from ops tooling that updates a row and wants the next
        message to see the new value immediately (without waiting for
        the TTL).
        """
        self._cache.pop((tenant_id, device_id), None)


__all__ = ["CACHE_TTL_SECONDS", "PgDeviceCalibrationRepo"]
