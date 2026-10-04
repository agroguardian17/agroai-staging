"""Assemble a :class:`PlotRunTrace` from the daily-run objects (pure).

Keeps the ginger-daily hot path to one call and makes the assembly testable.
No I/O — the caller persists the returned trace best-effort.
"""

from __future__ import annotations

import datetime as _dt
import uuid
from decimal import Decimal
from typing import Any

from app.application.ports.plot_run_trace_repo import PlotRunTrace
from app.domain import pipeline_validation as pv

# The downstream KB fields ops care about when a daily advisory looks wrong.
_DERIVED_FIELDS: tuple[str, ...] = (
    "dap",
    "current_stage",
    "previous_stage",
    "plot_status",
    "vwc_status",
    "plot_plants_estimated",
    "planting_geometry_incomplete",
    "stage_water_deficit_ratio",
    "per_plant_cumulative_vs_lifecycle_ratio",
    "days_since_last_irrigation",
    "days_since_last_flow_reading",
)
_UNKNOWN_SAMPLE = 40  # cap the stored unknown-field list


def _json(v: object) -> object:
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, uuid.UUID | _dt.date | _dt.datetime):
        return str(v)
    return v


def build_plot_run_trace(
    *,
    plot_id: str,
    season: Any,
    run_date: _dt.date,
    state: Any,
    engine_result: dict[str, Any] | None,
    advisories_written: int,
    error: str | None = None,
    now: _dt.datetime | None = None,
) -> PlotRunTrace:
    now = now or _dt.datetime.now(_dt.UTC)

    filled = len(getattr(state, "filled", ()) or ())
    unknown_set = sorted(getattr(state, "unknown", ()) or ())
    unknown = len(unknown_set)
    total = filled + unknown
    coverage_pct = (filled / total) if total else None
    coverage = {
        "filled": filled,
        "unknown": unknown,
        "total": total,
        "coverage_pct": round(coverage_pct, 3) if coverage_pct is not None else None,
        "unknown_sample": unknown_set[:_UNKNOWN_SAMPLE],
    }

    state_dict = getattr(state, "state", {}) or {}
    derived = {f: _json(state_dict.get(f)) for f in _DERIVED_FIELDS}

    er = engine_result or {}
    messages = er.get("messages", []) or []
    rule_ids = [getattr(m, "rule_id", None) for m in messages]
    engine: dict[str, Any] = {
        "messages": len(messages),
        "rule_ids": rule_ids,
        "delivery": er.get("delivery") if isinstance(er.get("delivery"), dict) else {},
        "gap_days": er.get("gap_days"),
        "state_reset": er.get("state_reset"),
    }

    stages: dict[str, Any] = {
        "s8_farm_brain": {
            "status": "fail" if error else "ok",
            "coverage_pct": coverage["coverage_pct"],
            "filled": filled,
            "unknown": unknown,
        },
        "s9_kb_engine": {
            "status": "skipped" if error else "ok",
            "rules_fired": len(messages),
        },
        "s10_advisory": {
            "status": "skipped" if error else "ok",
            "advisories_written": advisories_written,
        },
    }

    findings = pv.validate_run(
        coverage_pct=coverage_pct, advisories_written=advisories_written, error=error
    )
    return PlotRunTrace(
        trace_id=str(uuid.uuid4()),
        plot_id=plot_id,
        run_date=run_date,
        overall=pv.worst_level(findings),
        created_at=now,
        season_id=str(getattr(season, "season_id", "")) or None,
        tenant_id=str(getattr(season, "tenant_id", "")) or None,
        farm_id=str(getattr(season, "farm_id", "")) or None,
        advisories_written=advisories_written,
        coverage=coverage,
        derived=derived,
        engine=engine,
        stages=stages,
        validations=[pv.finding_to_dict(f) for f in findings],
        error=error,
    )
