"""Use-case tests for the device-liveness watchdog (fakes, no DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from app.application.check_device_liveness import DeviceLivenessDeps, check_device_liveness
from app.application.ports.event_bus import EVENT_ALERT_CREATED
from app.domain.alert import AlertType, Severity
from app.domain.main_node_reading import MainNodeReading
from app.domain.plot import DataTier, Plot, PlotStatus

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TENANT = uuid.uuid4()
FARM = uuid.uuid4()
FARMER = uuid.uuid4()


def _heartbeat(*, online: bool, silence_ms: int, recorded_at: datetime = NOW) -> MainNodeReading:
    return MainNodeReading(
        tenant_id=TENANT,
        farm_id=FARM,
        main_node_id="AGR-MN-0001",
        recorded_at=recorded_at,
        received_at_master=recorded_at,
        sub_node_online=online,
        sub_node_silence_ms=silence_ms,
    )


def _plot(node_id: str | None) -> Plot:
    return Plot(
        plot_id="PLOT_PILOT_001",
        tenant_id=TENANT,
        farm_id=FARM,
        plot_number=1,
        area_acre=Decimal("1.0"),
        gps_lat=19.9,
        gps_lng=75.7,
        irrigation_valve_id="V1",
        data_tier=DataTier.SUB_NODE,
        plot_status=PlotStatus.ACTIVE,
        node_id=node_id,
    )


class _FakeHeartbeatRepo:
    def __init__(self, rows: list[MainNodeReading]) -> None:
        self._rows = rows

    async def latest_per_node(self) -> list[MainNodeReading]:
        return self._rows


class _FakeFarmerRepo:
    def __init__(self, owner: uuid.UUID | None) -> None:
        self._owner = owner

    async def owner_of_farm(self, farm_id: uuid.UUID) -> uuid.UUID | None:
        return self._owner


class _FakePlotRepo:
    def __init__(self, plots: list[Plot]) -> None:
        self._plots = plots

    async def for_farmer(self, farmer_id: uuid.UUID) -> list[Plot]:
        return self._plots


class _FakeAlertRepo:
    def __init__(self, last_at: datetime | None = None) -> None:
        self.created: list[Any] = []
        self._last_at = last_at

    async def last_triggered_at(self, plot_id: str, alert_type: AlertType) -> datetime | None:
        return self._last_at

    async def create(self, candidate: Any) -> int:
        self.created.append(candidate)
        self._last_at = candidate.triggered_at
        return len(self.created)


class _FakeEventBus:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        self.events.append((event_name, payload))


def _deps(hb_rows: list[MainNodeReading], *, last_at: datetime | None = None, plots=None):
    alert_repo = _FakeAlertRepo(last_at=last_at)
    bus = _FakeEventBus()
    deps = DeviceLivenessDeps(
        heartbeat_repo=_FakeHeartbeatRepo(hb_rows),  # type: ignore[arg-type]
        alert_repo=alert_repo,  # type: ignore[arg-type]
        farmer_repo=_FakeFarmerRepo(FARMER),  # type: ignore[arg-type]
        plot_repo=_FakePlotRepo([_plot("AGR-SN-0001")] if plots is None else plots),  # type: ignore[arg-type]
        event_bus=bus,  # type: ignore[arg-type]
        warn_minutes=15,
        critical_minutes=60,
        cooldown_minutes=360,
    )
    return deps, alert_repo, bus


async def test_silent_sub_node_raises_one_alert_and_event() -> None:
    deps, alert_repo, bus = _deps([_heartbeat(online=False, silence_ms=30 * 60_000)])
    raised = await check_device_liveness(deps, now=NOW)
    assert raised == 1
    assert len(alert_repo.created) == 1
    cand = alert_repo.created[0]
    assert cand.alert_type is AlertType.DEVICE_OFFLINE
    assert cand.severity is Severity.WARNING
    assert cand.device_id == "AGR-SN-0001"
    assert len(bus.events) == 1
    name, payload = bus.events[0]
    assert name == EVENT_ALERT_CREATED
    assert payload["alert_type"] == AlertType.DEVICE_OFFLINE.value
    assert payload["plot_id"] == "PLOT_PILOT_001"


async def test_online_node_raises_nothing() -> None:
    deps, alert_repo, _ = _deps([_heartbeat(online=True, silence_ms=0)])
    assert await check_device_liveness(deps, now=NOW) == 0
    assert alert_repo.created == []


async def test_cooldown_suppresses_repeat() -> None:
    # Last alert fired 1 hour ago; cooldown is 6h → suppressed.
    deps, alert_repo, _ = _deps(
        [_heartbeat(online=False, silence_ms=30 * 60_000)],
        last_at=NOW - timedelta(hours=1),
    )
    assert await check_device_liveness(deps, now=NOW) == 0
    assert alert_repo.created == []


async def test_no_node_bearing_plot_is_skipped() -> None:
    deps, alert_repo, _ = _deps(
        [_heartbeat(online=False, silence_ms=30 * 60_000)], plots=[_plot(None)]
    )
    assert await check_device_liveness(deps, now=NOW) == 0
    assert alert_repo.created == []
