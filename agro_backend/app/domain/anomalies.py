"""Pure anomaly detector (Round-3 observability, R3.4).

Where the diagnostics battery answers "is the pipeline alive and are the
invariants intact?", the anomaly engine answers the sharper question the pilot
kept asking by hand: "is anything *off* that the system should point out
itself?" — a device that stopped reporting (the 18-Oct outage would have shown
as a ``data_gap`` immediately), a sensor stuck on one value, a rule that fires
on almost every reading (a mis-set threshold), or the advisory volume spiking
or drying up.

Same shape as :mod:`app.domain.diagnostics`: the *logic* is here as pure
functions over gathered inputs (stdlib only, no I/O), the SQL lives in
``app/infra/anomaly`` and the orchestration in
``app/application/run_anomaly_detection``. Unlike diagnostics, a finding only
exists when something is wrong — an empty result list means "nothing anomalous".

Severity convention: ``critical`` for a hard outage/clearly-broken signal,
``warn`` for a strong smell worth a human look, ``info`` for a mild deviation.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field

SEVERITY_INFO = "info"
SEVERITY_WARN = "warn"
SEVERITY_CRITICAL = "critical"
_SEVERITY_RANK = {SEVERITY_INFO: 0, SEVERITY_WARN: 1, SEVERITY_CRITICAL: 2}

ANOMALY_DATA_GAP = "data_gap"
ANOMALY_STUCK_SENSOR = "stuck_sensor"
ANOMALY_RULE_FIRE_RATE = "rule_fire_rate"
ANOMALY_ADVISORY_VOLUME = "advisory_volume"

ENTITY_DEVICE = "device"
ENTITY_RULE = "rule"
ENTITY_SYSTEM = "system"


@dataclass(frozen=True)
class AnomalyFinding:
    """One thing the system flagged as off, with the offending entity id."""

    anomaly_type: str
    severity: str  # info | warn | critical
    entity_type: str  # device | rule | system
    entity_id: str | None = None
    observed: str | None = None
    expected: str | None = None
    detail: str | None = None


# --- gathered signals (populated best-effort by the collector) --------------
@dataclass(frozen=True)
class DeviceGap:
    device_id: str
    minutes_since_last: float


@dataclass(frozen=True)
class StuckSensor:
    device_id: str
    field: str
    value: str
    n_readings: int


@dataclass(frozen=True)
class RuleFireRate:
    rule_id: str
    samples: int
    fires: int


@dataclass(frozen=True)
class AnomalyInputs:
    """Plain data gathered by the collector; evaluated here with no I/O."""

    now: _dt.datetime
    # thresholds (overridable from Settings)
    data_gap_minutes: int = 180
    stuck_min_readings: int = 12
    rule_always_rate: float = 0.95
    rule_min_samples: int = 20
    advisory_spike_factor: float = 3.0
    # signals
    device_gaps: list[DeviceGap] = field(default_factory=list)
    stuck_sensors: list[StuckSensor] = field(default_factory=list)
    rule_fire_rates: list[RuleFireRate] = field(default_factory=list)
    advisory_today: int | None = None
    advisory_baseline_avg: float | None = None


def detect(inp: AnomalyInputs) -> list[AnomalyFinding]:
    """Turn gathered signals into a list of findings (pure). Empty = all clear."""
    findings: list[AnomalyFinding] = []
    findings += _detect_data_gaps(inp)
    findings += _detect_stuck_sensors(inp)
    findings += _detect_rule_fire_rates(inp)
    findings += _detect_advisory_volume(inp)
    return findings


def _detect_data_gaps(inp: AnomalyInputs) -> list[AnomalyFinding]:
    out: list[AnomalyFinding] = []
    for gap in inp.device_gaps:
        if gap.minutes_since_last <= inp.data_gap_minutes:
            continue
        # A gap over a full day past the threshold is a hard outage, not a blip.
        severity = (
            SEVERITY_CRITICAL
            if gap.minutes_since_last >= inp.data_gap_minutes + 24 * 60
            else SEVERITY_WARN
        )
        out.append(
            AnomalyFinding(
                anomaly_type=ANOMALY_DATA_GAP,
                severity=severity,
                entity_type=ENTITY_DEVICE,
                entity_id=gap.device_id,
                observed=f"{gap.minutes_since_last / 60:.1f}h since last reading",
                expected=f"<= {inp.data_gap_minutes / 60:.1f}h",
                detail="device stopped reporting — check 4G/power/antenna in the field",
            )
        )
    return out


def _detect_stuck_sensors(inp: AnomalyInputs) -> list[AnomalyFinding]:
    out: list[AnomalyFinding] = []
    for s in inp.stuck_sensors:
        if s.n_readings < inp.stuck_min_readings:
            continue
        out.append(
            AnomalyFinding(
                anomaly_type=ANOMALY_STUCK_SENSOR,
                severity=SEVERITY_WARN,
                entity_type=ENTITY_DEVICE,
                entity_id=s.device_id,
                observed=f"{s.field}={s.value} for {s.n_readings} readings",
                expected="some variation between consecutive readings",
                detail=f"{s.field} may be stuck/disconnected",
            )
        )
    return out


def _detect_rule_fire_rates(inp: AnomalyInputs) -> list[AnomalyFinding]:
    out: list[AnomalyFinding] = []
    for r in inp.rule_fire_rates:
        if r.samples < inp.rule_min_samples:
            continue
        rate = r.fires / r.samples if r.samples else 0.0
        if rate < inp.rule_always_rate:
            continue
        out.append(
            AnomalyFinding(
                anomaly_type=ANOMALY_RULE_FIRE_RATE,
                severity=SEVERITY_WARN,
                entity_type=ENTITY_RULE,
                entity_id=r.rule_id,
                observed=f"fired on {r.fires}/{r.samples} readings ({rate:.0%})",
                expected=f"< {inp.rule_always_rate:.0%} of readings",
                detail="a rule firing on nearly every reading usually means a mis-set threshold",
            )
        )
    return out


def _detect_advisory_volume(inp: AnomalyInputs) -> list[AnomalyFinding]:
    if inp.advisory_today is None or inp.advisory_baseline_avg is None:
        return []
    today = inp.advisory_today
    baseline = inp.advisory_baseline_avg
    # Drop: a steady advisory stream suddenly produced nothing today.
    if baseline >= 1.0 and today == 0:
        return [
            AnomalyFinding(
                anomaly_type=ANOMALY_ADVISORY_VOLUME,
                severity=SEVERITY_WARN,
                entity_type=ENTITY_SYSTEM,
                observed="0 advisories today",
                expected=f"~{baseline:.1f}/day (trailing baseline)",
                detail="advisory volume dried up — is the ginger job or compose step failing?",
            )
        ]
    # Spike: well above the trailing baseline (and not just noise around a tiny one).
    if baseline >= 1.0 and today > baseline * inp.advisory_spike_factor:
        return [
            AnomalyFinding(
                anomaly_type=ANOMALY_ADVISORY_VOLUME,
                severity=SEVERITY_WARN,
                entity_type=ENTITY_SYSTEM,
                observed=f"{today} advisories today",
                expected=f"~{baseline:.1f}/day (trailing baseline)",
                detail=f"{today / baseline:.1f}x the baseline — possible duplicate/loop or a real event",
            )
        ]
    return []


def summarize(findings: list[AnomalyFinding]) -> dict[str, int]:
    """Count findings by severity; always returns all three keys."""
    counts = dict.fromkeys((SEVERITY_INFO, SEVERITY_WARN, SEVERITY_CRITICAL), 0)
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts


def worst_severity(findings: list[AnomalyFinding]) -> str:
    """Highest severity present; 'ok' when there are no findings."""
    if not findings:
        return "ok"
    return max(findings, key=lambda f: _SEVERITY_RANK.get(f.severity, 0)).severity


__all__ = [
    "ANOMALY_ADVISORY_VOLUME",
    "ANOMALY_DATA_GAP",
    "ANOMALY_RULE_FIRE_RATE",
    "ANOMALY_STUCK_SENSOR",
    "ENTITY_DEVICE",
    "ENTITY_RULE",
    "ENTITY_SYSTEM",
    "SEVERITY_CRITICAL",
    "SEVERITY_INFO",
    "SEVERITY_WARN",
    "AnomalyFinding",
    "AnomalyInputs",
    "DeviceGap",
    "RuleFireRate",
    "StuckSensor",
    "detect",
    "summarize",
    "worst_severity",
]
