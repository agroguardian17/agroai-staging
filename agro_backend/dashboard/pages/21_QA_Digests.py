"""QA Digests — the weekly D12 advisory-QA + bias digests (persisted, fix A2).

The weekly job renders two Markdown docs (agronomist report + KB-author bias
digest). They're now persisted to `qa_digest` (durable, not the ephemeral
container FS), so they're viewable here. Read-only.
"""

from __future__ import annotations

import db
import streamlit as st

st.title("📰 QA Digests")
st.caption(
    "Weekly advisory-QA + bias digests. Produced by the `qa_weekly_digest` job (Sun 18:00 IST)."
)

try:
    weeks = db.df("SELECT DISTINCT week_start FROM qa_digest ORDER BY week_start DESC LIMIT 26")
except Exception as exc:
    st.warning(f"Could not read `qa_digest` — is migration 0070 applied?\n\n`{str(exc)[:200]}`")
    st.stop()

if weeks.empty:
    st.info("No digests persisted yet. The job runs Sundays 18:00 IST (or run it manually).")
    st.stop()

week = st.selectbox("Week starting", weeks["week_start"].tolist())
rows = db.df(
    "SELECT kind, filename, content, generated_at FROM qa_digest WHERE week_start = :w ORDER BY kind",
    {"w": week},
)
for _, r in rows.iterrows():
    st.markdown(f"### {r['kind']} — `{r['filename']}`")
    st.caption(f"generated {r['generated_at']}")
    st.markdown(r["content"])
    st.divider()
