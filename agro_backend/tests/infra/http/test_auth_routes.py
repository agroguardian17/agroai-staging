"""HTTP-layer tests for /api/v1/auth/*.


Uses FastAPI TestClient + ``app.dependency_overrides`` to inject stub
repos/senders so no real DB or WhatsApp call happens.
"""


from __future__ import annotations


import uuid
from datetime import UTC, datetime, timedelta


import pytest
from fastapi.testclient import TestClient


from app.application.ports.farmer_repo import FarmerIdentity
from app.application.ports.whatsapp_sender import WhatsappSendResult
from app.domain.auth import (
    AccessClaims,
    AuthRole,
    AuthSession,
    OtpChallenge,
    OtpTransport,
    hash_otp_code,
    hash_refresh_token,
)
from app.infra.http.deps import (
    get_auth_session_repo,
    get_farmer_repo,
    get_otp_repo,
    get_token_issuer,
    get_whatsapp_sender,
)
from app.main import create_app


PHONE = "+918123456789"
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
NOW = datetime.now(UTC).replace(microsecond=0)




# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
def _farmer(status: str = "active") -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=FARMER,
        tenant_id=TENANT,
        phone=PHONE,
        full_name="Test",
        language_preference="marathi",
        account_status=status,
    )




class StubFarmerRepo:
    def __init__(self, farmer: FarmerIdentity | None) -> None:
        self.farmer = farmer


    async def find_by_phone(self, phone):
        return self.farmer


    async def find_by_id(self, farmer_id):
        return self.farmer




class StubOtpRepo:
    def __init__(self, latest: OtpChallenge | None = None) -> None:
        self.latest = latest
        self.created: list[OtpChallenge] = []
        self.consumed: list[uuid.UUID] = []


    async def create(self, c):
        self.created.append(c)
        return c.challenge_id


    async def find_latest_active(self, phone):
        return self.latest


    async def find_by_id(self, cid):
        return None


    async def increment_attempt(self, cid):
        return 1


    async def mark_consumed(self, cid):
        self.consumed.append(cid)


    async def recent_attempts_count(self, phone, since_minutes):
        return 0




class StubSessionRepo:
    def __init__(self, existing: AuthSession | None = None) -> None:
        self.existing = existing
        self.created: list[AuthSession] = []
        self.revoked: list[uuid.UUID] = []


    async def create(self, s):
        self.created.append(s)
        return s.session_id


    async def find_by_token_hash(self, h):
        if self.existing is None:
            return None
        return self.existing if self.existing.refresh_token_hash == h else None


    async def revoke(self, sid):
        self.revoked.append(sid)


    async def revoke_all_for_farmer(self, fid):
        return 2


    async def touch(self, sid):
        pass




class StubSender:
    def __init__(self, ok: bool = True) -> None:
        self.ok = ok
        self.sent: list[tuple[str, str]] = []


    async def send_otp_template(self, *, phone, code, template_name, language_code="en"):
        self.sent.append((phone, code))
        return WhatsappSendResult(
            accepted=self.ok,
            provider_message_id="m-1" if self.ok else None,
            error_code=None if self.ok else "rate_limited",
        )




class StubTokenIssuer:
    def issue_access_token(self, *, subject, tenant_id, role, session_id):
        return "FAKE.JWT", AccessClaims(
            subject=subject,
            tenant_id=tenant_id,
            role=role,
            issued_at=NOW,
            expires_at=NOW + timedelta(minutes=15),
            session_id=session_id,
        )


    def verify_access_token(self, token):
        # The /me + /logout tests pass a token we recognise:
        if token == "FAKE.JWT":
            return AccessClaims(
                subject=FARMER,
                tenant_id=TENANT,
                role=AuthRole.FARMER,
                issued_at=NOW,
                expires_at=NOW + timedelta(minutes=15),
                session_id=uuid.uuid4(),
            )
        from app.application.ports.token_issuer import InvalidTokenError


        raise InvalidTokenError("not the fake token")




# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------
@pytest.fixture
def app_with_stubs() -> tuple[TestClient, dict]:
    app = create_app()
    stubs: dict = {
        "farmer_repo": StubFarmerRepo(_farmer()),
        "otp_repo": StubOtpRepo(),
        "session_repo": StubSessionRepo(),
        "sender": StubSender(),
        "token_issuer": StubTokenIssuer(),
    }
    app.dependency_overrides[get_farmer_repo] = lambda: stubs["farmer_repo"]
    app.dependency_overrides[get_otp_repo] = lambda: stubs["otp_repo"]
    app.dependency_overrides[get_auth_session_repo] = lambda: stubs["session_repo"]
    app.dependency_overrides[get_whatsapp_sender] = lambda: stubs["sender"]
    app.dependency_overrides[get_token_issuer] = lambda: stubs["token_issuer"]


    client = TestClient(app)
    yield client, stubs
    app.dependency_overrides.clear()




