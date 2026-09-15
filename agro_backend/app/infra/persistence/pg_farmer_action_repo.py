"""Postgres adapter for
:class:`~app.application.ports.farmer_action_repo.FarmerActionRepo`.
"""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farmer_action_repo import AdvisoryContext, FarmerActionInput


class PgFarmerActionRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def latest_advisory_for_farmer(
        self, farmer_id: uuid.UUID, *, within_days: int
    ) -> AdvisoryContext | None:
        stmt = text(
            """
            SELECT suggestion_id, tenant_id, farmer_id, farm_id, season_id, plot_id,
                   (water_liters_suggested IS NOT NULL OR water_action IS NOT NULL)
                       AS is_watering
            FROM ai_suggestions
            WHERE farmer_id = :fid
              AND delivery_status = 'sent'
              AND generated_at >= now() - CAST(:days AS int) * interval '1 day'
            ORDER BY generated_at DESC
            LIMIT 1
            """
        )
        async with self._sm() as session:
            row = (await session.execute(stmt, {"fid": farmer_id, "days": within_days})).first()
        if row is None:
            return None
        r: Any = row
        return AdvisoryContext(
            suggestion_id=r.suggestion_id,
            tenant_id=r.tenant_id,
            farmer_id=r.farmer_id,
            farm_id=r.farm_id,
            season_id=r.season_id,
            plot_id=r.plot_id,
            is_watering=bool(r.is_watering),
        )

    async def record(self, action: FarmerActionInput) -> int:
        stmt = text(
            """
            INSERT INTO farmer_actions (
                tenant_id, farmer_id, farm_id, season_id, plot_id,
                ai_suggestion_id, action_date, action_type,
                ai_suggested, farmer_followed_ai, water_liters, farmer_note, source
            ) VALUES (
                :tenant_id, :farmer_id, :farm_id, :season_id, :plot_id,
                :ai_suggestion_id, :action_date, :action_type,
                :ai_suggested, :farmer_followed_ai, :water_liters, :farmer_note, :source
            )
            RETURNING action_id
            """
        )
        params: dict[str, Any] = {
            "tenant_id": action.tenant_id,
            "farmer_id": action.farmer_id,
            "farm_id": action.farm_id,
            "season_id": action.season_id,
            "plot_id": action.plot_id,
            "ai_suggestion_id": action.ai_suggestion_id,
            "action_date": action.action_date,
            "action_type": action.action_type,
            "ai_suggested": action.ai_suggested,
            "farmer_followed_ai": action.farmer_followed_ai,
            "water_liters": action.water_liters,
            "farmer_note": action.farmer_note,
            "source": action.source,
        }
        async with self._sm() as session:
            rid = (await session.execute(stmt, params)).scalar()
            await session.commit()
        return int(cast(Any, rid))


__all__ = ["PgFarmerActionRepo"]
