"""Port: inbound WhatsApp message log.

Round 14 (PR B). The webhook records every inbound farmer message to
``wa_inbound_log`` — the raw feed that later powers two-way chat and the
learning loop's "did the farmer act?" signal.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class WaInboundMessage:
    """One inbound WhatsApp message from a known farmer."""

    tenant_id: uuid.UUID
    farmer_id: uuid.UUID
    phone_e164: str
    wa_message_id: str | None
    body: str | None
    received_at: datetime


@runtime_checkable
class WaInboundRepo(Protocol):
    async def record(self, message: WaInboundMessage) -> bool:
        """Persist one inbound message. Idempotent on ``wa_message_id``.

        Returns True if a new row was written, False if it was a duplicate
        (Meta re-delivers webhooks, so the same message can arrive twice).
        """
        ...


__all__ = ["WaInboundMessage", "WaInboundRepo"]
