"""D12-DPDP-001 consent capture use-case."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime

import pytest

from app.application.ports.farmer_consent_repo import ConsentCapture
from app.application.record_consent import (
    ConsentRequiredError,
    MinorConsentError,
    record_consent,
)
from app.domain.consent_notice import CONSENT_NOTICE_VERSION, consent_notice_hash

_FARMER = uuid.uuid4()
_TENANT = uuid.uuid4()
_NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


@dataclass
class _Event:
    event_type: str
    scope: str


class _FakeConsentRepo:
    def __init__(self) -> None:
        self.captured: ConsentCapture | None = None
        self.events: list[_Event] = []

    async def for_farmer(self, farmer_id: uuid.UUID):  # pragma: no cover - unused
        return None

    async def capture(self, record: ConsentCapture) -> None:
        self.captured = record

    async def record_event(
        self, *, farmer_id, event_type, scope, consent_version, channel, actor
    ) -> None:
        self.events.append(_Event(event_type, scope))


async def _run(repo: _FakeConsentRepo, **kw: object):
    return await record_consent(
        farmer_id=_FARMER,
        tenant_id=_TENANT,
        consent_advisory=kw.get("consent_advisory", True),  # type: ignore[arg-type]
        consent_research=kw.get("consent_research", False),  # type: ignore[arg-type]
        third_party_share=kw.get("third_party_share", False),  # type: ignore[arg-type]
        channel="whatsapp",
        actor="reg_flow",
        consent_repo=repo,  # type: ignore[arg-type]
        date_of_birth=kw.get("date_of_birth"),  # type: ignore[arg-type]
        parental_consent_by=kw.get("parental_consent_by"),  # type: ignore[arg-type]
        now=_NOW,
    )


async def test_captures_versioned_consent_and_retention() -> None:
    repo = _FakeConsentRepo()
    res = await _run(repo)
    assert repo.captured is not None
    assert repo.captured.consent_version == CONSENT_NOTICE_VERSION
    assert repo.captured.consent_notice_hash == consent_notice_hash()
    assert repo.captured.consent_date == date(2026, 11, 1)
    assert res.data_retention_until == date(2029, 11, 1)  # consent + 3 years
    assert [e.scope for e in repo.events] == ["advisory"]  # only granted scopes


async def test_all_scopes_log_events() -> None:
    repo = _FakeConsentRepo()
    await _run(repo, consent_research=True, third_party_share=True)
    assert {e.scope for e in repo.events} == {"advisory", "research", "third_party"}
    assert all(e.event_type == "given" for e in repo.events)


async def test_advisory_consent_is_blocking() -> None:
    with pytest.raises(ConsentRequiredError):
        await _run(_FakeConsentRepo(), consent_advisory=False)


async def test_minor_without_parental_consent_raises() -> None:
    with pytest.raises(MinorConsentError):
        await _run(_FakeConsentRepo(), date_of_birth=date(2015, 1, 1))


async def test_minor_with_parental_consent_is_verified() -> None:
    repo = _FakeConsentRepo()
    res = await _run(repo, date_of_birth=date(2015, 1, 1), parental_consent_by="Parent Name")
    assert res.parental_consent_required is True
    assert repo.captured is not None
    assert repo.captured.parental_consent_by == "Parent Name"
    assert repo.captured.parental_consent_verified is True


async def test_adult_has_no_parental_fields() -> None:
    repo = _FakeConsentRepo()
    await _run(repo, date_of_birth=date(1990, 1, 1))
    assert repo.captured is not None
    assert repo.captured.parental_consent_by is None
    assert repo.captured.parental_consent_verified is None
