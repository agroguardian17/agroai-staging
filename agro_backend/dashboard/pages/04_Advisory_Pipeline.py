"""Advisory pipeline — alert → compose → WhatsApp delivery → farmer reply.

The whole Round 13 + Round 14 loop on one screen, so the team can see exactly
where an advisory is: composed but not sent, sent, failed, replied-to.
"""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Advisory Pipeline", page_icon="📨", layout="wide")
st.title("📨 Advisory Pipeline")

# Funnel counts across the whole loop.
st.subheader("Funnel")
f = st.columns(6)
f[0].metric("Alerts", int(db.scalar("SELECT count(*) FROM alerts_notifications") or 0))
f[1].metric(
    "Composed",
    int(
        db.scalar("SELECT count(*) FROM alerts_notifications WHERE advisory_status='composed'") or 0
    ),
)
f[2].metric("Advisories", int(db.scalar("SELECT count(*) FROM ai_suggestions") or 0))
f[3].metric(
    "Sent", int(db.scalar("SELECT count(*) FROM ai_suggestions WHERE delivery_status='sent'") or 0)
)
f[4].metric(
    "Failed",
    int(
        db.scalar(
            "SELECT count(*) FROM ai_suggestions "
            "WHERE delivery_status IN ('failed_permanent','failed_transient')"
        )
        or 0
    ),
)
f[5].metric("Inbound replies", int(db.scalar("SELECT count(*) FROM wa_inbound_log") or 0))

st.divider()

# Recent advisories with their delivery state.
st.subheader("Recent advisories")
adv = db.df(
    """
    SELECT generated_at, suggestion_type, plot_id,
           delivery_status, delivery_attempts, whatsapp_sent, whatsapp_sent_at,
           delivery_last_error, delivery_provider_message_id,
           left(coalesce(full_message_marathi,''), 80) AS message_preview,
           ai_model_version, review_status
    FROM ai_suggestions
    ORDER BY generated_at DESC
    LIMIT 100
    """
)
if adv.empty:
    st.info("No advisories composed yet.")
else:
    st.dataframe(adv, use_container_width=True, hide_index=True)

st.divider()

# Alerts still stuck pre-compose (retrying / failed).
st.subheader("Alerts by compose state")
st.dataframe(
    db.df(
        """
        SELECT advisory_status, count(*) AS n,
               max(advisory_last_error) AS sample_error
        FROM alerts_notifications
        GROUP BY advisory_status ORDER BY n DESC
        """
    ),
    use_container_width=True,
    hide_index=True,
)

st.divider()

st.subheader("Inbound farmer messages")
inbound = db.df(
    "SELECT received_at, phone_e164, left(coalesce(body,''),120) AS body, processed "
    "FROM wa_inbound_log ORDER BY received_at DESC LIMIT 100"
)
if inbound.empty:
    st.info("No inbound WhatsApp messages yet (needs the live webhook).")
else:
    st.dataframe(inbound, use_container_width=True, hide_index=True)
