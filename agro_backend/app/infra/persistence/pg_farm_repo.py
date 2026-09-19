"""Postgres adapter for :class:`~app.application.ports.farm_repo.FarmRepo`."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farm_repo import FarmFacts, FarmLocation


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

    async def find_facts(self, farm_id: uuid.UUID) -> FarmFacts | None:
        stmt = text(
            "SELECT farm_id, soil_type, soil_depth_cm, water_source_primary, "
            "irrigation_type, drip_emitter_lph, previous_crops_json "
            "FROM farms WHERE farm_id = :farm_id"
        )
        async with self._sm() as session:
            row = (await session.execute(stmt, {"farm_id": farm_id})).first()
        if row is None:
            return None
        r: Any = row
        return FarmFacts(
            farm_id=r.farm_id,
            soil_type=r.soil_type,
            soil_depth_cm=r.soil_depth_cm,
            water_source_primary=r.water_source_primary,
            irrigation_type=r.irrigation_type,
            drip_emitter_lph=r.drip_emitter_lph,
            previous_crops_json=r.previous_crops_json,
        )


__all__ = ["PgFarmRepo"]
