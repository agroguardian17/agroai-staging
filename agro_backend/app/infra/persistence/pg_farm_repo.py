"""Postgres adapter for :class:`~app.application.ports.farm_repo.FarmRepo`."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farm_repo import FarmLocation


class PgFarmRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def list_with_location(self) -> list[FarmLocation]:
        stmt = text("SELECT farm_id, tenant_id, gps_lat_center, gps_lng_center FROM farms")
        async with self._sm() as session:
            rows = (await session.execute(stmt)).all()
        out: list[FarmLocation] = []
        for row in rows:
            r: Any = row
            out.append(
                FarmLocation(
                    farm_id=r.farm_id,
                    tenant_id=r.tenant_id,
                    lat=float(r.gps_lat_center),
                    lng=float(r.gps_lng_center),
                )
            )
        return out


__all__ = ["PgFarmRepo"]
