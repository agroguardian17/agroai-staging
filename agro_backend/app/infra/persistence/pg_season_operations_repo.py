"""Postgres adapter for the SeasonOperationsRepo port."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.season_operations_repo import SeasonOperationsView

_SELECT_COLS = "season_id, basal_k_kg_per_acre, basal_p_kg_per_acre, castor_bait_prepared_date, castor_bait_units_per_acre, drip_runtime_min, ethephon_spray_count, fertigation_active, fertigation_last_ec_response, herbicide_post_emergent_date, herbicide_pre_emergent_date, irrigation_applied_litres_today, kulav_passes, last_fungicide_date, last_fungicide_group, last_insecticide_date, last_insecticide_group, metarhizium_kg_per_acre, naa_spray_count, weeding_count, labour_arranged_date"


def _row_to_view(row: object) -> SeasonOperationsView:
    r: Any = row
    return SeasonOperationsView(
        season_id=r.season_id,
        labour_arranged_date=r.labour_arranged_date,
        basal_k_kg_per_acre=r.basal_k_kg_per_acre,
        basal_p_kg_per_acre=r.basal_p_kg_per_acre,
        castor_bait_prepared_date=r.castor_bait_prepared_date,
        castor_bait_units_per_acre=r.castor_bait_units_per_acre,
        drip_runtime_min=r.drip_runtime_min,
        ethephon_spray_count=r.ethephon_spray_count,
        fertigation_active=r.fertigation_active,
        fertigation_last_ec_response=r.fertigation_last_ec_response,
        herbicide_post_emergent_date=r.herbicide_post_emergent_date,
        herbicide_pre_emergent_date=r.herbicide_pre_emergent_date,
        irrigation_applied_litres_today=r.irrigation_applied_litres_today,
        kulav_passes=r.kulav_passes,
        last_fungicide_date=r.last_fungicide_date,
        last_fungicide_group=r.last_fungicide_group,
        last_insecticide_date=r.last_insecticide_date,
        last_insecticide_group=r.last_insecticide_group,
        metarhizium_kg_per_acre=r.metarhizium_kg_per_acre,
        naa_spray_count=r.naa_spray_count,
        weeding_count=r.weeding_count,
    )


class PgSeasonOperationsRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def for_season(self, season_id: uuid.UUID) -> SeasonOperationsView | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM season_operations WHERE season_id = :k")
        async with self._sm() as session:
            row = (await session.execute(stmt, {"k": season_id})).first()
        return None if row is None else _row_to_view(row)


__all__ = ["PgSeasonOperationsRepo"]
