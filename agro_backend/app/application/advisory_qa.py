"""D12 advisory-QA use-cases (D12_QA_WORKFLOW §5.1, §5.2).

``classify_advisory`` records a delivered advisory's true/false-positive verdict
for the current review week; ``capture_non_compliance`` records why a farmer did
not act on one. Both resolve the advisory's plot/farmer/rule from
``ai_suggestions`` (so the caller passes only the advisory id), validate the
controlled vocabularies, and upsert on the natural key.

The review week is the Monday (IST) of the week the review happens in — the
weekly digest (a later PR) buckets by it.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import TypeVar

from app.application.ports.advisory_qa_repo import (
    AdvisoryQaRepo,
    ClassificationRow,
    NonComplianceRow,
)
from app.application.ports.ai_suggestion_repo import AiSuggestionRepo
from app.domain.advisory_qa import (
    ActionState,
    CapturedVia,
    Classification,
    EvidenceSource,
    NonComplianceReason,
)
from app.lib.time import IST, now_ist

_E = TypeVar("_E", bound=StrEnum)


class AdvisoryNotFoundError(Exception):
    """No ``ai_suggestions`` row for the given advisory id."""


class AdvisoryNotClassifiableError(Exception):
    """The advisory lacks the rule/plot linkage a classification needs.

    True for advisories written before migration 0043 (no ``rule_id``) and for
    non-engine advisories that never came from a KB rule.
    """


def _review_week(now: datetime) -> date:
    """The Monday (IST) of the review week containing ``now``."""
    ist = now.astimezone(IST)
    return (ist - timedelta(days=ist.weekday())).date()


def _validate(value: str, enum: type[_E], field: str) -> str:
    try:
        return enum(value).value
    except ValueError as exc:
        allowed = ", ".join(e.value for e in enum)
        raise ValueError(f"invalid {field} {value!r}; expected one of: {allowed}") from exc


async def classify_advisory(
    *,
    advisory_id: uuid.UUID,
    classification: str,
    evidence_source: str | None,
    note: str | None,
    reviewer: str,
    ai_suggestion_repo: AiSuggestionRepo,
    advisory_qa_repo: AdvisoryQaRepo,
    now: datetime | None = None,
) -> ClassificationRow:
    """Record the true/false-positive verdict for one advisory this review week."""
    classification = _validate(classification, Classification, "classification")
    if evidence_source is not None:
        evidence_source = _validate(evidence_source, EvidenceSource, "evidence_source")

    advisory = await ai_suggestion_repo.find_by_id(advisory_id)
    if advisory is None:
        raise AdvisoryNotFoundError(str(advisory_id))
    if advisory.rule_id is None or advisory.plot_id is None:
        raise AdvisoryNotClassifiableError(
            f"advisory {advisory_id} has no rule_id/plot_id to classify against"
        )

    row = ClassificationRow(
        advisory_id=advisory_id,
        plot_id=advisory.plot_id,
        farmer_id=advisory.farmer_id,
        rule_id=advisory.rule_id,
        fired_at=advisory.generated_at,
        review_week=_review_week(now or now_ist()),
        classification=classification,
        evidence_source=evidence_source,
        classification_note=note,
        reviewer=reviewer,
    )
    await advisory_qa_repo.upsert_classification(row)
    return row


async def capture_non_compliance(
    *,
    advisory_id: uuid.UUID,
    action_state: str,
    reason: str,
    detail_mr: str | None,
    captured_via: str,
    captured_by: str,
    ai_suggestion_repo: AiSuggestionRepo,
    advisory_qa_repo: AdvisoryQaRepo,
) -> NonComplianceRow:
    """Record why a farmer did not (fully) act on one advisory."""
    action_state = _validate(action_state, ActionState, "action_state")
    reason = _validate(reason, NonComplianceReason, "reason")
    captured_via = _validate(captured_via, CapturedVia, "captured_via")

    advisory = await ai_suggestion_repo.find_by_id(advisory_id)
    if advisory is None:
        raise AdvisoryNotFoundError(str(advisory_id))
    if advisory.plot_id is None:
        raise AdvisoryNotClassifiableError(f"advisory {advisory_id} has no plot_id")

    row = NonComplianceRow(
        advisory_id=advisory_id,
        plot_id=advisory.plot_id,
        farmer_id=advisory.farmer_id,
        action_state=action_state,
        reason=reason,
        reason_detail_mr=detail_mr,
        captured_via=captured_via,
        captured_by=captured_by,
    )
    await advisory_qa_repo.upsert_non_compliance(row)
    return row


__all__ = [
    "AdvisoryNotClassifiableError",
    "AdvisoryNotFoundError",
    "capture_non_compliance",
    "classify_advisory",
]
