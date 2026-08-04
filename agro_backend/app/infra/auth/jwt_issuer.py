"""HS256 JWT issuer / verifier.


Implements :class:`~app.application.ports.token_issuer.TokenIssuer`
using python-jose. The secret + algorithm + iss/aud come from the
Settings object so test code can pass a deterministic instance.


Why HS256 and not RS256: the pilot has a single backend process; we
don't need key separation between issuer and verifier. Phase 7 will
move to RS256 when we add a mobile-edge process that should verify
without holding the signing key.
"""


from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.application.ports.token_issuer import InvalidTokenError
from app.domain.auth import AccessClaims, AuthRole


@dataclass(frozen=True, slots=True)
class JwtSettings:
    """Subset of app Settings the JWT layer actually reads."""


    secret: str
    algorithm: str
    issuer: str
    audience: str
    access_ttl_seconds: int




class JwtIssuer:
    """Concrete :class:`TokenIssuer` over python-jose / HS256."""


    def __init__(self, settings: JwtSettings) -> None:
        self._s = settings


    # ------------------------------------------------------------------
    # Issue
    # ------------------------------------------------------------------
    def issue_access_token(
        self,
        *,
        subject: uuid.UUID,
        tenant_id: uuid.UUID,
        role: AuthRole,
        session_id: uuid.UUID,
    ) -> tuple[str, AccessClaims]:
        now = datetime.now(UTC).replace(microsecond=0)
        exp = now + timedelta(seconds=self._s.access_ttl_seconds)
        payload = {
            "iss": self._s.issuer,
            "aud": self._s.audience,
            "sub": str(subject),
            "tenant_id": str(tenant_id),
            "role": role.value,
            "session_id": str(session_id),
            "iat": int(now.timestamp()),
            "exp": int(exp.timestamp()),
        }
        token = jwt.encode(payload, self._s.secret, algorithm=self._s.algorithm)
        claims = AccessClaims(
            subject=subject,
            tenant_id=tenant_id,
            role=role,
            issued_at=now,
            expires_at=exp,
            session_id=session_id,
        )
        return token, claims


    # ------------------------------------------------------------------
    # Verify
    # ------------------------------------------------------------------
    def verify_access_token(self, token: str) -> AccessClaims:
        try:
            payload = jwt.decode(
                token,
                self._s.secret,
                algorithms=[self._s.algorithm],
                audience=self._s.audience,
                issuer=self._s.issuer,
            )
        except JWTError as exc:
            raise InvalidTokenError(str(exc)) from exc


        try:
            subject = uuid.UUID(payload["sub"])
            tenant_id = uuid.UUID(payload["tenant_id"])
            role = AuthRole(payload["role"])
            session_id_raw = payload.get("session_id")
            session_id = uuid.UUID(session_id_raw) if session_id_raw else None
            iat = datetime.fromtimestamp(int(payload["iat"]), tz=UTC)
            exp = datetime.fromtimestamp(int(payload["exp"]), tz=UTC)
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError(f"malformed claims: {exc}") from exc


        return AccessClaims(
            subject=subject,
            tenant_id=tenant_id,
            role=role,
            issued_at=iat,
            expires_at=exp,
            session_id=session_id,
        )




__all__ = ["JwtIssuer", "JwtSettings"]
