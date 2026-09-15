"""WhatsApp inbound webhook (Round 14 PR B).

Two endpoints under ``/webhooks/whatsapp``:

* ``GET``  — Meta's one-time verification handshake. Echoes ``hub.challenge``
  iff ``hub.verify_token`` matches ``META_WHATSAPP_VERIFY_TOKEN``.
* ``POST`` — inbound events (farmer messages + delivery receipts). The raw body
  is HMAC-verified against ``X-Hub-Signature-256`` using
  ``META_WHATSAPP_APP_SECRET`` (skipped when that secret is unset, i.e. dev /
  staging without a WABA). Always answers 200 quickly so Meta does not retry;
  per-message work is best-effort.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Request, Response, status

from app.application import handle_whatsapp_webhook
from app.application.handle_whatsapp_webhook import HandleWebhookDeps
from app.application.ports.wa_inbound_repo import WaInboundRepo
from app.infra.http.deps import SessionmakerDep, SettingsDep, get_farmer_repo
from app.infra.persistence.pg_wa_inbound_repo import PgWaInboundRepo

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks/whatsapp", tags=["webhooks"])


def get_wa_inbound_repo(sm: SessionmakerDep) -> WaInboundRepo:
    return PgWaInboundRepo(sm)


@router.get("", include_in_schema=False)
async def verify(request: Request, settings: SettingsDep) -> Response:
    """Meta verification handshake."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    expected = settings.META_WHATSAPP_VERIFY_TOKEN.get_secret_value()
    if mode == "subscribe" and expected and token == expected and challenge is not None:
        return Response(content=challenge, media_type="text/plain")
    log.warning("whatsapp.webhook.verify_rejected", mode=mode)
    return Response(status_code=status.HTTP_403_FORBIDDEN)


def _signature_ok(app_secret: str, raw_body: bytes, header: str | None) -> bool:
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


@router.post("")
async def receive(
    request: Request,
    settings: SettingsDep,
    farmer_repo: Annotated[Any, Depends(get_farmer_repo)],
    wa_inbound_repo: Annotated[Any, Depends(get_wa_inbound_repo)],
) -> Response:
    raw = await request.body()
    app_secret = settings.META_WHATSAPP_APP_SECRET.get_secret_value()
    if app_secret and not _signature_ok(
        app_secret, raw, request.headers.get("X-Hub-Signature-256")
    ):
        log.warning("whatsapp.webhook.bad_signature")
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    try:
        payload = json.loads(raw or b"{}")
    except json.JSONDecodeError:
        # Ack anyway so Meta stops retrying a body we will never parse.
        log.warning("whatsapp.webhook.bad_json")
        return Response(status_code=status.HTTP_200_OK)

    try:
        result = await handle_whatsapp_webhook.execute(
            payload=payload,
            deps=HandleWebhookDeps(farmer_repo=farmer_repo, wa_inbound_repo=wa_inbound_repo),
        )
    except Exception:
        # Never fail the webhook — Meta would retry indefinitely.
        log.exception("whatsapp.webhook.handler_error")
        return Response(status_code=status.HTTP_200_OK)

    if result.recorded or result.duplicates or result.unknown_sender:
        log.info(
            "whatsapp.webhook.inbound",
            recorded=result.recorded,
            duplicates=result.duplicates,
            unknown_sender=result.unknown_sender,
        )
    for st in result.statuses:
        level = log.warning if st.status == "failed" else log.info
        level("whatsapp.webhook.status", status=st.status, wa_message_id=st.wa_message_id)
    return Response(status_code=status.HTTP_200_OK)


__all__ = ["get_wa_inbound_repo", "router"]
