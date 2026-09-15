"""Data Explorer — browse any relation in the database, read-only.

This is the "everything is reachable" page: every one of the ~99 relations
(tables + partitions) shows up here with its row count, columns, and most-recent
rows, so nothing in the schema is invisible to the team.
"""

from __future__ import annotations

import db
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Data Explorer", page_icon="🗂️", layout="wide")
st.title("🗂️ Data Explorer")

rel = db.relations()
st.caption(f"{len(rel)} relations · {int((rel['approx_rows'] > 0).sum())} populated")

# Overview table of every relation, with a populated/empty filter.
only_pop = st.checkbox("Only populated tables", value=False)
view = rel[rel["approx_rows"] > 0] if only_pop else rel
st.dataframe(view, use_container_width=True, hide_index=True, height=260)

st.divider()

# Pick one relation and inspect it.
names = rel["table"].tolist()
default_ix = names.index("ai_suggestions") if "ai_suggestions" in names else 0
table = st.selectbox("Inspect a table", names, index=default_ix)

cols = db.columns(table)
n = int(db.scalar(f"SELECT count(*) FROM {table}") or 0)
c1, c2 = st.columns(2)
c1.metric("Rows", f"{n:,}")
c2.metric("Columns", len(cols))

# Order by a sensible recency column when present, else primary- key-ish.
order_candidates = [
    "generated_at",
    "received_at",
    "recorded_at",
    "triggered_at",
    "created_at",
    "timestamp",
]
order_col = next((c for c in order_candidates if c in cols), cols[0] if cols else None)
limit = st.slider("Rows to show", 10, 500, 100, step=10)

if order_col:
    order_dir = st.radio("Order", ["newest first", "oldest first"], horizontal=True)
    direction = "DESC" if order_dir == "newest first" else "ASC"
    rows = db.df(
        f'SELECT * FROM "{table}" ORDER BY "{order_col}" {direction} LIMIT :lim', {"lim": limit}
    )
else:
    rows = db.df(f'SELECT * FROM "{table}" LIMIT :lim', {"lim": limit})

st.dataframe(rows, use_container_width=True, hide_index=True)

# Let the team pull a table down for offline analysis.
if not rows.empty:
    st.download_button(
        "Download shown rows (CSV)",
        data=rows.to_csv(index=False).encode(),
        file_name=f"{table}.csv",
        mime="text/csv",
    )
else:
    st.info("This table is empty — likely awaiting hardware or activity.")

with st.expander("Columns"):
    st.write(pd.DataFrame({"column": cols}))
