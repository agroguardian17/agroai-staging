"""System health — ingest freshness, device liveness, dead-letter queue."""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="System Health", page_icon="🩺", layout="wide")
st.title("🩺 System Health")

# --- Ingest freshness -------------------------------------------------------
st.subheader("Ingest freshness")
c = st.columns(3)
last_reading = db.scalar("SELECT max(recorded_at) FROM node_sensor_readings")
last_main = db.scalar("SELECT max(received_at_master) FROM main_node_readings")
last_alert = db.scalar("SELECT max(triggered_at) FROM alerts_notifications")
c[0].metric("Last sensor reading", str(last_reading or "—"))
c[1].metric("Last main-node reading", str(last_main or "—"))
c[2].metric("Last alert", str(last_alert or "—"))

st.divider()

# --- Device liveness --------------------------------------------------------
st.subheader("Devices — last seen")
st.caption("Main Node heartbeats. A device silent for a while is likely offline.")
devices = db.df(
    """
    SELECT d.device_id,
           d.device_type,
           d.device_status,
           max(m.received_at_master) AS last_seen
    FROM device_registry d
    LEFT JOIN main_node_readings m ON m.main_node_id = d.device_id
    GROUP BY d.device_id, d.device_type, d.device_status
    ORDER BY last_seen DESC NULLS LAST
    """
)
if devices.empty:
    st.info("No devices registered yet.")
else:
    st.dataframe(devices, use_container_width=True, hide_index=True)

st.divider()

# --- Notification pipeline health ------------------------------------------
st.subheader("Notification pipeline")
c = st.columns(4)
c[0].metric("Dispatch log", int(db.scalar("SELECT count(*) FROM notification_dispatch_log") or 0))
c[1].metric("Dead-letter queue", int(db.scalar("SELECT count(*) FROM notification_dlq") or 0))
c[2].metric(
    "Advisories failed (permanent)",
    int(
        db.scalar("SELECT count(*) FROM ai_suggestions WHERE delivery_status='failed_permanent'")
        or 0
    ),
)
c[3].metric(
    "Advisories in retry",
    int(db.scalar("SELECT count(*) FROM ai_suggestions WHERE delivery_status='pending'") or 0),
)

dlq = db.df("SELECT * FROM notification_dlq ORDER BY 1 DESC LIMIT 50")
if not dlq.empty:
    st.markdown("**Dead-letter queue (latest 50)**")
    st.dataframe(dlq, use_container_width=True, hide_index=True)

st.divider()

# --- Advisory compose vs delivery state ------------------------------------
st.subheader("Advisory state machine")
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Compose (alerts)**")
    st.dataframe(
        db.df(
            "SELECT advisory_status AS status, count(*) AS n "
            "FROM alerts_notifications GROUP BY advisory_status ORDER BY n DESC"
        ),
        use_container_width=True,
        hide_index=True,
    )
with col2:
    st.markdown("**Delivery (suggestions)**")
    st.dataframe(
        db.df(
            "SELECT delivery_status AS status, count(*) AS n "
            "FROM ai_suggestions GROUP BY delivery_status ORDER BY n DESC"
        ),
        use_container_width=True,
        hide_index=True,
    )
