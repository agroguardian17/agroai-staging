"""Meta Cloud API WhatsApp sender.


Posts to ``POST /{graph_version}/{phone_number_id}/messages`` with an
OTP-template payload. Returns the provider message id on success;
maps known error shapes to the WhatsappSendResult error_code so
metrics + structlog don't see a raw provider stack.


We keep the surface small: only ``send_otp_template`` is needed for
Round 8. Advisory messages and webhook receipt handling land in
Round 12.


The Meta error envelope looks like::


    {
      "error": {
        "message": "Rate limit hit",
        "type": "OAuthException",
        "code": 80008,
        "fbtrace_id": "..."
      }
    }


We don't try to enumerate every code; ``error_code`` is set to the
HTTP status (4xx vs 5xx) plus the provider's ``code`` if present.
"""


from __future__ import annotations


from dataclasses import dataclass


import httpx
import structlog


from app.application.ports.whatsapp_sender import WhatsappSendResult
from app.domain.auth import mask_phone


log = structlog.get_logger(__name__)




@dataclass(frozen=True, slots=True)
class MetaCloudSettings:
    graph_version: str  # e.g. "v20.0"
    phone_number_id: str
    access_token: str
    base_url: str = "https://graph.facebook.com"
    timeout_seconds: float = 10.0




class MetaCloudWhatsappSender:
    def __init__(
        self,
        settings: MetaCloudSettings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._s = settings
        # Caller can inject a shared client (recommended in production
        # so connection pools are warm). Tests pass an httpx.AsyncClient
        # wired through respx so no real network is touched.
        self._client = client


    def _url(self) -> str:
        return (
            f"{self._s.base_url.rstrip('/')}/"
            f"{self._s.graph_version}/{self._s.phone_number_id}/messages"
        )


    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._s.access_token}",
            "Content-Type": "application/json",
        }


    def _payload(self, *, phone: str, code: str, template_name: str, language_code: str) -> dict:
        # Meta's OTP-button template requires the code in BOTH the body
        # placeholder and in a button "copy_code" parameter.
        return {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language_code},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": code}],
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": code}],
                    },
                ],
            },
        }


    async def send_otp_template(
        self, *, phone: str, code: str, template_name: str, language_code: str = "en"
    ) -> WhatsappSendResult:
        payload = self._payload(
            phone=phone, code=code, template_name=template_name, language_code=language_code
        )
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self._s.timeout_seconds)
        try:
            resp = await client.post(self._url(), headers=self._headers(), json=payload)
        except httpx.HTTPError as exc:
            log.error("whatsapp.meta.network_error", phone=mask_phone(phone), error=str(exc))
            return WhatsappSendResult(
                accepted=False,
                provider_message_id=None,
                error_code="network_error",
                error_detail=str(exc),
            )
        finally:
            if owns_client:
                await client.aclose()


        if resp.status_code >= 400:
            return self._failure_from(resp, phone)
        return self._success_from(resp, phone)


    def _success_from(self, resp: httpx.Response, phone: str) -> WhatsappSendResult:
        try:
            body = resp.json()
            messages = body.get("messages") or []
            msg_id = messages[0].get("id") if messages else None
        except Exception:
            msg_id = None
        log.info("whatsapp.meta.sent", phone=mask_phone(phone), provider_message_id=msg_id)
        return WhatsappSendResult(accepted=True, provider_message_id=msg_id)


    def _failure_from(self, resp: httpx.Response, phone: str) -> WhatsappSendResult:
        try:
            err = resp.json().get("error") or {}
            code = err.get("code")
            message = err.get("message")
        except Exception:
            code = None
            message = resp.text[:200]
        error_code = f"http_{resp.status_code}" if code is None else f"meta_{code}"
        log.warning(
            "whatsapp.meta.rejected",
            phone=mask_phone(phone),
            status=resp.status_code,
            error_code=error_code,
            detail=message,
        )
        return WhatsappSendResult(
            accepted=False,
            provider_message_id=None,
            error_code=error_code,
            error_detail=message,
        )




__all__ = ["MetaCloudSettings", "MetaCloudWhatsappSender"]
