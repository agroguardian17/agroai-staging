"""Unit test for run_anomaly_detection orchestration with a fake data source."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.run_anomaly_detection import run_anomaly_detection
from app.domain.anomalies import ANOMALY_DATA_GAP, AnomalyInputs, DeviceGap

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


class _FakeSource:
    def __init__(self, inputs: AnomalyInputs) -> None:
        self._inputs = inputs
        self.called_with: dict[str, object] = {}

    async def collect(self, now: datetime, **kwargs: object) -> AnomalyInputs:
        self.called_with = {"now": now, **kwargs}
        return self._inputs


async def test_run_anomaly_detection_forwards_params_then_detects() -> None:
    source = _FakeSource(
        AnomalyInputs(now=NOW, data_gap_minutes=180, device_gaps=[DeviceGap("N1", 600)])
    )
    findings = await run_anomaly_detection(
        source,
        now=NOW,
        data_gap_minutes=180,
        stuck_min_readings=12,
        rule_always_rate=0.95,
        rule_min_samples=20,
        advisory_spike_factor=3.0,
        advisory_baseline_days=14,
        trace_window_days=7,
    )
    # thresholds were forwarded to the source
    assert source.called_with["data_gap_minutes"] == 180
    assert source.called_with["trace_window_days"] == 7
    # and the gathered signal produced a finding
    assert [f.anomaly_type for f in findings] == [ANOMALY_DATA_GAP]
