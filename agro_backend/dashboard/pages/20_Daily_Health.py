"""Daily Health — the single "is everything OK today?" pane.

Rolls up the two detailed pages into one verdict: scheduler health (from the
`job_run` ledger) + the latest nightly diagnostics run (freshness, invariants and
dependency self-tests). For the per-job / per-check detail, see **Scheduler
Health** and **System Diagnostics**. Read-only.
"""

from __future__ import annotations

import db
import pandas as pd
import streamlit as st

st.title("🌅 Daily Health")
st.caption("One-glance system health. Needs `JOB_RUN_LEDGER_ENABLED` + `DIAGNOSTICS_ENABLED`.")

_DEFAULT_MAX_AGE_H = 26.0
_now = pd.Timestamp.now(tz="UTC")

# --- schedulers -------------------------------------------------------------
stale_jobs: list[str] = []
jobs_total = 0
try:
    last_success = db.df(
        "SELECT job_name, max(started_at) AS last_success FROM job_run "
        "WHERE status = 'ok' GROUP BY job_name"
    )
    seen = db.df("SELECT DISTINCT job_name FROM job_run")
    jobs_total = len(seen)
    ok_names = set(last_success["job_name"].tolist()) if not last_success.empty else set()
    for name in seen["job_name"].tolist() if not seen.empty else []:
        if name not in ok_names:
            stale_jobs.append(name)
            continue
        ts = last_success.loc[last_success["job_name"] == name, "last_success"].iloc[0]
        age_h = (_now - ts).total_seconds() / 3600.0
        if age_h > _DEFAULT_MAX_AGE_H:
            stale_jobs.append(name)
    jobs_ok = True
except Exception as exc:
    jobs_ok = False
    st.warning(f"Scheduler ledger unavailable (migration 0068 / flag?): `{str(exc)[:160]}`")

# --- diagnostics ------------------------------------------------------------
diag_counts: dict[str, int] = {}
try:
    diag = db.df(
        """
        SELECT status, count(*) AS n FROM diagnostics_result
        WHERE run_id = (SELECT run_id FROM diagnostics_result ORDER BY created_at DESC LIMIT 1)
        GROUP BY status
        """
    )
    diag_counts = dict(zip(diag["status"], diag["n"], strict=False)) if not diag.empty else {}
    diag_ok = True
except Exception as exc:
    diag_ok = False
    st.warning(f"Diagnostics unavailable (migration 0069 / flag?): `{str(exc)[:160]}`")

diag_fail = int(diag_counts.get("fail", 0))
diag_warn = int(diag_counts.get("warn", 0))

# --- verdict ----------------------------------------------------------------
if (jobs_ok and stale_jobs) or (diag_ok and diag_fail):
    st.error("❌ Attention needed — a scheduler is stale or a diagnostic check failed.")
elif diag_ok and diag_warn:
    st.warning("⚠️ Mostly healthy, with warnings.")
elif jobs_ok and diag_ok:
    st.success("✅ All systems healthy.")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Jobs tracked", jobs_total)
c2.metric("❌ stale jobs", len(stale_jobs))
c3.metric("Diagnostics fail", diag_fail)
c4.metric("Diagnostics warn", diag_warn)

if stale_jobs:
    st.markdown("**Stale / never-succeeded jobs:** " + ", ".join(f"`{j}`" for j in stale_jobs))

st.markdown("### Latest diagnostics checks")
try:
    rows = db.df(
        """
        SELECT status, category, check_id, observed, detail FROM diagnostics_result
        WHERE run_id = (SELECT run_id FROM diagnostics_result ORDER BY created_at DESC LIMIT 1)
        ORDER BY CASE status WHEN 'fail' THEN 0 WHEN 'warn' THEN 1 WHEN 'ok' THEN 2 ELSE 3 END,
                 category, check_id
        """
    )
    if rows.empty:
        st.info("No diagnostics run recorded yet.")
    else:
        icon = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skip": "⚪"}
        rows["status"] = rows["status"].map(lambda s: f"{icon.get(s, '')} {s}")
        st.dataframe(rows, use_container_width=True, hide_index=True)
except Exception:
    pass

st.caption("Detail: **Scheduler Health** (per-job) and **System Diagnostics** (per-check).")
