"""Page: Plot Detail - readings chart + alerts + AI advisories.

Sidebar selector lets the user pick any plot. Main panel has three
tabs (Readings / Alerts / Advisories) so the page stays scannable.
"""

from __future__ import annotations

from datetime import UTC, datetime

import api_client
import pandas as pd
import plotly.express as px
import streamlit as st


# ---------------------------------------------------------------------------
# Helpers (declared first so the tab bodies can call them)
# ---------------------------------------------------------------------------
def _fmt_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso


st.title("Plot Detail")

plots = api_client.list_plots()
if not plots:
    st.info("No plots visible.")
    st.stop()

plot_ids = [p["plot_id"] for p in plots]
selected = st.sidebar.selectbox("Plot", plot_ids)
chosen = next(p for p in plots if p["plot_id"] == selected)

# Header card.
c1, c2, c3, c4 = st.columns(4)
c1.metric("Plot", chosen["plot_id"])
c2.metric("Area", f"{chosen['area_acre']} ac")
c3.metric("Tier", chosen["data_tier"])
c4.metric("Status", chosen["plot_status"])

tab_readings, tab_alerts, tab_advisories = st.tabs(["📈 Readings", "🚨 Alerts", "🤖 AI Advisories"])

# ---------------------------------------------------------------------------
# Readings tab
# ---------------------------------------------------------------------------
with tab_readings:
    limit = st.slider("How many recent readings?", 10, 500, 100, step=10)
    readings = api_client.list_readings(selected, limit=limit)
    if not readings:
        st.info("No readings yet for this plot.")
    else:
        df = pd.DataFrame(readings)
        # Coerce numeric strings -> floats for plotting.
        for col in (
            "soil_moisture_avg_pct",
            "soil_temp_rootzone_c",
            "soil_ph",
            "soil_ec_ms_cm",
            "battery_voltage_v",
            "battery_percent",
        ):
            if col in df:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["recorded_at"] = pd.to_datetime(df["recorded_at"])
        df = df.sort_values("recorded_at")

        st.plotly_chart(
            px.line(
                df,
                x="recorded_at",
                y="soil_moisture_avg_pct",
                title="Soil Moisture (%)",
            ),
            use_container_width=True,
        )
        st.plotly_chart(
            px.line(
                df,
                x="recorded_at",
                y="battery_voltage_v",
                title="Battery Voltage (V)",
            ),
            use_container_width=True,
        )
        with st.expander("Raw rows"):
            st.dataframe(df, use_container_width=True)


# ---------------------------------------------------------------------------
# Alerts tab
# ---------------------------------------------------------------------------
with tab_alerts:
    alerts = api_client.list_plot_alerts(selected, limit=50)
    if not alerts:
        st.success("No alerts for this plot.")
    else:
        rows = []
        for a in alerts:
            rows.append(
                {
                    "Triggered": _fmt_ts(a["triggered_at"]),
                    "Type": a["alert_type"],
                    "Severity": a["severity"],
                    "Resolved": "✅" if a["resolved"] else "🔴",
                    "Message": a["alert_message_marathi"],
                }
            )
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Advisories tab
# ---------------------------------------------------------------------------
with tab_advisories:
    sugs = api_client.list_plot_suggestions(selected, limit=20)
    if not sugs:
        st.info(
            "No persisted AI advisories yet. The current MQTT path does not generate them automatically."
        )
    else:
        for s in sugs:
            with st.container(border=True):
                hdr_l, hdr_r = st.columns([3, 1])
                hdr_l.markdown(
                    f"**{s['suggestion_type'].title()}** &nbsp;·&nbsp; `{s['ai_model_version']}`"
                )
                hdr_r.caption(_fmt_ts(s["generated_at"]))
                if s.get("crop_stage"):
                    st.caption(f"Crop: {s['crop_stage']} ({s.get('crop_age_days') or '?'} days)")
                st.markdown(s["full_message_marathi"])
                if s.get("tokens_used"):
                    st.caption(f"{s['tokens_used']} tokens")
