"""Main Node liveness + weather-history endpoints (Round 17 + 17.5).

Four routes under ``/api/v1/main_nodes/{main_node_id}``:

    GET /heartbeat         -> latest v2-master heartbeat (liveness)
    GET /heartbeat/history -> paginated slice of heartbeats
    GET /weather/latest    -> latest weather_station_readings row
    GET /weather/history   -> paginated slice of weather readings

All routes are tenant-scoped through the caller's JWT. If the Main Node
belongs to a different tenant we return 404 (never 403 — reveals nothing).

The routes are read-only. Ingest happens through the MQTT broker, not the
HTTP surface.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.application.ports.main_node_reading_repo import MainNodeReadingRepo
from app.application.ports.weather_station_reading_repo import (
    WeatherStationReadingRepo,
)
from app.domain.main_node_reading import MainNodeReading
from app.domain.weather_station_reading import WeatherStationReading
from app.infra.http.deps import (
    ClaimsDep,
    get_main_node_reading_repo,
    get_weather_station_reading_repo,
)

router = APIRouter(prefix="/api/v1/main_nodes", tags=["main_nodes"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class HeartbeatRow(BaseModel):
    """Serialised MainNodeReading for the ops API."""

    main_node_id: str
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    recorded_at: datetime
    received_at_master: datetime
    time_source: str | None
    sub_node_online: bool
    sub_node_silence_ms: int
    bme280_temp_c: Decimal | None
    bme280_humidity_pct: Decimal | None
    bme280_pressure_pa: Decimal | None
    ina219_bus_v: Decimal | None
    ina219_current_ma: Decimal | None
    rain_pulses_window: int
    wind_pulses_window: int
    wind_dir_adc: int
    firmware_version: str | None
    validation_warn: bool

    @classmethod
    def from_domain(cls, h: MainNodeReading) -> HeartbeatRow:
        return cls(
            main_node_id=h.main_node_id,
            tenant_id=h.tenant_id,
            farm_id=h.farm_id,
            recorded_at=h.recorded_at,
            received_at_master=h.received_at_master,
            time_source=h.time_source,
            sub_node_online=h.sub_node_online,
            sub_node_silence_ms=h.sub_node_silence_ms,
            bme280_temp_c=h.bme280_temp_c,
            bme280_humidity_pct=h.bme280_humidity_pct,
            bme280_pressure_pa=h.bme280_pressure_pa,
            ina219_bus_v=h.ina219_bus_v,
            ina219_current_ma=h.ina219_current_ma,
            rain_pulses_window=h.rain_pulses_window,
            wind_pulses_window=h.wind_pulses_window,
            wind_dir_adc=h.wind_dir_adc,
            firmware_version=h.firmware_version,
            validation_warn=h.validation_warn,
        )


class WeatherRow(BaseModel):
    """Serialised WeatherStationReading for the ops API."""

    master_node_id: str
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    recorded_at: datetime
    air_temp_c: Decimal | None
    humidity_pct: Decimal | None
    atmospheric_pressure_hpa: Decimal | None
    wind_speed_kmh: Decimal | None
    wind_speed_max_gust_kmh: Decimal | None
    wind_direction_degrees: Decimal | None
    wind_direction_cardinal: str | None
    rain_mm_current_hour: Decimal | None
    rain_mm_today: Decimal | None
    weather_station_battery_v: Decimal | None
    validation_warn: bool

    @classmethod
    def from_domain(cls, w: WeatherStationReading) -> WeatherRow:
        return cls(
            master_node_id=w.master_node_id,
            tenant_id=w.tenant_id,
            farm_id=w.farm_id,
            recorded_at=w.recorded_at,
            air_temp_c=w.air_temp_c,
            humidity_pct=w.humidity_pct,
            atmospheric_pressure_hpa=w.atmospheric_pressure_hpa,
            wind_speed_kmh=w.wind_speed_kmh,
            wind_speed_max_gust_kmh=w.wind_speed_max_gust_kmh,
            wind_direction_degrees=w.wind_direction_degrees,
            wind_direction_cardinal=w.wind_direction_cardinal,
            rain_mm_current_hour=w.rain_mm_current_hour,
            rain_mm_today=w.rain_mm_today,
            weather_station_battery_v=w.weather_station_battery_v,
            validation_warn=w.validation_warn,
        )


# ---------------------------------------------------------------------------
# Heartbeat endpoints (Round 17.5)
# ---------------------------------------------------------------------------
@router.get(
    "/{main_node_id}/heartbeat",
    response_model=HeartbeatRow,
    summary="Latest Main Node master-only heartbeat (liveness + weather).",
)
async def get_latest_heartbeat(
    main_node_id: str,
    claims: ClaimsDep,
    repo: Annotated[MainNodeReadingRepo, Depends(get_main_node_reading_repo)],
) -> HeartbeatRow:
    latest = await repo.most_recent(main_node_id)
    if latest is None or latest.tenant_id != claims.tenant_id:
        # 404 (not 403) — don't leak whether the Main Node exists in
        # another tenant.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )
    return HeartbeatRow.from_domain(latest)


@router.get(
    "/{main_node_id}/heartbeat/history",
    response_model=list[HeartbeatRow],
    summary="Recent Main Node heartbeats (newest first).",
)
async def get_heartbeat_history(
    main_node_id: str,
    claims: ClaimsDep,
    repo: Annotated[MainNodeReadingRepo, Depends(get_main_node_reading_repo)],
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[HeartbeatRow]:
    rows = await repo.latest_for_node(main_node_id, limit=limit)
    # Tenant scope: filter out any row that isn't this tenant's — the
    # composite unique on (main_node_id, recorded_at) means all rows for
    # a given main_node_id share the same tenant, so this is a defence in
    # depth against a mis-owned row rather than a routine filter.
    scoped = [r for r in rows if r.tenant_id == claims.tenant_id]
    if not scoped:
        # Return [] rather than 404 when the Main Node has no history yet
        # AND belongs to the caller's tenant; return [] also when the
        # Main Node is another tenant's — indistinguishable from the
        # empty case, which is the correct security posture.
        return []
    return [HeartbeatRow.from_domain(r) for r in scoped]


# ---------------------------------------------------------------------------
# Weather endpoints (Round 17)
# ---------------------------------------------------------------------------
@router.get(
    "/{main_node_id}/weather/latest",
    response_model=WeatherRow,
    summary="Latest weather station reading from this Main Node.",
)
async def get_latest_weather(
    main_node_id: str,
    claims: ClaimsDep,
    repo: Annotated[WeatherStationReadingRepo, Depends(get_weather_station_reading_repo)],
) -> WeatherRow:
    latest = await repo.most_recent(main_node_id)
    if latest is None or latest.tenant_id != claims.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "not_found"},
        )
    return WeatherRow.from_domain(latest)


@router.get(
    "/{main_node_id}/weather/history",
    response_model=list[WeatherRow],
    summary="Recent weather station readings (newest first).",
)
async def get_weather_history(
    main_node_id: str,
    claims: ClaimsDep,
    repo: Annotated[WeatherStationReadingRepo, Depends(get_weather_station_reading_repo)],
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[WeatherRow]:
    rows = await repo.latest_for_node(main_node_id, limit=limit)
    scoped = [r for r in rows if r.tenant_id == claims.tenant_id]
    return [WeatherRow.from_domain(r) for r in scoped]


__all__ = ["router"]
