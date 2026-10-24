"""Port for the anomaly detector's data source (Round-3 R3.4).

The nightly anomaly engine needs gathered signals from the DB (per-device
reading gaps, stuck-sensor runs, per-rule fire rates from the pipeline traces,
and advisory volume vs a trailing baseline). That gathering is infra (SQL); the
orchestration (`run_anomaly_detection`) depends on this Protocol so it stays
framework-free and testable with a fake source.
"""

from __future__ import annotations

import datetime as _dt
from typing import Protocol, runtime_checkable

from app.domain.anomalies import AnomalyInputs


@runtime_checkable
class AnomalyDataSource(Protocol):
    async def collect(
        self,
        now: _dt.datetime,
        *,
        data_gap_minutes: int,
        stuck_min_readings: int,
        rule_always_rate: float,
        rule_min_samples: int,
        advisory_spike_factor: float,
        advisory_baseline_days: int,
        trace_window_days: int,
    ) -> AnomalyInputs:
        """Gather observed signals into a pure :class:`AnomalyInputs`.

        Each probe is best-effort: a failed query leaves its signal empty/``None``
        so the corresponding detector simply emits no finding rather than crashing.
        """
        ...
