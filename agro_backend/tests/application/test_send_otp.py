"""Tests for app.application.send_otp.execute."""


from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ports.farmer_repo import FarmerIdentity
from app.application.ports.whatsapp_sender import WhatsappSendResult
from app.application.send_otp import (
    OtpThrottledError,
    SendOtpDeps,
    UnknownPhoneError,
    WhatsappDeliveryError,
    execute,
)
from app.domain.auth import OtpChallenge, OtpTransport, hash_otp_code

PHONE = "+918123456789"
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")




def _farmer() -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        full_name="Test",
        language_preference="marathi",
        account_status="active",
    )




class _StubFarmerRepo:
    def __init__(self, by_phone: FarmerIdentity | None) -> None:
        self._by_phone = by_phone
        self.lookups: list[str] = []


    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        self.lookups.append(phone)
        return self._by_phone


    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        return None




class _StubOtpRepo:
    def __init__(
        self,
        latest_active: OtpChallenge | None = None,
        recent_count: int = 0,
    ) -> None:
        self.latest_active = latest_active
        self.recent_count = recent_count
        self.created: list[OtpChallenge] = []


    async def create(self, c: OtpChallenge) -> uuid.UUID:
        self.created.append(c)
        return c.challenge_id


    async def find_latest_active(self, phone: str) -> OtpChallenge | None:
        return self.latest_active


    async def find_by_id(self, cid: uuid.UUID) -> OtpChallenge | None:
        return None


    async def increment_attempt(self, cid: uuid.UUID) -> int:
        return 0


    async def mark_consumed(self, cid: uuid.UUID) -> None:
        pass


    async def recent_attempts_count(self, phone: str, since_minutes: int) -> int:
        return self.recent_count




class _StubSender:
    def __init__(self, accepted: bool = True, error: str | None = None) -> None:
        self.accepted = accepted
        self.error = error
        self.sent: list[tuple[str, str]] = []


    async def send_otp_template(
        self, *, phone: str, code: str, template_name: str, language_code: str = "en"
    ) -> WhatsappSendResult:
        self.sent.append((phone, code))
        return WhatsappSendResult(
            accepted=self.accepted,
            provider_message_id="msg-1" if self.accepted else None,
            error_code=self.error,
        )




def _deps(
    farmer: FarmerIdentity | None,
    *,
    latest_active: OtpChallenge | None = None,
    recent_count: int = 0,
    sender_ok: bool = True,
    sender_error: str | None = None,
) -> tuple[SendOtpDeps, _StubOtpRepo, _StubSender]:
    otp = _StubOtpRepo(latest_active=latest_active, recent_count=recent_count)
    sender = _StubSender(accepted=sender_ok, error=sender_error)
    return (
        SendOtpDeps(
            farmer_repo=_StubFarmerRepo(farmer),
            otp_repo=otp,
            sender=sender,
            transport=OtpTransport.LOG_ONLY,
        ),
        otp,
        sender,
    )




# ===========================================================================
# Happy path
# ===========================================================================
async def test_send_otp_creates_challenge_and_sends() -> None:
    deps, otp, sender = _deps(_farmer())
    out = await execute(phone=PHONE, deps=deps)
    assert out.challenge_id == otp.created[0].challenge_id
    assert out.masked_phone.endswith(PHONE[-4:])
    # Code was sent (we don't know which code because it's random, but
    # the call happened).
    assert len(sender.sent) == 1
    assert sender.sent[0][0] == PHONE




async def test_send_otp_creates_hashed_code_not_plain() -> None:
    deps, otp, sender = _deps(_farmer())
    await execute(phone=PHONE, deps=deps)
    saved = otp.created[0]
    # The stored hash is NOT the plain code that was sent.
    assert saved.code_hash != sender.sent[0][1]
    # And it must be a sha256-format hash.
    assert saved.code_hash.startswith("sha256$")




async def test_send_otp_attaches_farmer_tenant() -> None:
    farmer = _farmer()
    deps, otp, _ = _deps(farmer)
    await execute(phone=PHONE, deps=deps)
    assert otp.created[0].tenant_id == farmer.tenant_id




# ===========================================================================
# Negative paths
# ===========================================================================
async def test_send_otp_unknown_phone_raises() -> None:
    deps, _, _ = _deps(None)
    with pytest.raises(UnknownPhoneError):
        await execute(phone=PHONE, deps=deps)




async def test_send_otp_rejects_when_active_challenge_exists() -> None:
    now = datetime.now(UTC)
    alive = OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        code_hash=hash_otp_code("123456", "s"),
        transport=OtpTransport.LOG_ONLY,
        expires_at=now + timedelta(minutes=4),
        consumed_at=None,
        attempt_count=0,
        max_attempts=5,
        created_at=now,
    )
    deps, _, _ = _deps(_farmer(), latest_active=alive)
    with pytest.raises(OtpThrottledError) as exc_info:
        await execute(phone=PHONE, deps=deps)
    assert exc_info.value.reason == "active_challenge_exists"




async def test_send_otp_rejects_when_rate_limited() -> None:
    deps, _, _ = _deps(_farmer(), recent_count=10)
    with pytest.raises(OtpThrottledError) as exc_info:
        await execute(phone=PHONE, deps=deps)
    assert exc_info.value.reason == "rate_limited"




async def test_send_otp_raises_when_provider_rejects() -> None:
    deps, _, _ = _deps(_farmer(), sender_ok=False, sender_error="rate_limited")
    with pytest.raises(WhatsappDeliveryError) as exc_info:
        await execute(phone=PHONE, deps=deps)
    assert exc_info.value.provider_error == "rate_limited"
