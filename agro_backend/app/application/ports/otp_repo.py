"""Port: OTP challenge persistence.


The verify_otp use case talks to this port exclusively; the Postgres
implementation lives in :mod:`app.infra.persistence.pg_otp_repo`.
"""


from __future__ import annotations


import uuid
from typing import Protocol, runtime_checkable


from app.domain.auth import OtpChallenge




@runtime_checkable
class OtpRepo(Protocol):
    """CRUD for ``otp_challenges`` rows."""


    async def create(self, challenge: OtpChallenge) -> uuid.UUID:
        """Insert a fresh challenge. Returns the (server-side) challenge_id."""
        ...


    async def find_latest_active(self, phone: str) -> OtpChallenge | None:
        """Return the most recent unconsumed, unexpired challenge for ``phone``.


        ``send_otp`` uses this to rate-limit (we refuse to issue a second
        challenge while one is still alive). ``verify_otp`` uses it to
        locate the challenge to compare against - we deliberately don't
        accept a challenge_id from the client; that would let an
        attacker who guessed a challenge_id race past the rate limit.
        """
        ...


    async def find_by_id(self, challenge_id: uuid.UUID) -> OtpChallenge | None: ...


    async def increment_attempt(self, challenge_id: uuid.UUID) -> int:
        """Bump ``attempt_count`` by 1 and return the new value."""
        ...


    async def mark_consumed(self, challenge_id: uuid.UUID) -> None:
        """Set ``consumed_at = now()``. Once consumed, this challenge is dead."""
        ...


    async def recent_attempts_count(self, phone: str, since_minutes: int) -> int:
        """Number of challenges created for ``phone`` in the last N minutes.


        send_otp uses this for per-phone throttling (the application
        layer policy is "no more than 5 challenges per 30 minutes").
        """
        ...




__all__ = ["OtpRepo"]
