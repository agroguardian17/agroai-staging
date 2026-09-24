"""Consent withdrawal use-case (A3.5)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

import pytest

from app.application.withdraw_consent import NoConsentError, withdraw_consent

_FARMER = uuid.uuid4()


@dataclass
class _Event:
    event_type: str
    scope: str


class _FakeConsentRepo:
    def __init__(self, has_row: bool = True) -> None:
        self._has_row = has_row
        self.scope_calls: list[tuple[str, bool]] = []
        self.events: list[_Event] = []

    async def set_scope(self, farmer_id, scope, *, granted, withdrawn_at=None) -> bool:
        if not self._has_row:
            return False
        self.scope_calls.append((scope, granted))
        return True

    async def record_event(self, *, farmer_id, event_type, scope, consent_version, channel, actor):
        self.events.append(_Event(event_type, scope))


async def _run(repo: _FakeConsentRepo, scope: str):
    return await withdraw_consent(
        farmer_id=_FARMER,
        scope=scope,
        actor="farmer_app",
        channel="farmer_app",
        consent_repo=repo,  # type: ignore[arg-type]
        now=datetime(2026, 11, 1),
    )


async def test_withdraw_research_keeps_advisory_active() -> None:
    repo = _FakeConsentRepo()
    res = await _run(repo, "research")
    assert res.advisory_still_active is True
    assert repo.scope_calls == [("research", False)]
    assert repo.events[0].event_type == "withdrawn"


async def test_withdraw_advisory_is_full_optout() -> None:
    res = await _run(_FakeConsentRepo(), "advisory")
    assert res.advisory_still_active is False


async def test_unknown_scope_raises() -> None:
    with pytest.raises(ValueError, match="unknown consent scope"):
        await _run(_FakeConsentRepo(), "marketing")


async def test_no_consent_row_raises() -> None:
    with pytest.raises(NoConsentError):
        await _run(_FakeConsentRepo(has_row=False), "research")
