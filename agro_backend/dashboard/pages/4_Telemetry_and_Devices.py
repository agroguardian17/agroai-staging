"""Telemetry & Devices — sensor data, device registry, the live event bus.

Groups the former Telemetry, Devices & Calibration, and Live Events pages.
"""

from __future__ import annotations

import streamlit as st
from views import devices_and_calibration, live_events, telemetry

_VIEWS = {
    "Telemetry": telemetry.render,
    "Devices & Calibration": devices_and_calibration.render,
    "Live Events": live_events.render,
}

st.sidebar.caption("Telemetry & Devices")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_telemetry"
)
st.divider()
_VIEWS[choice]()
