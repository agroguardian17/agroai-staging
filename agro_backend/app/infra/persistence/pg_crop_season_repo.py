"""Postgres adapter for :class:`~app.application.ports.crop_season_repo.CropSeasonRepo`."""

from __future__ import annotations

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
    return CropSeasonView(
        season_id=row.season_id,
        tenant_id=row.tenant_id,
        farm_id=row.farm_id,
        plot_id=row.plot_id,
        crop_name_english=row.crop_name_english,
        crop_name_marathi=row.crop_name_marathi,
        crop_category=row.crop_category,
        crop_variety=row.crop_variety,
        sowing_date=row.sowing_date,
        expected_harvest_date=row.expected_harvest_date,
        current_growth_stage=row.current_growth_stage,
        crop_age_days_today=row.crop_age_days_today,
    )


class PgCropSeasonRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def find_active_for_plot(self, plot_id: str):
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM crop_seasons "
            "WHERE plot_id = :plot_id AND season_status = 'active' "
            "ORDER BY sowing_date DESC LIMIT 1"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id})
            row = res.first()
        return None if row is None else _row_to_view(row)

    async def list_active_by_crop(self, crop_name_english: str):
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
