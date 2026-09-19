"""Data Entry — add / change the pilot's DB fields (no more manual SQL).

Human-sourced fields (FI / FO / TECH / OPS / DEALER / AGRO) for the pilot's
identity, farm, plot, season, Main Node and installation records, grouped by
source. Widgets follow the intake sheet's suggestions: dropdowns, date pickers,
yes/no, the electricity multi-select, and acre/गुंठा area entry.

Unlike every other dashboard page, this one WRITES (via ``db.execute_write`` on
the separate write engine). To stay NOT-NULL-safe it only writes fields you
actually fill — a blank widget leaves the stored value untouched (it does not
clear it). The field list is generated from the sheet in ``pilot_fields.py``.
"""

from __future__ import annotations

from datetime import date

import db
import pilot_fields as pf
import streamlit as st

GUNTHA_PER_ACRE = 40.0
_TABLE_TITLES = {
    "tenants": "Tenant",
    "farmers": "Farmer",
    "farms": "Farm",
    "plots": "Plot (PLOT_PILOT_001)",
    "crop_seasons": "Crop season (active Ginger)",
    "device_registry": "Main Node (AGR-MN-0001)",
    "technician_installations": "Technician installation",
}

st.title("📝 Data Entry")
st.caption("Add or change the pilot's fields, grouped by source. Blank = leave unchanged.")


def _load_rows() -> dict[str, dict]:
    rows: dict[str, dict] = {}
    for table, meta in pf.RECORDS.items():
        if meta["key"] is not None:
            row = db.fetch_row(
                f'SELECT * FROM "{table}" WHERE {meta["pk"]} = :k', {"k": meta["key"]}
            )
        else:
            row = db.fetch_row(f'SELECT * FROM "{table}" WHERE {meta["lookup"]} LIMIT 1')
        rows[table] = row or {}
    return rows


def _num(raw: str):
    """Parse a numeric string to int (no dot) or float; '' → None. Raises ValueError."""
    raw = raw.strip()
    if raw == "":
        return None
    return float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)


def _render(field: dict, current) -> tuple:
    """Render one widget; return (kind, raw_value) for save-time normalization."""
    key = f"{field['table']}.{field['col']}"
    label = field["label"]
    w = field["widget"]
    helptext = field.get("help") or None

    if w == "select":
        opts = ["(unset)", *field["options"]]
        idx = opts.index(current) if current in field["options"] else 0
        return ("select", st.selectbox(label, opts, index=idx, key=key, help=helptext))
    if w == "multiselect":
        default = [x for x in (current.split(",") if current else []) if x in field["options"]]
        return (
            "multiselect",
            st.multiselect(label, field["options"], default=default, key=key, help=helptext),
        )
    if w == "bool":
        opts = ["(unset)", "Yes", "No"]
        idx = 1 if current is True else 2 if current is False else 0
        return ("bool", st.selectbox(label, opts, index=idx, key=key, help=helptext))
    if w == "date":
        val = current if isinstance(current, date) else None
        return (
            "date",
            st.date_input(label, value=val, key=key, format="YYYY-MM-DD", help=helptext),
        )
    if w == "area":
        c1, c2 = st.columns([3, 1])
        raw = c1.text_input(
            f"{label} (area)", value="" if current is None else str(current), key=key, help=helptext
        )
        unit = c2.radio("unit", ["acre", "गुंठा"], key=f"{key}.unit", horizontal=True)
        return ("area", (raw, unit))
    if w == "textarea":
        return (
            "text",
            st.text_area(
                label, value="" if current is None else str(current), key=key, help=helptext
            ),
        )
    if w == "number":
        return (
            "number",
            st.text_input(
                label, value="" if current is None else str(current), key=key, help=helptext
            ),
        )
    return (
        "text",
        st.text_input(label, value="" if current is None else str(current), key=key, help=helptext),
    )


def _normalize(kind: str, raw):
    """Widget output → DB value, or _SKIP when the user left it blank."""
    if kind == "select":
        return _SKIP if raw == "(unset)" else raw
    if kind == "multiselect":
        return ",".join(raw) if raw else _SKIP
    if kind == "bool":
        return _SKIP if raw == "(unset)" else (raw == "Yes")
    if kind == "date":
        return raw if isinstance(raw, date) else _SKIP
    if kind == "area":
        text, unit = raw
        val = _num(text)  # may raise
        if val is None:
            return _SKIP
        return round(val / GUNTHA_PER_ACRE, 4) if unit == "गुंठा" else val
    if kind == "number":
        val = _num(raw)  # may raise
        return _SKIP if val is None else val
    return _SKIP if str(raw).strip() == "" else str(raw).strip()


_SKIP = object()

rows = _load_rows()
missing = [t for t, r in rows.items() if not r]
if missing:
    st.warning(
        "No row found for: " + ", ".join(missing) + ". Run seed_pilot / load_pilot_sheet first."
    )

with st.form("data_entry"):
    tabs = st.tabs(pf.SOURCES)
    widgets: dict[str, tuple[dict, tuple]] = {}
    for tab, source in zip(tabs, pf.SOURCES, strict=False):
        with tab:
            src_fields = [f for f in pf.FIELDS if f["source"] == source]
            if not src_fields:
                st.info("No fields from this source on the pilot records.")
                continue
            for table in pf.RECORDS:
                tfields = [f for f in src_fields if f["table"] == table]
                if not tfields:
                    continue
                st.subheader(_TABLE_TITLES.get(table, table))
                row = rows.get(table) or {}
                for f in tfields:
                    kind, raw = _render(f, row.get(f["col"]))
                    widgets[f"{table}.{f['col']}"] = (f, (kind, raw))
    submitted = st.form_submit_button("💾 Save all", type="primary")

if submitted:
    # Group provided values by table; skip blanks (NOT-NULL-safe).
    by_table: dict[str, dict] = {}
    errors: list[str] = []
    for _key, (f, (kind, raw)) in widgets.items():
        try:
            value = _normalize(kind, raw)
        except ValueError:
            errors.append(f'{f["label"]}: "{raw}" is not a number')
            continue
        if value is _SKIP:
            continue
        by_table.setdefault(f["table"], {})[f["col"]] = value

    if errors:
        st.error("Fix these and save again:\n\n- " + "\n- ".join(errors))
        st.stop()

    written = []
    for table, cols in by_table.items():
        meta = pf.RECORDS[table]
        pk = meta["pk"]
        if meta["key"] is not None:
            pk_val = meta["key"]
        else:
            found = db.fetch_row(f'SELECT {pk} FROM "{table}" WHERE {meta["lookup"]} LIMIT 1')
            if not found:
                st.error(f"{table}: no target row (active Ginger season) — skipped.")
                continue
            pk_val = found[pk]
        sets = ", ".join(f'"{c}" = :{c}' for c in cols)
        params = {**cols, "_pk": pk_val}
        n = db.execute_write(f'UPDATE "{table}" SET {sets} WHERE "{pk}" = :_pk', params)
        written.append(f"{_TABLE_TITLES.get(table, table)}: {len(cols)} field(s) ({n} row)")

    if written:
        st.success("Saved:\n\n- " + "\n- ".join(written))
        st.caption("Reload the page to see the stored values re-read from the DB.")
    else:
        st.info("Nothing to save — every field was left blank.")
