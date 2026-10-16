"""Unit test for run_diagnostics orchestration with a fake data source."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.run_diagnostics import run_diagnostics
from app.domain.diagnostics import DiagnosticsInputs

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)


class _FakeSource:
    def __init__(self, inputs: DiagnosticsInputs) -> None:
        self._inputs = inputs
        self.called_with: dict[str, object] = {}

    async def collect(
        self,
        now: datetime,
        *,
        readings_max_age_hours: int,
        satellite_enabled: bool,
        satellite_max_age_days: int,
    ) -> DiagnosticsInputs:
        self.called_with = {
            "now": now,
            "readings_max_age_hours": readings_max_age_hours,
            "satellite_enabled": satellite_enabled,
            "satellite_max_age_days": satellite_max_age_days,
        }
        return self._inputs


async def test_run_diagnostics_collects_then_evaluates() -> None:
    source = _FakeSource(DiagnosticsInputs(now=NOW, latest_reading_at=None))
    results = await run_diagnostics(
        source,
        now=NOW,
        readings_max_age_hours=6,
        satellite_enabled=False,
        satellite_max_age_days=14,
    )
    # thresholds were forwarded to the source
    assert source.called_with["readings_max_age_hours"] == 6
    assert source.called_with["satellite_enabled"] is False
    # and the domain evaluation ran over the gathered inputs
    by_id = {r.check_id: r for r in results}
    assert by_id["readings_fresh"].status == "fail"
    assert by_id["satellite_fresh"].status == "skip"
