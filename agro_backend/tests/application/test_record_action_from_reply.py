"""Tests for record_action_from_reply (WhatsApp reply -> farmer_action)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

import pytest

from app.application.ports.farmer_action_repo import AdvisoryContext, FarmerActionInput
from app.application.record_action_from_reply import (
    RecordActionDeps,
    execute,
    parse_followed,
    parse_quantity,
)

NOW = datetime.datetime(2026, 9, 15, 10, 0, tzinfo=datetime.UTC)
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _ctx(is_watering: bool = True) -> AdvisoryContext:
    return AdvisoryContext(
        suggestion_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        farmer_id=FARMER,
        farm_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        season_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        plot_id="PLOT_PILOT_001",
        is_watering=is_watering,
    )


class _FakeActionRepo:
    def __init__(self, ctx: AdvisoryContext | None) -> None:
        self._ctx = ctx
        self.recorded: list[FarmerActionInput] = []

    async def latest_advisory_for_farmer(
        self, farmer_id: uuid.UUID, *, within_days: int
    ) -> AdvisoryContext | None:
        return self._ctx

    async def record(self, action: FarmerActionInput) -> int:
        self.recorded.append(action)
        return len(self.recorded)


def _deps(repo: Any) -> RecordActionDeps:
    return RecordActionDeps(farmer_action_repo=cast(Any, repo))


# --- parsing helpers --------------------------------------------------------
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("500", 500.0),
        ("हो ५०० लिटर दिले", 500.0),
        ("250 litres", 250.0),
        ("no idea", None),
        ("", None),
    ],
)
def test_parse_quantity(text: str, expected: float | None) -> None:
    assert parse_quantity(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("हो", True),
        ("होय दिले", True),
        ("yes", True),
        ("नाही", False),
        ("no", False),
        ("हो नाही", None),
        ("maybe", None),
    ],
)
def test_parse_followed(text: str, expected: bool | None) -> None:
    assert parse_followed(text) == expected


# --- orchestration ----------------------------------------------------------
async def test_watering_reply_is_recorded() -> None:
    repo = _FakeActionRepo(_ctx(is_watering=True))
    out = await execute(farmer_id=FARMER, reply_text="हो, 500 दिले", deps=_deps(repo), now=NOW)
    assert out == 1
    a = repo.recorded[0]
    assert a.action_type == "watering"
    assert a.water_liters == 500.0
    assert a.farmer_followed_ai is True
    assert a.ai_suggestion_id == _ctx().suggestion_id
    assert a.source == "whatsapp_reply"
    assert a.farmer_note == "हो, 500 दिले"


async def test_non_watering_advisory_without_number_is_other() -> None:
    repo = _FakeActionRepo(_ctx(is_watering=False))
    await execute(farmer_id=FARMER, reply_text="केले", deps=_deps(repo), now=NOW)
    a = repo.recorded[0]
    assert a.action_type == "other"
    assert a.water_liters is None
    assert a.farmer_followed_ai is True


async def test_no_recent_advisory_records_nothing() -> None:
    repo = _FakeActionRepo(None)
    out = await execute(farmer_id=FARMER, reply_text="500", deps=_deps(repo), now=NOW)
    assert out is None
    assert repo.recorded == []
