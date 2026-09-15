"""Farmers & farms — tenants, farmers, farms, plots, seasons, billing."""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Farmers & Farms", page_icon="👨‍🌾", layout="wide")
st.title("👨‍🌾 Farmers & Farms")

_SECTIONS = {
    "Tenants": "tenants",
    "Farmers": "farmers",
    "Farms": "farms",
    "Plots": "plots",
    "Crop seasons": "crop_seasons",
    "Subscriptions / billing": "subscriptions_billing",
    "Users (staff)": "users",
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
