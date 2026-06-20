"""Postgres adapter for :class:`~app.application.ports.alert_repo.AlertRepo`.


Inserts into ``alerts_notifications`` with ``dispatch_status='pending'``
(server default per migration 0002 + schema decisions §11d) so the Round 7
notification dispatcher picks the row up. Cooldown queries select only
``triggered_at`` - the dispatch decision needs nothing more.
"""


from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.alert import AlertCandidate, AlertType


def _decimal_to_float(v: Decimal | None) -> float | None:
    return None if v is None else float(v)




class PgAlertRepo:
    """Concrete :class:`AlertRepo` against Postgres."""


    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    # ------------------------------------------------------------------
    async def create(self, candidate: AlertCandidate) -> int:
        stmt = text(
            """
            INSERT INTO alerts_notifications (
                tenant_id, farm_id, farmer_id, device_id,
                alert_type, severity, alert_message_marathi,
                alert_value, alert_threshold, triggered_at
            ) VALUES (
                :tenant_id, :farm_id, :farmer_id, :device_id,
                :alert_type, :severity, :alert_message_marathi,
                :alert_value, :alert_threshold, :triggered_at
            ) RETURNING alert_id
            """
        )
        params: dict[str, Any] = {
            "tenant_id": candidate.tenant_id,
            "farm_id": candidate.farm_id,
            "farmer_id": candidate.farmer_id,
            "device_id": candidate.device_id,
            "alert_type": candidate.alert_type.value,
            "severity": candidate.severity.value,
            "alert_message_marathi": candidate.alert_message_marathi,
            "alert_value": _decimal_to_float(candidate.alert_value),
            "alert_threshold": _decimal_to_float(candidate.alert_threshold),
            "triggered_at": candidate.triggered_at,
        }
        async with self._sm() as session:
            res = await session.execute(stmt, params)
            row = res.one()  # RETURNING always yields one row on successful INSERT
            await session.commit()
        return int(row.alert_id)


    # ------------------------------------------------------------------
    async def last_triggered_at(self, plot_id: str, alert_type: AlertType) -> datetime | None:
        # alerts_notifications doesn't have a plot_id FK (the table is
        # device-centric). We join through device_registry -> plots to
        # find alerts for any device assigned to this plot.
        stmt = text(
            """
            SELECT MAX(a.triggered_at) AS last_at
            FROM alerts_notifications a
            JOIN plots p ON p.node_id = a.device_id
            WHERE p.plot_id = :plot_id
              AND a.alert_type = :alert_type
            """
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id, "alert_type": alert_type.value})
            row = res.first()
        return row.last_at if row is not None else None


    # ------------------------------------------------------------------
    async def resolve(self, alert_id: int, notes: str | None = None) -> None:
        stmt = text(
            """
            UPDATE alerts_notifications
            SET resolved = TRUE,
                resolved_at = NOW(),
                resolution_note = :notes
            WHERE alert_id = :alert_id
            """
        )
        async with self._sm() as session:
            await session.execute(stmt, {"alert_id": alert_id, "notes": notes})
            await session.commit()




__all__ = ["PgAlertRepo"]
