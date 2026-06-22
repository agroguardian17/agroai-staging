"""HTTP-layer tests for /api/v1/plots/*."""


from __future__ import annotations


import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal


import pytest
from fastapi.testclient import TestClient


from app.application.ports.alert_repo import PlotAlertView
from app.domain.alert import AlertType, Severity
from app.domain.auth import AccessClaims, AuthRole
from app.domain.plot import DataTier, Plot, PlotStatus
from app.domain.sensor import CadenceMode, Reading, TransmissionType
from app.infra.http.deps import (
    get_alert_repo,
    get_current_claims,
    get_plot_repo,
    get_reading_repo,
)
from app.main import create_app


TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")
NOW = datetime.now(UTC).replace(microsecond=0)




def _plot(plot_id: str = "PLOT_A", tenant: uuid.UUID = TENANT) -> Plot:
    return Plot(
        plot_id=plot_id,
        tenant_id=tenant,
        farm_id=FARM,
        plot_number=1,
        plot_name="A",
        area_acre=Decimal("1.0"),
        gps_lat=19.9,
        gps_lng=75.7,
        node_id="AGR-DEMO-1",
        data_tier=DataTier.SUB_NODE,
        plot_status=PlotStatus.ACTIVE,
        irrigation_valve_id="V_1",
    )




def _reading() -> Reading:
    return Reading(
        tenant_id=TENANT,
        farmer_id=FARMER,
        farm_id=FARM,
        plot_id="PLOT_A",
        node_id="AGR-DEMO-1",
        recorded_at=NOW,
        received_at_master=NOW,
        transmission_type=TransmissionType.LORA,
        soil_moisture_avg_pct=Decimal("32.5"),
        soil_ph=Decimal("6.7"),
        battery_voltage_v=Decimal("3.55"),
        cadence_mode=CadenceMode.NORMAL,
    )




def _alert_view() -> PlotAlertView:
    return PlotAlertView(
        alert_id=1,
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.WARNING,
        alert_message_marathi="बॅटरी कमी आहे.",
        triggered_at=NOW,
        resolved=False,
        resolved_at=None,
        device_id="AGR-DEMO-1",
        farmer_id=FARMER,
    )




class StubPlotRepo:
    def __init__(self, plots: list[Plot]) -> None:
        self.plots = plots


    async def find(self, plot_id):
        for p in self.plots:
            if p.plot_id == plot_id:
                return p
        return None


    async def for_farmer(self, farmer_id):
        return self.plots


    async def for_tenant(self, tenant_id):
        return self.plots


    async def update_data_tier(self, plot_id, tier):
        pass




class StubReadingRepo:
    def __init__(self, items: list[Reading]) -> None:
        self.items = items


    async def save(self, r):
        return 1


    async def latest_for_plot(self, plot_id, limit):
        return self.items[:limit]


    async def recent_for_node(self, node_id, since):
        return []


    async def history_for_stuck_check(self, node_id, field, minutes):
        return []


    async def history_for_mad_check(self, node_id, field, hours):
        return []




class StubAlertRepo:
    def __init__(self, items: list[PlotAlertView]) -> None:
        self.items = items


    async def create(self, c):
        return 1


    async def last_triggered_at(self, plot_id, alert_type):
        return None


    async def resolve(self, alert_id, notes=None):
        pass


    async def list_for_plot(self, plot_id, limit=50):
        return self.items




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
    plot = _plot()
    reading = _reading()
    alert = _alert_view()
    plot_repo = StubPlotRepo([plot])
    reading_repo = StubReadingRepo([reading])
    alert_repo = StubAlertRepo([alert])


    app.dependency_overrides[get_plot_repo] = lambda: plot_repo
    app.dependency_overrides[get_reading_repo] = lambda: reading_repo
    app.dependency_overrides[get_alert_repo] = lambda: alert_repo
    app.dependency_overrides[get_current_claims] = lambda: _claims()


    client = TestClient(app)
    yield client, plot_repo, reading_repo, alert_repo
    app.dependency_overrides.clear()




# ===========================================================================
# /plots
# ===========================================================================
def test_list_plots_returns_farmer_plots(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get("/api/v1/plots", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert body[0]["plot_id"] == "PLOT_A"
    assert body[0]["data_tier"] == "sub_node"




def test_get_plot_404_when_not_found(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get("/api/v1/plots/NOT_EXIST", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 404




def test_get_plot_returns_one(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get("/api/v1/plots/PLOT_A", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 200
    assert resp.json()["plot_id"] == "PLOT_A"




def test_get_plot_cross_tenant_returns_404(app_with_stubs) -> None:
    client, plot_repo, *_ = app_with_stubs
    # Replace the plot with one in a different tenant.
    plot_repo.plots = [_plot(tenant=uuid.uuid4())]
    resp = client.get("/api/v1/plots/PLOT_A", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 404




# ===========================================================================
# /plots/{id}/readings
# ===========================================================================
def test_get_plot_readings_returns_list(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get("/api/v1/plots/PLOT_A/readings", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["soil_moisture_avg_pct"] == "32.5"
    assert body[0]["cadence_mode"] == "normal"




def test_readings_limit_validation(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get(
        "/api/v1/plots/PLOT_A/readings?limit=0", headers={"Authorization": "Bearer X"}
    )
    assert resp.status_code == 422  # Query(ge=1)




# ===========================================================================
# /plots/{id}/alerts
# ===========================================================================
def test_get_plot_alerts_returns_list(app_with_stubs) -> None:
    client, *_ = app_with_stubs
    resp = client.get("/api/v1/plots/PLOT_A/alerts", headers={"Authorization": "Bearer X"})
    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["alert_type"] == "low_battery"
    assert body[0]["severity"] == "warning"
    assert body[0]["resolved"] is False




# ===========================================================================
# Auth gating: without claims override, endpoints require a real token.
# ===========================================================================
def test_plots_requires_auth_without_override() -> None:
    app = create_app()
    client = TestClient(app)
    # No Authorization header.
    resp = client.get("/api/v1/plots")
    assert resp.status_code == 401