# ===========================================================================
# /auth/send_otp
# ===========================================================================
def test_send_otp_returns_202_with_challenge_id(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    resp = client.post("/api/v1/auth/send_otp", json={"phone": PHONE})
    assert resp.status_code == 202
    body = resp.json()
    assert "challenge_id" in body
    assert "masked_phone" in body
    assert len(stubs["sender"].sent) == 1




def test_send_otp_unknown_phone_returns_202_without_send(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    stubs["farmer_repo"].farmer = None  # unknown phone
    resp = client.post("/api/v1/auth/send_otp", json={"phone": "+919999999999"})
    # 202 either way to avoid enumeration; nothing was actually sent.
    assert resp.status_code == 202
    assert len(stubs["sender"].sent) == 0




def test_send_otp_rate_limited_returns_429(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    # Pre-fill the OTP repo with an active challenge.
    stubs["otp_repo"].latest = OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        code_hash=hash_otp_code("123456", "s"),
        transport=OtpTransport.LOG_ONLY,
        expires_at=NOW + timedelta(minutes=4),
        consumed_at=None,
        attempt_count=0,
        max_attempts=5,
        created_at=NOW,
    )
    resp = client.post("/api/v1/auth/send_otp", json={"phone": PHONE})
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"] == "rate_limited"




# ===========================================================================
# /auth/verify_otp
# ===========================================================================
def test_verify_otp_correct_code_returns_token_pair(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    # Plant an active challenge for "123456".
    stubs["otp_repo"].latest = OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        code_hash=hash_otp_code("123456", "saltX"),
        transport=OtpTransport.LOG_ONLY,
        expires_at=NOW + timedelta(minutes=5),
        consumed_at=None,
        attempt_count=0,
        max_attempts=5,
        created_at=NOW,
    )
    resp = client.post("/api/v1/auth/verify_otp", json={"phone": PHONE, "code": "123456"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "FAKE.JWT"
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"




def test_verify_otp_no_challenge_returns_400(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.post("/api/v1/auth/verify_otp", json={"phone": PHONE, "code": "123456"})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error"] == "no_active_challenge"




def test_verify_otp_wrong_code_returns_401_with_attempts_remaining(
    app_with_stubs,
) -> None:
    client, stubs = app_with_stubs
    stubs["otp_repo"].latest = OtpChallenge(
        challenge_id=uuid.uuid4(),
        tenant_id=TENANT,
        phone=PHONE,
        code_hash=hash_otp_code("123456", "saltY"),
        transport=OtpTransport.LOG_ONLY,
        expires_at=NOW + timedelta(minutes=5),
        consumed_at=None,
        attempt_count=0,
        max_attempts=5,
        created_at=NOW,
    )
    resp = client.post("/api/v1/auth/verify_otp", json={"phone": PHONE, "code": "000000"})
    assert resp.status_code == 401
    assert resp.json()["detail"]["error"] == "invalid_otp"
    assert "attempts_remaining" in resp.json()["detail"]




# ===========================================================================
# /auth/refresh
# ===========================================================================
def test_refresh_rotates_token(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    secret = "good-refresh-secret"
    stubs["session_repo"].existing = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=TENANT,
        farmer_id=FARMER,
        refresh_token_hash=hash_refresh_token(secret),
        expires_at=NOW + timedelta(days=30),
        revoked_at=None,
        created_at=NOW,
        last_used_at=NOW,
    )
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": secret})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"] == "FAKE.JWT"
    assert body["refresh_token"] != secret  # rotated
    assert len(stubs["session_repo"].revoked) == 1




def test_refresh_rejects_unknown_token(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": "bogus"})
    assert resp.status_code == 401




# ===========================================================================
# /me
# ===========================================================================
def test_me_without_token_returns_401(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/me")
    assert resp.status_code == 401




def test_me_with_valid_token_returns_claims(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/me", headers={"Authorization": "Bearer FAKE.JWT"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["farmer_id"] == str(FARMER)
    assert body["tenant_id"] == str(TENANT)
    assert body["role"] == "farmer"




def test_me_with_invalid_token_returns_401(app_with_stubs) -> None:
    client, _ = app_with_stubs
    resp = client.get("/api/v1/me", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401




# ===========================================================================
# /auth/logout
# ===========================================================================
def test_logout_one_device(app_with_stubs) -> None:
    client, stubs = app_with_stubs
    secret = "device-secret"
    stubs["session_repo"].existing = AuthSession(
        session_id=uuid.uuid4(),
        tenant_id=TENANT,
        farmer_id=FARMER,
        refresh_token_hash=hash_refresh_token(secret),
        expires_at=NOW + timedelta(days=30),
        revoked_at=None,
        created_at=NOW,
        last_used_at=NOW,
    )
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer FAKE.JWT"},
        json={"refresh_token": secret},
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] == 1




def test_logout_everywhere(app_with_stubs) -> None:
    client, _stubs = app_with_stubs
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": "Bearer FAKE.JWT"},
        json={"everywhere": True},
    )
    assert resp.status_code == 200
    assert resp.json()["revoked"] == 2  # StubSessionRepo returns 2.
