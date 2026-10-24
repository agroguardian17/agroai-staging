"""Advisory Journey — one advisory from trigger to delivery (R3.3).

Pick an advisory and see its whole lifecycle in one place: the triggering rule
and the crop/soil context it was composed against → the compose step (model,
prompt template, tokens, latency, cost, log-only?) → the rendered Marathi
message with its disclaimer → the delivery state machine (status, attempts,
retries, last error, WhatsApp provider id + sent time).

Every stage comes from the one durable `ai_suggestions` row that the advisory
pipeline already writes (trigger rule_id + compose metadata + the migration-0016
`delivery_*` state machine) — no new table, no hot-path change. Read-only.
"""

from __future__ import annotations

from typing import Any

import db
import pandas as pd
import streamlit as st


def render() -> None:
    _DELIVERY_ICON = {
        "sent": "✅ sent",
        "pending": "⏳ pending",
        "in_flight": "🚚 in flight",
        "failed_transient": "🔁 failed (transient)",
        "failed_permanent": "❌ failed (permanent)",
        "skipped": "⚪ skipped",
    }

    st.title("📨 Advisory Journey")
    st.caption(
        "One advisory, trigger → compose → message → delivery. Sourced from `ai_suggestions`."
    )

    def _fmt(v: Any) -> str:
        return "—" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v)

    try:
        plots_df = db.df(
            "SELECT DISTINCT plot_id FROM ai_suggestions WHERE plot_id IS NOT NULL ORDER BY plot_id"
        )
    except Exception as exc:
        st.warning(f"Could not read `ai_suggestions`.\n\n`{str(exc)[:200]}`")
        return

    c1, c2, c3 = st.columns([2, 1, 1])
    plot = c1.selectbox("Plot", ["(all)", *plots_df["plot_id"].tolist()])
    stype = c2.selectbox("Type", ["(all)", "alert", "daily", "weekly", "monthly", "end_of_season"])
    hours = c3.selectbox("Window", [24, 72, 168, 720], index=2, format_func=lambda h: f"last {h}h")

    where = ["generated_at >= now() - make_interval(hours => :h)"]
    params: dict[str, Any] = {"h": int(hours)}
    if plot != "(all)":
        where.append("plot_id = :p")
        params["p"] = plot
    if stype != "(all)":
        where.append("suggestion_type = :st")
        params["st"] = stype

    rows = db.df(
        "SELECT suggestion_id, generated_at, plot_id, suggestion_type, rule_id, "
        "crop_age_days, crop_stage, soil_moisture_at_time, ndvi_at_time, "
        "ai_model_version, prompt_template_version, tokens_used, generation_time_ms, llm_cost_inr, "
        "full_message_marathi, delivery_status, delivery_attempts, delivery_claimed_at, "
        "delivery_next_retry_at, delivery_last_error, delivery_provider_message_id, "
        "whatsapp_sent, whatsapp_sent_at "
        f"FROM ai_suggestions WHERE {' AND '.join(where)} ORDER BY generated_at DESC LIMIT 300",
        params,
    )

    if rows.empty:
        st.info("No advisories match these filters in this window.")
        return

    picker = rows[
        ["generated_at", "plot_id", "suggestion_type", "rule_id", "delivery_status"]
    ].copy()
    picker.insert(0, "#", range(len(picker)))
    st.dataframe(picker, use_container_width=True, hide_index=True)

    idx = st.number_input("Inspect advisory # (0 = most recent)", 0, len(rows) - 1, 0, 1)
    row = rows.iloc[int(idx)]

    st.divider()
    st.subheader(f"{row['plot_id']} · {row['suggestion_type']} · {row['generated_at']}")

    # 1 · trigger + context
    st.markdown("### 1 · Trigger & context")
    t1, t2, t3 = st.columns(3)
    t1.metric("Rule", _fmt(row["rule_id"]))
    t1.metric("Type", _fmt(row["suggestion_type"]))
    t2.metric("Crop age (days)", _fmt(row["crop_age_days"]))
    t2.metric("Crop stage", _fmt(row["crop_stage"]))
    t3.metric("Soil moisture @ compose", _fmt(row["soil_moisture_at_time"]))
    t3.metric("NDVI @ compose", _fmt(row["ndvi_at_time"]))

    # 2 · compose
    st.markdown("### 2 · Compose (LLM)")
    c1_, c2_, c3_ = st.columns(3)
    c1_.metric("Model", _fmt(row["ai_model_version"]))
    c1_.metric("Prompt template", _fmt(row["prompt_template_version"]))
    c2_.metric("Tokens", _fmt(row["tokens_used"]))
    c2_.metric("Latency (ms)", _fmt(row["generation_time_ms"]))
    c3_.metric("Cost (₹)", _fmt(row["llm_cost_inr"]))
    log_only = not bool(row["whatsapp_sent"]) and row["delivery_status"] in (
        None,
        "skipped",
        "pending",
    )
    c3_.metric("Mode", "log-only" if log_only else "live")

    # 3 · message + disclaimer
    st.markdown("### 3 · Rendered message")
    msg = row["full_message_marathi"]
    if msg:
        st.text_area("full_message_marathi", value=str(msg), height=200, disabled=True)
        has_disclaimer = any(
            k in str(msg) for k in ("सल्ला", "डॉक्टर", "तज्ञ", "disclaimer", "Disclaimer")
        )
        (st.success if has_disclaimer else st.warning)(
            "Disclaimer detected in the message."
            if has_disclaimer
            else "No disclaimer marker found."
        )
    else:
        st.caption("No rendered message stored (compose may have skipped or been log-only).")

    # 4 · delivery state machine
    st.markdown("### 4 · Delivery")
    d_status = row["delivery_status"]
    st.markdown(f"**Status:** {_DELIVERY_ICON.get(str(d_status), _fmt(d_status))}")
    d1, d2, d3 = st.columns(3)
    d1.metric("Attempts", _fmt(row["delivery_attempts"]))
    d1.metric("WhatsApp sent", "yes" if row["whatsapp_sent"] else "no")
    d2.metric("Claimed at", _fmt(row["delivery_claimed_at"]))
    d2.metric("Sent at", _fmt(row["whatsapp_sent_at"]))
    d3.metric("Next retry", _fmt(row["delivery_next_retry_at"]))
    d3.metric("Provider msg id", _fmt(row["delivery_provider_message_id"]))
    if row["delivery_last_error"]:
        st.error(f"Last delivery error: `{row['delivery_last_error']}`")
