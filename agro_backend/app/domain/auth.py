"""Auth-domain value objects and entities.


Pure dataclasses + enums. No framework imports, no IO. The Round-4
purity test enforces this.


* :class:`OtpChallenge` represents one row in ``otp_challenges``:
  a hashed code, an expiry, an attempt counter.
* :class:`AuthSession` represents one row in ``auth_sessions``:
  a hashed refresh token, an expiry, a revocation marker.
* :class:`TokenPair` is the access+refresh tuple returned to clients.
* :class:`AuthRole` is the StrEnum that lives in JWT claims.
* Helpers (:func:`hash_otp_code`, :func:`hash_refresh_token`,
  :func:`mask_phone`) are pure functions used by the application layer.


Why we hash the OTP code rather than store it plain: a DB dump must not
hand over live OTPs. We use a salted SHA-256 (fast: this is server-side
verification, not a password hash). The OTP TTL is short (default
5 minutes) so the slow-hash trade-off doesn't apply.
"""


from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------




class AuthRole(StrEnum):
    """Role claim carried in the JWT access token.


    The set is deliberately small for the pilot. Phase 6+ will add
    ``TECHNICIAN`` and ``DEALER``; until then any non-farmer caller is
    an admin (us).
    """


    FARMER = "farmer"
    ADMIN = "admin"




class OtpTransport(StrEnum):
    """Channel used to deliver the OTP.


    ``LOG_ONLY`` is the dev-mode sender that writes the code to the
    server log instead of dialing Meta. It is the default in Round 8;
    Round 8.5 will flip the production default to ``WHATSAPP`` once the
    Meta business account is verified.
    """


    WHATSAPP = "whatsapp"
    SMS = "sms"
    LOG_ONLY = "log_only"




# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------




@dataclass(frozen=True, slots=True)
class TokenPair:
    """Access + refresh tokens. Returned by login and refresh endpoints."""


    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_type: str = "bearer"




@dataclass(frozen=True, slots=True)
class AccessClaims:
    """The fields we put into a JWT access token's payload.


    Verbatim translation to/from the JWT envelope happens in
    :mod:`app.infra.auth.jwt_issuer`. Keeping the shape here in the
    domain layer means the application layer can reason about claims
    without depending on python-jose.
    """


    subject: uuid.UUID  # farmer_id or admin user id
    tenant_id: uuid.UUID
    role: AuthRole
    issued_at: datetime
    expires_at: datetime
    session_id: uuid.UUID | None = None  # ties access to refresh session




# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------




@dataclass(frozen=True, slots=True)
class OtpChallenge:
    """A single OTP challenge row.


    The ``code_hash`` is what we store; the plain code lives only in the
    response back to the WhatsApp template renderer and the server log
    line (dev mode only).
    """


    challenge_id: uuid.UUID
    tenant_id: uuid.UUID
    phone: str  # E.164, e.g. +918123456789
    code_hash: str
    transport: OtpTransport
    expires_at: datetime
    consumed_at: datetime | None
    attempt_count: int
    max_attempts: int
    created_at: datetime


    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


    def is_consumed(self) -> bool:
        return self.consumed_at is not None


    def is_locked(self) -> bool:
        """Too many wrong guesses; the row is dead even before expiry."""
        return self.attempt_count >= self.max_attempts


    def can_attempt(self, now: datetime) -> bool:
        return not (self.is_expired(now) or self.is_consumed() or self.is_locked())




@dataclass(frozen=True, slots=True)
class AuthSession:
    """One active refresh token. ``refresh_token_hash`` is SHA-256 of
    the random secret; the plain secret is only ever in the response
    body of /auth/verify_otp and /auth/refresh.
    """


    session_id: uuid.UUID
    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    refresh_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
    last_used_at: datetime


    def is_active(self, now: datetime) -> bool:
        return self.revoked_at is None and now < self.expires_at




# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


# 6-digit OTPs are the pilot default. The constant lives here so domain
# tests can assert against it without re-importing the application layer.
OTP_CODE_LENGTH: int = 6


# Hash separator chosen to never collide with anything pyhashes might
# put in the digest (hex chars only -> separator '$').
_HASH_SEP: str = "$"




def generate_otp_code(rng: secrets.SystemRandom | None = None) -> str:
    """Return a fresh 6-digit OTP code as a zero-padded decimal string.


    Uses ``secrets.SystemRandom`` for cryptographic randomness; the
    optional ``rng`` argument exists so unit tests can inject a seeded
    Random for deterministic output. Production calls pass ``None``.
    """
    r = rng if rng is not None else secrets.SystemRandom()
    n = r.randrange(0, 10**OTP_CODE_LENGTH)
    return f"{n:0{OTP_CODE_LENGTH}d}"




def generate_refresh_secret(num_bytes: int = 32) -> str:
    """Return a URL-safe random refresh secret. Caller hashes for storage."""
    return secrets.token_urlsafe(num_bytes)




def hash_otp_code(code: str, salt: str) -> str:
    """Salted SHA-256 of an OTP code. Format: ``sha256$<salt>$<hex>``.


    The salt is a per-challenge random string supplied by the
    application layer; storing it inside the digest keeps the
    verification operation single-column (no separate salt column).
    """
    h = hashlib.sha256()
    h.update(salt.encode("utf-8"))
    h.update(b":")
    h.update(code.encode("utf-8"))
    return f"sha256{_HASH_SEP}{salt}{_HASH_SEP}{h.hexdigest()}"




def verify_otp_code(code: str, code_hash: str) -> bool:
    """Constant-time compare of a candidate code against a stored hash."""
    try:
        scheme, salt, _digest = code_hash.split(_HASH_SEP, 2)
    except ValueError:
        return False
    if scheme != "sha256":
        return False
    candidate = hash_otp_code(code, salt)
    return hmac.compare_digest(candidate, code_hash)




def hash_refresh_token(secret: str) -> str:
    """SHA-256 of the refresh secret (hex-encoded). No salt because the
    secret itself is 32 random bytes - a salt adds nothing.
    """
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()




def mask_phone(phone: str) -> str:
    """Mask all but the last 4 digits for log output: '+91********7890'."""
    if len(phone) <= 4:
        return "*" * len(phone)
    return phone[0] + "*" * (len(phone) - 5) + phone[-4:]




def otp_expires_at(now: datetime, ttl_seconds: int) -> datetime:
    return now + timedelta(seconds=ttl_seconds)




__all__ = [
    "OTP_CODE_LENGTH",
    "AccessClaims",
    "AuthRole",
    "AuthSession",
    "OtpChallenge",
    "OtpTransport",
    "TokenPair",
    "generate_otp_code",
    "generate_refresh_secret",
    "hash_otp_code",
    "hash_refresh_token",
    "mask_phone",
    "otp_expires_at",
    "verify_otp_code",
]
