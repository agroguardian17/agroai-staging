"""Event Timeline — every pipeline event in one chronological stream (R3.2).

One page that merges ingest traces, device/KB alerts, advisories composed,
notifications delivered, job ticks, diagnostics results and anomaly findings —
filterable by kind / entity / time, each row carrying its source table + id so
you can drill into the originating record (e.g. a trace_id on the Reading
Journey, an alert_id on the Advisory pages). Backed by the read-only
`event_timeline` UNION view (migration 0072); pure read, no hot-path writes.
"""

from __future__ import annotations

from typing import Any

import db
import streamlit as st


def render() -> None:
    _KIND_ICON = {
        "ingest": "📥",
        "alert": "🔔",
        "advisory": "🌱",
        "notification": "📤",
        "job": "⚙️",
        "diagnostic": "🩺",
        "anomaly": "🚨",
    }
    _LEVEL_ICON = {
        "ok": "✅",
        "warn": "⚠️",
        "warning": "⚠️",
        "fail": "❌",
        "error": "❌",
        "critical": "🔴",
        "info": "🔵",
        "skip": "⚪",
        "sent": "✅",
        "composed": "📝",
        "success": "✅",
    }
    _ALL_KINDS = ["ingest", "alert", "advisory", "notification", "job", "diagnostic", "anomaly"]

    st.title("🧵 Event Timeline")
    st.caption(
        "Every pipeline event in one place. Backed by the `event_timeline` view (migration 0072)."
    )

    c1, c2, c3 = st.columns([2, 1, 1])
    kinds = c1.multiselect("Event kinds", _ALL_KINDS, default=_ALL_KINDS)
    hours = c2.selectbox(
        "Window", [6, 24, 72, 168, 720], index=1, format_func=lambda h: f"last {h}h"
    )
    entity_q = c3.text_input("Entity contains", placeholder="plot / node / device id")

    if not kinds:
        st.info("Pick at least one event kind.")
        return

    where = ["ts >= now() - make_interval(hours => :h)", "event_kind = ANY(:kinds)"]
    params: dict[str, Any] = {"h": int(hours), "kinds": kinds}
    if entity_q.strip():
        where.append("entity ILIKE :eq")
        params["eq"] = f"%{entity_q.strip()}%"

    try:
        rows = db.df(
            "SELECT ts, event_kind, event_type, level, entity, summary, source_table, source_id "
            f"FROM event_timeline WHERE {' AND '.join(where)} ORDER BY ts DESC LIMIT 500",
            params,
        )
    except Exception as exc:
        st.warning(
            f"Could not read `event_timeline`. Is migration 0072 applied?\n\n`{str(exc)[:200]}`"
        )
        return

    if rows.empty:
        st.info("No events match these filters in this window.")
        return

    # summary counts by kind
    counts = rows["event_kind"].value_counts().to_dict()
    cols = st.columns(len(_ALL_KINDS))
    for col, k in zip(cols, _ALL_KINDS, strict=False):
        col.metric(f"{_KIND_ICON.get(k, '')} {k}", counts.get(k, 0))

    view = rows.copy()
    view.insert(0, "when", view["ts"])
    view["kind"] = view["event_kind"].map(lambda k: f"{_KIND_ICON.get(k, '')} {k}")
    view["level"] = view["level"].map(
        lambda v: f"{_LEVEL_ICON.get(str(v).lower(), '')} {v}" if v else ""
    )
    view = view[
        ["when", "kind", "event_type", "level", "entity", "summary", "source_table", "source_id"]
    ]
    st.dataframe(view, use_container_width=True, hide_index=True)
    st.caption(
        "Drill-in: a `pipeline_trace` source_id is the trace_id on the Reading Journey (page 22); "
        "an `alerts_notifications` id joins the Advisory pages; `anomaly_finding` → page 23."
    )
