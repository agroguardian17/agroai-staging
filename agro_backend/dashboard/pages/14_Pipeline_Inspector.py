"""Pipeline Inspector — see each ingest message move through the server stages.

For every v2-raw message the broker records a `pipeline_trace` row (when
`PIPELINE_TRACE_ENABLED` is on): the raw sensor block *before* calibration, the
engineering values *after*, the per-stage checklist (receive → validate → RAW →
calibrate → clock-skew → persist → device-rules), and any plausibility findings.
This page lets ops confirm each stage ran correctly and spot wrong values at the
exact stage they appear. Read-only.
"""

from __future__ import annotations

import json
from typing import Any

import db
import pandas as pd
import streamlit as st

_STAGE_ORDER = [
    ("s1_receive", "1 · Receive"),
    ("s2_validate", "2 · Validate"),
    ("s3_raw", "3 · Raw snapshot"),
    ("s4_calibrate", "4 · Calibrate"),
    ("s5_clock_skew", "5 · Clock-skew"),
    ("s6_persist", "6 · Persist"),
    ("s7_rules", "7 · Device-rules"),
]
_LEVEL_ICON = {
    "ok": "✅",
    "warn": "⚠️",
    "fail": "❌",
    "inserted": "✅",
    "duplicate": "⚪",
    "skipped": "⚪",
}

st.title("🔍 Pipeline Inspector")
st.caption(
    "Per-message journey through the server-side stages. Needs `PIPELINE_TRACE_ENABLED=true`."
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
        "SELECT DISTINCT node_id FROM pipeline_trace WHERE node_id IS NOT NULL ORDER BY node_id"
    )
except Exception as exc:  # table missing / DB down
    st.warning(
        "Could not read `pipeline_trace`. Is migration 0064 applied and "
        f"`PIPELINE_TRACE_ENABLED` on?\n\n`{str(exc)[:200]}`"
    )
    st.stop()

c1, c2, c3 = st.columns([2, 1, 1])
node = c1.selectbox("Device", ["(all)", *nodes_df["node_id"].tolist()])
hours = c2.selectbox("Window", [6, 24, 72, 168], index=1, format_func=lambda h: f"last {h}h")
level = c3.selectbox("Outcome", ["(all)", "fail", "warn", "ok"])

where = ["created_at >= now() - make_interval(hours => :h)"]
params: dict[str, Any] = {"h": int(hours)}
if node != "(all)":
    where.append("node_id = :n")
    params["n"] = node
if level != "(all)":
    where.append("overall = :lvl")
    params["lvl"] = level

rows = db.df(
    f"SELECT trace_id, created_at, node_id, plot_id, schema_id, overall, drop_reason, "
    f"stages, raw_payload, calibrated, validations FROM pipeline_trace "
    f"WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 300",
    params,
)

if rows.empty:
    st.info(
        "No traces in this window. If the device is sending v2-raw and the flag is on, "
        "check the ingest logs."
    )
    st.stop()

# --- summary counts ---------------------------------------------------------
counts = rows["overall"].value_counts().to_dict()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Messages", len(rows))
m2.metric("✅ ok", counts.get("ok", 0))
m3.metric("⚠️ warn", counts.get("warn", 0))
m4.metric("❌ fail", counts.get("fail", 0))

# --- message list -----------------------------------------------------------
summary = rows[["created_at", "node_id", "overall", "drop_reason"]].copy()
summary["persist"] = rows["stages"].apply(lambda s: _obj(s).get("s6_persist", {}).get("status"))
summary.insert(0, "#", range(len(summary)))
st.dataframe(summary, use_container_width=True, hide_index=True)

idx = st.number_input("Inspect message #", min_value=0, max_value=len(rows) - 1, value=0, step=1)
row = rows.iloc[int(idx)]

st.divider()
st.subheader(
    f"Message {row['node_id']} · {row['created_at']} · {_LEVEL_ICON.get(row['overall'], '')} "
    f"{row['overall'].upper()}"
)
if row["drop_reason"]:
    st.error(f"**Dropped** at ingest — reason: `{row['drop_reason']}` (never persisted).")

# --- stage timeline ---------------------------------------------------------
stages = _obj(row["stages"])
cols = st.columns(len(_STAGE_ORDER))
for col, (key, label) in zip(cols, _STAGE_ORDER, strict=False):
    s = stages.get(key)
    status = s.get("status") if isinstance(s, dict) else None
    col.markdown(f"**{label}**\n\n{_LEVEL_ICON.get(status, '—')} {status or 'n/a'}")

# --- raw vs calibrated ------------------------------------------------------
st.markdown("### Raw (pre-calibration) → Calibrated")
rc1, rc2 = st.columns(2)
raw = _obj(row["raw_payload"])
cal = _obj(row["calibrated"])
with rc1:
    st.caption("raw_readings (as received)")
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
    st.caption(f"calibrated values (calibration v{cv})")
    st.dataframe(
        pd.DataFrame(sorted(cal.items()), columns=["field", "calibrated value"]),
        use_container_width=True,
        hide_index=True,
    )

# --- validation findings ----------------------------------------------------
findings = _obj(row["validations"])
st.markdown("### Validation checklist")
if findings:
    fdf = pd.DataFrame(findings)
    st.dataframe(fdf, use_container_width=True, hide_index=True)
else:
    st.success("All plausibility checks passed for this message.")
