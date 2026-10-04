"""Daily Run Inspector — the downstream half of the pipeline.

For each plot's 06:30 ginger run the job records a `plot_run_trace` row (when
`PIPELINE_TRACE_ENABLED` is on): farm-brain field coverage, the key derived KB
values, which rules the engine fired, and how many advisories were written. This
page lets ops see why a plot got (or didn't get) an advisory, and whether low
field coverage is starving the rules. Read-only.
"""

from __future__ import annotations

import json
from typing import Any

import db
import pandas as pd
import streamlit as st

_STAGES = [
    ("s8_farm_brain", "8 · Farm Brain"),
    ("s9_kb_engine", "9 · KB engine"),
    ("s10_advisory", "10 · Advisory"),
]
_ICON = {"ok": "✅", "warn": "⚠️", "fail": "❌", "skipped": "⚪"}

st.title("🗓️ Daily Run Inspector")
st.caption(
    "Per-plot daily pipeline: farm-brain → KB engine → advisory. Needs "
    "`PIPELINE_TRACE_ENABLED=true`."
)


def _obj(v: Any) -> Any:
    if isinstance(v, dict | list):
        return v
    if isinstance(v, str) and v:
        try:
            return json.loads(v)
        except ValueError:
            return {}
    return {} if v is None else v


try:
    plots_df = db.df(
        "SELECT DISTINCT plot_id FROM plot_run_trace WHERE plot_id IS NOT NULL ORDER BY plot_id"
    )
except Exception as exc:
    st.warning(
        "Could not read `plot_run_trace`. Is migration 0065 applied and "
        f"`PIPELINE_TRACE_ENABLED` on?\n\n`{str(exc)[:200]}`"
    )
    st.stop()

c1, c2 = st.columns([2, 1])
plot = c1.selectbox("Plot", ["(all)", *plots_df["plot_id"].tolist()])
days = c2.selectbox("Window", [7, 30, 90], index=1, format_func=lambda d: f"last {d}d")

where = ["created_at >= now() - make_interval(days => :d)"]
params: dict[str, Any] = {"d": int(days)}
if plot != "(all)":
    where.append("plot_id = :p")
    params["p"] = plot

rows = db.df(
    f"SELECT trace_id, created_at, run_date, plot_id, overall, advisories_written, error, "
    f"coverage, derived, engine, stages, validations FROM plot_run_trace "
    f"WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200",
    params,
)
if rows.empty:
    st.info("No daily-run traces in this window.")
    st.stop()

# --- run list ---------------------------------------------------------------
summary = rows[["run_date", "plot_id", "overall", "advisories_written", "error"]].copy()
summary["coverage"] = rows["coverage"].apply(lambda c: _obj(c).get("coverage_pct"))
summary["rules_fired"] = rows["engine"].apply(lambda e: _obj(e).get("messages"))
summary.insert(0, "#", range(len(summary)))
st.dataframe(summary, use_container_width=True, hide_index=True)

idx = st.number_input("Inspect run #", min_value=0, max_value=len(rows) - 1, value=0, step=1)
row = rows.iloc[int(idx)]

st.divider()
st.subheader(
    f"{row['plot_id']} · run {row['run_date']} · {_ICON.get(row['overall'], '')} "
    f"{row['overall'].upper()}"
)
if row["error"]:
    st.error(f"**Run failed:** `{row['error']}`")

# --- stage checklist --------------------------------------------------------
stages = _obj(row["stages"])
cols = st.columns(len(_STAGES))
for col, (key, label) in zip(cols, _STAGES, strict=False):
    s = stages.get(key, {})
    status = s.get("status") if isinstance(s, dict) else None
    extra = ""
    if key == "s8_farm_brain" and isinstance(s, dict):
        extra = f"\n\ncoverage {s.get('coverage_pct')}"
    elif key == "s9_kb_engine" and isinstance(s, dict):
        extra = f"\n\n{s.get('rules_fired')} rules"
    elif key == "s10_advisory" and isinstance(s, dict):
        extra = f"\n\n{s.get('advisories_written')} written"
    col.markdown(f"**{label}**\n\n{_ICON.get(status, '—')} {status or 'n/a'}{extra}")

# --- farm-brain coverage ----------------------------------------------------
cov = _obj(row["coverage"])
st.markdown("### Farm-Brain coverage")
mc1, mc2, mc3 = st.columns(3)
mc1.metric("Filled", cov.get("filled"))
mc2.metric("Unknown", cov.get("unknown"))
pct = cov.get("coverage_pct")
mc3.metric("Coverage", f"{pct:.0%}" if isinstance(pct, int | float) else "n/a")
unk = cov.get("unknown_sample") or []
if unk:
    with st.expander(f"Unknown fields (sample of {len(unk)})"):
        st.write(", ".join(unk))

# --- derived KB values + engine --------------------------------------------
dc1, dc2 = st.columns(2)
with dc1:
    st.markdown("#### Key derived values")
    derived = _obj(row["derived"])
    st.dataframe(
        pd.DataFrame(sorted(derived.items()), columns=["field", "value"]),
        use_container_width=True,
        hide_index=True,
    )
with dc2:
    st.markdown("#### Engine")
    eng = _obj(row["engine"])
    st.write(f"**Rules fired:** {eng.get('messages')}")
    rule_ids = [r for r in (eng.get("rule_ids") or []) if r]
    if rule_ids:
        st.write("**Rule IDs:** " + ", ".join(f"`{r}`" for r in rule_ids))
    deliv = eng.get("delivery") or {}
    if deliv:
        st.write("**Delivery classes:**")
        st.dataframe(
            pd.DataFrame(sorted(deliv.items()), columns=["rule", "delivery"]),
            use_container_width=True,
            hide_index=True,
        )

# --- validations ------------------------------------------------------------
findings = _obj(row["validations"])
st.markdown("### Validation checklist")
if findings:
    st.dataframe(pd.DataFrame(findings), use_container_width=True, hide_index=True)
else:
    st.success("No run-level findings.")
