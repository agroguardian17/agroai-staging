"""Port: read-side farmer_schemes lookup for the ginger farm-brain."""

from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable  # noqa: F401


@dataclass(frozen=True, slots=True)
class FarmerSchemesView:
    """Read-side projection of the farmer_schemes row (KB-consumed columns)."""

    farmer_id: uuid.UUID
    cgwb_block_category: str | None = None
    cibrc_list_checked_date: datetime.date | None = None
    data_review_due: datetime.date | None = None
    drip_subsidy_pct_applicable: Decimal | None = None
    drought_prone_listed: str | None = None
    farm_pond_planned: bool | None = None
    farmer_category: str | None = None
    geo_tagging_done: bool | None = None
    kvk_contacted: bool | None = None
    pmfby_notified_for_ginger: str | None = None
    pre_sanction_date: datetime.date | None = None
    pre_sanction_received: bool | None = None
    priority_category: str | None = None
    research_centre_contacted: bool | None = None
    scale_of_finance_per_acre: Decimal | None = None
    seed_supplier_identified: bool | None = None
    soil_lab_selected: str | None = None
    subsidy_applied_date: datetime.date | None = None
    subsidy_documents_ready: bool | None = None
    subsidy_lottery_result: str | None = None
    subsidy_scheme_applied: str | None = None


@runtime_checkable
class FarmerSchemesRepo(Protocol):
    async def for_farmer(self, farmer_id: uuid.UUID) -> FarmerSchemesView | None:
        """The farmer_schemes row for this farmer, or None."""
        ...


__all__ = ["FarmerSchemesRepo", "FarmerSchemesView"]
