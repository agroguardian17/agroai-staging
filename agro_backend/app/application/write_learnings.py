"""Use case: materialize ai_learning_log rows from farmer actions.

For each farmer_action that references an advisory but has not yet been turned
into a learning row, compute the immediately-knowable comparison (advised vs
actual watering + an accuracy band) and persist it. The time-delayed outcome
fields (NDVI/moisture deltas) are left NULL for a later backfill.

PURE w.r.t. imports: stdlib + ports only. No infra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.application.ports.learning_repo import ActionOutcome, LearningRepo, LearningRow


@dataclass(frozen=True, slots=True)
class WriteLearningsDeps:
    learning_repo: LearningRepo
    batch_limit: int = 200


@dataclass(frozen=True, slots=True)
class WriteLearningsResult:
    written: int


def _accuracy(suggested: float | None, actual: float | None) -> str | None:
    """Classify how close the farmer's watering was to the advice.

    Bands match the ai_learning_log.suggestion_accuracy CHECK:
    good / slight_over / slight_under / poor. None when we can't compare.
    """
    if suggested is None or actual is None or suggested <= 0:
        return None
    ratio = (actual - suggested) / suggested
    if abs(ratio) <= 0.10:
        return "good"
    if 0.10 < ratio <= 0.30:
        return "slight_over"
    if -0.30 <= ratio < -0.10:
        return "slight_under"
    return "poor"


def _to_row(a: ActionOutcome, now: datetime) -> LearningRow:
    # Water comparison only makes sense for a watering action.
    gave = a.water_liters if a.action_type == "watering" else None
    suggested = a.ai_suggested_liters if a.action_type == "watering" else None
    variance = None if (gave is None or suggested is None) else round(gave - suggested, 3)
    return LearningRow(
        tenant_id=a.tenant_id,
        farmer_id=a.farmer_id,
        season_id=a.season_id,
        suggestion_id=a.suggestion_id,
        action_id=a.action_id,
        learning_date=a.action_date,
        suggestion_type=a.suggestion_type,
        ai_suggested_liters=suggested,
        farmer_gave_liters=gave,
        water_variance_liters=variance,
        suggestion_accuracy=_accuracy(suggested, gave),
        crop_stage=a.crop_stage,
        soil_type=a.soil_type,
        learning_applied_at=now,
    )


async def execute(*, deps: WriteLearningsDeps, now: datetime) -> WriteLearningsResult:
    actions = await deps.learning_repo.list_unlearned_actions(deps.batch_limit)
    written = 0
    for action in actions:
        await deps.learning_repo.record(_to_row(action, now))
        written += 1
    return WriteLearningsResult(written=written)


__all__ = ["WriteLearningsDeps", "WriteLearningsResult", "execute"]
