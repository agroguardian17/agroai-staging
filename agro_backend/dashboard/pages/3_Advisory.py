"""Advisory — alert → compose → delivery, plus quality digests.

Groups the former Advisory Pipeline, Advisory Journey, and QA Digests pages.
"""

from __future__ import annotations

import streamlit as st
from views import advisory_journey, advisory_pipeline, qa_digests

_VIEWS = {
    "Advisory Pipeline": advisory_pipeline.render,
    "Advisory Journey": advisory_journey.render,
    "QA Digests": qa_digests.render,
}

st.sidebar.caption("Advisory")
choice = st.radio(
    "View", list(_VIEWS), horizontal=True, label_visibility="collapsed", key="nav_advisory"
)
st.divider()
_VIEWS[choice]()
