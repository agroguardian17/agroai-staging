"""Postgres adapter for
:class:`~app.application.ports.qa_digest_repo.QaDigestRepo`.

Every figure is a direct count over the four QA tables (or ``ai_suggestions``)
for the review window. The window's ``review_week`` / ``observed_week`` DATE
columns are set from the IST Monday, so those match by date equality; the
timestamp columns (``generated_at``, ``captured_at``, ``submitted_at``) are
compared against IST-midnight bounds rebuilt from the window dates, so a UTC
session timezone does not shift the week boundary.
"""

from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.qa_digest_repo import (
    BiasObservationSummary,
    RuleCount,
    WeeklyQaData,
)
from app.lib.time import IST

_CLASSIFICATION_SQL = text(
    """
    SELECT classification, count(*) AS n
    FROM advisory_classification
    WHERE review_week = :week_start
    GROUP BY classification
    """
)

_CLASSIFIED_COUNT_SQL = text(
    """
    SELECT count(DISTINCT advisory_id) AS n
    FROM advisory_classification
    WHERE review_week = :week_start
    """
)

_TOTAL_ADVISORIES_SQL = text(
    """
    SELECT count(*) AS n
    FROM ai_suggestions
    WHERE rule_id IS NOT NULL
      AND generated_at >= :start_ts AND generated_at < :end_ts
    """
)

_FALSE_POSITIVE_RULES_SQL = text(
    """
    SELECT rule_id, count(*) AS n
    FROM advisory_classification
    WHERE review_week = :week_start AND classification = 'false_positive'
    GROUP BY rule_id
    ORDER BY n DESC, rule_id ASC
    LIMIT :limit
    """
)

_NON_COMPLIANCE_SQL = text(
    """
    SELECT reason, count(*) AS n
    FROM non_compliance_reason
    WHERE captured_at >= :start_ts AND captured_at < :end_ts
    GROUP BY reason
    """
)

_BIAS_OBS_SQL = text(
    """
    SELECT bias_type, scope_domain, scope_rule_id, observation_mr,
           suggested_change_mr, observed_by, kb_author_read
    FROM bias_observation
    WHERE observed_week = :week_start
    ORDER BY observed_at ASC
    """
)

_UNREAD_BIAS_SQL = text("SELECT count(*) AS n FROM bias_observation WHERE kb_author_read IS FALSE")

# "Unlabelled photos > 7 days old" (D12 §7) — a live backlog, relative to now.
_PHOTO_BACKLOG_SQL = text(
    """
    SELECT count(*) AS n
    FROM farmer_photos f
    WHERE f.submitted_at < now() - interval '7 days'
      AND NOT EXISTS (SELECT 1 FROM photo_label pl WHERE pl.photo_id = f.id)
    """
)


class PgQaDigestRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def gather(
        self, week_start: date, week_end: date, *, top_fp_rules: int = 10
    ) -> WeeklyQaData:
        start_ts = datetime.combine(week_start, time.min, tzinfo=IST)
        end_ts = datetime.combine(week_end, time.min, tzinfo=IST)
        params_week = {"week_start": week_start}
        params_ts = {"start_ts": start_ts, "end_ts": end_ts}

        async with self._sm() as session:
            classification_counts = {
                r.classification: int(r.n)
                for r in (await session.execute(_CLASSIFICATION_SQL, params_week)).all()
            }
            classified_count = int(
                (await session.execute(_CLASSIFIED_COUNT_SQL, params_week)).scalar_one()
            )
            total_advisories = int(
                (await session.execute(_TOTAL_ADVISORIES_SQL, params_ts)).scalar_one()
            )
            fp_rows = (
                await session.execute(
                    _FALSE_POSITIVE_RULES_SQL,
                    {"week_start": week_start, "limit": top_fp_rules},
                )
            ).all()
            non_compliance_counts = {
                r.reason: int(r.n)
                for r in (await session.execute(_NON_COMPLIANCE_SQL, params_ts)).all()
            }
            bias_rows = (await session.execute(_BIAS_OBS_SQL, params_week)).all()
            unread_bias_total = int((await session.execute(_UNREAD_BIAS_SQL)).scalar_one())
            photo_backlog = int((await session.execute(_PHOTO_BACKLOG_SQL)).scalar_one())

        false_positive_rules = [RuleCount(rule_id=r.rule_id, count=int(r.n)) for r in fp_rows]
        bias_observations = [
            BiasObservationSummary(
                bias_type=r.bias_type,
                scope_domain=r.scope_domain,
                scope_rule_id=r.scope_rule_id,
                observation_mr=r.observation_mr,
                suggested_change_mr=r.suggested_change_mr,
                observed_by=r.observed_by,
                kb_author_read=bool(r.kb_author_read),
            )
            for r in bias_rows
        ]

        return WeeklyQaData(
            week_start=week_start,
            week_end=week_end,
            classification_counts=classification_counts,
            total_advisories=total_advisories,
            classified_count=classified_count,
            false_positive_rules=false_positive_rules,
            non_compliance_counts=non_compliance_counts,
            bias_observations=bias_observations,
            unread_bias_total=unread_bias_total,
            photo_backlog=photo_backlog,
        )


__all__ = ["PgQaDigestRepo"]
