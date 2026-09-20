"""Postgres adapter for the FarmerSchemesRepo port."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farmer_schemes_repo import FarmerSchemesView

_SELECT_COLS = "farmer_id, cgwb_block_category, cibrc_list_checked_date, data_review_due, drip_subsidy_pct_applicable, drought_prone_listed, farm_pond_planned, farmer_category, geo_tagging_done, kvk_contacted, pmfby_notified_for_ginger, pre_sanction_date, pre_sanction_received, priority_category, research_centre_contacted, scale_of_finance_per_acre, seed_supplier_identified, soil_lab_selected, subsidy_applied_date, subsidy_documents_ready, subsidy_lottery_result, subsidy_scheme_applied"


def _row_to_view(row: object) -> FarmerSchemesView:
    r: Any = row
    return FarmerSchemesView(
        farmer_id=r.farmer_id,
        cgwb_block_category=r.cgwb_block_category,
        cibrc_list_checked_date=r.cibrc_list_checked_date,
        data_review_due=r.data_review_due,
        drip_subsidy_pct_applicable=r.drip_subsidy_pct_applicable,
        drought_prone_listed=r.drought_prone_listed,
        farm_pond_planned=r.farm_pond_planned,
        farmer_category=r.farmer_category,
        geo_tagging_done=r.geo_tagging_done,
        kvk_contacted=r.kvk_contacted,
        pmfby_notified_for_ginger=r.pmfby_notified_for_ginger,
        pre_sanction_date=r.pre_sanction_date,
        pre_sanction_received=r.pre_sanction_received,
        priority_category=r.priority_category,
        research_centre_contacted=r.research_centre_contacted,
        scale_of_finance_per_acre=r.scale_of_finance_per_acre,
        seed_supplier_identified=r.seed_supplier_identified,
        soil_lab_selected=r.soil_lab_selected,
        subsidy_applied_date=r.subsidy_applied_date,
        subsidy_documents_ready=r.subsidy_documents_ready,
        subsidy_lottery_result=r.subsidy_lottery_result,
        subsidy_scheme_applied=r.subsidy_scheme_applied,
    )


class PgFarmerSchemesRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def for_farmer(self, farmer_id: uuid.UUID) -> FarmerSchemesView | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM farmer_schemes WHERE farmer_id = :k")
        async with self._sm() as session:
            row = (await session.execute(stmt, {"k": farmer_id})).first()
        return None if row is None else _row_to_view(row)


__all__ = ["PgFarmerSchemesRepo"]
