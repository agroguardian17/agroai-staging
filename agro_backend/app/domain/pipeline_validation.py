"""Plausibility / invariant checks for the ingest pipeline (pure).

Produces a per-field checklist — the "is this stage correct?" layer behind the
Pipeline Inspector. Reused by the live tracer (``build_pipeline_trace``) and the
self-test harness, so it must stay framework-free (stdlib + Decimal only, per the
domain-purity gate).

Each check returns a :class:`Finding` with a ``level``:
* ``ok``   — within the expected range (not emitted; absence == pass).
* ``warn`` — suspicious but not necessarily wrong (e.g. NPK read failed, so the
  NPK fields are null by design; flow uncomputable on the first cycle).
* ``fail`` — physically impossible / inconsistent (e.g. soil moisture > 100%).

Only ``warn``/``fail`` findings are returned; an empty list means the stage
passed every check.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

OK = "ok"
WARN = "warn"
FAIL = "fail"

# Allowed clock drift into the future before we flag a timestamp (the broker's
# clock-skew net handles the extremes; this catches mild future times).
_FUTURE_TOLERANCE = timedelta(minutes=10)


@dataclass(frozen=True)
class Finding:
    stage: str
    field: str
    value: object
    check: str
    level: str
    msg: str


def _num(value: object) -> Decimal | None:
    """Coerce to Decimal for comparison; None/non-numeric -> None (skip)."""
    if value is None or isinstance(value, bool):
        return None
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _range(
    stage: str, field: str, value: object, lo: float, hi: float, *, level: str = FAIL
) -> Finding | None:
    v = _num(value)
    if v is None:
        return None
    if Decimal(str(lo)) <= v <= Decimal(str(hi)):
        return None
    return Finding(
        stage, field, value, f"{lo}..{hi}", level, f"{field}={value} outside [{lo}, {hi}]"
    )


def validate_raw(raw: dict[str, object]) -> list[Finding]:
    """Checks on the pre-calibration ``raw_readings`` block."""
    out: list[Finding] = []
    for f in ("soil_adc", "battery_adc", "pressure_adc"):
        hit = _range("raw", f, raw.get(f), 0, 1023)
        if hit:
            out.append(hit)
    for f in ("flow_pulses_window", "flow_pulses_total"):
        hit = _range("raw", f, raw.get(f), 0, 10_000_000)
        if hit:
            out.append(hit)
    window_s = raw.get("window_s")
    if window_s is not None and _num(window_s) == 0:
        out.append(
            Finding(
                "raw",
                "window_s",
                window_s,
                ">0",
                WARN,
                "window_s=0 (first cycle) → water_flow_lpm cannot be computed",
            )
        )
    if raw.get("npk_ok") is False:
        out.append(
            Finding(
                "raw", "npk_ok", False, "true", WARN, "NPK read failed → NPK fields will be null"
            )
        )
    fault = raw.get("fault_flags")
    if fault:
        out.append(
            Finding("raw", "fault_flags", fault, "empty", WARN, f"device fault flags: {fault}")
        )
    return out


def validate_calibrated(cal: dict[str, object]) -> list[Finding]:
    """Checks on the post-calibration engineering values."""
    out: list[Finding] = []
    checks: list[tuple[str, float, float, str]] = [
        ("soil_moisture_1_pct", 0, 100, FAIL),
        ("soil_moisture_2_pct", 0, 100, FAIL),
        ("soil_moisture_avg_pct", 0, 100, FAIL),
        ("soil_temp_c", -10, 60, WARN),
        ("water_flow_lpm", 0, 100_000, FAIL),
        ("water_pressure_bar", 0, 20, FAIL),
        ("battery_voltage_v", 0, 20, FAIL),
        ("battery_percent", 0, 100, FAIL),
        ("soil_ph", 0, 14, FAIL),
        ("soil_ec_ms_cm", 0, 50, WARN),
        ("soil_n_mg_kg", 0, 3000, WARN),
        ("soil_p_mg_kg", 0, 3000, WARN),
        ("soil_k_mg_kg", 0, 3000, WARN),
    ]
    for field, lo, hi, level in checks:
        hit = _range("calibrate", field, cal.get(field), lo, hi, level=level)
        if hit:
            out.append(hit)
    return out


def validate_recorded_at(recorded_at: datetime | None, now: datetime) -> list[Finding]:
    """A reading timestamp should not be in the future (beyond small drift)."""
    if recorded_at is None:
        return []
    if recorded_at > now + _FUTURE_TOLERANCE:
        return [
            Finding(
                "clock",
                "recorded_at",
                recorded_at.isoformat(),
                f"<= now+{_FUTURE_TOLERANCE}",
                FAIL,
                f"recorded_at {recorded_at.isoformat()} is in the future",
            )
        ]
    return []


def worst_level(findings: list[Finding]) -> str:
    """Roll a list of findings up to a single overall level."""
    if any(f.level == FAIL for f in findings):
        return FAIL
    if any(f.level == WARN for f in findings):
        return WARN
    return OK


def finding_to_dict(f: Finding) -> dict[str, object]:
    return {
        "stage": f.stage,
        "field": f.field,
        "value": f.value,
        "check": f.check,
        "level": f.level,
        "msg": f.msg,
    }
