"""Stage Health — is any pipeline stage systematically wrong?

Aggregates the `pipeline_trace` rows (written when `PIPELINE_TRACE_ENABLED` is on)
over a window so ops can spot a stage that fails/warns across many messages —
e.g. "calibration warn on 40% of soil readings" or a spike in dropped messages —
rather than inspecting one message at a time (that's the Pipeline Inspector).
Read-only.
"""

from __future__ import annotations

from typing import Any

import db
import streamlit as st

st.title("📊 Stage Health")
st.caption("Aggregate pipeline outcomes over a window. Needs `PIPELINE_TRACE_ENABLED=true`.")

try:
    nodes_df = db.df(
        "SELECT DISTINCT node_id FROM pipeline_trace WHERE node_id IS NOT NULL ORDER BY node_id"
    )
except Exception as exc:
    st.warning(
        "Could not read `pipeline_trace`. Is migration 0064 applied and "
        f"`PIPELINE_TRACE_ENABLED` on?\n\n`{str(exc)[:200]}`"
    )
    st.stop()

c1, c2 = st.columns([2, 1])
node = c1.selectbox("Device", ["(all)", *nodes_df["node_id"].tolist()])
hours = c2.selectbox("Window", [24, 72, 168, 720], index=1, format_func=lambda h: f"last {h}h")

where = ["created_at >= now() - make_interval(hours => :h)"]
params: dict[str, Any] = {"h": int(hours)}
node_sql = ""
if node != "(all)":
    where.append("node_id = :n")
    params["n"] = node
    node_sql = " AND node_id = :n"
win = " AND ".join(where)

total = db.scalar(f"SELECT count(*) FROM pipeline_trace WHERE {win}", params) or 0
if total == 0:
    st.info("No traces in this window.")
    st.stop()

# --- headline outcome counts ------------------------------------------------
counts = db.df(
    f"SELECT overall, count(*) AS n FROM pipeline_trace WHERE {win} GROUP BY overall", params
)
cmap = dict(zip(counts["overall"], counts["n"], strict=False))
drops = (
    db.scalar(
        f"SELECT count(*) FROM pipeline_trace WHERE {win} AND drop_reason IS NOT NULL", params
    )
    or 0
)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Messages", total)
m2.metric("✅ ok", int(cmap.get("ok", 0)))
m3.metric("⚠️ warn", int(cmap.get("warn", 0)))
m4.metric("❌ fail", int(cmap.get("fail", 0)))
m5.metric("Dropped", int(drops))

# --- outcome trend over time ------------------------------------------------
st.markdown("### Outcome trend")
trend = db.df(
    f"SELECT date_trunc('hour', created_at) AS bucket, overall, count(*) AS n "
    f"FROM pipeline_trace WHERE {win} GROUP BY 1, 2 ORDER BY 1",
    params,
)
if not trend.empty:
    pivot = trend.pivot_table(index="bucket", columns="overall", values="n", fill_value=0)
    st.bar_chart(pivot)

# --- the key view: findings by stage + field + level ------------------------
st.markdown("### Validation findings (which stage/field is systematically off)")
findings = db.df(
    f"SELECT v->>'stage' AS stage, v->>'field' AS field, v->>'level' AS level, "
    f"count(*) AS occurrences, "
    f"round(100.0 * count(*) / {int(total)}, 1) AS pct_of_messages "
    f"FROM pipeline_trace, jsonb_array_elements(validations) v "
    f"WHERE {win} GROUP BY 1, 2, 3 ORDER BY occurrences DESC LIMIT 50",
    params,
)
if findings.empty:
    st.success("No validation findings in this window — every message passed its checks.")
else:
    st.dataframe(findings, use_container_width=True, hide_index=True)

# --- persist outcomes + drop reasons ---------------------------------------
pc1, pc2 = st.columns(2)
with pc1:
    st.markdown("#### Persist outcomes")
    persist = db.df(
        f"SELECT coalesce(stages->'s6_persist'->>'status', '(none)') AS persist, "
        f"count(*) AS n FROM pipeline_trace WHERE {win} GROUP BY 1 ORDER BY n DESC",
        params,
    )
    st.dataframe(persist, use_container_width=True, hide_index=True)
with pc2:
    st.markdown("#### Drop reasons")
    dreasons = db.df(
        f"SELECT drop_reason, count(*) AS n FROM pipeline_trace "
        f"WHERE {win} AND drop_reason IS NOT NULL GROUP BY 1 ORDER BY n DESC",
        params,
    )
    if dreasons.empty:
        st.caption("No dropped messages in this window.")
    else:
        st.dataframe(dreasons, use_container_width=True, hide_index=True)

# --- calibration version in use (catches a stale/mixed calibration) --------
st.markdown("### Calibration versions seen")
calv = db.df(
    f"SELECT coalesce(stages->'s4_calibrate'->>'calibration_version', '(none)') AS version, "
    f"count(*) AS n, max(created_at) AS last_seen FROM pipeline_trace WHERE {win}{node_sql} "
    f"GROUP BY 1 ORDER BY n DESC",
    params,
)
st.dataframe(calv, use_container_width=True, hide_index=True)
