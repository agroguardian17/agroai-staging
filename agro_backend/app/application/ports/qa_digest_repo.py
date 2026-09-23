"""Port: D12 weekly-digest read model (D12_QA_WORKFLOW §5.4, §6.5, §7).

One ``gather`` call returns everything the two digests render from — all
decomposable to raw rows in the four QA tables plus ``ai_suggestions`` (standing
agronomy rule #1: no hidden aggregation). The counts keep their numerators and
denominators so the renderer can show the raw basis of every rate.

Concrete implementation:
:class:`app.infra.persistence.pg_qa_digest_repo.PgQaDigestRepo`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class RuleCount:
    rule_id: str
    count: int


@dataclass(frozen=True, slots=True)
class BiasObservationSummary:
    bias_type: str
    scope_domain: str | None
    scope_rule_id: str | None
    observation_mr: str
    suggested_change_mr: str | None
    observed_by: str
    kb_author_read: bool


@dataclass(frozen=True, slots=True)
class WeeklyQaData:
    week_start: date  # Monday (IST) of the review week
    week_end: date  # exclusive — next Monday
    # advisory_classification, bucketed by verdict (raw counts).
    classification_counts: dict[str, int] = field(default_factory=dict)
    # ai_suggestions with a rule_id fired in the window — coverage denominator.
    total_advisories: int = 0
    # Distinct advisories classified in the window — coverage numerator.
    classified_count: int = 0
    # Top false-positive rules this window.
    false_positive_rules: list[RuleCount] = field(default_factory=list)
    # non_compliance_reason, bucketed by reason (raw counts).
    non_compliance_counts: dict[str, int] = field(default_factory=dict)
    # bias_observation rows recorded this window + total still unread by the KB author.
    bias_observations: list[BiasObservationSummary] = field(default_factory=list)
    unread_bias_total: int = 0
    # farmer_photos with no photo_label, older than 7 days (D12 §7 backlog metric).
    photo_backlog: int = 0


@runtime_checkable
class QaDigestRepo(Protocol):
    async def gather(
        self, week_start: date, week_end: date, *, top_fp_rules: int = 10
    ) -> WeeklyQaData:
        """All digest inputs for the review window ``[week_start, week_end)``."""
        ...


__all__ = [
    "BiasObservationSummary",
    "QaDigestRepo",
    "RuleCount",
    "WeeklyQaData",
]
