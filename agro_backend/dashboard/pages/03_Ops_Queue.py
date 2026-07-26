"""Page: Operations Queue - all open alerts for the tenant.

Filterable by severity, with a Resolve button per row. Used by the
on-call agronomist to triage incoming alerts.
"""

from __future__ import annotations

from datetime import UTC, datetime

import api_client
import streamlit as st


# ---------------------------------------------------------------------------
# Helpers (declared first so the expander headers can call them)
# ---------------------------------------------------------------------------
def _fmt_ts(iso: str | None) -> str:
    if not iso:
        return "—"
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso


st.title("Operations Queue")

# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
fcol1, fcol2, fcol3 = st.columns(3)
status_filter = fcol1.radio(
    "Status",
    options=["open", "all", "closed"],
    horizontal=True,
    index=0,
)
severity = fcol2.selectbox(
    "Severity",
    options=["any", "critical", "warning", "info"],
    index=0,
)
limit = fcol3.slider("Limit", 10, 500, 100, step=10)

severity_param = None if severity == "any" else severity
alerts = api_client.list_alerts(
    status_filter=status_filter,
    severity=severity_param,
    limit=limit,
)

if not alerts:
    st.success("✅ Nothing in queue under these filters.")
    st.stop()

st.caption(f"Showing {len(alerts)} alert{'s' if len(alerts) != 1 else ''}.")

# ---------------------------------------------------------------------------
# Resolve action - a tiny form per alert; keeps notes contextual.
# ---------------------------------------------------------------------------
for a in alerts:
    sev_icon = {"critical": "🔴", "warning": "🟠", "info": "🔵"}.get(a["severity"], "⚪")
    resolved_icon = "✅" if a["resolved"] else "🟡"
    with st.expander(
        f"{resolved_icon} {sev_icon} #{a['alert_id']} · {a['alert_type']} · "
        f"{_fmt_ts(a['triggered_at'])}",
        expanded=False,
    ):
        meta_cols = st.columns(3)
        meta_cols[0].markdown(f"**Farmer**: `{a['farmer_id'][:8]}…`")
        meta_cols[1].markdown(f"**Farm**: `{a['farm_id'][:8]}…`")
        meta_cols[2].markdown(f"**Device**: `{a.get('device_id') or '—'}`")

        st.markdown(f"**Message**: {a['alert_message_marathi']}")
        if a.get("alert_value") is not None:
            st.markdown(
                f"**Measurement**: {a['alert_value']}"
                + (
                    f" (threshold {a['alert_threshold']})"
                    if a.get("alert_threshold") is not None
                    else ""
                )
            )

        if a["resolved"]:
            st.success(f"Resolved at {_fmt_ts(a['resolved_at'])}.")
        else:
            with st.form(key=f"resolve_form_{a['alert_id']}"):
                notes = st.text_input("Resolution notes (optional)")
                if st.form_submit_button("Resolve", type="primary"):
                    api_client.resolve_alert(a["alert_id"], notes or None)
                    st.toast(f"Alert #{a['alert_id']} resolved", icon="✅")
                    st.rerun()
