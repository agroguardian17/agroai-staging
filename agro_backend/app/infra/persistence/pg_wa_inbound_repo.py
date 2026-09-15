"""Postgres adapter for :class:`~app.application.ports.wa_inbound_repo.WaInboundRepo`."""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.wa_inbound_repo import WaInboundMessage


class PgWaInboundRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def record(self, message: WaInboundMessage) -> bool:
        # ON CONFLICT on the unique wa_message_id makes redelivery idempotent.
        # When wa_message_id is NULL (should be rare) the conflict clause never
        # fires, so every such row inserts — acceptable for an audit log.
        stmt = text(
            """
            INSERT INTO wa_inbound_log (
                tenant_id, farmer_id, wa_message_id, phone_e164, body, received_at
            ) VALUES (
                :tenant_id, :farmer_id, :wa_message_id, :phone, :body, :received_at
            )
            ON CONFLICT (wa_message_id) DO NOTHING
            RETURNING id
            """
        )
        params: dict[str, Any] = {
            "tenant_id": message.tenant_id,
            "farmer_id": message.farmer_id,
            "wa_message_id": message.wa_message_id,
            "phone": message.phone_e164,
            "body": message.body,
            "received_at": message.received_at,
        }
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            row = res.first()
            await session.commit()
        return cast(Any, row) is not None


__all__ = ["PgWaInboundRepo"]
