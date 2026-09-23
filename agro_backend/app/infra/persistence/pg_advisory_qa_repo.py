"""Postgres adapter for
:class:`~app.application.ports.advisory_qa_repo.AdvisoryQaRepo`.

Upserts on the tables' natural keys (``advisory_classification`` unique on
``(advisory_id, review_week)``; ``non_compliance_reason`` unique on
``advisory_id``) so a re-review corrects the row in place. The CHECK constraints
from migration 0041 backstop the enum values the use-case already validates.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.advisory_qa_repo import ClassificationRow, NonComplianceRow

_CLASSIFY_SQL = text(
    """
    INSERT INTO advisory_classification (
        advisory_id, plot_id, farmer_id, rule_id, fired_at, review_week,
        classification, evidence_source, classification_note, reviewer
    ) VALUES (
        :advisory_id, :plot_id, :farmer_id, :rule_id, :fired_at, :review_week,
        :classification, :evidence_source, :classification_note, :reviewer
    )
    ON CONFLICT (advisory_id, review_week) DO UPDATE SET
        classification = EXCLUDED.classification,
        evidence_source = EXCLUDED.evidence_source,
        classification_note = EXCLUDED.classification_note,
        reviewer = EXCLUDED.reviewer,
        reviewed_at = now()
    """
)

_NON_COMPLIANCE_SQL = text(
    """
    INSERT INTO non_compliance_reason (
        advisory_id, plot_id, farmer_id, action_state, reason,
        reason_detail_mr, captured_via, captured_by
    ) VALUES (
        :advisory_id, :plot_id, :farmer_id, :action_state, :reason,
        :reason_detail_mr, :captured_via, :captured_by
    )
    ON CONFLICT (advisory_id) DO UPDATE SET
        action_state = EXCLUDED.action_state,
        reason = EXCLUDED.reason,
        reason_detail_mr = EXCLUDED.reason_detail_mr,
        captured_via = EXCLUDED.captured_via,
        captured_by = EXCLUDED.captured_by,
        captured_at = now()
    """
)


class PgAdvisoryQaRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def upsert_classification(self, row: ClassificationRow) -> None:
        params = {
            "advisory_id": row.advisory_id,
            "plot_id": row.plot_id,
            "farmer_id": row.farmer_id,
            "rule_id": row.rule_id,
            "fired_at": row.fired_at,
            "review_week": row.review_week,
            "classification": row.classification,
            "evidence_source": row.evidence_source,
            "classification_note": row.classification_note,
            "reviewer": row.reviewer,
        }
        async with self._sm() as session:
            await session.execute(_CLASSIFY_SQL, params)
            await session.commit()

    async def upsert_non_compliance(self, row: NonComplianceRow) -> None:
        params = {
            "advisory_id": row.advisory_id,
            "plot_id": row.plot_id,
            "farmer_id": row.farmer_id,
            "action_state": row.action_state,
            "reason": row.reason,
            "reason_detail_mr": row.reason_detail_mr,
            "captured_via": row.captured_via,
            "captured_by": row.captured_by,
        }
        async with self._sm() as session:
            await session.execute(_NON_COMPLIANCE_SQL, params)
            await session.commit()


__all__ = ["PgAdvisoryQaRepo"]
