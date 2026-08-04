"""Use case: issue an OTP challenge for a farmer phone.


Orchestrates: generate code -> store hashed -> send via WhatsApp port.


Throttling policy (lives here in the application layer, not in HTTP):


* At most one ACTIVE (unconsumed, unexpired) challenge per phone at a
  time. A second send while the previous is alive is rejected with
  :class:`OtpThrottledError` - the client should ask the farmer to
  wait for the existing code (or for it to expire).
* At most 5 challenges per phone per 30 minutes. Catches the case
  where a previous challenge has expired but the farmer is hammering
  the button.


Returns the challenge_id only - never the plain code. The code goes
out via WhatsApp (or to the server log in dev mode).
"""


from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.otp_repo import OtpRepo
from app.application.ports.whatsapp_sender import WhatsappSender
from app.domain.auth import (
    OtpChallenge,
    OtpTransport,
    generate_otp_code,
    generate_refresh_secret,
    hash_otp_code,
    mask_phone,
    otp_expires_at,
)

# ---------------------------------------------------------------------------
# Errors - the use case raises domain-shaped errors; HTTP layer translates.
# ---------------------------------------------------------------------------




class SendOtpError(Exception):
    """Base class for send_otp problems."""




class UnknownPhoneError(SendOtpError):
    """No farmer registered with this phone number."""




class OtpThrottledError(SendOtpError):
    """Too many OTPs requested too recently."""


    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason




class WhatsappDeliveryError(SendOtpError):
    """Send was attempted but the provider rejected it."""


    def __init__(self, provider_error: str) -> None:
        super().__init__(provider_error)
        self.provider_error = provider_error




# ---------------------------------------------------------------------------
# Deps + result
# ---------------------------------------------------------------------------




@dataclass(frozen=True, slots=True)
class SendOtpDeps:
    farmer_repo: FarmerRepo
    otp_repo: OtpRepo
    sender: WhatsappSender
    transport: OtpTransport = OtpTransport.WHATSAPP
    template_name: str = "agroguardian_otp_v1"
    code_ttl_seconds: int = 300
    max_attempts_per_code: int = 5
    rate_window_minutes: int = 30
    rate_max_in_window: int = 5




@dataclass(frozen=True, slots=True)
class SendOtpResult:
    """What the use case returns. Plain code is NOT included."""


    challenge_id: uuid.UUID
    expires_at: datetime
    masked_phone: str




# ---------------------------------------------------------------------------
# Use case
# ---------------------------------------------------------------------------




async def execute(*, phone: str, deps: SendOtpDeps) -> SendOtpResult:
    """Send an OTP to ``phone``. ``phone`` must be E.164."""
    now = datetime.now(UTC)


    farmer = await deps.farmer_repo.find_by_phone(phone)
    if farmer is None:
        raise UnknownPhoneError(phone)


    # Throttle 1: no concurrent active challenge.
    active = await deps.otp_repo.find_latest_active(phone)
    if active is not None and active.can_attempt(now):
        raise OtpThrottledError("active_challenge_exists")


    # Throttle 2: rate limit per phone per window.
    recent = await deps.otp_repo.recent_attempts_count(phone, deps.rate_window_minutes)
    if recent >= deps.rate_max_in_window:
        raise OtpThrottledError("rate_limited")


    # Generate + persist.
    code = generate_otp_code()
    salt = generate_refresh_secret(num_bytes=8)
    challenge = OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=farmer.tenant_id,
        phone=phone,
        code_hash=hash_otp_code(code, salt),
        transport=deps.transport,
        expires_at=otp_expires_at(now, deps.code_ttl_seconds),
        consumed_at=None,
        attempt_count=0,
        max_attempts=deps.max_attempts_per_code,
        created_at=now,
    )
    challenge_id = await deps.otp_repo.create(challenge)


    # Deliver. The log-only sender prints the code; the Meta adapter doesn't.
    result = await deps.sender.send_otp_template(
        phone=phone,
        code=code,
        template_name=deps.template_name,
    )
    if not result.accepted:
        raise WhatsappDeliveryError(result.error_code or "unknown")


    return SendOtpResult(
        challenge_id=challenge_id,
        expires_at=challenge.expires_at,
        masked_phone=mask_phone(phone),
    )




__all__ = [
    "OtpThrottledError",
    "SendOtpDeps",
    "SendOtpError",
    "SendOtpResult",
    "UnknownPhoneError",
    "WhatsappDeliveryError",
    "execute",
]
