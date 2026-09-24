"""Erasure-fulfilment sweep (A4.3)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from app.application.fulfil_erasures import fulfil_erasures
from app.application.ports.erasure_request_repo import ErasureRequest

_NOW = datetime(2026, 12, 1, 2, 30, tzinfo=UTC)


def _req(farmer_id: uuid.UUID) -> ErasureRequest:
    return ErasureRequest(
        id=uuid.uuid4(),
        farmer_id=farmer_id,
        requested_at=_NOW - timedelta(days=31),
        due_at=_NOW - timedelta(days=1),
        status="pending",
    )


class _FakeErasureRepo:
    def __init__(self, due: list[ErasureRequest]) -> None:
        self._due = due
        self.completed: list[uuid.UUID] = []

    async def list_due(self, now, *, limit=500) -> list[ErasureRequest]:
        return self._due

    async def mark_completed(self, request_id, *, completed_at) -> None:
        self.completed.append(request_id)


class _FakeFarmerRepo:
    def __init__(self, missing: set[uuid.UUID] | None = None) -> None:
        self._missing = missing or set()
        self.anonymised: list[uuid.UUID] = []

    async def anonymise_identity(self, farmer_id) -> bool:
        if farmer_id in self._missing:
            return False
        self.anonymised.append(farmer_id)
        return True


async def test_anonymises_each_due_farmer_and_closes_request() -> None:
    f1, f2 = uuid.uuid4(), uuid.uuid4()
    due = [_req(f1), _req(f2)]
    erasure, farmer = _FakeErasureRepo(due), _FakeFarmerRepo()
    res = await fulfil_erasures(erasure_repo=erasure, farmer_repo=farmer, now=_NOW)  # type: ignore[arg-type]
    assert res.processed == 2
    assert res.anonymised == 2
    assert res.missing == 0
    assert set(farmer.anonymised) == {f1, f2}
    assert len(erasure.completed) == 2  # both requests closed


async def test_missing_farmer_still_closes_request() -> None:
    f1 = uuid.uuid4()
    due = [_req(f1)]
    erasure, farmer = _FakeErasureRepo(due), _FakeFarmerRepo(missing={f1})
    res = await fulfil_erasures(erasure_repo=erasure, farmer_repo=farmer, now=_NOW)  # type: ignore[arg-type]
    assert res.anonymised == 0
    assert res.missing == 1
    assert erasure.completed == [due[0].id]  # closed even though farmer was gone


async def test_no_due_requests_is_noop() -> None:
    erasure, farmer = _FakeErasureRepo([]), _FakeFarmerRepo()
    res = await fulfil_erasures(erasure_repo=erasure, farmer_repo=farmer, now=_NOW)  # type: ignore[arg-type]
    assert res == res.__class__(0, 0, 0)
    assert farmer.anonymised == []
