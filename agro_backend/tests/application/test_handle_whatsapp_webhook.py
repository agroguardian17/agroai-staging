"""Tests for the Round 14 PR B webhook use case (handle_whatsapp_webhook)."""

from __future__ import annotations

import uuid
from typing import Any, cast

from app.application.handle_whatsapp_webhook import (
    HandleWebhookDeps,
    execute,
    parse_inbound,
    parse_statuses,
)
from app.application.ports.farmer_repo import FarmerIdentity
from app.application.ports.wa_inbound_repo import WaInboundMessage

TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")


def _payload_with_message(
    sender: str = "919999999999", msg_id: str = "wamid.IN1"
) -> dict[str, Any]:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "field": "messages",
                        "value": {
                            "messaging_product": "whatsapp",
                            "messages": [
                                {
                                    "from": sender,
                                    "id": msg_id,
                                    "timestamp": "1700000000",
                                    "type": "text",
                                    "text": {"body": "होय, पाणी दिले"},
                                }
                            ],
                        },
                    }
                ],
            }
        ],
    }


def _payload_with_status() -> dict[str, Any]:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "statuses": [
                                {
                                    "id": "wamid.OUT1",
                                    "status": "delivered",
                                    "recipient_id": "919999999999",
                                }
                            ]
                        }
                    }
                ]
            }
        ]
    }


class _FakeFarmerRepo:
    def __init__(self, known: bool) -> None:
        self._known = known

    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        if not self._known:
            return None
        return FarmerIdentity(
            farmer_id=FARMER,
            tenant_id=TENANT,
            phone=phone,
            full_name="Test",
            language_preference="mr",
            account_status="active",
        )

    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:  # unused
        return None


class _FakeInboundRepo:
    def __init__(self, *, duplicate: bool = False) -> None:
        self._duplicate = duplicate
        self.recorded: list[WaInboundMessage] = []

    async def record(self, message: WaInboundMessage) -> bool:
        self.recorded.append(message)
        return not self._duplicate


def _deps(farmer_repo: Any, inbound_repo: Any) -> HandleWebhookDeps:
    return HandleWebhookDeps(
        farmer_repo=cast(Any, farmer_repo), wa_inbound_repo=cast(Any, inbound_repo)
    )


# --- pure parsing -----------------------------------------------------------
def test_parse_inbound_normalises_phone_and_extracts_body() -> None:
    [item] = parse_inbound(_payload_with_message())
    assert item.phone_e164 == "+919999999999"  # digits → E.164
    assert item.wa_message_id == "wamid.IN1"
    assert item.body == "होय, पाणी दिले"


def test_parse_statuses_reads_receipts() -> None:
    [st] = parse_statuses(_payload_with_status())
    assert st.status == "delivered"
    assert st.wa_message_id == "wamid.OUT1"


def test_parse_handles_empty_and_malformed() -> None:
    assert parse_inbound({}) == []
    assert parse_statuses({"entry": [{"changes": [{}]}]}) == []


# --- orchestration ----------------------------------------------------------
async def test_known_farmer_message_is_recorded() -> None:
    inbound = _FakeInboundRepo()
    out = await execute(payload=_payload_with_message(), deps=_deps(_FakeFarmerRepo(True), inbound))
    assert out.recorded == 1
    assert out.unknown_sender == 0
    assert inbound.recorded[0].tenant_id == TENANT
    assert inbound.recorded[0].farmer_id == FARMER
    assert inbound.recorded[0].body == "होय, पाणी दिले"


async def test_unknown_sender_is_counted_not_recorded() -> None:
    inbound = _FakeInboundRepo()
    out = await execute(
        payload=_payload_with_message(), deps=_deps(_FakeFarmerRepo(False), inbound)
    )
    assert out.recorded == 0
    assert out.unknown_sender == 1
    assert inbound.recorded == []


async def test_duplicate_is_counted_separately() -> None:
    inbound = _FakeInboundRepo(duplicate=True)
    out = await execute(payload=_payload_with_message(), deps=_deps(_FakeFarmerRepo(True), inbound))
    assert out.recorded == 0
    assert out.duplicates == 1


async def test_statuses_are_returned_for_logging() -> None:
    out = await execute(
        payload=_payload_with_status(), deps=_deps(_FakeFarmerRepo(True), _FakeInboundRepo())
    )
    assert out.recorded == 0
    assert [s.status for s in out.statuses] == ["delivered"]
