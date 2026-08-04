"""Tests for app.domain.auth - all pure, no IO, no fixtures needed."""


from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.auth import (
    OTP_CODE_LENGTH,
    AccessClaims,
    AuthRole,
    AuthSession,
    OtpChallenge,
    OtpTransport,
    TokenPair,
    generate_otp_code,
    generate_refresh_secret,
    hash_otp_code,
    hash_refresh_token,
    mask_phone,
    otp_expires_at,
    verify_otp_code,
)


# ===========================================================================
# OTP code generation
# ===========================================================================
def test_generate_otp_code_is_six_digits() -> None:
    code = generate_otp_code()
    assert len(code) == OTP_CODE_LENGTH
    assert code.isdigit()




def test_generate_otp_code_pads_leading_zeros() -> None:
    # A seeded Random instance is deterministic; randrange(0, 1_000_000)
    # with seed 0 returns a small number on cpython that needs padding.
    class _SeededRandom(random.Random):
        pass


    seeded = _SeededRandom(0)
    code = generate_otp_code(rng=seeded)  # type: ignore[arg-type]
    assert len(code) == OTP_CODE_LENGTH
    assert code.isdigit()




# ===========================================================================
# OTP hash / verify
# ===========================================================================
def test_hash_otp_code_then_verify_matches() -> None:
    salt = "abc123"
    h = hash_otp_code("123456", salt)
    assert h.startswith("sha256$")
    assert verify_otp_code("123456", h) is True




def test_verify_otp_code_rejects_wrong_code() -> None:
    h = hash_otp_code("123456", "salt")
    assert verify_otp_code("123457", h) is False




def test_verify_otp_code_rejects_malformed_hash() -> None:
    assert verify_otp_code("123456", "not-a-hash") is False
    assert verify_otp_code("123456", "") is False
    assert verify_otp_code("123456", "md5$x$abc") is False




def test_hash_otp_code_is_deterministic_for_same_salt() -> None:
    a = hash_otp_code("123456", "saltA")
    b = hash_otp_code("123456", "saltA")
    assert a == b




def test_hash_otp_code_differs_with_different_salt() -> None:
    a = hash_otp_code("123456", "saltA")
    b = hash_otp_code("123456", "saltB")
    assert a != b




# ===========================================================================
# Refresh-token hashing
# ===========================================================================
def test_generate_refresh_secret_is_url_safe_and_long() -> None:
    s = generate_refresh_secret()
    # token_urlsafe(32) returns ~43 chars; ample for our needs.
    assert len(s) >= 32
    assert all(c.isalnum() or c in "-_" for c in s)




def test_hash_refresh_token_is_sha256_hex() -> None:
    h = hash_refresh_token("test-secret")
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)
    # Same input -> same hash (deterministic).
    assert hash_refresh_token("test-secret") == h




# ===========================================================================
# Phone masking
# ===========================================================================
def test_mask_phone_keeps_last_4_digits() -> None:
    assert mask_phone("+918123456789") == "+********6789"




def test_mask_phone_handles_short_strings() -> None:
    assert mask_phone("123") == "***"




# ===========================================================================
# OtpChallenge state
# ===========================================================================
NOW = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)




def _challenge(**over: object) -> OtpChallenge:
    base: dict[str, object] = {
        "challenge_id": uuid.uuid4(),
        "tenant_id": uuid.uuid4(),
        "phone": "+918123456789",
        "code_hash": hash_otp_code("123456", "s"),
        "transport": OtpTransport.WHATSAPP,
        "expires_at": NOW + timedelta(minutes=5),
        "consumed_at": None,
        "attempt_count": 0,
        "max_attempts": 5,
        "created_at": NOW,
    }
    base.update(over)
    return OtpChallenge(**base)  # type: ignore[arg-type]




def test_otp_challenge_is_expired_when_now_past_expiry() -> None:
    c = _challenge(expires_at=NOW - timedelta(seconds=1))
    assert c.is_expired(NOW) is True




def test_otp_challenge_is_not_expired_before_expiry() -> None:
    assert _challenge().is_expired(NOW) is False




def test_otp_challenge_is_consumed_when_consumed_at_set() -> None:
    c = _challenge(consumed_at=NOW)
    assert c.is_consumed() is True
    assert c.can_attempt(NOW) is False




def test_otp_challenge_is_locked_at_max_attempts() -> None:
    c = _challenge(attempt_count=5, max_attempts=5)
    assert c.is_locked() is True
    assert c.can_attempt(NOW) is False




def test_otp_challenge_can_attempt_when_fresh() -> None:
    assert _challenge().can_attempt(NOW) is True




# ===========================================================================
# AuthSession state
# ===========================================================================
def test_auth_session_is_active_when_unrevoked_and_unexpired() -> None:
    s = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        farmer_id=uuid.uuid4(),
        refresh_token_hash="h",
        expires_at=NOW + timedelta(days=30),
        revoked_at=None,
        created_at=NOW,
        last_used_at=NOW,
    )
    assert s.is_active(NOW) is True




def test_auth_session_is_inactive_when_revoked() -> None:
    s = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        farmer_id=uuid.uuid4(),
        refresh_token_hash="h",
        expires_at=NOW + timedelta(days=30),
        revoked_at=NOW,
        created_at=NOW,
        last_used_at=NOW,
    )
    assert s.is_active(NOW) is False




def test_auth_session_is_inactive_when_expired() -> None:
    s = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        farmer_id=uuid.uuid4(),
        refresh_token_hash="h",
        expires_at=NOW - timedelta(seconds=1),
        revoked_at=None,
        created_at=NOW,
        last_used_at=NOW,
    )
    assert s.is_active(NOW) is False




# ===========================================================================
# Misc
# ===========================================================================
def test_otp_expires_at_is_ttl_plus_now() -> None:
    out = otp_expires_at(NOW, 300)
    assert out == NOW + timedelta(seconds=300)




def test_token_pair_default_token_type_is_bearer() -> None:
    p = TokenPair(
        access_token="a",
        refresh_token="r",
        access_expires_at=NOW,
        refresh_expires_at=NOW,
    )
    assert p.token_type == "bearer"




def test_access_claims_holds_subject_tenant_role() -> None:
    sub = uuid.uuid4()
    tid = uuid.uuid4()
    c = AccessClaims(
        subject=sub,
        tenant_id=tid,
        role=AuthRole.FARMER,
        issued_at=NOW,
        expires_at=NOW + timedelta(minutes=15),
    )
    assert c.subject == sub
    assert c.tenant_id == tid
    assert c.role is AuthRole.FARMER




def test_auth_role_values() -> None:
    assert AuthRole.FARMER == "farmer"
    assert AuthRole.ADMIN == "admin"




def test_otp_transport_includes_log_only() -> None:
    assert OtpTransport.LOG_ONLY == "log_only"




# Sanity: dataclass really is frozen.
def test_otp_challenge_is_frozen() -> None:
    c = _challenge()
    with pytest.raises(AttributeError):
        c.attempt_count = 99  # type: ignore[misc]
