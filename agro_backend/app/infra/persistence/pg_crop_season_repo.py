"""Postgres adapter for :class:`~app.application.ports.crop_season_repo.CropSeasonRepo`."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.crop_season_repo import CropSeasonView

_SELECT_COLS = (
    "season_id, tenant_id, farm_id, plot_id, "
    "crop_name_english, crop_name_marathi, crop_category, crop_variety, "
    "sowing_date, expected_harvest_date, current_growth_stage, "
    "crop_age_days_today"
)


def _row_to_view(row: object) -> CropSeasonView:
    r: Any = row
    return CropSeasonView(
        season_id=r.season_id,
        tenant_id=r.tenant_id,
        farm_id=r.farm_id,
        plot_id=r.plot_id,
        crop_name_english=r.crop_name_english,
        crop_name_marathi=r.crop_name_marathi,
        crop_category=r.crop_category,
        crop_variety=r.crop_variety,
        sowing_date=r.sowing_date,
        expected_harvest_date=r.expected_harvest_date,
        current_growth_stage=r.current_growth_stage,
        crop_age_days_today=r.crop_age_days_today,
    )


class PgCropSeasonRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def find_active_for_plot(self, plot_id: str) -> CropSeasonView | None:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_seasons "
            "WHERE plot_id = :plot_id AND season_status = 'active' "
            "ORDER BY sowing_date DESC LIMIT 1"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id})
            row = res.first()
        return None if row is None else _row_to_view(row)

    async def list_active_by_crop(self, crop_name_english: str) -> list[CropSeasonView]:
        """All active seasons for a given crop, newest sowing_date first.

        Used by the daily ginger advisory job to iterate every ginger plot
        across every tenant in a single query.
        """
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_seasons "
            "WHERE crop_name_english = :crop AND season_status = 'active' "
            "ORDER BY sowing_date DESC"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"crop": crop_name_english})
            return [_row_to_view(r) for r in res.all()]


__all__ = ["PgCropSeasonRepo"]
