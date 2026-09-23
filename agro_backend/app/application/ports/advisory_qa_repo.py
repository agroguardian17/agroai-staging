"""Port: D12 advisory-QA write-path (D12_QA_WORKFLOW §5.1, §5.2).

Writes the two review artefacts — an advisory's true/false-positive
classification for a review week, and a farmer's non-compliance reason. Both
upsert on their natural key (``(advisory_id, review_week)`` and ``advisory_id``
respectively) so a reviewer can correct an entry without a duplicate.

Concrete implementation:
:class:`app.infra.persistence.pg_advisory_qa_repo.PgAdvisoryQaRepo`.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ClassificationRow:
    advisory_id: uuid.UUID
    plot_id: str
    farmer_id: uuid.UUID
    rule_id: str
    fired_at: datetime
    review_week: date
    classification: str
    evidence_source: str | None
    classification_note: str | None
    reviewer: str


@dataclass(frozen=True, slots=True)
class NonComplianceRow:
    advisory_id: uuid.UUID
    plot_id: str
    farmer_id: uuid.UUID
    action_state: str
    reason: str
    reason_detail_mr: str | None
    captured_via: str
    captured_by: str


@runtime_checkable
class AdvisoryQaRepo(Protocol):
    async def upsert_classification(self, row: ClassificationRow) -> None:
        """Insert/replace the classification for ``(advisory_id, review_week)``."""
        ...

    async def upsert_non_compliance(self, row: NonComplianceRow) -> None:
        """Insert/replace the non-compliance reason for ``advisory_id``."""
        ...


__all__ = [
    "AdvisoryQaRepo",
    "ClassificationRow",
    "NonComplianceRow",
]
