"""Use case: verify an OTP and mint a token pair.


Steps:
1. Look up the active challenge for this phone.
2. Constant-time compare the supplied code against its hash.
3. On match: mark consumed, mint access token, create refresh session,
   return the TokenPair.
4. On miss: bump attempt_count, raise InvalidOtpError. After
   ``max_attempts`` misses the challenge is locked.
"""


from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from app.application.ports.auth_session_repo import AuthSessionRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.otp_repo import OtpRepo
from app.application.ports.token_issuer import TokenIssuer
from app.domain.auth import (
    AuthRole,
    AuthSession,
    TokenPair,
    generate_refresh_secret,
    hash_refresh_token,
    verify_otp_code,
)

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------




class VerifyOtpError(Exception):
    pass




class NoActiveChallengeError(VerifyOtpError):
    """No live OTP challenge for this phone (expired or never sent)."""




class ChallengeLockedError(VerifyOtpError):
    """Too many wrong guesses; the challenge is dead."""




class InvalidOtpError(VerifyOtpError):
    """Wrong code. ``attempts_remaining`` is the new count after this miss."""


    def __init__(self, attempts_remaining: int) -> None:
        super().__init__("invalid_otp")
        self.attempts_remaining = attempts_remaining




class FarmerInactiveError(VerifyOtpError):
    """Farmer's account_status is not 'active'."""




# ---------------------------------------------------------------------------
# Deps + result
# ---------------------------------------------------------------------------




@dataclass(frozen=True, slots=True)
class VerifyOtpDeps:
    farmer_repo: FarmerRepo
    otp_repo: OtpRepo
    session_repo: AuthSessionRepo
    token_issuer: TokenIssuer
    refresh_ttl_seconds: int = 30 * 24 * 3600  # 30 days




# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------




async def execute(
    *,
    phone: str,
    code: str,
    deps: VerifyOtpDeps,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> TokenPair:
    """Verify ``code`` against the active challenge for ``phone``.


    Returns a fresh TokenPair. Caller is responsible for shipping it
    over HTTPS only.
    """
    now = datetime.now(UTC)


    challenge = await deps.otp_repo.find_latest_active(phone)
    if challenge is None or challenge.is_expired(now) or challenge.is_consumed():
        raise NoActiveChallengeError(phone)


    if challenge.is_locked():
        raise ChallengeLockedError(phone)


    if not verify_otp_code(code, challenge.code_hash):
        new_count = await deps.otp_repo.increment_attempt(challenge.challenge_id)
        remaining = max(0, challenge.max_attempts - new_count)
        raise InvalidOtpError(attempts_remaining=remaining)


    # Hit. Lock the challenge so it can't be reused.
    await deps.otp_repo.mark_consumed(challenge.challenge_id)


    farmer = await deps.farmer_repo.find_by_phone(phone)
    if farmer is None or farmer.account_status != "active":
        raise FarmerInactiveError(phone)


    # Mint refresh session FIRST so we can embed its id in the access token.
    refresh_secret = generate_refresh_secret()
    refresh_expires_at = now + timedelta(seconds=deps.refresh_ttl_seconds)
    session = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=farmer.tenant_id,
        farmer_id=farmer.farmer_id,
        refresh_token_hash=hash_refresh_token(refresh_secret),
        expires_at=refresh_expires_at,
        revoked_at=None,
        created_at=now,
        last_used_at=now,
    )
    session_id = await deps.session_repo.create(session)


    access_token, claims = deps.token_issuer.issue_access_token(
        subject=farmer.farmer_id,
        tenant_id=farmer.tenant_id,
        role=AuthRole.FARMER,
        session_id=session_id,
    )


    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_secret,
        access_expires_at=claims.expires_at,
        refresh_expires_at=refresh_expires_at,
    )




__all__ = [
    "ChallengeLockedError",
    "FarmerInactiveError",
    "InvalidOtpError",
    "NoActiveChallengeError",
    "VerifyOtpDeps",
    "VerifyOtpError",
    "execute",
]
