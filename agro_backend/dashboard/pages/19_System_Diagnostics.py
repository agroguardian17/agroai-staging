"""System Diagnostics — the nightly freshness + invariant battery.

Shows the latest `diagnostics_result` run (written by the diagnostics scheduler
when `DIAGNOSTICS_ENABLED` is on): is live data fresh, does the forecast cover
today, is the partition catch-all present, are there duplicate advisories?
Catches the "bad data / stale pipeline" class automatically. Read-only.
"""

from __future__ import annotations

import db
import streamlit as st

st.title("✅ System Diagnostics")
st.caption("Latest nightly freshness + invariant checks. Needs `DIAGNOSTICS_ENABLED=true`.")

_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "⚪"}

try:
    latest = db.df(
        """
        SELECT check_id, category, status, observed, expected, detail, created_at
        FROM diagnostics_result
        WHERE run_id = (SELECT run_id FROM diagnostics_result ORDER BY created_at DESC LIMIT 1)
        ORDER BY
            CASE status WHEN 'fail' THEN 0 WHEN 'warn' THEN 1 WHEN 'ok' THEN 2 ELSE 3 END,
            category, check_id
        """
    )
except Exception as exc:
    st.warning(
        "Could not read `diagnostics_result`. Is migration 0069 applied and "
        f"`DIAGNOSTICS_ENABLED` on?\n\n`{str(exc)[:200]}`"
    )
    st.stop()

if latest.empty:
    st.info("No diagnostics runs recorded yet. The battery runs nightly (default 07:15 IST).")
    st.stop()

run_at = latest["created_at"].iloc[0]
st.caption(f"Latest run: **{run_at}**")

counts = latest["status"].value_counts().to_dict()
m1, m2, m3, m4 = st.columns(4)
m1.metric("✅ ok", int(counts.get("ok", 0)))
m2.metric("⚠️ warn", int(counts.get("warn", 0)))
m3.metric("❌ fail", int(counts.get("fail", 0)))
m4.metric("⚪ skip", int(counts.get("skip", 0)))

if int(counts.get("fail", 0)):
    st.error("One or more checks failed — see the ❌ rows below.")
elif int(counts.get("warn", 0)):
    st.warning("Some checks are in warning.")
else:
    st.success("All applicable checks passed in the latest run.")

view = latest.copy()
view["status"] = view["status"].map(lambda s: f"{_ICON.get(s, '')} {s}")
st.dataframe(
    view[["status", "category", "check_id", "observed", "expected", "detail"]],
    use_container_width=True,
    hide_index=True,
)

# --- trend: fail/warn counts per run over time ------------------------------
st.markdown("### Trend (last 30 runs)")
trend = db.df(
    """
    SELECT created_at,
           count(*) FILTER (WHERE status = 'fail') AS fail,
           count(*) FILTER (WHERE status = 'warn') AS warn,
           count(*) FILTER (WHERE status = 'ok')   AS ok
    FROM diagnostics_result
    WHERE run_id IN (
        SELECT DISTINCT run_id FROM diagnostics_result ORDER BY run_id LIMIT 1000
    )
    GROUP BY created_at
    ORDER BY created_at DESC
    LIMIT 30
    """
)
if not trend.empty:
    trend = trend.set_index("created_at").sort_index()
    st.bar_chart(trend[["fail", "warn", "ok"]])
