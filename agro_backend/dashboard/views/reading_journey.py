"""Reading Journey — everything that happened to one reading, start to finish.

Pick a device (and optionally a specific reading) and see a single timeline:
raw payload → calibration (raw↔units) → validations → persistence → each of the
7 device-rule evaluations (fired? suppressed? which alert?) → the events the
pipeline emitted → the alerts it created. This is the "see and verify what the
system did with this reading" view (Round-3 R3.1).

Backed by the same `pipeline_trace` rows as the Pipeline Inspector (page 14);
needs `PIPELINE_TRACE_ENABLED=true`. The per-rule detail and events live in the
`s7_rules` / `s6_persist` stages the broker records best-effort. Read-only.
"""

from __future__ import annotations

import json
from typing import Any

import db
import pandas as pd
import streamlit as st


def render() -> None:
    _LEVEL_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌"}
    _PERSIST_ICON = {"inserted": "✅ inserted", "duplicate": "⚪ duplicate (re-send)"}

    st.title("🧭 Reading Journey")
    st.caption(
        "One reading, end to end: raw → calibrate → validate → persist → rules → events → alerts. "
        "Needs `PIPELINE_TRACE_ENABLED=true`."
    )

    def _obj(v: Any) -> Any:
        """JSONB may arrive as a dict/list or as text depending on the driver."""
        if isinstance(v, dict | list):
            return v
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except ValueError:
                return {}
        return {} if v is None else v

    try:
        nodes_df = db.df(
            "SELECT DISTINCT node_id FROM pipeline_trace "
            "WHERE node_id IS NOT NULL AND drop_reason IS NULL ORDER BY node_id"
        )
    except Exception as exc:  # table missing / DB down
        st.warning(
            "Could not read `pipeline_trace`. Is the migration applied and "
            f"`PIPELINE_TRACE_ENABLED` on?\n\n`{str(exc)[:200]}`"
        )
        return

    c1, c2 = st.columns([2, 1])
    node = c1.selectbox("Device", ["(all)", *nodes_df["node_id"].tolist()])
    hours = c2.selectbox("Window", [6, 24, 72, 168], index=1, format_func=lambda h: f"last {h}h")

    where = ["created_at >= now() - make_interval(hours => :h)", "drop_reason IS NULL"]
    params: dict[str, Any] = {"h": int(hours)}
    if node != "(all)":
        where.append("node_id = :n")
        params["n"] = node

    rows = db.df(
        "SELECT trace_id, created_at, node_id, plot_id, recorded_at, overall, "
        "stages, raw_payload, calibrated, validations FROM pipeline_trace "
        f"WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200",
        params,
    )

    if rows.empty:
        st.info(
            "No readings in this window. Confirm the device is sending v2-raw and the flag is on."
        )
        return

    def _rule_badge(stages: dict[str, Any]) -> str:
        s7 = stages.get("s7_rules", {}) if isinstance(stages, dict) else {}
        if s7.get("status") == "skipped":
            return "— (duplicate)"
        created = s7.get("created", 0)
        suppressed = s7.get("cooldown_suppressed", 0)
        if created:
            return f"🔔 {created} alert(s)"
        if suppressed:
            return f"🔕 {suppressed} suppressed"
        return "✅ no alert"

    picker = rows[["created_at", "node_id", "plot_id", "overall"]].copy()
    picker["rules"] = rows["stages"].apply(lambda s: _rule_badge(_obj(s)))
    picker.insert(0, "#", range(len(picker)))
    st.dataframe(picker, use_container_width=True, hide_index=True)

    idx = st.number_input(
        "Inspect reading # (0 = most recent)",
        min_value=0,
        max_value=len(rows) - 1,
        value=0,
        step=1,
    )
    row = rows.iloc[int(idx)]
    stages = _obj(row["stages"])

    st.divider()
    st.subheader(
        f"{row['node_id']} · plot {row['plot_id']} · recorded {row['recorded_at']} "
        f"· {_LEVEL_ICON.get(row['overall'], '')} {row['overall'].upper()}"
    )

    # --- 1. raw → calibrated ----------------------------------------------------
    st.markdown("### 1 · Raw payload → 2 · Calibration (raw ↔ units)")
    rc1, rc2 = st.columns(2)
    raw = _obj(row["raw_payload"])
    cal = _obj(row["calibrated"])
    with rc1:
        st.caption("raw_readings (as received from the device)")
        st.dataframe(
            pd.DataFrame(sorted(raw.items()), columns=["field", "raw value"]),
            use_container_width=True,
            hide_index=True,
        )
    with rc2:
        cv = (
            stages.get("s4_calibrate", {}).get("calibration_version")
            if isinstance(stages, dict)
            else None
        )
        st.caption(f"calibrated engineering values (calibration v{cv})")
        st.dataframe(
            pd.DataFrame(sorted(cal.items()), columns=["field", "calibrated value"]),
            use_container_width=True,
            hide_index=True,
        )

    # --- 3. validations ---------------------------------------------------------
    st.markdown("### 3 · Validation checklist")
    findings = _obj(row["validations"])
    if findings:
        st.dataframe(pd.DataFrame(findings), use_container_width=True, hide_index=True)
    else:
        st.success("All plausibility checks passed.")

    # --- 4. persistence ---------------------------------------------------------
    st.markdown("### 4 · Persistence")
    persist = stages.get("s6_persist", {}) if isinstance(stages, dict) else {}
    pstatus = persist.get("status")
    if pstatus == "duplicate":
        st.info(
            f"{_PERSIST_ICON.get('duplicate')} — this (node, second) was already stored; "
            "rule evaluation was **skipped** so no duplicate alerts fire."
        )
    else:
        st.success(_PERSIST_ICON.get(pstatus, pstatus or "n/a"))
    skew = stages.get("s5_clock_skew", {}) if isinstance(stages, dict) else {}
    if skew.get("applied"):
        st.warning("⏱️ Clock-skew correction was applied — the device timestamp was implausible.")

    # --- 5. device-rule evaluations --------------------------------------------
    st.markdown("### 5 · Device-rule evaluations (all 7 rules)")
    s7 = stages.get("s7_rules", {}) if isinstance(stages, dict) else {}
    if s7.get("status") == "skipped":
        st.caption("Rules skipped — duplicate reading.")
    else:
        evals = s7.get("evaluations", [])
        if evals:
            edf = pd.DataFrame(evals)

            # Friendly verdict column up front.
            def _verdict(r: pd.Series) -> str:
                if not r.get("fired"):
                    return "·  did not fire"
                if r.get("cooldown_suppressed"):
                    return "🔕 fired — suppressed (cooldown)"
                if r.get("alert_id") is not None:
                    return f"🔔 fired — alert #{int(r['alert_id'])}"
                return "fired"

            edf["verdict"] = edf.apply(_verdict, axis=1)
            cols = ["rule_id", "verdict", "value", "threshold", "severity", "alert_type"]
            edf = edf[[c for c in cols if c in edf.columns]]
            st.dataframe(edf, use_container_width=True, hide_index=True)
            m1, m2, m3 = st.columns(3)
            m1.metric("Fired", s7.get("hits", 0))
            m2.metric("Alerts created", s7.get("created", 0))
            m3.metric("Suppressed (cooldown)", s7.get("cooldown_suppressed", 0))
        else:
            st.caption(
                "No per-rule detail on this trace (recorded before R3.1, or counts only): "
                f"hits={s7.get('hits', 0)}, created={s7.get('created', 0)}, "
                f"suppressed={s7.get('cooldown_suppressed', 0)}."
            )

    # --- 6. events fired --------------------------------------------------------
    st.markdown("### 6 · Events fired")
    events: list[Any] = []
    if persist.get("events"):
        events += [{"event": e, "detail": ""} for e in persist["events"]]
    for ev in s7.get("events", []) if isinstance(s7, dict) else []:
        events.append(
            {
                "event": ev.get("event"),
                "detail": f"alert #{ev.get('alert_id')} ({ev.get('alert_type')})",
            }
        )
    if events:
        st.dataframe(pd.DataFrame(events), use_container_width=True, hide_index=True)
    else:
        st.caption("No events emitted for this reading.")

    # --- 7. alerts created (joined for message/severity) ------------------------
    st.markdown("### 7 · Alerts created")
    alert_ids = [
        int(e["alert_id"])
        for e in (s7.get("evaluations", []) if isinstance(s7, dict) else [])
        if e.get("alert_id") is not None
    ]
    if alert_ids:
        # ids come straight from the trace (ints we parsed), so inlining them is
        # injection-safe and sidesteps array-param binding quirks.
        id_list = ", ".join(str(i) for i in alert_ids)
        try:
            adf = db.df(
                "SELECT alert_id, alert_type, severity, triggered_at, resolved, "
                "alert_message_marathi FROM alerts_notifications "
                f"WHERE alert_id IN ({id_list}) ORDER BY alert_id"
            )
            if adf.empty:
                st.caption(f"Alert ids {alert_ids} not found (purged?).")
            else:
                st.dataframe(adf, use_container_width=True, hide_index=True)
        except Exception as exc:
            st.caption(f"Could not load alert rows: `{str(exc)[:160]}`")
    else:
        st.caption("No alerts were created for this reading.")
