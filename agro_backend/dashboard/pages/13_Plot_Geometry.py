"""Plot Geometry — capture the water-budget geometry for the active season.

The water-budget engine (D03-WB rules) scales one drip pipe's flow reading up to
a per-plant dose. To do that it needs the plot's physical layout. Until every
field below is set, rule **D03-WB-008** keeps firing ``geometry_incomplete`` and
the dose/deficit numbers fall back to the coarse ``plants_per_acre x area``
estimate.

This is the pilot's capture surface for that layout (the farmer app will take it
over later). It writes the same ``crop_seasons`` columns the Farm-Brain mapper
reads, so a completed form here makes the engine run accurately from the next
06:30 batch.

Like the Data Entry page, this WRITES (via ``db.execute_write``) and is
NOT-NULL-safe: a blank field / "(keep)" leaves the stored value untouched.
"""

from __future__ import annotations

import db
import streamlit as st

# The active pilot Ginger season — same lookup the Data Entry page uses.
_SEASON_LOOKUP = (
    "plot_id = 'PLOT_PILOT_001' AND crop_name_english = 'Ginger' AND season_status = 'active'"
)

# The five fields D03-WB-008 / geometry_incomplete() require to be present.
# (planting_layout is the plot's planting method for the water-budget gate.)
_GATE_FIELDS = (
    "planting_layout",
    "dripper_spacing_cm",
    "drippers_per_acre",
    "rows_per_bed",
    "plants_per_acre",
)

_PLANTING_LAYOUTS = ["flat_bed", "ridge_furrow", "broad_ridge"]
_PIPE_POSITIONS = ["first", "middle", "last", "representative"]

st.title("🌱 Plot Geometry")
st.caption(
    "Capture the plot layout the water-budget engine needs. "
    "Blank / “(keep)” leaves a value unchanged."
)

row = db.fetch_row(f"SELECT * FROM crop_seasons WHERE {_SEASON_LOOKUP} LIMIT 1")
if not row:
    st.warning(
        "No active Ginger season found for PLOT_PILOT_001. "
        "Create it on the Data Entry page (or run seed_pilot) first."
    )
    st.stop()


def _num(raw: str):
    """'' -> None; else int (no dot) or float. Raises ValueError on junk."""
    raw = raw.strip()
    if raw == "":
        return None
    return float(raw) if ("." in raw or "e" in raw.lower()) else int(raw)


def _select(label: str, col: str, options: list[str], *, help: str | None = None) -> None:
    current = row.get(col)
    opts = ["(keep)", *options]
    idx = opts.index(current) if current in options else 0
    st.selectbox(label, opts, index=idx, key=col, help=help)


def _text_num(label: str, col: str, *, help: str | None = None) -> None:
    current = row.get(col)
    st.text_input(label, value="" if current is None else str(current), key=col, help=help)


# --- Completeness banner (reflects STORED state; refreshes after each save) ---
# `row` is re-read from the DB on every rerun, so this updates the moment a save
# commits. It is deliberately not keystroke-live: Streamlit forms defer widget
# values until submit, so an in-form edit only counts once you press Save.
missing_now = [c for c in _GATE_FIELDS if row.get(c) in (None, "")]
if missing_now:
    st.error(
        "**Geometry incomplete** (as saved) — D03-WB-008 will keep prompting. Still needed: "
        + ", ".join(f"`{c}`" for c in missing_now)
    )
else:
    st.success("**Geometry complete** — the water-budget engine will run accurately.")

st.divider()

with st.form("plot_geometry"):
    st.subheader("Planting method & bed")
    _select(
        "Planting layout",
        "planting_layout",
        _PLANTING_LAYOUTS,
        help="The plot's planting method. Required — clears the geometry gate.",
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        _text_num("Bed height (cm)", "bed_height_cm")
    with c2:
        _text_num("Bed width (cm)", "bed_width_cm")
    with c3:
        _text_num("Furrow width (cm)", "furrow_width_cm")
    c4, c5 = st.columns(2)
    with c4:
        _text_num("Rows per bed", "rows_per_bed", help="Required for the geometry gate.")
    with c5:
        _text_num("Planting depth (cm)", "planting_depth_cm")

    st.subheader("Plant density")
    _text_num(
        "Plants per acre",
        "plants_per_acre",
        help="Required. Used with plot area for the whole-plot plant estimate.",
    )

    st.subheader("Drip layout & flow sensor")
    c6, c7 = st.columns(2)
    with c6:
        _text_num("Dripper spacing (cm)", "dripper_spacing_cm", help="Required for the gate.")
    with c7:
        _text_num("Drippers per acre", "drippers_per_acre", help="Required for the gate.")
    _select(
        "Flow-sensor pipe position",
        "sensor_pipe_position",
        _PIPE_POSITIONS,
        help="Which drip pipe the flow sensor sits on — how representative the "
        "measured pipe is of the whole plot.",
    )

    submitted = st.form_submit_button("💾 Save geometry", type="primary")

if submitted:
    _NUMERIC_COLS = {
        "bed_height_cm",
        "bed_width_cm",
        "furrow_width_cm",
        "rows_per_bed",
        "planting_depth_cm",
        "plants_per_acre",
        "dripper_spacing_cm",
        "drippers_per_acre",
    }
    updates: dict[str, object] = {}
    errors: list[str] = []

    for col in ("planting_layout", "sensor_pipe_position"):
        v = st.session_state.get(col)
        if v and v != "(keep)":
            updates[col] = v

    for col in _NUMERIC_COLS:
        raw = st.session_state.get(col, "")
        try:
            val = _num(raw)
        except ValueError:
            errors.append(f"{col}: “{raw}” is not a number")
            continue
        if val is not None:
            updates[col] = val

    if errors:
        st.error("Fix these and save again:\n\n- " + "\n- ".join(errors))
        st.stop()
    if not updates:
        st.info("Nothing to save — every field was left blank / “(keep)”.")
        st.stop()

    sets = ", ".join(f'"{c}" = :{c}' for c in updates)
    n = db.execute_write(
        f"UPDATE crop_seasons SET {sets} WHERE {_SEASON_LOOKUP}",
        updates,
    )
    st.success(f"Saved {len(updates)} field(s) to the active season ({n} row).")
    st.caption("The completeness banner above reflects the newly-saved values.")
