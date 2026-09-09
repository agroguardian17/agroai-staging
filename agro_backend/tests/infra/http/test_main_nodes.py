"""HTTP tests for Round 17 + 17.5 main_nodes routes.

Uses ``app.dependency_overrides`` to inject fake repos, keeping tests
DB-free. Matches the fixture patterns used in ``test_alerts.py`` /
``test_plots.py``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.auth import AccessClaims, AuthRole
from app.domain.main_node_reading import MainNodeReading
from app.domain.weather_station_reading import WeatherStationReading
from app.infra.http import main_nodes as main_node_routes
from app.infra.http.deps import (
    get_current_claims,
    get_main_node_reading_repo,
    get_weather_station_reading_repo,
)

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
PILOT_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
OTHER_TENANT = uuid.UUID("22222222-2222-2222-2222-222222222222")
PILOT_FARM = uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222")
FARMER = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")


def _claims(tenant: uuid.UUID = PILOT_TENANT) -> AccessClaims:
    return AccessClaims(
        subject=FARMER,
        tenant_id=tenant,
        role=AuthRole.FARMER,
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC),
        session_id=uuid.uuid4(),
    )


def _heartbeat(
    tenant: uuid.UUID = PILOT_TENANT,
    sub_online: bool = True,
    silence_ms: int = 0,
) -> MainNodeReading:
    return MainNodeReading(
        tenant_id=tenant,
        farm_id=PILOT_FARM,
        main_node_id="AGR-MN-0001",
        recorded_at=datetime(2026, 9, 5, 7, 0, 0, tzinfo=UTC),
        received_at_master=datetime(2026, 9, 5, 7, 0, 0, tzinfo=UTC),
        time_source="ntp",
        sub_node_online=sub_online,
        sub_node_silence_ms=silence_ms,
        bme280_temp_c=Decimal("32.4"),
        bme280_humidity_pct=Decimal("65.1"),
        bme280_pressure_pa=Decimal("95000"),
        ina219_bus_v=Decimal("12.1"),
        ina219_current_ma=Decimal("250"),
        firmware_version="viraai-mn-1.0.0-raw",
    )


def _weather(tenant: uuid.UUID = PILOT_TENANT) -> WeatherStationReading:
    return WeatherStationReading(
        tenant_id=tenant,
        farm_id=PILOT_FARM,
        master_node_id="AGR-MN-0001",
        recorded_at=datetime(2026, 9, 5, 7, 0, 0, tzinfo=UTC),
        air_temp_c=Decimal("32.4"),
        humidity_pct=Decimal("65.1"),
        atmospheric_pressure_hpa=Decimal("950.00"),
        weather_station_battery_v=Decimal("12.1"),
    )


class _FakeHeartbeatRepo:
    def __init__(
        self, latest: MainNodeReading | None = None, history: list[MainNodeReading] | None = None
    ) -> None:
        self._latest = latest
        self._history = history or []

    async def save(self, reading: MainNodeReading) -> int | None:
        return 1

    async def latest_for_node(self, main_node_id: str, limit: int) -> list[MainNodeReading]:
        return [r for r in self._history if r.main_node_id == main_node_id][:limit]

    async def most_recent(self, main_node_id: str) -> MainNodeReading | None:
        if self._latest and self._latest.main_node_id == main_node_id:
            return self._latest
        return None


class _FakeWeatherRepo:
    def __init__(
        self,
        latest: WeatherStationReading | None = None,
        history: list[WeatherStationReading] | None = None,
    ) -> None:
        self._latest = latest
        self._history = history or []

    async def save(self, reading: WeatherStationReading) -> int | None:
        return 1

    async def latest_for_node(self, master_node_id: str, limit: int) -> list[WeatherStationReading]:
        return [r for r in self._history if r.master_node_id == master_node_id][:limit]

    async def most_recent(self, master_node_id: str) -> WeatherStationReading | None:
        if self._latest and self._latest.master_node_id == master_node_id:
            return self._latest
        return None


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------
def _make_app(
    heartbeat_repo: _FakeHeartbeatRepo,
    weather_repo: _FakeWeatherRepo,
    claims: AccessClaims | None = None,
) -> FastAPI:
    app = FastAPI()
    app.include_router(main_node_routes.router)
    app.dependency_overrides[get_current_claims] = lambda: claims or _claims()
    app.dependency_overrides[get_main_node_reading_repo] = lambda: heartbeat_repo
    app.dependency_overrides[get_weather_station_reading_repo] = lambda: weather_repo
    return app


# ---------------------------------------------------------------------------
# Heartbeat routes
# ---------------------------------------------------------------------------
def test_get_latest_heartbeat_returns_row() -> None:
    hb = _heartbeat()
    app = _make_app(_FakeHeartbeatRepo(latest=hb), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat")
    assert r.status_code == 200
    body = r.json()
    assert body["main_node_id"] == "AGR-MN-0001"
    assert body["sub_node_online"] is True
    assert body["time_source"] == "ntp"


def test_get_latest_heartbeat_404_when_missing() -> None:
    app = _make_app(_FakeHeartbeatRepo(latest=None), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat")
    assert r.status_code == 404


def test_get_latest_heartbeat_404_when_other_tenant() -> None:
    """Cross-tenant lookup returns 404 (not 403) — never leak existence."""
    other_tenant_hb = _heartbeat(tenant=OTHER_TENANT)
    app = _make_app(_FakeHeartbeatRepo(latest=other_tenant_hb), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat")
    assert r.status_code == 404


def test_get_heartbeat_history_returns_scoped_list() -> None:
    history = [
        _heartbeat(sub_online=True, silence_ms=30_000),
        _heartbeat(sub_online=False, silence_ms=920_000),
    ]
    app = _make_app(_FakeHeartbeatRepo(history=history), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat/history?limit=10")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 2


def test_get_heartbeat_history_empty_for_other_tenant() -> None:
    history = [_heartbeat(tenant=OTHER_TENANT)]
    app = _make_app(_FakeHeartbeatRepo(history=history), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat/history")
    assert r.status_code == 200
    assert r.json() == []


def test_get_heartbeat_history_rejects_bad_limit() -> None:
    app = _make_app(_FakeHeartbeatRepo(), _FakeWeatherRepo())
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat/history?limit=0")
    assert r.status_code == 422
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/heartbeat/history?limit=99999")
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Weather routes
# ---------------------------------------------------------------------------
def test_get_latest_weather_returns_row() -> None:
    w = _weather()
    app = _make_app(_FakeHeartbeatRepo(), _FakeWeatherRepo(latest=w))
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/weather/latest")
    assert r.status_code == 200
    body = r.json()
    assert body["master_node_id"] == "AGR-MN-0001"
    assert body["air_temp_c"] == "32.4"
    assert body["atmospheric_pressure_hpa"] == "950.00"


def test_get_latest_weather_404_when_missing() -> None:
    app = _make_app(_FakeHeartbeatRepo(), _FakeWeatherRepo(latest=None))
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/weather/latest")
    assert r.status_code == 404


def test_get_latest_weather_404_when_other_tenant() -> None:
    other = _weather(tenant=OTHER_TENANT)
    app = _make_app(_FakeHeartbeatRepo(), _FakeWeatherRepo(latest=other))
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/weather/latest")
    assert r.status_code == 404


def test_get_weather_history_returns_scoped_list() -> None:
    history = [_weather(), _weather()]
    app = _make_app(_FakeHeartbeatRepo(), _FakeWeatherRepo(history=history))
    with TestClient(app) as client:
        r = client.get("/api/v1/main_nodes/AGR-MN-0001/weather/history?limit=10")
    assert r.status_code == 200
    assert len(r.json()) == 2
