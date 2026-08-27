"""Postgres adapter for :class:`MainNodeReadingRepo` (Round 17.5).

Concrete implementation against the ``main_node_readings`` table from
migration 0013. Mirrors the shape + conventions of
``app.infra.persistence.pg_reading_repo.PgReadingRepo``:

* Idempotent INSERT via ``ON CONFLICT DO NOTHING RETURNING reading_id``.
* Decimal-safe conversion at the storage boundary (schema stores
  ``DOUBLE PRECISION`` for the numeric readings; domain uses ``Decimal``).
* No JSONB column — the heartbeat has no sensor_health equivalent to
  persist. If ``sensor_health_json`` is ever populated by upstream, we
  drop it silently; it's a domain-only convenience field.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.main_node_reading import MainNodeReading

_INSERT_COLUMNS: tuple[str, ...] = (
    "tenant_id",
    "farm_id",
    "main_node_id",
    "recorded_at",
    "received_at_master",
    "time_source",
    "sub_node_online",
    "sub_node_silence_ms",
    "bme280_temp_c",
    "bme280_humidity_pct",
    "bme280_pressure_pa",
    "ina219_bus_v",
    "ina219_current_ma",
    "rain_pulses_window",
    "wind_pulses_window",
    "wind_dir_adc",
    "firmware_version",
)


def _insert_sql() -> str:
    cols = ", ".join(_INSERT_COLUMNS)
    placeholders = ", ".join(f":{c}" for c in _INSERT_COLUMNS)
    return (
        f"INSERT INTO main_node_readings ({cols}) VALUES ({placeholders}) "
        "ON CONFLICT (main_node_id, recorded_at) DO NOTHING "
        "RETURNING reading_id"
    )


_SELECT_COLUMNS = "reading_id, " + ", ".join(_INSERT_COLUMNS)


def _to_decimal(v: float | int | Decimal | None) -> Decimal | None:
    """Storage -> domain Decimal conversion (via ``str`` to dodge float artefacts)."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    return Decimal(str(v))


def _decimal_to_float(v: Decimal | None) -> float | None:
    return None if v is None else float(v)


def _bind_params(reading: MainNodeReading) -> dict[str, Any]:
    return {
        "tenant_id": reading.tenant_id,
        "farm_id": reading.farm_id,
        "main_node_id": reading.main_node_id,
        "recorded_at": reading.recorded_at,
        "received_at_master": reading.received_at_master,
        "time_source": reading.time_source,
        "sub_node_online": reading.sub_node_online,
        "sub_node_silence_ms": reading.sub_node_silence_ms,
        "bme280_temp_c": _decimal_to_float(reading.bme280_temp_c),
        "bme280_humidity_pct": _decimal_to_float(reading.bme280_humidity_pct),
        "bme280_pressure_pa": _decimal_to_float(reading.bme280_pressure_pa),
        "ina219_bus_v": _decimal_to_float(reading.ina219_bus_v),
        "ina219_current_ma": _decimal_to_float(reading.ina219_current_ma),
        "rain_pulses_window": reading.rain_pulses_window,
        "wind_pulses_window": reading.wind_pulses_window,
        "wind_dir_adc": reading.wind_dir_adc,
        "firmware_version": reading.firmware_version,
    }


def _row_to_reading(row: Any) -> MainNodeReading:
    return MainNodeReading(
        tenant_id=row.tenant_id,
        farm_id=row.farm_id,
        main_node_id=row.main_node_id,
        recorded_at=row.recorded_at,
        received_at_master=row.received_at_master,
        time_source=row.time_source,
        sub_node_online=bool(row.sub_node_online),
        sub_node_silence_ms=int(row.sub_node_silence_ms or 0),
        bme280_temp_c=_to_decimal(row.bme280_temp_c),
        bme280_humidity_pct=_to_decimal(row.bme280_humidity_pct),
        bme280_pressure_pa=_to_decimal(row.bme280_pressure_pa),
        ina219_bus_v=_to_decimal(row.ina219_bus_v),
        ina219_current_ma=_to_decimal(row.ina219_current_ma),
        rain_pulses_window=int(row.rain_pulses_window or 0),
        wind_pulses_window=int(row.wind_pulses_window or 0),
        wind_dir_adc=int(row.wind_dir_adc or 0),
        firmware_version=row.firmware_version,
    )


class PgMainNodeReadingRepo:
    """Concrete :class:`MainNodeReadingRepo` against Postgres."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def save(self, reading: MainNodeReading) -> int | None:
        stmt = text(_insert_sql())
        async with self._sm() as session:
            res = await session.execute(stmt, _bind_params(reading))
            row = res.first()
            await session.commit()
        if row is None:
            return None
        return int(row.reading_id)

    async def latest_for_node(
        self, main_node_id: str, limit: int
    ) -> list[MainNodeReading]:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS} FROM main_node_readings "
            "WHERE main_node_id = :main_node_id "
            "ORDER BY recorded_at DESC LIMIT :limit"
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt, {"main_node_id": main_node_id, "limit": limit}
            )
            return [_row_to_reading(r) for r in res.all()]

    async def most_recent(self, main_node_id: str) -> MainNodeReading | None:
        rows = await self.latest_for_node(main_node_id, limit=1)
        return rows[0] if rows else None


__all__ = ["PgMainNodeReadingRepo"]
