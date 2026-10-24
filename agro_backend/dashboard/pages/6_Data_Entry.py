"""Data Entry — manual entry forms (lab tests, scouting, misc records).

Groups the former Data Entry, Lab Soil Test, and Crop Scouting pages.
"""

from __future__ import annotations

import streamlit as st
from views import crop_scouting, data_entry, lab_soil_test

_VIEWS = {
    "Data Entry": data_entry.render,
    "Lab Soil Test": lab_soil_test.render,
    "Crop Scouting": crop_scouting.render,
}

st.sidebar.caption("Data Entry")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_entry"
)
st.divider()
_VIEWS[choice]()
