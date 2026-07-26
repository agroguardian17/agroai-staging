"""Page: Farmer Overview - all plots at a glance.

For each plot in the caller's scope, fetches:

* The plot card (area, crop tier, plot status)
* The latest reading (soil moisture, battery, pH)
* The freshest open alert (severity colour)

Renders one card per plot so the agronomist can scan health visually
without drilling into each one.
"""

from __future__ import annotations

from datetime import UTC, datetime

import api_client
import streamlit as st


# ---------------------------------------------------------------------------
# Formatting helpers (declared first so the render loop can call them)
# ---------------------------------------------------------------------------
def _fmt_ts(iso: str) -> str:
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso


def _fmt_pct(v: object) -> str:
    return f"{v}%" if v is not None else "—"


def _fmt_volts(v: object) -> str:
    return f"{v} V" if v is not None else "—"


def _fmt_decimal(v: object) -> str:
    return f"{v}" if v is not None else "—"


def _render_plot_card(plot: dict) -> None:
    plot_id = plot["plot_id"]
    container = st.container(border=True)
    with container:
        st.subheader(f"📍 {plot_id}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Area", f"{plot['area_acre']} ac")
        c2.metric("Tier", plot["data_tier"])
        c3.metric("Status", plot["plot_status"])

        # Most recent reading.
        readings = api_client.list_readings(plot_id, limit=1)
        if readings:
            r = readings[0]
            ts = _fmt_ts(r["recorded_at"])
            r1, r2, r3 = st.columns(3)
            r1.metric("Soil Moisture", _fmt_pct(r["soil_moisture_avg_pct"]))
            r2.metric("Battery", _fmt_volts(r["battery_voltage_v"]))
            r3.metric("pH", _fmt_decimal(r["soil_ph"]))
            st.caption(f"Last reading: {ts}")
        else:
            st.caption("No readings yet.")

        # Top open alert.
        alerts = api_client.list_plot_alerts(plot_id, limit=5)
        open_alerts = [a for a in alerts if not a["resolved"]]
        if open_alerts:
            top = open_alerts[0]
            colour = {
                "critical": "🔴",
                "warning": "🟠",
                "info": "🔵",
            }.get(top["severity"], "⚪")
            st.error(
                f"{colour} {top['severity'].upper()} — {top['alert_type']}: "
                f"{top['alert_message_marathi']}"
            )
        else:
            st.success("✅ No open alerts")


# ---------------------------------------------------------------------------
# Page body
# ---------------------------------------------------------------------------
st.title("Farmer Overview")

plots = api_client.list_plots()
if not plots:
    st.info("No plots visible. Make sure your token is for a farmer who owns plots.")
    st.stop()

st.caption(f"Showing {len(plots)} plot{'s' if len(plots) != 1 else ''}.")

cols_per_row = 2
for i in range(0, len(plots), cols_per_row):
    row = st.columns(cols_per_row)
    for col, plot in zip(row, plots[i : i + cols_per_row], strict=False):
        with col:
            _render_plot_card(plot)
