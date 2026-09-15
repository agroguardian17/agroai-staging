"""Telemetry — Sub-Node sensor readings, Main-Node heartbeats, weather."""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Telemetry", page_icon="📈", layout="wide")
st.title("📈 Telemetry")

tab_sensor, tab_main, tab_weather = st.tabs(
    ["Sub-Node readings", "Main-Node readings", "Weather station"]
)

_NUMERIC = [
    "soil_moisture_avg_pct",
    "soil_temp_rootzone_c",
    "soil_ph",
    "soil_ec_ms_cm",
    "battery_voltage_v",
    "battery_percent",
    "water_flow_lpm",
    "water_pressure_bar",
]

with tab_sensor:
    nodes = db.df("SELECT DISTINCT node_id FROM node_sensor_readings ORDER BY node_id")
    if nodes.empty:
        st.info("No sensor readings yet (awaiting Sub-Node hardware).")
    else:
        node = st.selectbox("Node", nodes["node_id"].tolist())
        limit = st.slider("Readings", 20, 1000, 200, step=20)
        data = db.df(
            "SELECT * FROM node_sensor_readings WHERE node_id = :n "
            "ORDER BY recorded_at DESC LIMIT :lim",
            {"n": node, "lim": limit},
        ).sort_values("recorded_at")
        present = [c for c in _NUMERIC if c in data.columns]
        pick = st.multiselect(
            "Series", present, default=[c for c in ("soil_moisture_avg_pct", "battery_voltage_v") if c in present]
        )
        if pick and not data.empty:
            st.line_chart(data.set_index("recorded_at")[pick])
        with st.expander("Raw rows"):
            st.dataframe(data, use_container_width=True, hide_index=True)

with tab_main:
    data = db.df("SELECT * FROM main_node_readings ORDER BY received_at_master DESC LIMIT 500")
    if data.empty:
        st.info("No Main-Node readings yet.")
    else:
        st.caption(f"{len(data)} recent heartbeats")
        st.dataframe(data, use_container_width=True, hide_index=True)

with tab_weather:
    data = db.df("SELECT * FROM weather_station_readings ORDER BY 1 DESC LIMIT 500")
    if data.empty:
        st.info("No weather-station readings yet.")
    else:
        st.dataframe(data, use_container_width=True, hide_index=True)
