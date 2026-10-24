"""Health & Alerts — is the system OK right now?

Groups the former System Health, Daily Health, System Diagnostics, Scheduler
Health, Anomalies, and Errors & Warnings pages. Pick a view below; each renders
exactly as its old standalone page did (same charts, tables, queries).
"""

from __future__ import annotations

import streamlit as st
from views import (
    anomalies,
    daily_health,
    errors_and_warnings,
    scheduler_health,
    system_diagnostics,
    system_health,
)

_VIEWS = {
    "System Health": system_health.render,
    "Daily Health": daily_health.render,
    "System Diagnostics": system_diagnostics.render,
    "Scheduler Health": scheduler_health.render,
    "Anomalies": anomalies.render,
    "Errors & Warnings": errors_and_warnings.render,
}

st.sidebar.caption("Health & Alerts")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_health"
)
st.divider()
_VIEWS[choice]()
