"""HTTP-layer tests for /api/v1/alerts/*."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.application.ports.alert_repo import AlertFull
from app.domain.alert import AlertType, Severity
from app.domain.auth import AccessClaims, AuthRole
from app.infra.http.deps import get_alert_repo, get_current_claims
from app.main import create_app

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT = uuid.UUID("99999999-9999-9999-9999-999999999999")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime.now(UTC).replace(microsecond=0)


def _alert(*, alert_id: int = 1, tenant: uuid.UUID = TENANT, resolved: bool = False) -> AlertFull:
    return AlertFull(
        alert_id=alert_id,
        tenant_id=tenant,
        farm_id=FARM,
        farmer_id=FARMER,
        device_id="AGR-001",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.WARNING,
        alert_message_marathi="बॅटरी कमी",
        alert_value=None,
        alert_threshold=None,
        triggered_at=NOW,
        resolved=resolved,
        resolved_at=NOW if resolved else None,
    )


class _StubAlertRepo:
    def __init__(self, alerts: list[AlertFull]) -> None:
        self.alerts = list(alerts)
        self.resolved_calls: list[tuple[int, str | None]] = []

    async def create(self, c):
        return 1

    async def last_triggered_at(self, p, a):
        return None

    async def resolve(self, alert_id, notes=None):
        self.resolved_calls.append((alert_id, notes))
        for i, a in enumerate(self.alerts):
            if a.alert_id == alert_id:
                self.alerts[i] = _alert(alert_id=alert_id, tenant=a.tenant_id, resolved=True)

    async def list_for_plot(self, plot_id, limit=50):
        return []

    async def find_by_id(self, alert_id):
        return next((a for a in self.alerts if a.alert_id == alert_id), None)

    async def list_for_tenant(
        self, tenant_id, *, only_unresolved=True, severity_filter=None, limit=100
    ):
        out = [a for a in self.alerts if a.tenant_id == tenant_id]
        if only_unresolved:
            out = [a for a in out if not a.resolved]
        if severity_filter is not None:
            out = [a for a in out if a.severity is severity_filter]
        return out[:limit]


def _claims() -> AccessClaims:
    return AccessClaims(
        subject=FARMER,
        tenant_id=TENANT,
        role=AuthRole.FARMER,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
        session_id=uuid.uuid4(),
    )


@pytest.fixture
def app_with_stubs():
    app = create_app()
    repo = _StubAlertRepo(
        [
            _alert(alert_id=1, resolved=False),
            _alert(alert_id=2, resolved=True),
            _alert(alert_id=3, tenant=OTHER_TENANT, resolved=False),
        ]
    )
    app.dependency_overrides[get_alert_repo] = lambda: repo
    app.dependency_overrides[get_current_claims] = lambda: _claims()
    client = TestClient(app)
    yield client, repo
    app.dependency_overrides.clear()


# ===========================================================================
# GET /api/v1/alerts
# ===========================================================================
def test_list_alerts_default_returns_open_for_tenant(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/alerts", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 200
    body = resp.json()
    ids = {row["alert_id"] for row in body}
    # Open + same tenant = only id=1. id=2 closed; id=3 other tenant.
    assert ids == {1}


def test_list_alerts_status_all_includes_resolved(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/alerts?status=all", headers={"Authorization": "Bearer X"})
    body = resp.json()
    ids = {row["alert_id"] for row in body}
    # Both id=1 and id=2 (same tenant); id=3 still excluded.
    assert ids == {1, 2}


def test_list_alerts_severity_filter(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/alerts?severity=warning", headers={"Authorization": "Bearer X"})
    body = resp.json()
    assert all(row["severity"] == "warning" for row in body)


def test_list_alerts_invalid_status_returns_422(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/alerts?status=garbage", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 422


# ===========================================================================
# POST /api/v1/alerts/{id}/resolve
# ===========================================================================
def test_resolve_alert_success(app_with_stubs) -> None:
    client, repo = app_with_stubs
    resp = client.post(
        "/api/v1/alerts/1/resolve",
        headers={"Authorization": "Bearer X"},
        json={"notes": "checked - false alarm"},
    )
    assert resp.status_code == 200
    assert resp.json()["resolved"] is True
    assert repo.resolved_calls == [(1, "checked - false alarm")]


def test_resolve_already_resolved_is_idempotent(app_with_stubs) -> None:
    client, repo = app_with_stubs
    resp = client.post(
        "/api/v1/alerts/2/resolve",
        headers={"Authorization": "Bearer X"},
        json={},
    )
    assert resp.status_code == 200
    assert resp.json().get("already_resolved") is True
    assert repo.resolved_calls == []  # Repo not called.


def test_resolve_cross_tenant_returns_404(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.post(
        "/api/v1/alerts/3/resolve",
        headers={"Authorization": "Bearer X"},
        json={},
    )
    assert resp.status_code == 404


def test_resolve_unknown_id_returns_404(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.post(
        "/api/v1/alerts/9999/resolve",
        headers={"Authorization": "Bearer X"},
        json={},
    )
    assert resp.status_code == 404
