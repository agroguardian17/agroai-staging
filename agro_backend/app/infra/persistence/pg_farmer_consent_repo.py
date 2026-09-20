"""Postgres adapter for the FarmerConsentRepo port."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farmer_consent_repo import FarmerConsentView

_COLS = (
    "farmer_id, consent_advisory, consent_research, consent_date, "
    "third_party_share_consent_given, data_retention_until, deletion_requested, "
    "cluster_anonymised, sat_attribution_shown, sat_public_display_context"
)


class PgFarmerConsentRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def for_farmer(self, farmer_id: uuid.UUID) -> FarmerConsentView | None:
        stmt = text(f"SELECT {_COLS} FROM farmer_consent WHERE farmer_id = :k")
        async with self._sm() as session:
            row = (await session.execute(stmt, {"k": farmer_id})).first()
        if row is None:
            return None
        r: Any = row
        return FarmerConsentView(
            farmer_id=r.farmer_id,
            consent_advisory=r.consent_advisory,
            consent_research=r.consent_research,
            consent_date=r.consent_date,
            third_party_share_consent_given=r.third_party_share_consent_given,
            data_retention_until=r.data_retention_until,
            deletion_requested=r.deletion_requested,
            cluster_anonymised=r.cluster_anonymised,
            sat_attribution_shown=r.sat_attribution_shown,
            sat_public_display_context=r.sat_public_display_context,
        )


__all__ = ["PgFarmerConsentRepo"]
