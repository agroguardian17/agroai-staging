"""Postgres adapter for the FarmerConsentRepo port."""

from __future__ import annotations

import datetime
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.farmer_consent_repo import ConsentCapture, FarmerConsentView

# Whitelist: consent scope -> column (guards the interpolated UPDATE below).
_SCOPE_COLUMN = {
    "advisory": "consent_advisory",
    "research": "consent_research",
    "third_party": "third_party_share_consent_given",
}

_COLS = (
    "farmer_id, consent_advisory, consent_research, consent_date, "
    "third_party_share_consent_given, data_retention_until, deletion_requested, "
    "cluster_anonymised, sat_attribution_shown, sat_public_display_context"
)

_CAPTURE_SQL = text(
    """
    INSERT INTO farmer_consent (
        farmer_id, tenant_id, consent_advisory, consent_research,
        third_party_share_consent_given, consent_date, data_retention_until,
        consent_version, consent_notice_hash, notice_shown_at, consent_channel,
        parental_consent_by, parental_consent_verified, updated_at
    ) VALUES (
        :farmer_id, :tenant_id, :consent_advisory, :consent_research,
        :third_party, :consent_date, :data_retention_until,
        :consent_version, :consent_notice_hash, :notice_shown_at, :consent_channel,
        :parental_consent_by, :parental_consent_verified, now()
    )
    ON CONFLICT (farmer_id) DO UPDATE SET
        consent_advisory = EXCLUDED.consent_advisory,
        consent_research = EXCLUDED.consent_research,
        third_party_share_consent_given = EXCLUDED.third_party_share_consent_given,
        consent_date = EXCLUDED.consent_date,
        data_retention_until = EXCLUDED.data_retention_until,
        consent_version = EXCLUDED.consent_version,
        consent_notice_hash = EXCLUDED.consent_notice_hash,
        notice_shown_at = EXCLUDED.notice_shown_at,
        consent_channel = EXCLUDED.consent_channel,
        parental_consent_by = EXCLUDED.parental_consent_by,
        parental_consent_verified = EXCLUDED.parental_consent_verified,
        updated_at = now()
    """
)

_EVENT_SQL = text(
    """
    INSERT INTO consent_event (farmer_id, event_type, scope, consent_version, channel, actor)
    VALUES (:farmer_id, :event_type, :scope, :consent_version, :channel, :actor)
    """
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

    async def capture(self, record: ConsentCapture) -> None:
        params = {
            "farmer_id": record.farmer_id,
            "tenant_id": record.tenant_id,
            "consent_advisory": record.consent_advisory,
            "consent_research": record.consent_research,
            "third_party": record.third_party_share_consent_given,
            "consent_date": record.consent_date,
            "data_retention_until": record.data_retention_until,
            "consent_version": record.consent_version,
            "consent_notice_hash": record.consent_notice_hash,
            "notice_shown_at": record.notice_shown_at,
            "consent_channel": record.consent_channel,
            "parental_consent_by": record.parental_consent_by,
            "parental_consent_verified": record.parental_consent_verified,
        }
        async with self._sm() as session:
            await session.execute(_CAPTURE_SQL, params)
            await session.commit()

    async def record_event(
        self,
        *,
        farmer_id: uuid.UUID,
        event_type: str,
        scope: str,
        consent_version: str | None,
        channel: str | None,
        actor: str | None,
    ) -> None:
        params = {
            "farmer_id": farmer_id,
            "event_type": event_type,
            "scope": scope,
            "consent_version": consent_version,
            "channel": channel,
            "actor": actor,
        }
        async with self._sm() as session:
            await session.execute(_EVENT_SQL, params)
            await session.commit()

    async def set_scope(
        self,
        farmer_id: uuid.UUID,
        scope: str,
        *,
        granted: bool,
        withdrawn_at: datetime.datetime | None = None,
    ) -> bool:
        column = _SCOPE_COLUMN.get(scope)
        if column is None:
            raise ValueError(f"unknown consent scope: {scope!r}")
        # ``column`` is from the _SCOPE_COLUMN whitelist, never user input.
        stmt = text(
            f"UPDATE farmer_consent SET {column} = :granted, "
            "withdrawn_at = COALESCE(:withdrawn_at, withdrawn_at), updated_at = now() "
            "WHERE farmer_id = :farmer_id RETURNING farmer_id"
        )
        async with self._sm() as session:
            res = await session.execute(
                stmt,
                {"granted": granted, "withdrawn_at": withdrawn_at, "farmer_id": farmer_id},
            )
            row = res.first()
            await session.commit()
        return row is not None

    async def mark_deletion_requested(self, farmer_id: uuid.UUID, *, requested: bool) -> None:
        stmt = text(
            "UPDATE farmer_consent SET deletion_requested = :requested, updated_at = now() "
            "WHERE farmer_id = :farmer_id"
        )
        async with self._sm() as session:
            await session.execute(stmt, {"requested": requested, "farmer_id": farmer_id})
            await session.commit()


__all__ = ["PgFarmerConsentRepo"]
