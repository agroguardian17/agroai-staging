"""Tests for app.application.verify_otp.execute."""


from __future__ import annotations


import uuid
from datetime import UTC, datetime, timedelta


import pytest


from app.application.ports.farmer_repo import FarmerIdentity
from app.application.verify_otp import (
    ChallengeLockedError,
    FarmerInactiveError,
    InvalidOtpError,
    NoActiveChallengeError,
    VerifyOtpDeps,
    execute,
)
from app.domain.auth import (
    AccessClaims,
    AuthRole,
    AuthSession,
    OtpChallenge,
    OtpTransport,
    hash_otp_code,
)


PHONE = "+918123456789"
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
NOW = datetime.now(UTC)




def _farmer(status: str = "active") -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        full_name="Test",
        language_preference="marathi",
        account_status=status,
    )




def _challenge(
    *,
    code: str = "123456",
    salt: str = "saltA",
    expires_at: datetime | None = None,
    consumed_at: datetime | None = None,
    attempt_count: int = 0,
    max_attempts: int = 5,
) -> OtpChallenge:
    return OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        code_hash=hash_otp_code(code, salt),
        transport=OtpTransport.LOG_ONLY,
        expires_at=expires_at or NOW + timedelta(minutes=5),
        consumed_at=consumed_at,
        attempt_count=attempt_count,
        max_attempts=max_attempts,
        created_at=NOW,
    )




class _StubFarmerRepo:
    def __init__(self, farmer: FarmerIdentity | None) -> None:
        self._farmer = farmer


    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        return self._farmer


    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        return self._farmer




class _StubOtpRepo:
    def __init__(self, latest: OtpChallenge | None) -> None:
        self.latest = latest
        self.consumed: list[uuid.UUID] = []
        self.incremented: list[uuid.UUID] = []


    async def create(self, c: OtpChallenge) -> uuid.UUID:
        raise AssertionError


    async def find_latest_active(self, phone: str) -> OtpChallenge | None:
        return self.latest


    async def find_by_id(self, cid: uuid.UUID) -> OtpChallenge | None:
        return None


    async def increment_attempt(self, cid: uuid.UUID) -> int:
        self.incremented.append(cid)
        return (self.latest.attempt_count + 1) if self.latest else 1


    async def mark_consumed(self, cid: uuid.UUID) -> None:
        self.consumed.append(cid)


    async def recent_attempts_count(self, phone: str, since_minutes: int) -> int:
        return 0




class _StubSessionRepo:
    def __init__(self) -> None:
        self.created: list[AuthSession] = []


    async def create(self, s: AuthSession) -> uuid.UUID:
        self.created.append(s)
        return s.session_id


    async def find_by_token_hash(self, h: str) -> AuthSession | None:
        return None


    async def revoke(self, sid: uuid.UUID) -> None:
        pass


    async def revoke_all_for_farmer(self, farmer_id: uuid.UUID) -> int:
        return 0


    async def touch(self, sid: uuid.UUID) -> None:
        pass




class _StubTokenIssuer:
    def __init__(self) -> None:
        self.minted: list[uuid.UUID] = []


    def issue_access_token(
        self,
        *,
        subject: uuid.UUID,
        tenant_id: uuid.UUID,
        role: AuthRole,
        session_id: uuid.UUID,
    ) -> tuple[str, AccessClaims]:
        self.minted.append(subject)
        return "jwt.access.token", AccessClaims(
            subject=subject,
            tenant_id=tenant_id,
            role=role,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            session_id=session_id,
        )


    def verify_access_token(self, token: str) -> AccessClaims:
        raise AssertionError




def _deps(
    farmer: FarmerIdentity | None, latest: OtpChallenge | None
) -> tuple[VerifyOtpDeps, _StubOtpRepo, _StubSessionRepo, _StubTokenIssuer]:
    otp = _StubOtpRepo(latest)
    sess = _StubSessionRepo()
    issuer = _StubTokenIssuer()
    return (
        VerifyOtpDeps(
            farmer_repo=_StubFarmerRepo(farmer),
            otp_repo=otp,
            session_repo=sess,
            token_issuer=issuer,
        ),
        otp,
        sess,
        issuer,
    )




# ===========================================================================
# Happy path
# ===========================================================================
async def test_verify_otp_correct_code_returns_token_pair() -> None:
    chal = _challenge(code="123456", salt="saltA")
    deps, otp, sess, issuer = _deps(_farmer(), chal)
    tp = await execute(phone=PHONE, code="123456", deps=deps)
    assert tp.access_token == "jwt.access.token"
    assert tp.refresh_token and tp.refresh_token != tp.access_token
    assert chal.challenge_id in otp.consumed
    assert len(sess.created) == 1
    assert sess.created[0].farmer_id == issuer.minted[0]




# ===========================================================================
# Negative paths
# ===========================================================================
async def test_verify_otp_no_active_challenge_raises() -> None:
    deps, _, _, _ = _deps(_farmer(), None)
    with pytest.raises(NoActiveChallengeError):
        await execute(phone=PHONE, code="123456", deps=deps)




async def test_verify_otp_expired_challenge_raises_no_active() -> None:
    chal = _challenge(expires_at=NOW - timedelta(seconds=1))
    deps, _, _, _ = _deps(_farmer(), chal)
    with pytest.raises(NoActiveChallengeError):
        await execute(phone=PHONE, code="123456", deps=deps)




async def test_verify_otp_consumed_challenge_raises_no_active() -> None:
    chal = _challenge(consumed_at=NOW)
    deps, _, _, _ = _deps(_farmer(), chal)
    with pytest.raises(NoActiveChallengeError):
        await execute(phone=PHONE, code="123456", deps=deps)




async def test_verify_otp_locked_challenge_raises() -> None:
    chal = _challenge(attempt_count=5, max_attempts=5)
    deps, _, _, _ = _deps(_farmer(), chal)
    with pytest.raises(ChallengeLockedError):
        await execute(phone=PHONE, code="000000", deps=deps)




async def test_verify_otp_wrong_code_increments_and_raises() -> None:
    chal = _challenge(code="123456", attempt_count=0, max_attempts=5)
    deps, otp, _, _ = _deps(_farmer(), chal)
    with pytest.raises(InvalidOtpError) as exc_info:
        await execute(phone=PHONE, code="000000", deps=deps)
    assert chal.challenge_id in otp.incremented
    # 5 - (0+1) = 4 attempts remaining.
    assert exc_info.value.attempts_remaining == 4




async def test_verify_otp_inactive_farmer_raises() -> None:
    chal = _challenge(code="123456")
    deps, _, _, _ = _deps(_farmer(status="suspended"), chal)
    with pytest.raises(FarmerInactiveError):
        await execute(phone=PHONE, code="123456", deps=deps)
