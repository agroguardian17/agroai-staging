"""Anomalies — the system pointing out issues itself (Round-3 R3.4).

The nightly anomaly engine writes a typed finding per problem it spots: a device
that stopped reporting (`data_gap` — the 18-Oct outage would have shown here
immediately), a stuck sensor, a rule firing on nearly every reading, or an
advisory-volume spike/drop. A run with **no** findings writes no rows, so the
latest run (and whether it was clean) comes from the `job_run` ledger. Read-only;
needs `ANOMALY_DETECTION_ENABLED=true`.
"""

from __future__ import annotations

import json
from typing import Any

import db
import streamlit as st


def render() -> None:
    _SEV_ICON = {"critical": "🔴", "warn": "🟠", "info": "🔵", "ok": "✅"}

    st.title("🚨 Anomalies")
    st.caption(
        "Auto-detected issues from the nightly anomaly engine. Needs `ANOMALY_DETECTION_ENABLED=true`."
    )

    def _obj(v: Any) -> dict[str, Any]:
        if isinstance(v, dict):
            return v
        if isinstance(v, str) and v:
            try:
                return json.loads(v)
            except ValueError:
                return {}
        return {}

    try:
        last_run = db.df(
            "SELECT started_at, status, summary FROM job_run "
            "WHERE job_name = 'anomaly_engine' ORDER BY started_at DESC LIMIT 1"
        )
    except Exception as exc:
        st.warning(
            "Could not read `job_run`. Is migration 0071 applied and "
            f"`ANOMALY_DETECTION_ENABLED` on?\n\n`{str(exc)[:200]}`"
        )
        return

    if last_run.empty:
        st.info("The anomaly engine hasn't run yet. It fires nightly (default 07:25 IST).")
        return

    summary = _obj(last_run["summary"].iloc[0])
    run_id = summary.get("run_id")
    overall = summary.get("overall", "ok")
    run_at = last_run["started_at"].iloc[0]
    run_status = last_run["status"].iloc[0]

    st.subheader(f"Latest run · {run_at} · {_SEV_ICON.get(overall, '')} {str(overall).upper()}")
    if run_status != "ok":
        st.error(f"The last anomaly run did not complete cleanly (status: `{run_status}`).")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total", summary.get("total", 0))
    m2.metric("🔴 critical", summary.get("critical", 0))
    m3.metric("🟠 warn", summary.get("warn", 0))
    m4.metric("🔵 info", summary.get("info", 0))

    # --- findings of the latest run --------------------------------------------
    if run_id:
        latest = db.df(
            "SELECT severity, anomaly_type, entity_type, entity_id, observed, expected, detail "
            "FROM anomaly_finding WHERE run_id = :rid "
            "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warn' THEN 1 ELSE 2 END, anomaly_type",
            {"rid": str(run_id)},
        )
        if latest.empty:
            st.success("✅ No anomalies in the latest run — all clear.")
        else:
            latest = latest.copy()
            latest["sev"] = latest["severity"].map(lambda s: f"{_SEV_ICON.get(s, '')} {s}")
            cols = [
                "sev",
                "anomaly_type",
                "entity_type",
                "entity_id",
                "observed",
                "expected",
                "detail",
            ]
            st.dataframe(latest[cols], use_container_width=True, hide_index=True)
    else:
        st.caption("Latest run has no run_id in its ledger summary; showing recent history below.")

    # --- recent history ---------------------------------------------------------
    st.divider()
    st.markdown("### Recent findings (last 30 days)")
    hist = db.df(
        "SELECT created_at, severity, anomaly_type, entity_type, entity_id, observed "
        "FROM anomaly_finding WHERE created_at > now() - interval '30 days' "
        "ORDER BY created_at DESC LIMIT 500"
    )
    if hist.empty:
        st.caption("No anomalies recorded in the last 30 days.")
    else:
        st.dataframe(hist, use_container_width=True, hide_index=True)
