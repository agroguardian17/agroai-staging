"""Ginger Engine knowledge base — the loaded rule set that drives advisories."""

from __future__ import annotations

import db
import streamlit as st

st.set_page_config(page_title="Ginger KB", page_icon="🫚", layout="wide")
st.title("🫚 Ginger Engine — Knowledge Base")
st.caption("The authored rule engine loaded into Postgres (kb_* tables).")

# Headline counts across the KB.
kb = db.df(
    """
    SELECT c.relname AS table, COALESCE(s.n_live_tup, 0) AS rows
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
    WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relname LIKE 'kb\\_%'
    ORDER BY rows DESC
    """
)
st.dataframe(kb, use_container_width=True, hide_index=True, height=320)

st.divider()

if int(db.scalar("SELECT count(*) FROM kb_rules") or 0):
    st.subheader("Rules")
    rules = db.df("SELECT * FROM kb_rules LIMIT 1000")
    st.caption(f"{len(rules)} rules")
    st.dataframe(rules, use_container_width=True, hide_index=True)

    st.subheader("Golden tests")
    st.dataframe(
        db.df("SELECT * FROM kb_golden_tests LIMIT 1000"),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("Knowledge base not loaded.")
