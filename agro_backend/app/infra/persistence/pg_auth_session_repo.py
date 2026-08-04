"""Postgres adapter for :class:`~app.application.ports.auth_session_repo.AuthSessionRepo`."""


from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.auth import AuthSession

_SELECT_COLS = (
    "session_id, tenant_id, farmer_id, refresh_token_hash, "
    "expires_at, revoked_at, created_at, last_used_at"
)




def _row_to_session(row: object) -> AuthSession:
    return AuthSession(
        session_id=row.session_id,
        tenant_id=row.tenant_id,
        farmer_id=row.farmer_id,
        refresh_token_hash=row.refresh_token_hash,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
    )




class PgAuthSessionRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    async def create(self, s: AuthSession) -> uuid.UUID:
        stmt = text(
            "INSERT INTO auth_sessions ("
            "  session_id, tenant_id, farmer_id, refresh_token_hash, "
            "  expires_at, created_at, last_used_at"
            ") VALUES ("
            "  :sid, :tenant, :farmer, :token_hash, :expires_at, "
            "  :created_at, :last_used_at"
            ") RETURNING session_id"
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt,
                {
                    "sid": s.session_id,
                    "tenant": s.tenant_id,
                    "farmer": s.farmer_id,
                    "token_hash": s.refresh_token_hash,
                    "expires_at": s.expires_at,
                    "created_at": s.created_at,
                    "last_used_at": s.last_used_at,
                },
            )
            row = res.first()
            await session.commit()
        if row is None:
            raise RuntimeError("auth_sessions INSERT did not RETURN a row")
        return row.session_id


    async def find_by_token_hash(self, token_hash: str) -> AuthSession | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM auth_sessions WHERE refresh_token_hash = :h LIMIT 1"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"h": token_hash})
            row = res.first()
        return None if row is None else _row_to_session(row)


    async def revoke(self, session_id: uuid.UUID) -> None:
        stmt = text(
            "UPDATE auth_sessions SET revoked_at = NOW() "
            "WHERE session_id = :sid AND revoked_at IS NULL"
        )
        async with self._sm() as session:
            await session.execute(stmt, {"sid": session_id})
            await session.commit()


    async def revoke_all_for_farmer(self, farmer_id: uuid.UUID) -> int:
        stmt = text(
            "UPDATE auth_sessions SET revoked_at = NOW() "
            "WHERE farmer_id = :fid AND revoked_at IS NULL "
            "RETURNING session_id"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"fid": farmer_id})
            rows = res.all()
            await session.commit()
        return len(rows)


    async def touch(self, session_id: uuid.UUID) -> None:
        stmt = text("UPDATE auth_sessions SET last_used_at = NOW() WHERE session_id = :sid")
        async with self._sm() as session:
            await session.execute(stmt, {"sid": session_id})
            await session.commit()




__all__ = ["PgAuthSessionRepo"]
