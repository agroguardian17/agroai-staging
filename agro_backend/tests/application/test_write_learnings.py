"""Tests for the learning writer (write_learnings.execute)."""

from __future__ import annotations

import datetime
import uuid
from typing import Any, cast

import pytest

from app.application.ports.learning_repo import ActionOutcome, LearningRow
from app.application.write_learnings import WriteLearningsDeps, _accuracy, execute

NOW = datetime.datetime(2026, 9, 15, 22, 0, tzinfo=datetime.UTC)
T = uuid.UUID("11111111-1111-1111-1111-111111111111")
F = uuid.UUID("22222222-2222-2222-2222-222222222222")
SE = uuid.UUID("44444444-4444-4444-4444-444444444444")
SU = uuid.UUID("55555555-5555-5555-5555-555555555555")


def _action(
    action_id: int,
    *,
    action_type: str = "watering",
    water: float | None = 100.0,
    suggested: float | None = 100.0,
) -> ActionOutcome:
    return ActionOutcome(
        action_id=action_id,
        tenant_id=T,
        farmer_id=F,
        season_id=SE,
        suggestion_id=SU,
        action_date=datetime.date(2026, 9, 15),
        action_type=action_type,
        water_liters=water,
        farmer_followed_ai=True,
        suggestion_type="daily",
        ai_suggested_liters=suggested,
        crop_stage="vegetative",
        soil_type="black",
    )


class _FakeLearningRepo:
    def __init__(self, actions: list[ActionOutcome]) -> None:
        self._actions = actions
        self.recorded: list[LearningRow] = []

    async def list_unlearned_actions(self, limit: int = 200) -> list[ActionOutcome]:
        return self._actions[:limit]

    async def record(self, row: LearningRow) -> int:
        self.recorded.append(row)
        return len(self.recorded)


def _deps(repo: Any) -> WriteLearningsDeps:
    return WriteLearningsDeps(learning_repo=cast(Any, repo))


# --- accuracy classification (pure) -----------------------------------------
@pytest.mark.parametrize(
    ("suggested", "actual", "expected"),
    [
        (100.0, 100.0, "good"),
        (100.0, 108.0, "good"),  # within +/-10%
        (100.0, 120.0, "slight_over"),
        (100.0, 85.0, "slight_under"),
        (100.0, 200.0, "poor"),
        (100.0, 40.0, "poor"),
        (None, 100.0, None),
        (100.0, None, None),
        (0.0, 100.0, None),
    ],
)
def test_accuracy_bands(
    suggested: float | None, actual: float | None, expected: str | None
) -> None:
    assert _accuracy(suggested, actual) == expected


# --- sweep ------------------------------------------------------------------
async def test_writes_one_learning_row_per_action() -> None:
    repo = _FakeLearningRepo([_action(1), _action(2, water=130.0)])
    out = await execute(deps=_deps(repo), now=NOW)

    assert out.written == 2
    assert len(repo.recorded) == 2
    first = repo.recorded[0]
    assert first.action_id == 1
    assert first.ai_suggested_liters == 100.0
    assert first.farmer_gave_liters == 100.0
    assert first.water_variance_liters == 0.0
    assert first.suggestion_accuracy == "good"
    assert first.learning_applied_at == NOW
    # second: gave 130 vs 100 -> +30% -> slight_over
    assert repo.recorded[1].water_variance_liters == 30.0
    assert repo.recorded[1].suggestion_accuracy == "slight_over"


async def test_non_watering_action_has_no_water_comparison() -> None:
    repo = _FakeLearningRepo([_action(9, action_type="fertilizer", water=5.0, suggested=100.0)])
    await execute(deps=_deps(repo), now=NOW)
    row = repo.recorded[0]
    # Water fields only apply to watering actions.
    assert row.farmer_gave_liters is None
    assert row.ai_suggested_liters is None
    assert row.water_variance_liters is None
    assert row.suggestion_accuracy is None


async def test_no_actions_is_a_noop() -> None:
    repo = _FakeLearningRepo([])
    out = await execute(deps=_deps(repo), now=NOW)
    assert out.written == 0
    assert repo.recorded == []
