"""Live activity — a rolling timeline of what the system is doing.

The `agro_events` LISTEN/NOTIFY bus is fire-and-forget (events are not stored),
so this page reconstructs the event stream from the state changes those events
accompany: alerts created, advisories composed, advisories delivered, farmer
replies. It auto-refreshes so you can watch data land as hardware comes online.
"""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Live Activity", page_icon="📡", layout="wide")
st.title("📡 Live Activity")
st.caption("Reconstructed from state changes · refreshes every 15s")

_TIMELINE = """
    SELECT triggered_at AS ts, 'alert.created' AS event,
           alert_type AS detail, severity AS extra
    FROM alerts_notifications
    UNION ALL
    SELECT generated_at, 'suggestion.generated', suggestion_type, delivery_status
    FROM ai_suggestions
    UNION ALL
    SELECT whatsapp_sent_at, 'advisory.sent', suggestion_type, delivery_provider_message_id
    FROM ai_suggestions WHERE whatsapp_sent_at IS NOT NULL
    UNION ALL
    SELECT received_at, 'wa.inbound', phone_e164, left(coalesce(body,''), 40)
    FROM wa_inbound_log
    ORDER BY ts DESC NULLS LAST
    LIMIT 200
"""


@st.fragment(run_every="15s")
def _feed() -> None:
    rows = db.df(_TIMELINE)
    if rows.empty:
        st.info("No activity yet — the pipeline is quiet (awaiting hardware / advisories).")
        return
    counts = rows["event"].value_counts()
    cols = st.columns(len(counts))
    for col, (event, n) in zip(cols, counts.items(), strict=False):
        col.metric(event, int(n))
    st.dataframe(rows, use_container_width=True, hide_index=True, height=520)


_feed()
