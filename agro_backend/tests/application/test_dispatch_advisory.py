"""Tests for the Round 13 advisory state machine (dispatch_advisory.execute).

Pure unit tests: a fake AlertRepo records claim + outcome calls, a fake EventBus
records publishes, and ``compose_advisory.execute`` is monkeypatched so we drive
every branch (composed / skipped / permanent / transient / exhausted / claim-miss)
without a DB or an LLM.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from app.application import compose_advisory
from app.application.compose_advisory import ComposeAdvisoryDeps, ComposeAdvisoryResult
from app.application.dispatch_advisory import (
    DEFAULT_BACKOFF_SECONDS,
    DispatchAdvisoryDeps,
    execute,
)
from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.application.ports.chat_model import ChatModelError

NOW = datetime.datetime(2026, 6, 20, 12, 0, tzinfo=datetime.UTC)


def _suggestion() -> AiSuggestion:
    return AiSuggestion(
        suggestion_id=uuid.UUID("55555555-5555-5555-5555-555555555555"),
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        farmer_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
        farm_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        plot_id="PLOT_PILOT_001",
        season_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        generated_at=NOW,
        suggestion_type="alert",
        full_message_marathi="पाणी द्या.",
        ai_model_version="claude-sonnet-4-5",
        tokens_used=120,
        generation_time_ms=800,
    )


class _FakeAlertRepo:
    def __init__(self, claim_attempts: int | None = 0) -> None:
        self._claim_attempts = claim_attempts
        self.claimed: list[int] = []
        self.outcomes: list[dict[str, Any]] = []

    async def claim_for_advisory(self, alert_id: int, now: datetime.datetime) -> int | None:
        self.claimed.append(alert_id)
        return self._claim_attempts

    async def set_advisory_outcome(
        self,
        alert_id: int,
        *,
        status: str,
        attempts: int | None = None,
        next_retry_at: datetime.datetime | None = None,
        last_error: str | None = None,
    ) -> None:
        self.outcomes.append(
            {
                "status": status,
                "attempts": attempts,
                "next_retry_at": next_retry_at,
                "last_error": last_error,
            }
        )

    @property
    def last(self) -> dict[str, Any]:
        return self.outcomes[-1]


class _FakeEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []

    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        self.published.append((event_name, payload))


def _deps(repo: _FakeAlertRepo, bus: _FakeEventBus) -> DispatchAdvisoryDeps:
    return DispatchAdvisoryDeps(
        alert_repo=cast(Any, repo),
        compose_deps=cast(ComposeAdvisoryDeps, object()),  # ignored (compose is patched)
        event_bus=cast(Any, bus),
    )


def _patch_compose(monkeypatch: Any, fn: Any) -> None:
    monkeypatch.setattr(compose_advisory, "execute", fn)


# ---------------------------------------------------------------------------
# Terminal success
# ---------------------------------------------------------------------------
async def test_composed_marks_and_emits(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(0), _FakeEventBus()
    sug = _suggestion()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        return ComposeAdvisoryResult(suggestion=sug)

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "composed"
    assert repo.claimed == [7]
    assert repo.last["status"] == "composed"
    assert bus.published[0][0] == "suggestion.generated"
    payload = bus.published[0][1]
    assert payload["advisory_status"] == "composed"
    assert payload["confidence_band"] is None
    assert payload["suggestion_id"] == str(sug.suggestion_id)


# ---------------------------------------------------------------------------
# Skip
# ---------------------------------------------------------------------------
async def test_skipped_records_reason_no_event(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(0), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        return ComposeAdvisoryResult(suggestion=None, skip_reason="no_active_season")

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "skipped"
    assert out.skip_reason == "no_active_season"
    assert repo.last["status"] == "skipped"
    assert repo.last["last_error"] == "skip:no_active_season"
    assert bus.published == []


# ---------------------------------------------------------------------------
# Claim miss
# ---------------------------------------------------------------------------
async def test_already_handled_when_claim_returns_none(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(claim_attempts=None), _FakeEventBus()
    called = False

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        nonlocal called
        called = True
        return ComposeAdvisoryResult(suggestion=_suggestion())

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "already_handled"
    assert called is False  # compose never ran
    assert repo.outcomes == []  # nothing written
    assert bus.published == []


# ---------------------------------------------------------------------------
# Permanent failure
# ---------------------------------------------------------------------------
async def test_permanent_error_marks_failed_permanent(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(0), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        raise ChatModelError("content_policy", transient=False)

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "failed_permanent"
    assert repo.last["status"] == "failed_permanent"
    assert "content_policy" in repo.last["last_error"]
    assert bus.published == []


# ---------------------------------------------------------------------------
# Transient retry + backoff
# ---------------------------------------------------------------------------
async def test_transient_error_schedules_backoff(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(claim_attempts=0), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        raise ChatModelError("timeout", transient=True)

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "transient_retry"
    assert repo.last["status"] == "pending"
    assert repo.last["attempts"] == 1
    expected = NOW + datetime.timedelta(seconds=DEFAULT_BACKOFF_SECONDS[0])
    assert repo.last["next_retry_at"] == expected


async def test_transient_honours_retry_after(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(claim_attempts=0), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        raise ChatModelError("rate_limited", transient=True, retry_after_seconds=17)

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "transient_retry"
    assert repo.last["next_retry_at"] == NOW + datetime.timedelta(seconds=17)


async def test_transient_exhausted_becomes_failed_transient(monkeypatch: Any) -> None:
    # claim returns attempts == len(backoff); the next failure exhausts it.
    repo, bus = _FakeAlertRepo(claim_attempts=len(DEFAULT_BACKOFF_SECONDS)), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        raise ChatModelError("timeout", transient=True)

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "failed_transient"
    assert repo.last["status"] == "failed_transient"
    assert repo.last["attempts"] == len(DEFAULT_BACKOFF_SECONDS) + 1


async def test_unexpected_exception_is_treated_as_transient(monkeypatch: Any) -> None:
    repo, bus = _FakeAlertRepo(claim_attempts=0), _FakeEventBus()

    async def fake(*, alert_id: int, deps: Any, now: datetime.datetime) -> ComposeAdvisoryResult:
        raise ValueError("boom")

    _patch_compose(monkeypatch, fake)
    out = await execute(alert_id=7, deps=_deps(repo, bus), now=NOW)

    assert out.outcome == "transient_retry"
    assert repo.last["status"] == "pending"
