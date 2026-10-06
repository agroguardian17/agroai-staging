"""Unit tests for CropSeasonView.days_after_planting (the authoritative dap).

Guards the fix for the "crop_age_days frozen at 50" bug: crop age must be
recomputed from sowing_date, never read from the static crop_age_days_today
snapshot column.
"""

from __future__ import annotations

import datetime
import uuid

from app.application.ports.crop_season_repo import CropSeasonView


def _season(sowing: datetime.date, *, crop_age_days_today: int | None = 50) -> CropSeasonView:
    return CropSeasonView(
        season_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        farm_id=uuid.uuid4(),
        plot_id="PLOT_TEST_001",
        crop_name_english="Ginger",
        crop_name_marathi="आले",
        crop_category="cash_crop",
        crop_variety="Mahima",
        sowing_date=sowing,
        expected_harvest_date=sowing + datetime.timedelta(days=240),
        current_growth_stage="vegetative",
        crop_age_days_today=crop_age_days_today,
    )


def test_days_after_planting_ignores_stale_snapshot() -> None:
    # Stale snapshot says 50; the real age from sowing_date is 128.
    season = _season(datetime.date(2026, 6, 1), crop_age_days_today=50)
    assert season.days_after_planting(datetime.date(2026, 10, 7)) == 128


def test_days_after_planting_on_sowing_day_is_zero() -> None:
    season = _season(datetime.date(2026, 6, 1))
    assert season.days_after_planting(datetime.date(2026, 6, 1)) == 0


def test_days_after_planting_before_sowing_is_negative() -> None:
    season = _season(datetime.date(2026, 6, 1))
    assert season.days_after_planting(datetime.date(2026, 5, 30)) == -2
