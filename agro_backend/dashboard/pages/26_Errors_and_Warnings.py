"""Recent Errors & Warnings — the failure stream, queryable (R3.5).

Pulls the pipeline's errors/warnings into one page instead of `docker logs`:
failed/errored `job_run` ticks (every scheduler's failures, with the captured
error), the lightweight `app_event` stream (e.g. the ingest drain loop's
unexpected-error branch), and dropped/failed ingest messages from
`pipeline_trace`. Read-only; `app_event` needs `APP_EVENT_ENABLED=true`.
"""

from __future__ import annotations

from typing import Any

import db
import pandas as pd
import streamlit as st

_LEVEL_ICON = {"error": "❌", "warn": "⚠️", "warning": "⚠️", "info": "🔵"}

st.title("🔧 Recent Errors & Warnings")
st.caption("Failure stream from `job_run` + `app_event` + ingest drops — no more log-diving.")

c1, c2 = st.columns([1, 1])
hours = c1.selectbox("Window", [24, 72, 168, 720], index=1, format_func=lambda h: f"last {h}h")
levels = c2.multiselect("Levels", ["error", "warn"], default=["error", "warn"])

if not levels:
    st.info("Pick at least one level.")
    st.stop()

# One UNION over the durable sources. Each branch normalises to the same shape.
# job 'error' status → error; a job that finished non-ok but not 'error' → warn.
sql = """
WITH stream AS (
    SELECT j.started_at AS ts,
           (CASE WHEN j.status = 'error' THEN 'error' ELSE 'warn' END) AS level,
           'job' AS source,
           j.job_name AS event,
           NULL AS entity,
           COALESCE(j.error_type || ': ' || j.error_message, j.status) AS detail
    FROM job_run j
    WHERE j.status <> 'ok'
  UNION ALL
    SELECT e.created_at, e.level, e.source, e.event, e.entity, e.detail::text
    FROM app_event e
    WHERE e.level IN ('error', 'warn')
  UNION ALL
    SELECT t.created_at,
           (CASE WHEN t.drop_reason IS NOT NULL THEN 'error' ELSE 'warn' END),
           'ingest',
           COALESCE(t.drop_reason, 'trace_fail'),
           t.node_id,
           ('overall=' || t.overall) AS detail
    FROM pipeline_trace t
    WHERE t.drop_reason IS NOT NULL OR t.overall = 'fail'
)
SELECT ts, level, source, event, entity, detail
FROM stream
WHERE ts >= now() - make_interval(hours => :h) AND level = ANY(:levels)
ORDER BY ts DESC
LIMIT 500
"""

try:
    rows = db.df(sql, {"h": int(hours), "levels": levels})
except Exception as exc:
    st.warning(
        "Could not read the error stream. Is migration 0073 (`app_event`) applied?\n\n"
        f"`{str(exc)[:200]}`"
    )
    st.stop()

if rows.empty:
    st.success("✅ No errors or warnings in this window.")
    st.stop()

err = int((rows["level"] == "error").sum())
warn = int((rows["level"] == "warn").sum())
m1, m2, m3 = st.columns(3)
m1.metric("Total", len(rows))
m2.metric("❌ errors", err)
m3.metric("⚠️ warnings", warn)

# counts by source — quick "where are the failures coming from"
by_source = (
    rows.groupby("source").size().reset_index(name="count").sort_values("count", ascending=False)
)
st.markdown("##### By source")
st.dataframe(by_source, use_container_width=True, hide_index=True)

view = rows.copy()
view["level"] = view["level"].map(lambda v: f"{_LEVEL_ICON.get(str(v), '')} {v}")


def _clip(v: Any) -> Any:
    return str(v)[:200] if v is not None and not (isinstance(v, float) and pd.isna(v)) else ""


view["detail"] = view["detail"].map(_clip)
st.markdown("##### Stream")
st.dataframe(
    view[["ts", "level", "source", "event", "entity", "detail"]],
    use_container_width=True,
    hide_index=True,
)
