"""Erasure-request use-case (A3.4)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.application.ports.erasure_request_repo import ErasureRequest
from app.application.request_erasure import request_erasure

_FARMER = uuid.uuid4()
_NOW = datetime(2026, 11, 1, 9, 0, tzinfo=UTC)


class _FakeErasureRepo:
    def __init__(self, already_pending: bool = False) -> None:
        self._already = already_pending
        self.created_due: datetime | None = None

    async def create(self, *, farmer_id, due_at, method, actor) -> bool:
        if self._already:
            return False
        self.created_due = due_at
        return True

    async def pending_for(self, farmer_id) -> ErasureRequest | None:
        if not self._already:
            return None
        return ErasureRequest(
            id=uuid.uuid4(),
            farmer_id=farmer_id,
            requested_at=_NOW - timedelta(days=5),
            due_at=_NOW + timedelta(days=25),  # 5 days into a prior request
            status="pending",
        )


class _FakeConsentRepo:
    def __init__(self) -> None:
        self.deletion_flag: bool | None = None

    async def mark_deletion_requested(self, farmer_id, *, requested) -> None:
        self.deletion_flag = requested


async def test_creates_request_with_30day_due_and_flags_deletion() -> None:
    erasure, consent = _FakeErasureRepo(), _FakeConsentRepo()
    res = await request_erasure(
        farmer_id=_FARMER,
        actor="farmer_app",
        erasure_repo=erasure,
        consent_repo=consent,
        now=_NOW,  # type: ignore[arg-type]
    )
    assert res.already_pending is False
    assert res.due_at == _NOW + timedelta(days=30)
    assert consent.deletion_flag is True


async def test_idempotent_returns_existing_pending() -> None:
    erasure, consent = _FakeErasureRepo(already_pending=True), _FakeConsentRepo()
    res = await request_erasure(
        farmer_id=_FARMER,
        actor="farmer_app",
        erasure_repo=erasure,
        consent_repo=consent,
        now=_NOW,  # type: ignore[arg-type]
    )
    assert res.already_pending is True
    assert res.due_at == _NOW + timedelta(days=25)  # the existing request's due date
    assert consent.deletion_flag is True  # still (re)flagged, harmless
