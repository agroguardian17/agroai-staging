"""Pipeline & Traces — trace what happened to a message / run.

Groups the former Pipeline Inspector, Stage Health, Daily Run Inspector,
Pipeline Self-Test, Reading Journey, and Event Timeline pages.
"""

from __future__ import annotations

import streamlit as st
from views import (
    daily_run_inspector,
    event_timeline,
    pipeline_inspector,
    pipeline_self_test,
    reading_journey,
    stage_health,
)

_VIEWS = {
    "Reading Journey": reading_journey.render,
    "Event Timeline": event_timeline.render,
    "Pipeline Inspector": pipeline_inspector.render,
    "Stage Health": stage_health.render,
    "Daily Run Inspector": daily_run_inspector.render,
    "Pipeline Self-Test": pipeline_self_test.render,
}

st.sidebar.caption("Pipeline & Traces")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_pipeline"
)
st.divider()
_VIEWS[choice]()
