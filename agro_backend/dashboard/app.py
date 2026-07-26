"""AgroGuardian Operations Dashboard - entrypoint.

Launch with::

    streamlit run dashboard/app.py

Three pages live in ``dashboard/pages/`` and are auto-discovered:

* 01_Farmer_Overview — all plots side-by-side
* 02_Plot_Detail    — readings chart + alerts + AI advisories
* 03_Ops_Queue      — tenant-wide alerts, filterable + resolvable

This module is the entry point Streamlit lands on by default; we use
it for the welcome / identity card.
"""

from __future__ import annotations

import api_client
import streamlit as st

st.set_page_config(
    page_title="AgroGuardian Dashboard",
    page_icon="🌾",
    layout="wide",
)

st.title("AgroGuardian Operations Dashboard")
st.caption("Pilot — Aurangabad, Maharashtra")

me = api_client.whoami()

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Farmer ID", me["farmer_id"][:8] + "…")
with col2:
    st.metric("Tenant", me["tenant_id"][:8] + "…")
with col3:
    st.metric("Role", me["role"])

st.divider()

st.markdown(
    """
    ### Pages

    Use the sidebar to navigate:

    * **Farmer Overview** — at-a-glance health of every plot in your farm.
    * **Plot Detail** — pick one plot, see its recent readings, alerts,
      and Claude-generated Marathi advisories.
    * **Operations Queue** — every alert across the tenant.
      Filter by severity, resolve from the table.

    ### How data flows

    1. Sub Nodes publish telemetry to Mosquitto every minute.
    2. The ingest worker validates, saves, and runs the rule engine.
    3. Rule hits become rows in ``alerts_notifications``.
    4. Each fresh alert triggers a Claude advisory (Round 11).
    5. This dashboard reads everything from the FastAPI read endpoints.

    *(No direct Postgres access from the dashboard — every screen is a
    consumer of the same API a mobile client would use.)*
    """
)
