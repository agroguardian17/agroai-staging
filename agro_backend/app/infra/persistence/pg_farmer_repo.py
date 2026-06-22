"""Postgres adapter for :class:`~app.application.ports.farmer_repo.FarmerRepo`."""


from __future__ import annotations


import uuid


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


from app.application.ports.farmer_repo import FarmerIdentity


_SELECT_COLS = "farmer_id, tenant_id, phone_primary, full_name, language_preference, account_status"




def _row_to_identity(row: object) -> FarmerIdentity:
    return FarmerIdentity(
        farmer_id=row.farmer_id,
        tenant_id=row.tenant_id,
        phone=row.phone_primary,
        full_name=row.full_name,
        language_preference=row.language_preference,
        account_status=row.account_status,
    )




class PgFarmerRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    async def find_by_phone(self, phone: str) -> FarmerIdentity | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM farmers WHERE phone_primary = :phone LIMIT 1")
        async with self._sm() as session:
            res = await session.execute(stmt, {"phone": phone})
            row = res.first()
        return None if row is None else _row_to_identity(row)


    async def find_by_id(self, farmer_id: uuid.UUID) -> FarmerIdentity | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM farmers WHERE farmer_id = :fid LIMIT 1")
        async with self._sm() as session:
            res = await session.execute(stmt, {"fid": farmer_id})
            row = res.first()
        return None if row is None else _row_to_identity(row)




__all__ = ["PgFarmerRepo"]
