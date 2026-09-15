"""Route tests for the WhatsApp webhook (verify handshake + signature)."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.application.ports.farmer_repo import FarmerIdentity
from app.application.ports.wa_inbound_repo import WaInboundMessage
from app.config import get_settings
from app.infra.http.deps import get_farmer_repo
from app.infra.http.webhooks import get_wa_inbound_repo
from app.main import create_app

VERIFY_TOKEN = "verify-me-123"


class _FakeFarmerRepo:
    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        return FarmerIdentity(
            farmer_id=uuid.UUID("22222222-2222-2222-2222-222222222222"),
            tenant_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            phone=phone,
            full_name="Test",
            language_preference="mr",
            account_status="active",
        )

    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        return None


class _FakeInboundRepo:
    def __init__(self) -> None:
        self.recorded: list[WaInboundMessage] = []

    async def record(self, message: WaInboundMessage) -> bool:
        self.recorded.append(message)
        return True


def _app(*, app_secret: str = ""):
    app = create_app()
    base = get_settings()
    test_settings = base.model_copy(
        update={
            "META_WHATSAPP_VERIFY_TOKEN": SecretStr(VERIFY_TOKEN),
            "META_WHATSAPP_APP_SECRET": SecretStr(app_secret),
        }
    )
    inbound = _FakeInboundRepo()
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_farmer_repo] = lambda: _FakeFarmerRepo()
    app.dependency_overrides[get_wa_inbound_repo] = lambda: inbound
    return app, inbound


_MSG: dict[str, Any] = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "919999999999",
                                "id": "wamid.X",
                                "type": "text",
                                "text": {"body": "hello"},
                            }
                        ]
                    }
                }
            ]
        }
    ]
}


# --- GET verify handshake ---------------------------------------------------
def test_verify_echoes_challenge_on_match() -> None:
    app, _ = _app()
    with TestClient(app) as client:
        resp = client.get(
            "/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": VERIFY_TOKEN,
                "hub.challenge": "42",
            },
        )
    assert resp.status_code == 200
    assert resp.text == "42"
    app.dependency_overrides.clear()


def test_verify_rejects_wrong_token() -> None:
    app, _ = _app()
    with TestClient(app) as client:
        resp = client.get(
            "/webhooks/whatsapp",
            params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "42"},
        )
    assert resp.status_code == 403
    app.dependency_overrides.clear()


# --- POST signature ---------------------------------------------------------
def test_post_without_secret_records_inbound() -> None:
    app, inbound = _app(app_secret="")  # dev/staging: signature skipped
    body = json.dumps(_MSG).encode()
    with TestClient(app) as client:
        resp = client.post(
            "/webhooks/whatsapp", content=body, headers={"Content-Type": "application/json"}
        )
    assert resp.status_code == 200
    assert len(inbound.recorded) == 1
    assert inbound.recorded[0].body == "hello"
    app.dependency_overrides.clear()


def test_post_rejects_bad_signature_when_secret_set() -> None:
    app, inbound = _app(app_secret="s3cr3t")
    body = json.dumps(_MSG).encode()
    with TestClient(app) as client:
        resp = client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": "sha256=deadbeef"},
        )
    assert resp.status_code == 403
    assert inbound.recorded == []
    app.dependency_overrides.clear()


def test_post_accepts_valid_signature() -> None:
    secret = "s3cr3t"
    app, inbound = _app(app_secret=secret)
    body = json.dumps(_MSG).encode()
    sig = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    with TestClient(app) as client:
        resp = client.post(
            "/webhooks/whatsapp",
            content=body,
            headers={"Content-Type": "application/json", "X-Hub-Signature-256": sig},
        )
    assert resp.status_code == 200
    assert len(inbound.recorded) == 1
    app.dependency_overrides.clear()


@pytest.mark.parametrize("bad", [b"not json", b"", b"{"])
def test_post_bad_json_still_acks(bad: bytes) -> None:
    app, _ = _app()
    with TestClient(app) as client:
        resp = client.post(
            "/webhooks/whatsapp", content=bad, headers={"Content-Type": "application/json"}
        )
    assert resp.status_code == 200
    app.dependency_overrides.clear()
