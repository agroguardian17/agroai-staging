"""Scheduler Health — did every background job run, and did it succeed?

Reads the `job_run` ledger (written by `instrument_job` when
`JOB_RUN_LEDGER_ENABLED` is on). Turns a silently-failing nightly job from
"invisible in the logs for weeks" (the k_source outage) into one red row here.
Read-only.
"""

from __future__ import annotations

import db
import pandas as pd
import streamlit as st

st.title("🩺 Scheduler Health")
st.caption(
    "Per-job last run + status from the `job_run` ledger. Needs `JOB_RUN_LEDGER_ENABLED=true`."
)

# How long each job may go without a successful run before it's flagged red (hours).
EXPECTED_MAX_AGE_H: dict[str, float] = {
    "ginger_daily": 26,
    "weather_forecast": 26,
    "satellite_fetch": 26,
    "landsat_lst_fetch": 26,
    "ai_learning_writer": 26,
    "dpdp_retention_worker": 26,
    "partition_maintenance": 26,
    "diagnostics_battery": 26,
    "device_watchdog": 2,
    "qa_weekly_digest": 192,  # weekly
}
DEFAULT_MAX_AGE_H = 26.0

try:
    last = db.df(
        """
        SELECT DISTINCT ON (job_name)
               job_name, status, started_at, finished_at, duration_ms,
               error_type, error_message
        FROM job_run
        ORDER BY job_name, started_at DESC
        """
    )
except Exception as exc:
    st.warning(
        "Could not read `job_run`. Is migration 0068 applied and "
        f"`JOB_RUN_LEDGER_ENABLED` on?\n\n`{str(exc)[:200]}`"
    )
    st.stop()

if last.empty:
    st.info("No job runs recorded yet. The ledger fills as the schedulers tick.")
    st.stop()

success = db.df(
    "SELECT job_name, max(started_at) AS last_success FROM job_run "
    "WHERE status = 'ok' GROUP BY job_name"
)
window = db.df(
    """
    SELECT job_name,
           count(*) FILTER (WHERE status = 'ok')      AS ok_24h,
           count(*) FILTER (WHERE status = 'failed')  AS failed_24h,
           count(*) FILTER (WHERE status = 'skipped') AS skipped_24h
    FROM job_run
    WHERE started_at >= now() - interval '24 hours'
    GROUP BY job_name
    """
)

df = last.merge(success, on="job_name", how="left").merge(window, on="job_name", how="left")
now = pd.Timestamp.now(tz="UTC")


def _age_h(ts: pd.Timestamp | None) -> float | None:
    if ts is None or pd.isna(ts):
        return None
    return round((now - ts).total_seconds() / 3600.0, 1)


df["last_run_age_h"] = df["started_at"].apply(_age_h)
df["last_success_age_h"] = df["last_success"].apply(_age_h)
df["max_age_h"] = df["job_name"].map(EXPECTED_MAX_AGE_H).fillna(DEFAULT_MAX_AGE_H)


def _health(row: pd.Series) -> str:
    age = row["last_success_age_h"]
    if age is None:
        return "❌ never succeeded"
    if age > row["max_age_h"]:
        return "❌ stale"
    if row.get("failed_24h") and row["failed_24h"] > 0:
        return "⚠️ ok, recent failures"
    return "✅ healthy"


df["health"] = df.apply(_health, axis=1)

# --- headline ---------------------------------------------------------------
red = int((df["health"].str.startswith("❌")).sum())
amber = int((df["health"].str.startswith("⚠️")).sum())
green = int((df["health"].str.startswith("✅")).sum())
m1, m2, m3 = st.columns(3)
m1.metric("✅ healthy", green)
m2.metric("⚠️ attention", amber)
m3.metric("❌ problems", red)
if red:
    st.error(f"{red} job(s) are stale or have never succeeded — see the table below.")

# --- per-job table ----------------------------------------------------------
view = df[
    [
        "health",
        "job_name",
        "status",
        "last_run_age_h",
        "last_success_age_h",
        "max_age_h",
        "ok_24h",
        "failed_24h",
        "skipped_24h",
        "duration_ms",
    ]
].sort_values(["health", "job_name"])
st.dataframe(view, use_container_width=True, hide_index=True)

# --- recent failures --------------------------------------------------------
st.markdown("### Recent failures (last 7 days)")
fails = db.df(
    """
    SELECT started_at, job_name, error_type, left(error_message, 300) AS error_message
    FROM job_run
    WHERE status = 'failed' AND started_at >= now() - interval '7 days'
    ORDER BY started_at DESC
    LIMIT 100
    """
)
if fails.empty:
    st.success("No failed job runs in the last 7 days.")
else:
    st.dataframe(fails, use_container_width=True, hide_index=True)
