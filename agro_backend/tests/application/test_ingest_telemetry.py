"""Tests for ``app.application.ingest_telemetry.execute``.


Pure-unit tests with fake ReadingRepo + fake EventBus. The use case
contains no IO of its own; the fakes capture every call so we can
assert the orchestration is correct.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.application.ingest_telemetry import IngestDeps, execute
from app.application.ports.event_bus import EVENT_TELEMETRY_INGESTED, EventBus
from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import Reading, TransmissionType


def _r(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "farmer_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "farm_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "plot_id": "P1",
        "node_id": "N1",
        "recorded_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "received_at_master": datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




class _StubReadingRepo:
    """Fake ReadingRepo capturing the last saved reading + returning a chosen id."""


    def __init__(
        self,
        *,
        save_return: int | None = 42,
        stuck: dict[str, list[Decimal | None]] | None = None,
        mad: dict[str, list[Decimal]] | None = None,
    ) -> None:
        self._save_return = save_return
        self._stuck = stuck or {}
        self._mad = mad or {}
        self.saved: list[Reading] = []


    async def save(self, reading: Reading) -> int | None:
        self.saved.append(reading)
        return self._save_return


    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]:  # pragma: no cover
        raise AssertionError("ingest must not call latest_for_plot()")


    async def recent_for_node(
        self, node_id: str, since: datetime
    ) -> list[Reading]:  # pragma: no cover
        raise AssertionError("ingest must not call recent_for_node()")


    async def history_for_stuck_check(
        self, node_id: str, field: str, minutes: int
    ) -> list[Decimal | None]:
        return self._stuck.get(field, [])


    async def history_for_mad_check(self, node_id: str, field: str, hours: int) -> list[Decimal]:
        return self._mad.get(field, [])




class _StubEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []


    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        self.published.append((event_name, payload))




def _deps(repo: ReadingRepo | None = None, bus: EventBus | None = None) -> IngestDeps:
    return IngestDeps(
        reading_repo=repo or _StubReadingRepo(),
        event_bus=bus or _StubEventBus(),
    )




# ===========================================================================
# Happy path
# ===========================================================================
async def test_clean_reading_saves_and_publishes() -> None:
    repo = _StubReadingRepo(save_return=100)
    bus = _StubEventBus()
    result = await execute(
        _r(soil_moisture_1_pct=Decimal("30"), soil_moisture_2_pct=Decimal("31")),
        _deps(repo, bus),
    )
    assert result.reading_id == 100
    assert result.validation_warn is False
    assert result.flags == {}
    assert len(repo.saved) == 1
    # The published event carries IDs only (Roadmap §1.3 - never full objects).
    assert len(bus.published) == 1
    name, payload = bus.published[0]
    assert name == EVENT_TELEMETRY_INGESTED
    assert payload == {"plot_id": "P1", "reading_id": 100, "validation_warn": False}




# ===========================================================================
# Duplicate
# ===========================================================================
async def test_duplicate_save_returns_none_and_suppresses_event() -> None:
    repo = _StubReadingRepo(save_return=None)
    bus = _StubEventBus()
    result = await execute(_r(), _deps(repo, bus))
    assert result.reading_id is None
    assert result.validation_warn is False
    # No event published when the row was a duplicate; the ingest worker's
    # drain loop will increment metrics.ingest_dropped_total{reason=duplicate}.
    assert bus.published == []




# ===========================================================================
# Validation warning
# ===========================================================================
async def test_range_fail_propagates_into_flags_and_event_payload() -> None:
    repo = _StubReadingRepo(save_return=7)
    bus = _StubEventBus()
    result = await execute(
        _r(soil_ph=Decimal("15")),  # out of range
        _deps(repo, bus),
    )
    assert result.reading_id == 7
    assert result.validation_warn is True
    assert result.flags["soil_ph"] == "range_fail"
    # Validation warn flag carried through to the event payload.
    _, payload = bus.published[0]
    assert payload["validation_warn"] is True




async def test_cross_sensor_disagreement_recorded_in_flags() -> None:
    repo = _StubReadingRepo(save_return=8)
    bus = _StubEventBus()
    result = await execute(
        _r(
            soil_moisture_1_pct=Decimal("20"),
            soil_moisture_2_pct=Decimal("80"),
        ),
        _deps(repo, bus),
    )
    assert result.validation_warn is True
    assert result.flags["soil_moisture_avg_pct"] == "cross_sensor"




# ===========================================================================
# Repo / bus error propagation
# ===========================================================================
class _BoomRepo(_StubReadingRepo):
    async def save(self, reading: Reading) -> int | None:
        raise RuntimeError("DB down")




class _BoomBus:
    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        raise RuntimeError("bus down")




async def test_repo_save_error_propagates() -> None:
    # Per .cursorrules #4 the use case does NOT swallow exceptions.
    # The broker drain loop catches and meters them.
    with pytest.raises(RuntimeError, match="DB down"):
        await execute(_r(), _deps(repo=_BoomRepo()))




async def test_bus_publish_error_propagates_after_save() -> None:
    # If the row was already persisted but the event fails, surface the
    # exception. The drain loop's metric label distinguishes it.
    repo = _StubReadingRepo(save_return=99)
    with pytest.raises(RuntimeError, match="bus down"):
        await execute(_r(), _deps(repo=repo, bus=_BoomBus()))
    # And the save did happen.
    assert len(repo.saved) == 1




# ===========================================================================
# Ports are satisfied by the fakes (sanity)
# ===========================================================================
def test_stub_reading_repo_satisfies_protocol() -> None:
    assert isinstance(_StubReadingRepo(), ReadingRepo)




def test_stub_event_bus_satisfies_protocol() -> None:
    assert isinstance(_StubEventBus(), EventBus)
