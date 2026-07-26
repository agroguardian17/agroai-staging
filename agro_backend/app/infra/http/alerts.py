"""Alerts queue + resolve endpoints (Round 12 dashboard surface).

* ``GET /api/v1/alerts`` lists alerts for the caller's tenant, filterable
  by severity and open/closed status. Powers the ops queue page.
* ``POST /api/v1/alerts/{id}/resolve`` flips ``resolved=true`` + notes.
  Used by the queue's "Resolve" button.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from app.application.ports.alert_repo import AlertFull, AlertRepo
from app.domain.alert import Severity
from app.infra.http.deps import ClaimsDep, get_alert_repo

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class AlertQueueRow(BaseModel):
    alert_id: int
    alert_type: str
    severity: str
    alert_message_marathi: str
    triggered_at: datetime
    resolved: bool
    resolved_at: datetime | None
    device_id: str | None
    farm_id: uuid.UUID
    farmer_id: uuid.UUID
    alert_value: Decimal | None
    alert_threshold: Decimal | None

    @classmethod
    def from_full(cls, a: AlertFull) -> AlertQueueRow:
        return cls(
            alert_id=a.alert_id,
            alert_type=a.alert_type.value,
            severity=a.severity.value,
            alert_message_marathi=a.alert_message_marathi,
            triggered_at=a.triggered_at,
            resolved=a.resolved,
            resolved_at=a.resolved_at,
            device_id=a.device_id,
            farm_id=a.farm_id,
            farmer_id=a.farmer_id,
            alert_value=a.alert_value,
            alert_threshold=a.alert_threshold,
        )


class ResolveAlertRequest(BaseModel):
    notes: str | None = None


@router.get(
    "",
    response_model=list[AlertQueueRow],
    summary="List alerts for the caller's tenant (ops queue).",
)
async def list_alerts(
    claims: ClaimsDep,
    alert_repo: Annotated[AlertRepo, Depends(get_alert_repo)],
    status_filter: str = Query(
        default="open",
        pattern="^(open|closed|all)$",
        alias="status",
        description="open=unresolved, closed=resolved, all=both",
    ),
    severity: str | None = Query(default=None, pattern="^(info|warning|critical)$"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[AlertQueueRow]:
    only_unresolved = status_filter == "open"
    sev_enum = Severity(severity) if severity else None
    rows = await alert_repo.list_for_tenant(
        claims.tenant_id,
        only_unresolved=only_unresolved,
        severity_filter=sev_enum,
        limit=limit,
    )
    # Closed-only is a niche; filter client-side for simplicity.
    if status_filter == "closed":
        rows = [a for a in rows if a.resolved]
    return [AlertQueueRow.from_full(a) for a in rows]


@router.post(
    "/{alert_id}/resolve",
    summary="Mark an alert as resolved (records optional notes).",
)
async def resolve_alert(
    alert_id: int,
    payload: ResolveAlertRequest,
    claims: ClaimsDep,
    alert_repo: Annotated[AlertRepo, Depends(get_alert_repo)],
) -> dict[str, object]:
    # Tenant scope: refuse to resolve another tenant's alert.
    target = await alert_repo.find_by_id(alert_id)
    if target is None or target.tenant_id != claims.tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "not_found"})
    if target.resolved:
        return {"alert_id": alert_id, "already_resolved": True}
    await alert_repo.resolve(alert_id, payload.notes)
    return {"alert_id": alert_id, "resolved": True}


__all__ = ["router"]
