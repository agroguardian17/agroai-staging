"""Postgres adapter for
:class:`~app.application.ports.learning_repo.LearningRepo`.
"""

from __future__ import annotations

from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.learning_repo import ActionOutcome, LearningRow


def _row_to_outcome(row: object) -> ActionOutcome:
    r: Any = row
    return ActionOutcome(
        action_id=int(r.action_id),
        tenant_id=r.tenant_id,
        farmer_id=r.farmer_id,
        season_id=r.season_id,
        suggestion_id=r.suggestion_id,
        action_date=r.action_date,
        action_type=r.action_type,
        water_liters=(None if r.water_liters is None else float(r.water_liters)),
        farmer_followed_ai=r.farmer_followed_ai,
        suggestion_type=r.suggestion_type,
        ai_suggested_liters=(
            None if r.ai_suggested_liters is None else float(r.ai_suggested_liters)
        ),
        crop_stage=r.crop_stage,
        soil_type=r.soil_type,
    )


class PgLearningRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def list_unlearned_actions(self, limit: int = 200) -> list[ActionOutcome]:
        stmt = text(
            """
            SELECT a.action_id, a.tenant_id, a.farmer_id, a.season_id,
                   a.action_date, a.action_type, a.water_liters, a.farmer_followed_ai,
                   s.suggestion_id, s.suggestion_type,
                   s.water_liters_suggested AS ai_suggested_liters, s.crop_stage,
                   fm.soil_type
            FROM farmer_actions a
            JOIN ai_suggestions s ON s.suggestion_id = a.ai_suggestion_id
            LEFT JOIN farms fm ON fm.farm_id = a.farm_id
            LEFT JOIN ai_learning_log l ON l.action_id = a.action_id
            WHERE a.ai_suggestion_id IS NOT NULL
              AND l.learning_id IS NULL
            ORDER BY a.action_date ASC, a.action_id ASC
            LIMIT :limit
            """
        )
        async with self._sm() as session:
            rows = (await session.execute(stmt, {"limit": limit})).all()
        return [_row_to_outcome(r) for r in rows]

    async def record(self, row: LearningRow) -> int:
        stmt = text(
            """
            INSERT INTO ai_learning_log (
                tenant_id, farmer_id, season_id, suggestion_id, action_id,
                learning_date, suggestion_type, ai_suggested_liters,
                farmer_gave_liters, water_variance_liters, suggestion_accuracy,
                crop_stage, soil_type, learning_applied_at
            ) VALUES (
                :tenant_id, :farmer_id, :season_id, :suggestion_id, :action_id,
                :learning_date, :suggestion_type, :ai_suggested_liters,
                :farmer_gave_liters, :water_variance_liters, :suggestion_accuracy,
                :crop_stage, :soil_type, :learning_applied_at
            )
            RETURNING learning_id
            """
        )
        params: dict[str, Any] = {
            "tenant_id": row.tenant_id,
            "farmer_id": row.farmer_id,
            "season_id": row.season_id,
            "suggestion_id": row.suggestion_id,
            "action_id": row.action_id,
            "learning_date": row.learning_date,
            "suggestion_type": row.suggestion_type,
            "ai_suggested_liters": row.ai_suggested_liters,
            "farmer_gave_liters": row.farmer_gave_liters,
            "water_variance_liters": row.water_variance_liters,
            "suggestion_accuracy": row.suggestion_accuracy,
            "crop_stage": row.crop_stage,
            "soil_type": row.soil_type,
            "learning_applied_at": row.learning_applied_at,
        }
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            rid = res.scalar()
            await session.commit()
        return int(cast(Any, rid))


__all__ = ["PgLearningRepo"]
