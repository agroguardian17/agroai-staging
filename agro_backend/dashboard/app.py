"""AgroGuardian internal Ops Dashboard — entrypoint / system overview.

Launch with::

    streamlit run dashboard/app.py

A team-internal observability tool. It reads Postgres **directly, read-only**
(see ``db.py``) so it can surface every table, the whole advisory pipeline, and
live events without a farmer-facing endpoint per view. Pages in ``pages/`` are
auto-discovered into the sidebar.

This is NOT the farmer app — it shows all tenants and all raw data, and is meant
to sit behind auth (Caddy basic-auth in prod; see dashboard/README.md).
"""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="AgroGuardian Ops", page_icon="🌾", layout="wide")

st.title("🌾 AgroGuardian — Internal Ops Dashboard")
st.caption("Pilot — Aurangabad, Maharashtra · reads Postgres read-only, all tenants")

ok, detail = db.healthy()
if not ok:
    st.error(f"Database not reachable: {detail}")
    st.stop()

rel = db.relations()
total_rows = int(rel["approx_rows"].sum())
populated = int((rel["approx_rows"] > 0).sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("Migration head", db.migration_head())
c2.metric("Relations", len(rel))
c3.metric("Populated", f"{populated}/{len(rel)}")
c4.metric("Approx rows", f"{total_rows:,}")

st.divider()

# A few headline operational counts (each guarded — tables may be empty pre-pilot).
st.subheader("At a glance")


def _count(table: str, where: str = "") -> int:
    try:
        clause = f" WHERE {where}" if where else ""
        return int(db.scalar(f"SELECT count(*) FROM {table}{clause}") or 0)
    except Exception:
        return 0


g = st.columns(4)
g[0].metric("Tenants", _count("tenants"))
g[1].metric("Farmers", _count("farmers"))
g[2].metric("Plots", _count("plots"))
g[3].metric("Devices", _count("device_registry"))

g = st.columns(4)
g[0].metric("Sensor readings", _count("node_sensor_readings"))
g[1].metric("Main-node readings", _count("main_node_readings"))
g[2].metric("Open alerts", _count("alerts_notifications", "resolved IS NOT TRUE"))
g[3].metric("Advisories", _count("ai_suggestions"))

g = st.columns(4)
g[0].metric("Advisories sent", _count("ai_suggestions", "delivery_status = 'sent'"))
g[1].metric("Pending delivery", _count("ai_suggestions", "delivery_status = 'pending'"))
g[2].metric("Inbound WA msgs", _count("wa_inbound_log"))
g[3].metric("KB rules", _count("kb_rules"))

st.divider()
st.markdown(
    """
    ### Pages
    - **System Health** — ingest freshness, device online/offline, dead-letter queue.
    - **Data Explorer** — browse *any* of the tables, with row counts and recent rows.
    - **Telemetry** — Sub-Node + Main-Node + weather readings, charted.
    - **Advisory Pipeline** — alert → compose → WhatsApp delivery → farmer reply, end to end.
    - **Devices & Calibration** — registry, calibration, installs, maintenance.
    - **Ginger Knowledge Base** — the loaded rule engine (rules, fields, golden tests).
    - **Farmers & Farms** — tenants, farmers, farms, plots, seasons, billing.
    - **Live Events** — the `agro_events` bus, live.

    ### Data flow
    Sub Node → LoRa → Main Node → MQTT → ingest → `node_sensor_readings` → rule engine →
    `alerts_notifications` → compose (Claude) → `ai_suggestions` → WhatsApp delivery →
    `wa_inbound_log`. Empty panels mean that stage has no data **yet** (awaiting hardware).
    """
)
