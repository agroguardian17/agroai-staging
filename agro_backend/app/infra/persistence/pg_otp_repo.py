"""Postgres adapter for :class:`~app.application.ports.otp_repo.OtpRepo`."""


from __future__ import annotations


import uuid


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


from app.domain.auth import OtpChallenge, OtpTransport


_SELECT_COLS = (
    "challenge_id, tenant_id, phone, code_hash, transport, "
    "expires_at, consumed_at, attempt_count, max_attempts, created_at"
)




def _row_to_challenge(row: object) -> OtpChallenge:
    return OtpChallenge(
        challenge_id=row.challenge_id,
        tenant_id=row.tenant_id,
        phone=row.phone,
        code_hash=row.code_hash,
        transport=OtpTransport(row.transport),
        expires_at=row.expires_at,
        consumed_at=row.consumed_at,
        attempt_count=row.attempt_count,
        max_attempts=row.max_attempts,
        created_at=row.created_at,
    )




class PgOtpRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    async def create(self, c: OtpChallenge) -> uuid.UUID:
        stmt = text(
            "INSERT INTO otp_challenges ("
            "  challenge_id, tenant_id, phone, code_hash, transport, "
            "  expires_at, attempt_count, max_attempts, created_at"
            ") VALUES ("
            "  :cid, :tenant, :phone, :code_hash, :transport, "
            "  :expires_at, :attempt_count, :max_attempts, :created_at"
            ") RETURNING challenge_id"
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt,
                {
                    "cid": c.challenge_id,
                    "tenant": c.tenant_id,
                    "phone": c.phone,
                    "code_hash": c.code_hash,
                    "transport": c.transport.value,
                    "expires_at": c.expires_at,
                    "attempt_count": c.attempt_count,
                    "max_attempts": c.max_attempts,
                    "created_at": c.created_at,
                },
            )
            row = res.first()
            await session.commit()
        if row is None:
            raise RuntimeError("otp_challenges INSERT did not RETURN a row")
        return row.challenge_id


    async def find_latest_active(self, phone: str) -> OtpChallenge | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM otp_challenges "
            "WHERE phone = :phone "
            "  AND consumed_at IS NULL "
            "  AND expires_at > NOW() "
            "ORDER BY expires_at DESC "
            "LIMIT 1"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"phone": phone})
            row = res.first()
        return None if row is None else _row_to_challenge(row)


    async def find_by_id(self, challenge_id: uuid.UUID) -> OtpChallenge | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM otp_challenges WHERE challenge_id = :cid LIMIT 1")
        async with self._sm() as session:
            res = await session.execute(stmt, {"cid": challenge_id})
            row = res.first()
        return None if row is None else _row_to_challenge(row)


    async def increment_attempt(self, challenge_id: uuid.UUID) -> int:
        # RETURNING the new value avoids a second SELECT.
        stmt = text(
            "UPDATE otp_challenges SET attempt_count = attempt_count + 1 "
            "WHERE challenge_id = :cid "
            "RETURNING attempt_count"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"cid": challenge_id})
            row = res.first()
            await session.commit()
        if row is None:
            return 0
        return int(row.attempt_count)


    async def mark_consumed(self, challenge_id: uuid.UUID) -> None:
        stmt = text(
            "UPDATE otp_challenges SET consumed_at = NOW() "
            "WHERE challenge_id = :cid AND consumed_at IS NULL"
        )
        async with self._sm() as session:
            await session.execute(stmt, {"cid": challenge_id})
            await session.commit()


    async def recent_attempts_count(self, phone: str, since_minutes: int) -> int:
        # Interval arithmetic (avoids the ``::cast`` form that breaks
        # SQLAlchemy text() under the asyncpg dialect).
        stmt = text(
            "SELECT COUNT(*) AS n FROM otp_challenges "
            "WHERE phone = :phone "
            "  AND created_at >= NOW() - :mins * interval '1 minute'"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"phone": phone, "mins": since_minutes})
            row = res.one()
        return int(row.n)




__all__ = ["PgOtpRepo"]
