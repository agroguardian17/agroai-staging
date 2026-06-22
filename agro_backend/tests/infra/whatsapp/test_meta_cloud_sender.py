"""Tests for MetaCloudWhatsappSender. Uses respx to mock the Graph API."""


from __future__ import annotations


import httpx
import pytest
import respx


from app.infra.whatsapp.meta_cloud_sender import (
    MetaCloudSettings,
    MetaCloudWhatsappSender,
)


PHONE_ID = "1234567890"
URL = f"https://graph.facebook.com/v20.0/{PHONE_ID}/messages"




def _settings() -> MetaCloudSettings:
    return MetaCloudSettings(
        graph_version="v20.0",
        phone_number_id=PHONE_ID,
        access_token="test-token",
    )




@pytest.mark.asyncio
@respx.mock
async def test_sends_template_with_otp_payload() -> None:
    route = respx.post(URL).mock(
        return_value=httpx.Response(200, json={"messages": [{"id": "wamid.HBgM12345"}]})
    )
    async with httpx.AsyncClient() as client:
        sender = MetaCloudWhatsappSender(_settings(), client=client)
        out = await sender.send_otp_template(
            phone="+918123456789",
            code="123456",
            template_name="agroguardian_otp_v1",
        )
    assert route.called
    assert out.accepted is True
    assert out.provider_message_id == "wamid.HBgM12345"


    sent = route.calls.last.request
    body = sent.read().decode()
    # Code shows up in both body and button params.
    assert body.count('"123456"') >= 2
    assert "agroguardian_otp_v1" in body




@pytest.mark.asyncio
@respx.mock
async def test_rate_limit_failure_returns_meta_error_code() -> None:
    respx.post(URL).mock(
        return_value=httpx.Response(
            429,
            json={"error": {"code": 80008, "message": "Rate limit hit", "type": "OAuthException"}},
        )
    )
    async with httpx.AsyncClient() as client:
        sender = MetaCloudWhatsappSender(_settings(), client=client)
        out = await sender.send_otp_template(
            phone="+918123456789", code="123456", template_name="t"
        )
    assert out.accepted is False
    assert out.error_code == "meta_80008"




@pytest.mark.asyncio
@respx.mock
async def test_unrecognised_4xx_uses_http_status_as_error_code() -> None:
    respx.post(URL).mock(return_value=httpx.Response(400, text="bad request"))
    async with httpx.AsyncClient() as client:
        sender = MetaCloudWhatsappSender(_settings(), client=client)
        out = await sender.send_otp_template(
            phone="+918123456789", code="123456", template_name="t"
        )
    assert out.accepted is False
    assert out.error_code == "http_400"




@pytest.mark.asyncio
@respx.mock
async def test_network_error_returns_network_error_code() -> None:
    respx.post(URL).mock(side_effect=httpx.ConnectError("conn refused"))
    async with httpx.AsyncClient() as client:
        sender = MetaCloudWhatsappSender(_settings(), client=client)
        out = await sender.send_otp_template(
            phone="+918123456789", code="123456", template_name="t"
        )
    assert out.accepted is False
    assert out.error_code == "network_error"




@pytest.mark.asyncio
async def test_log_only_sender_always_accepts() -> None:
    from app.infra.whatsapp.log_only_sender import LogOnlyWhatsappSender


    out = await LogOnlyWhatsappSender().send_otp_template(
        phone="+918123456789", code="123456", template_name="t"
    )
    assert out.accepted is True
    assert out.provider_message_id is not None
    assert out.provider_message_id.startswith("log-")
