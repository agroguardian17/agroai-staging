"""Unit tests for JwtIssuer. Pure: no DB, no HTTP."""


from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.application.ports.token_issuer import InvalidTokenError
from app.domain.auth import AuthRole
from app.infra.auth.jwt_issuer import JwtIssuer, JwtSettings


def _issuer(ttl: int = 900) -> JwtIssuer:
    return JwtIssuer(
        JwtSettings(
            secret="test-secret-do-not-use-in-prod",
            algorithm="HS256",
            issuer="agroguardian-test",
            audience="agroguardian-app",
            access_ttl_seconds=ttl,
        )
    )




def test_issue_and_verify_round_trip() -> None:
    iss = _issuer()
    sub = uuid.uuid4()
    tid = uuid.uuid4()
    sid = uuid.uuid4()
    token, claims = iss.issue_access_token(
        subject=sub, tenant_id=tid, role=AuthRole.FARMER, session_id=sid
    )
    assert isinstance(token, str)
    assert token.count(".") == 2  # JWT has three segments.


    decoded = iss.verify_access_token(token)
    assert decoded.subject == sub
    assert decoded.tenant_id == tid
    assert decoded.role is AuthRole.FARMER
    assert decoded.session_id == sid
    assert decoded.expires_at > claims.issued_at




def test_verify_rejects_garbage_token() -> None:
    iss = _issuer()
    with pytest.raises(InvalidTokenError):
        iss.verify_access_token("not.a.jwt")




def test_verify_rejects_wrong_audience() -> None:
    a = _issuer()
    b = JwtIssuer(
        JwtSettings(
            secret="test-secret-do-not-use-in-prod",
            algorithm="HS256",
            issuer="agroguardian-test",
            audience="OTHER-audience",
            access_ttl_seconds=900,
        )
    )
    token, _ = a.issue_access_token(
        subject=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=AuthRole.FARMER,
        session_id=uuid.uuid4(),
    )
    with pytest.raises(InvalidTokenError):
        b.verify_access_token(token)




def test_verify_rejects_wrong_signature() -> None:
    a = _issuer()
    b = JwtIssuer(
        JwtSettings(
            secret="DIFFERENT-secret",
            algorithm="HS256",
            issuer="agroguardian-test",
            audience="agroguardian-app",
            access_ttl_seconds=900,
        )
    )
    token, _ = a.issue_access_token(
        subject=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=AuthRole.FARMER,
        session_id=uuid.uuid4(),
    )
    with pytest.raises(InvalidTokenError):
        b.verify_access_token(token)




def test_expiry_is_set_to_ttl() -> None:
    iss = _issuer(ttl=60)
    _, claims = iss.issue_access_token(
        subject=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        role=AuthRole.FARMER,
        session_id=uuid.uuid4(),
    )
    delta = claims.expires_at - claims.issued_at
    assert delta == timedelta(seconds=60)
    # And the issued_at is recent (within 5s of now).
    assert abs((datetime.now(UTC) - claims.issued_at).total_seconds()) < 5
