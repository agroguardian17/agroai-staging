"""Assemble a :class:`PipelineTrace` from the ingest objects (pure).

Kept out of the broker so the hot-path edit is one call and the assembly is unit
testable. No I/O here — the caller persists the returned trace best-effort.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from app.application.ports.pipeline_trace_repo import PipelineTrace
from app.domain import pipeline_validation as pv

# Calibrated Reading fields worth showing next to their raw inputs.
_CALIBRATED_FIELDS: tuple[str, ...] = (
    "soil_moisture_1_pct",
    "soil_moisture_2_pct",
    "soil_moisture_avg_pct",
    "soil_temp_c",
    "soil_ph",
    "soil_ec_ms_cm",
    "soil_n_mg_kg",
    "soil_p_mg_kg",
    "soil_k_mg_kg",
    "battery_voltage_v",
    "battery_percent",
    "water_flow_lpm",
    "water_pressure_bar",
)


def _json(v: object) -> object:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, uuid.UUID):
        return str(v)
    return v


def _calibrated_snapshot(reading: Any) -> dict[str, Any]:
    return {f: _json(getattr(reading, f, None)) for f in _CALIBRATED_FIELDS}


def build_ingest_trace(
    *,
    topic: str,
    model: Any,
    reading: Any,
    result: Any,
    calibration: Any,
    now: datetime | None = None,
) -> PipelineTrace:
    """Trace for a successfully-parsed v2-raw message (persisted or duplicate)."""
    now = now or datetime.now(UTC)
    raw = model.raw_readings.model_dump()
    calibrated = _calibrated_snapshot(reading)

    reading_id = getattr(result, "reading_id", None)
    rules = getattr(result, "rules", None)
    # The broker reassigns `reading` after _normalize_clock_skew, so a changed
    # recorded_at vs the original model is how we detect a skew rewrite.
    skew_applied = getattr(model, "recorded_at", None) != getattr(reading, "recorded_at", None)

    stages: dict[str, Any] = {
        "s1_receive": {"status": "ok", "topic": topic, "schema": getattr(model, "schema_id", None)},
        "s2_validate": {"status": "ok"},
        "s3_raw": {"status": "ok"},
        "s4_calibrate": {
            "status": "ok",
            "calibration_version": getattr(calibration, "calibration_version", None),
        },
        "s5_clock_skew": {"status": "ok", "applied": bool(skew_applied)},
        "s6_persist": {"status": "inserted" if reading_id is not None else "duplicate"},
    }
    if rules is not None:
        stages["s7_rules"] = {
            "status": "ok",
            "hits": getattr(rules, "hits", 0),
            "created": getattr(rules, "created", 0),
            "cooldown_suppressed": getattr(rules, "cooldown_suppressed", 0),
        }
    else:
        stages["s7_rules"] = {"status": "skipped", "reason": "duplicate row"}

    findings = (
        pv.validate_raw(raw)
        + pv.validate_calibrated(calibrated)
        + pv.validate_recorded_at(getattr(reading, "recorded_at", None), now)
    )
    validations = [pv.finding_to_dict(f) for f in findings]

    return PipelineTrace(
        trace_id=str(uuid.uuid4()),
        topic=topic,
        overall=pv.worst_level(findings),
        created_at=now,
        schema_id=getattr(model, "schema_id", None),
        node_id=getattr(model, "node_id", None),
        plot_id=getattr(model, "plot_id", None),
        tenant_id=str(getattr(model, "tenant_id", "")) or None,
        recorded_at=getattr(reading, "recorded_at", None),
        raw_payload=raw,
        calibrated=calibrated,
        stages=stages,
        validations=validations,
        drop_reason=None,
    )


def build_drop_trace(
    *,
    topic: str,
    reason: str,
    stage: str,
    now: datetime | None = None,
    schema_id: str | None = None,
    node_id: str | None = None,
) -> PipelineTrace:
    """Trace for a message dropped before it could be persisted."""
    now = now or datetime.now(UTC)
    return PipelineTrace(
        trace_id=str(uuid.uuid4()),
        topic=topic,
        overall=pv.FAIL,
        created_at=now,
        schema_id=schema_id,
        node_id=node_id,
        stages={stage: {"status": "fail", "reason": reason}},
        validations=[],
        drop_reason=reason,
    )
