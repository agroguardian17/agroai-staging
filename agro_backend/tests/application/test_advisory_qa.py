"""D12 advisory-QA use-cases: classify_advisory + capture_non_compliance."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from app.application.advisory_qa import (
    AdvisoryNotClassifiableError,
    AdvisoryNotFoundError,
    capture_non_compliance,
    classify_advisory,
)
from app.application.ports.advisory_qa_repo import ClassificationRow, NonComplianceRow
from app.application.ports.ai_suggestion_repo import AiSuggestion

_ADVISORY_ID = uuid.uuid4()
_FARMER_ID = uuid.uuid4()


def _advisory(*, rule_id: str | None = "D05-RF-001", plot_id: str | None = "P1") -> AiSuggestion:
    return AiSuggestion(
        suggestion_id=_ADVISORY_ID,
        tenant_id=uuid.uuid4(),
        farmer_id=_FARMER_ID,
        farm_id=uuid.uuid4(),
        plot_id=plot_id,
        season_id=uuid.uuid4(),
        generated_at=datetime(2026, 6, 17, 6, 0, tzinfo=UTC),
        suggestion_type="daily",
        full_message_marathi="...",
        ai_model_version="ginger/v1",
        tokens_used=None,
        generation_time_ms=None,
        rule_id=rule_id,
    )


class _FakeAiRepo:
    def __init__(self, advisory: AiSuggestion | None) -> None:
        self._advisory = advisory

    async def find_by_id(self, suggestion_id: uuid.UUID) -> AiSuggestion | None:
        return self._advisory


class _FakeQaRepo:
    def __init__(self) -> None:
        self.classifications: list[ClassificationRow] = []
        self.non_compliance: list[NonComplianceRow] = []

    async def upsert_classification(self, row: ClassificationRow) -> None:
        self.classifications.append(row)

    async def upsert_non_compliance(self, row: NonComplianceRow) -> None:
        self.non_compliance.append(row)


async def _classify(
    advisory: AiSuggestion | None, **kw: object
) -> tuple[ClassificationRow, _FakeQaRepo]:
    qa = _FakeQaRepo()
    row = await classify_advisory(
        advisory_id=_ADVISORY_ID,
        classification=kw.get("classification", "false_positive"),  # type: ignore[arg-type]
        evidence_source=kw.get("evidence_source", "agronomist_visit"),  # type: ignore[arg-type]
        note=kw.get("note", "no soft rot on visit"),  # type: ignore[arg-type]
        reviewer="agronomist_a",
        ai_suggestion_repo=_FakeAiRepo(advisory),  # type: ignore[arg-type]
        advisory_qa_repo=qa,  # type: ignore[arg-type]
        now=kw.get("now"),  # type: ignore[arg-type]
    )
    return row, qa


# --- classify_advisory -----------------------------------------------------


async def test_classify_writes_row_from_advisory_lookup() -> None:
    row, qa = await _classify(_advisory())
    assert len(qa.classifications) == 1
    assert row.rule_id == "D05-RF-001"
    assert row.plot_id == "P1"
    assert row.farmer_id == _FARMER_ID
    assert row.classification == "false_positive"
    assert row.fired_at == datetime(2026, 6, 17, 6, 0, tzinfo=UTC)


async def test_classify_review_week_is_ist_monday() -> None:
    # 2026-06-17 is a Wednesday; the review week Monday is 2026-06-15.
    row, _ = await _classify(_advisory(), now=datetime(2026, 6, 17, 12, 0, tzinfo=UTC))
    assert row.review_week.isoformat() == "2026-06-15"


async def test_classify_rejects_bad_classification() -> None:
    with pytest.raises(ValueError, match="invalid classification"):
        await _classify(_advisory(), classification="nonsense")


async def test_classify_rejects_bad_evidence_source() -> None:
    with pytest.raises(ValueError, match="invalid evidence_source"):
        await _classify(_advisory(), evidence_source="rumour")


async def test_classify_allows_null_evidence_source() -> None:
    row, _ = await _classify(_advisory(), evidence_source=None)
    assert row.evidence_source is None


async def test_classify_missing_advisory_raises() -> None:
    with pytest.raises(AdvisoryNotFoundError):
        await _classify(None)


async def test_classify_without_rule_id_raises() -> None:
    with pytest.raises(AdvisoryNotClassifiableError):
        await _classify(_advisory(rule_id=None))


# --- capture_non_compliance ------------------------------------------------


async def _capture(
    advisory: AiSuggestion | None, **kw: object
) -> tuple[NonComplianceRow, _FakeQaRepo]:
    qa = _FakeQaRepo()
    row = await capture_non_compliance(
        advisory_id=_ADVISORY_ID,
        action_state=kw.get("action_state", "not_acted"),  # type: ignore[arg-type]
        reason=kw.get("reason", "cost_barrier"),  # type: ignore[arg-type]
        detail_mr=kw.get("detail_mr", "महाग"),  # type: ignore[arg-type]
        captured_via=kw.get("captured_via", "agronomist_call"),  # type: ignore[arg-type]
        captured_by="agronomist_a",
        ai_suggestion_repo=_FakeAiRepo(advisory),  # type: ignore[arg-type]
        advisory_qa_repo=qa,  # type: ignore[arg-type]
    )
    return row, qa


async def test_capture_writes_row() -> None:
    row, qa = await _capture(_advisory())
    assert len(qa.non_compliance) == 1
    assert row.reason == "cost_barrier"
    assert row.action_state == "not_acted"
    assert row.farmer_id == _FARMER_ID


async def test_capture_rejects_bad_reason() -> None:
    with pytest.raises(ValueError, match="invalid reason"):
        await _capture(_advisory(), reason="lazy")


async def test_capture_rejects_bad_captured_via() -> None:
    with pytest.raises(ValueError, match="invalid captured_via"):
        await _capture(_advisory(), captured_via="carrier_pigeon")


async def test_capture_missing_advisory_raises() -> None:
    with pytest.raises(AdvisoryNotFoundError):
        await _capture(None)
