"""Postgres adapter for :class:`~app.application.ports.ai_suggestion_repo.AiSuggestionRepo`."""

from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.ai_suggestion_repo import AiSuggestion

_SELECT_COLS = (
    "suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id, "
    "generated_at, suggestion_type, full_message_marathi, "
    "ai_model_version, tokens_used, generation_time_ms, "
    "crop_age_days, crop_stage"
)


def _row_to_suggestion(row: object) -> AiSuggestion:
    r: Any = row
    return AiSuggestion(
        suggestion_id=r.suggestion_id,
        tenant_id=r.tenant_id,
        farmer_id=r.farmer_id,
        farm_id=r.farm_id,
        plot_id=r.plot_id,
        season_id=r.season_id,
        generated_at=r.generated_at,
        suggestion_type=r.suggestion_type,
        full_message_marathi=r.full_message_marathi,
        ai_model_version=r.ai_model_version,
        tokens_used=r.tokens_used,
        generation_time_ms=r.generation_time_ms,
        crop_age_days=r.crop_age_days,
        crop_stage=r.crop_stage,
    )


class PgAiSuggestionRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def create(self, s: AiSuggestion) -> uuid.UUID:
        stmt = text(
            """
            INSERT INTO ai_suggestions (
                suggestion_id, tenant_id, farmer_id, farm_id, plot_id,
                season_id, generated_at, suggestion_type,
                full_message_marathi, ai_model_version, tokens_used,
                generation_time_ms, crop_age_days, crop_stage
            ) VALUES (
                :sid, :tenant, :farmer, :farm, :plot,
                :season, :gen_at, :stype,
                :msg, :model, :tokens,
                :ms, :age, :stage
            )
            RETURNING suggestion_id
            """
        )
        params = {
            "sid": s.suggestion_id,
            "tenant": s.tenant_id,
            "farmer": s.farmer_id,
            "farm": s.farm_id,
            "plot": s.plot_id,
            "season": s.season_id,
            "gen_at": s.generated_at,
            "stype": s.suggestion_type,
            "msg": s.full_message_marathi,
            "model": s.ai_model_version,
            "tokens": s.tokens_used,
            "ms": s.generation_time_ms,
            "age": s.crop_age_days,
            "stage": s.crop_stage,
        }
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            row = res.first()
            await session.commit()
        if row is None:
            raise RuntimeError("ai_suggestions INSERT did not RETURN a row")
        r: Any = row
        return cast(uuid.UUID, r.suggestion_id)

    async def find_by_id(self, suggestion_id: uuid.UUID) -> AiSuggestion | None:
        stmt = text(f"SELECT {_SELECT_COLS} FROM ai_suggestions WHERE suggestion_id = :sid LIMIT 1")
        async with self._sm() as session:
            res = await session.execute(stmt, {"sid": suggestion_id})
            row = res.first()
        return None if row is None else _row_to_suggestion(row)

    async def list_for_plot(self, plot_id: str, limit: int = 50) -> list[AiSuggestion]:
        stmt = text(
            f"SELECT {_SELECT_COLS} FROM ai_suggestions "
            "WHERE plot_id = :plot_id "
            "ORDER BY generated_at DESC LIMIT :limit"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id, "limit": limit})
            rows = res.all()
        return [_row_to_suggestion(r) for r in rows]


__all__ = ["PgAiSuggestionRepo"]
