"""Records & Knowledge Base — master data and the loaded rule engine.

Groups the former Farmers & Farms, Season & Scheme Records, Plot Geometry, and
Ginger Knowledge Base pages.
"""

from __future__ import annotations

import streamlit as st
from views import farmers_and_farms, ginger_knowledge_base, plot_geometry, season_and_scheme_records

_VIEWS = {
    "Farmers & Farms": farmers_and_farms.render,
    "Season & Scheme Records": season_and_scheme_records.render,
    "Plot Geometry": plot_geometry.render,
    "Ginger Knowledge Base": ginger_knowledge_base.render,
}

st.sidebar.caption("Records & KB")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_records"
)
st.divider()
_VIEWS[choice]()
