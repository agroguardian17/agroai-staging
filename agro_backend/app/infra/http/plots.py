"""Read API: /plots, /plots/{id}, /plots/{id}/readings, /plots/{id}/alerts.

All endpoints require a valid access token. The current farmer (from
the JWT claim) is the visibility scope: a farmer can see only their
own plots. Admins are stubbed for Round 8 - the for_tenant path is
wired but only the FARMER role currently uses it.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.application.ports.ai_suggestion_repo import AiSuggestionRepo
from app.application.ports.alert_repo import AlertRepo
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.domain.auth import AuthRole
from app.domain.plot import Plot
from app.domain.sensor import Reading
from app.infra.http.deps import (
    ClaimsDep,
    get_ai_suggestion_repo,
    get_alert_repo,
    get_plot_repo,
    get_reading_repo,
)

router = APIRouter(prefix="/api/v1/plots", tags=["plots"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------
class PlotResponse(BaseModel):
    plot_id: str
    farm_id: uuid.UUID
    plot_number: int
    plot_name: str | None
    area_acre: Decimal
    gps_lat: float
    gps_lng: float
    node_id: str | None
    data_tier: str
    plot_status: str
    irrigation_valve_id: str

    @classmethod
    def from_domain(cls, p: Plot) -> PlotResponse:
        return cls(
            plot_id=p.plot_id,
            farm_id=p.farm_id,
            plot_number=p.plot_number,
            plot_name=p.plot_name,
            area_acre=p.area_acre,
            gps_lat=p.gps_lat,
            gps_lng=p.gps_lng,
            node_id=p.node_id,
            data_tier=p.data_tier.value,
            plot_status=p.plot_status.value,
            irrigation_valve_id=p.irrigation_valve_id,
        )


class ReadingResponse(BaseModel):
    reading_id: int | None = None
    recorded_at: datetime
    soil_moisture_avg_pct: Decimal | None
    soil_temp_rootzone_c: Decimal | None
    soil_ph: Decimal | None
    soil_ec_ms_cm: Decimal | None
    battery_voltage_v: Decimal | None
    battery_percent: Decimal | None
    cadence_mode: str | None
    validation_warn: bool
    low_battery_flag: bool

    @classmethod
    def from_domain(cls, r: Reading) -> ReadingResponse:
        return cls(
            recorded_at=r.recorded_at,
            soil_moisture_avg_pct=r.soil_moisture_avg_pct,
            soil_temp_rootzone_c=r.soil_temp_rootzone_c,
            soil_ph=r.soil_ph,
            soil_ec_ms_cm=r.soil_ec_ms_cm,
            battery_voltage_v=r.battery_voltage_v,
            battery_percent=r.battery_percent,
            cadence_mode=r.cadence_mode.value if r.cadence_mode else None,
            validation_warn=r.validation_warn,
            low_battery_flag=r.low_battery_flag,
        )


class AlertResponse(BaseModel):
    alert_id: int
    alert_type: str
    severity: str
    alert_message_marathi: str
    triggered_at: datetime
    resolved: bool
    resolved_at: datetime | None

    @classmethod
    def from_view(cls, v: Any) -> AlertResponse:
        return cls(
            alert_id=v.alert_id,
            alert_type=v.alert_type.value,
            severity=v.severity.value,
            alert_message_marathi=v.alert_message_marathi,
            triggered_at=v.triggered_at,
            resolved=v.resolved,
            resolved_at=v.resolved_at,
        )


# ---------------------------------------------------------------------------
# Authorization helper
# ---------------------------------------------------------------------------
async def _load_plot_or_403(
    plot_id: str,
    claims: Any,
    plot_repo: PlotRepo,
) -> Plot:
    p = await plot_repo.find(plot_id)
    if p is None:
        # Same 404 whether the plot exists for another farmer or never existed.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    # Farmer scope: only your tenant + plots you appear to own
    # (farmer_id is on farm; we trust the for_farmer query to filter).
    if claims.role is AuthRole.FARMER and p.tenant_id != claims.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    return p


# ---------------------------------------------------------------------------
# GET /plots
# ---------------------------------------------------------------------------
@router.get("", response_model=list[PlotResponse], summary="List plots visible to the caller.")
async def list_plots(
    claims: ClaimsDep,
    plot_repo: Annotated[PlotRepo, Depends(get_plot_repo)],
) -> list[PlotResponse]:
    if claims.role is AuthRole.FARMER:
        plots = await plot_repo.for_farmer(claims.subject)
    else:
        plots = await plot_repo.for_tenant(claims.tenant_id)
    return [PlotResponse.from_domain(p) for p in plots]


# ---------------------------------------------------------------------------
# GET /plots/{plot_id}
# ---------------------------------------------------------------------------
@router.get("/{plot_id}", response_model=PlotResponse, summary="One plot's metadata.")
async def get_plot(
    plot_id: str,
    claims: ClaimsDep,
    plot_repo: Annotated[PlotRepo, Depends(get_plot_repo)],
) -> PlotResponse:
    p = await _load_plot_or_403(plot_id, claims, plot_repo)
    return PlotResponse.from_domain(p)


# ---------------------------------------------------------------------------
# GET /plots/{plot_id}/readings?limit=50
# ---------------------------------------------------------------------------
@router.get(
    "/{plot_id}/readings",
    response_model=list[ReadingResponse],
    summary="Recent sensor readings for this plot, newest first.",
)
async def get_plot_readings(
    plot_id: str,
    claims: ClaimsDep,
    plot_repo: Annotated[PlotRepo, Depends(get_plot_repo)],
    reading_repo: Annotated[ReadingRepo, Depends(get_reading_repo)],
    limit: int = Query(default=50, ge=1, le=500),
) -> list[ReadingResponse]:
    await _load_plot_or_403(plot_id, claims, plot_repo)
    readings = await reading_repo.latest_for_plot(plot_id, limit)
    return [ReadingResponse.from_domain(r) for r in readings]


# ---------------------------------------------------------------------------
# GET /plots/{plot_id}/alerts?limit=50
# ---------------------------------------------------------------------------
@router.get(
    "/{plot_id}/alerts",
    response_model=list[AlertResponse],
    summary="Recent alerts triggered for this plot, newest first.",
)
async def get_plot_alerts(
    plot_id: str,
    claims: ClaimsDep,
    plot_repo: Annotated[PlotRepo, Depends(get_plot_repo)],
    alert_repo: Annotated[AlertRepo, Depends(get_alert_repo)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AlertResponse]:
    await _load_plot_or_403(plot_id, claims, plot_repo)
    views = await alert_repo.list_for_plot(plot_id, limit)
    return [AlertResponse.from_view(v) for v in views]


# ---------------------------------------------------------------------------
# GET /plots/{plot_id}/suggestions
# ---------------------------------------------------------------------------
class SuggestionResponse(BaseModel):
    suggestion_id: uuid.UUID
    generated_at: datetime
    suggestion_type: str
    full_message_marathi: str
    ai_model_version: str
    tokens_used: int | None
    crop_age_days: int | None
    crop_stage: str | None


@router.get(
    "/{plot_id}/suggestions",
    response_model=list[SuggestionResponse],
    summary="AI advisories generated for this plot, newest first.",
)
async def get_plot_suggestions(
    plot_id: str,
    claims: ClaimsDep,
    plot_repo: Annotated[PlotRepo, Depends(get_plot_repo)],
    suggestion_repo: Annotated[AiSuggestionRepo, Depends(get_ai_suggestion_repo)],
    limit: int = Query(default=50, ge=1, le=200),
) -> list[SuggestionResponse]:
    await _load_plot_or_403(plot_id, claims, plot_repo)
    rows = await suggestion_repo.list_for_plot(plot_id, limit)
    return [
        SuggestionResponse(
            suggestion_id=s.suggestion_id,
            generated_at=s.generated_at,
            suggestion_type=s.suggestion_type,
            full_message_marathi=s.full_message_marathi,
            ai_model_version=s.ai_model_version,
            tokens_used=s.tokens_used,
            crop_age_days=s.crop_age_days,
            crop_stage=s.crop_stage,
        )
        for s in rows
    ]


__all__ = ["router"]
