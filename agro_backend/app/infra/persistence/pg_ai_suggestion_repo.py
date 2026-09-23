"""Postgres adapter for :class:`~app.application.ports.ai_suggestion_repo.AiSuggestionRepo`."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.ai_suggestion_repo import AiSuggestion

_SELECT_COLS = (
    "suggestion_id, tenant_id, farmer_id, farm_id, plot_id, season_id, "
    "generated_at, suggestion_type, full_message_marathi, "
    "ai_model_version, tokens_used, generation_time_ms, "
    "crop_age_days, crop_stage, rule_id, confidence, rule_version"
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
        rule_id=r.rule_id,
        confidence=float(r.confidence) if r.confidence is not None else None,
        rule_version=r.rule_version,
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
                generation_time_ms, crop_age_days, crop_stage, rule_id,
                confidence, rule_version
            ) VALUES (
                :sid, :tenant, :farmer, :farm, :plot,
                :season, :gen_at, :stype,
                :msg, :model, :tokens,
                :ms, :age, :stage, :rule_id,
                :confidence, :rule_version
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
            "rule_id": s.rule_id,
            "confidence": s.confidence,
            "rule_version": s.rule_version,
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

    # --- Round 14 delivery state machine (migration 0016) -----------------

    async def claim_for_delivery(
        self, suggestion_id: uuid.UUID, now: datetime, *, require_review: bool
    ) -> int | None:
        stmt = text(
            """
            UPDATE ai_suggestions
            SET delivery_status = 'in_flight',
                delivery_claimed_at = :now
            WHERE suggestion_id = :sid
              AND delivery_status = 'pending'
              AND (delivery_next_retry_at IS NULL OR delivery_next_retry_at <= :now)
              AND (NOT CAST(:require_review AS boolean) OR review_status = 'approved')
            RETURNING delivery_attempts
            """
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt, {"sid": suggestion_id, "now": now, "require_review": require_review}
            )
            row = res.first()
            await session.commit()
        if row is None:
            return None
        return int(cast(Any, row).delivery_attempts)

    async def set_delivery_outcome(
        self,
        suggestion_id: uuid.UUID,
        *,
        status: str,
        attempts: int | None = None,
        next_retry_at: datetime | None = None,
        last_error: str | None = None,
        provider_message_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        sets = [
            "delivery_status = :status",
            "delivery_next_retry_at = :nra",
            "delivery_last_error = :err",
        ]
        params: dict[str, Any] = {
            "sid": suggestion_id,
            "status": status,
            "nra": next_retry_at,
            "err": last_error,
        }
        if attempts is not None:
            sets.append("delivery_attempts = :attempts")
            params["attempts"] = attempts
        if provider_message_id is not None:
            sets.append("delivery_provider_message_id = :pmid")
            params["pmid"] = provider_message_id
        if status == "sent":
            # Also set the base 0001 markers so existing readers see it as sent.
            sets.append("whatsapp_sent = TRUE")
            sets.append("whatsapp_sent_at = :sent_at")
            params["sent_at"] = sent_at
        stmt = text(f"UPDATE ai_suggestions SET {', '.join(sets)} WHERE suggestion_id = :sid")
        async with self._sm() as session:
            await session.execute(stmt, params)
            await session.commit()

    async def list_due_deliveries(
        self, now: datetime, *, require_review: bool, limit: int = 100
    ) -> list[uuid.UUID]:
        stmt = text(
            """
            SELECT suggestion_id
            FROM ai_suggestions
            WHERE delivery_status = 'pending'
              AND (delivery_next_retry_at IS NULL OR delivery_next_retry_at <= :now)
              AND (NOT CAST(:require_review AS boolean) OR review_status = 'approved')
            ORDER BY generated_at ASC
            LIMIT :limit
            """
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt, {"now": now, "require_review": require_review, "limit": limit}
            )
            rows = res.all()
        return [cast(uuid.UUID, cast(Any, r).suggestion_id) for r in rows]

    async def revert_stale_deliveries(self, cutoff: datetime, now: datetime) -> int:
        stmt = text(
            """
            UPDATE ai_suggestions
            SET delivery_status = 'pending',
                delivery_next_retry_at = :now,
                delivery_last_error = 'stale_revert'
            WHERE delivery_status = 'in_flight'
              AND delivery_claimed_at IS NOT NULL
              AND delivery_claimed_at < :cutoff
            """
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"cutoff": cutoff, "now": now})
            await session.commit()
        return int(cast(Any, res).rowcount or 0)


__all__ = ["PgAiSuggestionRepo"]
