"""Devices & calibration — registry, calibration, installs, maintenance."""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Devices & Calibration", page_icon="🔧", layout="wide")
st.title("🔧 Devices & Calibration")

_SECTIONS = {
    "Device registry": "device_registry",
    "Calibration (per device)": "device_calibration",
    "Technician installs": "technician_installations",
    "Service / maintenance": "service_maintenance",
    "Component inventory": "component_inventory",
    "Calibration history": "calibration_history",
}

tabs = st.tabs(list(_SECTIONS))
for tab, (label, table) in zip(tabs, _SECTIONS.items(), strict=True):
    with tab:
        n = int(db.scalar(f"SELECT count(*) FROM {table}") or 0)
        st.metric(label, n)
        rows = db.df(f"SELECT * FROM {table} LIMIT 500")
        if rows.empty:
            st.info(f"`{table}` is empty.")
        else:
            st.dataframe(rows, use_container_width=True, hide_index=True)
