"""Tests for the Round 14 delivery state machine (deliver_advisory.execute).

Pure unit tests: a fake AiSuggestionRepo records claim + outcome calls, a fake
FarmerRepo returns a recipient, and a fake WhatsappSender returns a scripted
result so we drive every branch (sent / skipped / permanent / transient /
exhausted / claim-miss / no-recipient) without a DB or a network.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

from app.application.deliver_advisory import (
    DEFAULT_BACKOFF_SECONDS,
    DeliverAdvisoryDeps,
    execute,
)
from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.application.ports.farmer_repo import FarmerIdentity
from app.application.ports.whatsapp_sender import WhatsappSendResult

NOW = datetime.datetime(2026, 6, 20, 12, 0, tzinfo=datetime.UTC)
SID = uuid.UUID("55555555-5555-5555-5555-555555555555")
FARMER_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _suggestion(message: str = "पाणी द्या.") -> AiSuggestion:
    return AiSuggestion(
        suggestion_id=SID,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        farmer_id=FARMER_ID,
        farm_id=uuid.UUID("33333333-3333-3333-3333-333333333333"),
        plot_id="PLOT_PILOT_001",
        season_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        generated_at=NOW,
        suggestion_type="alert",
        full_message_marathi=message,
        ai_model_version="claude-sonnet-4-5",
        tokens_used=120,
        generation_time_ms=800,
    )


def _farmer() -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=FARMER_ID,
        tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        phone="+919999999999",
        full_name="Test Farmer",
        language_preference="mr",
        account_status="active",
    )


class _FakeSuggestionRepo:
    def __init__(
        self, *, claim_attempts: int | None = 0, suggestion: AiSuggestion | None = None
    ) -> None:
        self._claim_attempts = claim_attempts
        self._suggestion = suggestion if suggestion is not None else _suggestion()
        self.claimed: list[tuple[uuid.UUID, bool]] = []
        self.outcomes: list[dict[str, Any]] = []

    async def claim_for_delivery(
        self, suggestion_id: uuid.UUID, now: datetime.datetime, *, require_review: bool
    ) -> int | None:
        self.claimed.append((suggestion_id, require_review))
        return self._claim_attempts

    async def find_by_id(self, suggestion_id: uuid.UUID) -> AiSuggestion | None:
        return self._suggestion

    async def set_delivery_outcome(
        self,
        suggestion_id: uuid.UUID,
        *,
        status: str,
        attempts: int | None = None,
        next_retry_at: datetime.datetime | None = None,
        last_error: str | None = None,
        provider_message_id: str | None = None,
        sent_at: datetime.datetime | None = None,
    ) -> None:
        self.outcomes.append(
            {
                "status": status,
                "attempts": attempts,
                "next_retry_at": next_retry_at,
                "last_error": last_error,
                "provider_message_id": provider_message_id,
                "sent_at": sent_at,
            }
        )

    @property
    def last(self) -> dict[str, Any]:
        return self.outcomes[-1]


class _FakeFarmerRepo:
    def __init__(self, farmer: FarmerIdentity | None) -> None:
        self._farmer = farmer

    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        return self._farmer


class _FakeSender:
    def __init__(self, result: WhatsappSendResult | Exception) -> None:
        self._result = result
        self.calls: list[dict[str, Any]] = []

    async def send_template(
        self, *, phone: str, template_name: str, language_code: str, body_params: list[str]
    ) -> WhatsappSendResult:
        self.calls.append(
            {
                "phone": phone,
                "template_name": template_name,
                "language_code": language_code,
                "body_params": body_params,
            }
        )
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


def _deps(
    repo: _FakeSuggestionRepo,
    farmer_repo: _FakeFarmerRepo,
    sender: _FakeSender,
    *,
    require_review: bool = False,
) -> DeliverAdvisoryDeps:
    return DeliverAdvisoryDeps(
        ai_suggestion_repo=cast(Any, repo),
        farmer_repo=cast(Any, farmer_repo),
        sender=cast(Any, sender),
        template_name="agroguardian_advisory_v1",
        require_review=require_review,
    )


_OK = WhatsappSendResult(accepted=True, provider_message_id="wamid.ABC")


# --- Terminal success -------------------------------------------------------
async def test_sent_marks_delivered_and_sets_provider_id() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(_OK)
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "sent"
    assert out.provider_message_id == "wamid.ABC"
    assert repo.last["status"] == "sent"
    assert repo.last["provider_message_id"] == "wamid.ABC"
    assert repo.last["sent_at"] == NOW
    # The advisory text is passed as the template body param, in Marathi.
    assert sender.calls[0]["body_params"] == ["पाणी द्या."]
    assert sender.calls[0]["language_code"] == "mr"


# --- Claim miss -------------------------------------------------------------
async def test_already_handled_when_claim_returns_none() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=None)
    sender = _FakeSender(_OK)
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "already_handled"
    assert repo.outcomes == []
    assert sender.calls == []  # never attempted a send


# --- Skip: empty message ----------------------------------------------------
async def test_empty_message_is_skipped() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0, suggestion=_suggestion(message="   "))
    sender = _FakeSender(_OK)
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "skipped"
    assert out.skip_reason == "empty_message"
    assert repo.last["status"] == "skipped"
    assert sender.calls == []


# --- Permanent: no recipient ------------------------------------------------
async def test_unknown_farmer_is_permanent() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(_OK)
    out = await execute(suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(None), sender), now=NOW)

    assert out.outcome == "failed_permanent"
    assert repo.last["status"] == "failed_permanent"
    assert repo.last["last_error"] == "unknown_farmer"
    assert sender.calls == []


# --- Permanent: 4xx rejection -----------------------------------------------
async def test_non_transient_rejection_is_permanent() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(
        WhatsappSendResult(accepted=False, provider_message_id=None, error_code="http_400")
    )
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "failed_permanent"
    assert repo.last["status"] == "failed_permanent"
    assert repo.last["last_error"] == "http_400"


# --- Transient retry + backoff ----------------------------------------------
async def test_network_error_schedules_backoff() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(
        WhatsappSendResult(accepted=False, provider_message_id=None, error_code="network_error")
    )
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "transient_retry"
    assert repo.last["status"] == "pending"
    assert repo.last["attempts"] == 1
    assert repo.last["next_retry_at"] == NOW + datetime.timedelta(
        seconds=DEFAULT_BACKOFF_SECONDS[0]
    )


async def test_http_5xx_is_transient() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(
        WhatsappSendResult(accepted=False, provider_message_id=None, error_code="http_503")
    )
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )
    assert out.outcome == "transient_retry"


async def test_transient_exhausted_becomes_failed_transient() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=len(DEFAULT_BACKOFF_SECONDS))
    sender = _FakeSender(
        WhatsappSendResult(accepted=False, provider_message_id=None, error_code="network_error")
    )
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "failed_transient"
    assert repo.last["status"] == "failed_transient"
    assert repo.last["attempts"] == len(DEFAULT_BACKOFF_SECONDS) + 1


async def test_sender_raising_is_treated_as_transient() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(RuntimeError("boom"))
    out = await execute(
        suggestion_id=SID, deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender), now=NOW
    )

    assert out.outcome == "transient_retry"
    assert repo.last["status"] == "pending"


# --- Review gating is forwarded to the claim --------------------------------
async def test_require_review_is_passed_to_claim() -> None:
    repo = _FakeSuggestionRepo(claim_attempts=0)
    sender = _FakeSender(_OK)
    await execute(
        suggestion_id=SID,
        deps=_deps(repo, _FakeFarmerRepo(_farmer()), sender, require_review=True),
        now=NOW,
    )
    assert repo.claimed == [(SID, True)]
