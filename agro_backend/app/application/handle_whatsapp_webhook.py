"""Use case: process one inbound WhatsApp webhook payload.

Round 14 (PR B). Meta POSTs a nested envelope carrying two kinds of event:

* **messages** — a farmer replied. We resolve the sender to a known farmer (by
  phone) and record the message to ``wa_inbound_log``.
* **statuses** — a delivery receipt (sent / delivered / read / failed) for a
  message *we* sent. Parsed and returned to the caller for logging; a ``failed``
  receipt names the provider message id so ops can correlate it.

Parsing is pure (stdlib only); the orchestration talks to ports. The webhook
must always answer 200 quickly (Meta retries non-200), so callers treat any
per-item failure as swallowed — this use case never raises on bad shapes.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.wa_inbound_repo import WaInboundMessage, WaInboundRepo


@dataclass(frozen=True, slots=True)
class ParsedInbound:
    phone_e164: str
    wa_message_id: str | None
    body: str | None


@dataclass(frozen=True, slots=True)
class ParsedStatus:
    wa_message_id: str | None
    status: str
    recipient: str | None


@dataclass(frozen=True, slots=True)
class HandleWebhookDeps:
    farmer_repo: FarmerRepo
    wa_inbound_repo: WaInboundRepo


@dataclass(frozen=True, slots=True)
class HandleWebhookResult:
    recorded: int
    duplicates: int
    unknown_sender: int
    statuses: list[ParsedStatus]


def _normalise_phone(raw: str) -> str:
    """Meta sends the sender wa_id as digits (``919...``); we store E.164."""
    raw = raw.strip()
    return raw if raw.startswith("+") else f"+{raw}"


def _iter_values(payload: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for entry in payload.get("entry") or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes") or []:
            if isinstance(change, dict) and isinstance(change.get("value"), dict):
                values.append(change["value"])
    return values


def parse_inbound(payload: dict[str, Any]) -> list[ParsedInbound]:
    out: list[ParsedInbound] = []
    for value in _iter_values(payload):
        for msg in value.get("messages") or []:
            if not isinstance(msg, dict):
                continue
            sender = msg.get("from")
            if not sender:
                continue
            text = msg.get("text")
            body = text.get("body") if isinstance(text, dict) else None
            out.append(
                ParsedInbound(
                    phone_e164=_normalise_phone(str(sender)),
                    wa_message_id=(str(msg["id"]) if msg.get("id") else None),
                    body=body,
                )
            )
    return out


def parse_statuses(payload: dict[str, Any]) -> list[ParsedStatus]:
    out: list[ParsedStatus] = []
    for value in _iter_values(payload):
        for st in value.get("statuses") or []:
            if not isinstance(st, dict):
                continue
            out.append(
                ParsedStatus(
                    wa_message_id=(str(st["id"]) if st.get("id") else None),
                    status=str(st.get("status") or "unknown"),
                    recipient=(str(st["recipient_id"]) if st.get("recipient_id") else None),
                )
            )
    return out


async def execute(
    *, payload: dict[str, Any], deps: HandleWebhookDeps, now: datetime | None = None
) -> HandleWebhookResult:
    """Record inbound farmer messages; parse (don't persist) status receipts."""
    now = now or datetime.now(UTC)
    recorded = duplicates = unknown = 0

    for item in parse_inbound(payload):
        farmer = await deps.farmer_repo.find_by_phone(item.phone_e164)
        if farmer is None:
            # No tenant/farmer to attribute it to (wa_inbound_log.tenant_id is
            # NOT NULL). Count it; the pilot only cares about registered farmers.
            unknown += 1
            continue
        wrote = await deps.wa_inbound_repo.record(
            WaInboundMessage(
                tenant_id=farmer.tenant_id,
                farmer_id=farmer.farmer_id,
                phone_e164=item.phone_e164,
                wa_message_id=item.wa_message_id,
                body=item.body,
                received_at=now,
            )
        )
        if wrote:
            recorded += 1
        else:
            duplicates += 1

    return HandleWebhookResult(
        recorded=recorded,
        duplicates=duplicates,
        unknown_sender=unknown,
        statuses=parse_statuses(payload),
    )


__all__ = [
    "HandleWebhookDeps",
    "HandleWebhookResult",
    "ParsedInbound",
    "ParsedStatus",
    "execute",
    "parse_inbound",
    "parse_statuses",
]
