"""Pure unit tests for the anomaly detector (no DB)."""

from __future__ import annotations

from datetime import UTC, datetime

from app.domain import anomalies
from app.domain.anomalies import (
    ANOMALY_ADVISORY_VOLUME,
    ANOMALY_DATA_GAP,
    ANOMALY_RULE_FIRE_RATE,
    ANOMALY_STUCK_SENSOR,
    SEVERITY_CRITICAL,
    SEVERITY_WARN,
    AnomalyFinding,
    AnomalyInputs,
    DeviceGap,
    RuleFireRate,
    StuckSensor,
)

NOW = datetime(2026, 10, 24, 12, 0, tzinfo=UTC)


def _by_type(findings: list[AnomalyFinding]) -> dict[str, AnomalyFinding]:
    return {f.anomaly_type: f for f in findings}


def test_no_signals_is_all_clear() -> None:
    assert anomalies.detect(AnomalyInputs(now=NOW)) == []
    assert anomalies.worst_severity([]) == "ok"


def test_data_gap_warn_and_critical() -> None:
    # 4h silent with a 3h threshold → warn; >1 day past threshold → critical.
    warn = anomalies.detect(
        AnomalyInputs(now=NOW, data_gap_minutes=180, device_gaps=[DeviceGap("N1", 240)])
    )
    assert _by_type(warn)[ANOMALY_DATA_GAP].severity == SEVERITY_WARN
    assert _by_type(warn)[ANOMALY_DATA_GAP].entity_id == "N1"

    crit = anomalies.detect(
        AnomalyInputs(now=NOW, data_gap_minutes=180, device_gaps=[DeviceGap("N1", 180 + 25 * 60)])
    )
    assert _by_type(crit)[ANOMALY_DATA_GAP].severity == SEVERITY_CRITICAL


def test_data_gap_within_threshold_is_silent() -> None:
    out = anomalies.detect(
        AnomalyInputs(now=NOW, data_gap_minutes=180, device_gaps=[DeviceGap("N1", 60)])
    )
    assert out == []


def test_stuck_sensor_needs_min_readings() -> None:
    enough = anomalies.detect(
        AnomalyInputs(
            now=NOW,
            stuck_min_readings=12,
            stuck_sensors=[StuckSensor("N1", "soil_ph", "6.5", 12)],
        )
    )
    assert _by_type(enough)[ANOMALY_STUCK_SENSOR].entity_id == "N1"
    assert "soil_ph" in _by_type(enough)[ANOMALY_STUCK_SENSOR].observed

    too_few = anomalies.detect(
        AnomalyInputs(
            now=NOW,
            stuck_min_readings=12,
            stuck_sensors=[StuckSensor("N1", "soil_ph", "6.5", 5)],
        )
    )
    assert too_few == []


def test_rule_fire_rate_flags_runaway_rule_only() -> None:
    runaway = anomalies.detect(
        AnomalyInputs(
            now=NOW,
            rule_always_rate=0.95,
            rule_min_samples=20,
            rule_fire_rates=[RuleFireRate("low_water", samples=50, fires=50)],
        )
    )
    assert _by_type(runaway)[ANOMALY_RULE_FIRE_RATE].entity_id == "low_water"

    # A normal rule (fires sometimes) and an under-sampled one are both silent.
    quiet = anomalies.detect(
        AnomalyInputs(
            now=NOW,
            rule_always_rate=0.95,
            rule_min_samples=20,
            rule_fire_rates=[
                RuleFireRate("frost", samples=50, fires=2),
                RuleFireRate("new_rule", samples=5, fires=5),  # too few samples
            ],
        )
    )
    assert quiet == []


def test_advisory_volume_spike_and_drop() -> None:
    spike = anomalies.detect(
        AnomalyInputs(
            now=NOW, advisory_spike_factor=3.0, advisory_today=20, advisory_baseline_avg=4.0
        )
    )
    assert _by_type(spike)[ANOMALY_ADVISORY_VOLUME].severity == SEVERITY_WARN

    drop = anomalies.detect(AnomalyInputs(now=NOW, advisory_today=0, advisory_baseline_avg=5.0))
    assert "dried up" in _by_type(drop)[ANOMALY_ADVISORY_VOLUME].detail

    # Normal day near baseline → nothing; missing baseline → nothing.
    assert (
        anomalies.detect(AnomalyInputs(now=NOW, advisory_today=5, advisory_baseline_avg=4.0)) == []
    )
    assert (
        anomalies.detect(AnomalyInputs(now=NOW, advisory_today=0, advisory_baseline_avg=None)) == []
    )


def test_summarize_and_worst_severity() -> None:
    findings = anomalies.detect(
        AnomalyInputs(
            now=NOW,
            data_gap_minutes=180,
            device_gaps=[DeviceGap("N1", 180 + 25 * 60)],  # critical
            stuck_min_readings=12,
            stuck_sensors=[StuckSensor("N1", "soil_ph", "6.5", 12)],  # warn
        )
    )
    counts = anomalies.summarize(findings)
    assert set(counts) == {"info", "warn", "critical"}
    assert counts["critical"] == 1 and counts["warn"] == 1
    assert anomalies.worst_severity(findings) == SEVERITY_CRITICAL
