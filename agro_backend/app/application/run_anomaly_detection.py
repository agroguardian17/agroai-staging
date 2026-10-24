"""Run the anomaly engine (Round-3 R3.4).

Thin orchestration mirroring ``run_diagnostics``: gather signals via the
data-source port, then evaluate them with the pure domain detector. Framework-
free (domain + ports only), so the nightly ``anomaly_scheduler`` and any future
CLI share one code path.
"""

from __future__ import annotations

import datetime as _dt

from app.application.ports.anomaly_data import AnomalyDataSource
from app.domain import anomalies
from app.domain.anomalies import AnomalyFinding


async def run_anomaly_detection(
    source: AnomalyDataSource,
    *,
    now: _dt.datetime,
    data_gap_minutes: int,
    stuck_min_readings: int,
    rule_always_rate: float,
    rule_min_samples: int,
    advisory_spike_factor: float,
    advisory_baseline_days: int,
    trace_window_days: int,
) -> list[AnomalyFinding]:
    inputs = await source.collect(
        now,
        data_gap_minutes=data_gap_minutes,
        stuck_min_readings=stuck_min_readings,
        rule_always_rate=rule_always_rate,
        rule_min_samples=rule_min_samples,
        advisory_spike_factor=advisory_spike_factor,
        advisory_baseline_days=advisory_baseline_days,
        trace_window_days=trace_window_days,
    )
    return anomalies.detect(inputs)


__all__ = ["run_anomaly_detection"]
