"""Postgres adapter for :class:`~app.application.ports.lab_soil_test_repo.LabSoilTestRepo`."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.lab_soil_test_repo import LabSoilTestView

_SELECT_COLS = (
    "lab_test_id, farm_id, sample_date, "
    "soil_oc_pct, soil_ec, soil_free_lime_pct, "
    "soil_zn_ppm, soil_fe_ppm, soil_ca_ppm, soil_mg_ppm, soil_s_ppm, "
    "sand_pct, silt_pct, clay_pct"
)


def _row_to_view(row: object) -> LabSoilTestView:
    r: Any = row
    return LabSoilTestView(
        lab_test_id=r.lab_test_id,
        farm_id=r.farm_id,
        sample_date=r.sample_date,
        soil_oc_pct=r.soil_oc_pct,
        soil_ec=r.soil_ec,
        soil_free_lime_pct=r.soil_free_lime_pct,
        soil_zn_ppm=r.soil_zn_ppm,
        soil_fe_ppm=r.soil_fe_ppm,
        soil_ca_ppm=r.soil_ca_ppm,
        soil_mg_ppm=r.soil_mg_ppm,
        soil_s_ppm=r.soil_s_ppm,
        sand_pct=r.sand_pct,
        silt_pct=r.silt_pct,
        clay_pct=r.clay_pct,
    )


class PgLabSoilTestRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def latest_for_farm(self, farm_id: uuid.UUID) -> LabSoilTestView | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM lab_soil_tests "
            "WHERE farm_id = :farm_id ORDER BY sample_date DESC LIMIT 1"
        )
        async with self._sm() as session:
            row = (await session.execute(stmt, {"farm_id": farm_id})).first()
        return None if row is None else _row_to_view(row)


__all__ = ["PgLabSoilTestRepo"]
