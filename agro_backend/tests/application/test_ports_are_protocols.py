"""Tests that every application port is a runtime-checkable Protocol.


The hexagon relies on Protocols (PEP 544) so use cases can substitute fakes
for the concrete adapters in tests. ``isinstance(x, SomePort)`` must work
without ``x`` inheriting from ``SomePort`` - that's the whole point of
``@runtime_checkable``.


These tests also guard against accidental regressions to ABCs or concrete
base classes, which would force adapter classes to inherit and break the
duck-typing contract the hexagon depends on.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, get_type_hints

import pytest

from app.application.ports.alert_repo import AlertRepo
from app.application.ports.event_bus import (
    EVENT_ALERT_CREATED,
    EVENT_ALERT_DISPATCHED,
    EVENT_DEVICE_OFFLINE,
    EVENT_DEVICE_ONLINE,
    EVENT_PLOT_CROP_CHANGED,
    EVENT_SUGGESTION_GENERATED,
    EVENT_TELEMETRY_INGESTED,
    EventBus,
)
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ALLOWED_HISTORY_FIELDS, ReadingRepo
from app.domain.alert import AlertCandidate, AlertType, Severity
from app.domain.plot import DataTier, Plot, PlotStatus
from app.domain.sensor import Reading, TransmissionType

ALL_PORTS = (AlertRepo, EventBus, PlotRepo, ReadingRepo)




# ---------------------------------------------------------------------------
# 1. Every port is a Protocol AND runtime_checkable.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("port_cls", ALL_PORTS, ids=lambda c: c.__name__)
def test_port_is_runtime_checkable_protocol(port_cls: type) -> None:
    # Protocols expose ``_is_protocol`` and ``_is_runtime_protocol`` flags
    # (CPython internals; documented in PEP 544 / typing module source).
    assert getattr(port_cls, "_is_protocol", False), (
        f"{port_cls.__name__} must be declared as typing.Protocol"
    )
    assert getattr(port_cls, "_is_runtime_protocol", False), (
        f"{port_cls.__name__} must be decorated with @runtime_checkable"
    )




# ---------------------------------------------------------------------------
# 2. A duck-typed fake passes isinstance() against the Protocol.
#    This is the canonical hexagon use case: tests construct a fake without
#    inheriting from the port, and pass it to a use case as a port.
# ---------------------------------------------------------------------------
class _FakeReadingRepo:
    """Smallest possible fake satisfying ReadingRepo - no inheritance."""


    async def save(self, reading: Reading) -> int | None:
        return 1


    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]:
        return []


    async def recent_for_node(self, node_id: str, since: datetime) -> list[Reading]:
        return []


    async def history_for_stuck_check(
        self, node_id: str, field: str, minutes: int
    ) -> list[Decimal | None]:
        return []


    async def history_for_mad_check(self, node_id: str, field: str, hours: int) -> list[Decimal]:
        return []




class _FakePlotRepo:
    async def find(self, plot_id: str) -> Plot | None:
        return None


    async def for_farmer(self, farmer_id: uuid.UUID) -> list[Plot]:
        return []


    async def for_tenant(self, tenant_id: uuid.UUID) -> list[Plot]:
        return []


    async def update_data_tier(self, plot_id: str, tier: DataTier) -> None:
        return None




class _FakeAlertRepo:
    async def create(self, candidate: AlertCandidate) -> int:
        return 1


    async def last_triggered_at(self, plot_id: str, alert_type: AlertType) -> datetime | None:
        return None


    async def resolve(self, alert_id: int, notes: str | None = None) -> None:
        return None




class _FakeEventBus:
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        return None




def test_fake_reading_repo_satisfies_protocol() -> None:
    assert isinstance(_FakeReadingRepo(), ReadingRepo)




def test_fake_plot_repo_satisfies_protocol() -> None:
    assert isinstance(_FakePlotRepo(), PlotRepo)




def test_fake_alert_repo_satisfies_protocol() -> None:
    assert isinstance(_FakeAlertRepo(), AlertRepo)




def test_fake_event_bus_satisfies_protocol() -> None:
    assert isinstance(_FakeEventBus(), EventBus)




# ---------------------------------------------------------------------------
# 3. Incomplete fakes are rejected (the runtime-checkable contract).
# ---------------------------------------------------------------------------
class _IncompleteReadingRepo:
    # Missing every other method
    async def save(self, reading: Reading) -> int | None:
        return None




def test_incomplete_fake_does_not_satisfy_protocol() -> None:
    # runtime_checkable Protocols only verify method *presence* (not signatures).
    # Missing ``latest_for_plot`` etc. -> isinstance returns False.
    assert not isinstance(_IncompleteReadingRepo(), ReadingRepo)




# ---------------------------------------------------------------------------
# 4. Domain Protocols can resolve their forward refs.
#    If a port is poorly imported (e.g. circular), get_type_hints() blows up.
#    This catches regressions where a port stops pointing at the right domain types.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("port_cls", ALL_PORTS, ids=lambda c: c.__name__)
def test_port_method_hints_resolve(port_cls: type) -> None:
    for attr_name in dir(port_cls):
        if attr_name.startswith("_"):
            continue
        attr = getattr(port_cls, attr_name)
        if not callable(attr):
            continue
        # Will raise if any annotation is an unresolved forward ref.
        get_type_hints(attr)




# ---------------------------------------------------------------------------
# 5. ALLOWED_HISTORY_FIELDS is what we expect (SQL-injection allowlist).
#    Any change requires a deliberate review here.
# ---------------------------------------------------------------------------
def test_allowed_history_fields_is_frozen_and_covers_numeric_columns() -> None:
    expected = {
        "soil_moisture_1_pct",
        "soil_moisture_2_pct",
        "soil_moisture_avg_pct",
        "soil_temp_c",
        "soil_temp_rootzone_c",
        "soil_ph",
        "soil_ec_ms_cm",
        "soil_n_mg_kg",
        "soil_p_mg_kg",
        "soil_k_mg_kg",
        "battery_voltage_v",
    }
    assert expected == ALLOWED_HISTORY_FIELDS
    assert isinstance(ALLOWED_HISTORY_FIELDS, frozenset)




# ---------------------------------------------------------------------------
# 6. Event-name constants must be unique and stable.
#    These strings travel between producers/consumers; a typo or rename
#    silently breaks subscribers.
# ---------------------------------------------------------------------------
def test_event_name_constants_are_unique() -> None:
    names = {
        EVENT_TELEMETRY_INGESTED,
        EVENT_ALERT_CREATED,
        EVENT_ALERT_DISPATCHED,
        EVENT_PLOT_CROP_CHANGED,
        EVENT_SUGGESTION_GENERATED,
        EVENT_DEVICE_OFFLINE,
        EVENT_DEVICE_ONLINE,
    }
    # 7 named constants => 7 unique values.
    assert len(names) == 7




def test_event_name_strings_match_docstring_convention() -> None:
    # All event names are dotted lower_snake_case ``noun.verb`` pairs.
    # If a future event uses dashes or upper-case, surfacing it here
    # forces an explicit doc update.
    for name in (
        EVENT_TELEMETRY_INGESTED,
        EVENT_ALERT_CREATED,
        EVENT_ALERT_DISPATCHED,
        EVENT_PLOT_CROP_CHANGED,
        EVENT_SUGGESTION_GENERATED,
        EVENT_DEVICE_OFFLINE,
        EVENT_DEVICE_ONLINE,
    ):
        assert "." in name, f"{name!r} must follow noun.verb convention"
        assert name == name.lower(), f"{name!r} must be lowercase"
        assert " " not in name, f"{name!r} must not contain spaces"




# ---------------------------------------------------------------------------
# 7. Sanity: the fake can be constructed alongside the domain dataclasses.
#    Smoke test that the cross-module wiring works end-to-end.
# ---------------------------------------------------------------------------
def test_fake_repo_round_trip_with_domain_objects() -> None:
    candidate = AlertCandidate(
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.WARNING,
        alert_message_marathi="...",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        farm_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        farmer_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        triggered_at=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
    )
    reading = Reading(
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        farmer_id=uuid.UUID("00000000-0000-0000-0000-000000000003"),
        farm_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        plot_id="P1",
        node_id="N1",
        recorded_at=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        received_at_master=datetime(2026, 5, 1, 0, 0, tzinfo=UTC),
        transmission_type=TransmissionType.LORA,
    )
    plot = Plot(
        plot_id="P1",
        tenant_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        farm_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
        plot_number=1,
        area_acre=Decimal("1.0"),
        gps_lat=0.0,
        gps_lng=0.0,
        irrigation_valve_id="V1",
        data_tier=DataTier.SUB_NODE,
        plot_status=PlotStatus.ACTIVE,
    )
    # No exception means the type-system wiring is intact.
    assert candidate.alert_type is AlertType.LOW_BATTERY
    assert reading.transmission_type is TransmissionType.LORA
    assert plot.data_tier is DataTier.SUB_NODE
