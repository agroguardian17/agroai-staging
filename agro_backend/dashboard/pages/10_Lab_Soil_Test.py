"""Lab Soil Test — record a soil-lab report (INSERT, one row per test).

Unlike the Data Entry page (which *updates* the fixed pilot records), this page
*inserts* a new ``lab_soil_tests`` row each time — a farm is re-tested across
seasons and every result is kept. The KB's D02/D04/D10 nutrient rules read the
chemistry columns (organic carbon, EC, free lime, micronutrients) named to
match ``kb_farm_brain_fields``; the rest of a standard lab report is stored too
for the future soil-composition engine.

Writes via ``db.execute_write`` (the separate write engine). SQL identifiers
come from the trusted field spec below; every value is parameterized.
"""

from __future__ import annotations

from datetime import date

import db
import streamlit as st

st.title("🧪 Lab Soil Test")
st.caption("Record a soil-lab report. Blank fields are stored as NULL (unknown).")

# Numeric fields: (column, label, group). Column names are the trusted, fixed
# lab_soil_tests schema — never user-supplied.
_KB_CHEM = [
    ("soil_oc_pct", "Organic carbon — OC (%)"),
    ("soil_ec", "EC (dS/m)"),
    ("soil_free_lime_pct", "Free lime — CaCO₃ (%)"),
    ("soil_zn_ppm", "Zinc — Zn (ppm)"),
    ("soil_fe_ppm", "Iron — Fe (ppm)"),
    ("soil_ca_ppm", "Calcium — Ca (ppm)"),
    ("soil_mg_ppm", "Magnesium — Mg (ppm)"),
    ("soil_s_ppm", "Sulphur — S (ppm)"),
]
_FULL_LAB = [
    ("soil_ph_lab", "pH (lab)"),
    ("soil_n_kg_per_ha", "Nitrogen — N (kg/ha)"),
    ("soil_p_kg_per_ha", "Phosphorus — P (kg/ha)"),
    ("soil_k_kg_per_ha", "Potassium — K (kg/ha)"),
    ("soil_b_ppm", "Boron — B (ppm)"),
    ("sand_pct", "Sand (%)"),
    ("silt_pct", "Silt (%)"),
    ("clay_pct", "Clay (%)"),
]
_NUM_COLS = [c for c, _ in (_KB_CHEM + _FULL_LAB)]


def _num(raw: str):
    """Parse a numeric string; '' → None. Raises ValueError on junk."""
    raw = (raw or "").strip()
    if raw == "":
        return None
    return float(raw)


# ---- Farm + plot pickers --------------------------------------------------
farms = db.df(
    "SELECT farm_id::text AS farm_id, tenant_id::text AS tenant_id, "
    "COALESCE(farm_name, farm_id::text) AS label FROM farms ORDER BY label"
)
if farms.empty:
    st.warning("No farms in the database yet.")
    st.stop()

farm_map = {r.label: (r.farm_id, r.tenant_id) for r in farms.itertuples()}
farm_label = st.selectbox("Farm", list(farm_map))
farm_id, tenant_id = farm_map[farm_label]

plots = db.df(
    "SELECT plot_id FROM plots WHERE farm_id = CAST(:fid AS uuid) ORDER BY plot_id",
    {"fid": farm_id},
)
plot_opts = ["(whole farm)", *plots["plot_id"].tolist()]
plot_choice = st.selectbox("Plot (optional)", plot_opts)
plot_id = None if plot_choice == "(whole farm)" else plot_choice

# ---- Entry form -----------------------------------------------------------
with st.form("lab_soil_test"):
    c1, c2 = st.columns(2)
    sample_date = c1.date_input("Sample date", value=date.today(), format="YYYY-MM-DD")
    lab_name = c2.text_input("Lab name")
    report_reference = st.text_input("Report reference (id / URL)")

    st.subheader("KB nutrient chemistry")
    st.caption("These feed the ginger nutrient rules (D02 / D04 / D10).")
    raw: dict[str, str] = {}
    cols = st.columns(4)
    for i, (col, label) in enumerate(_KB_CHEM):
        raw[col] = cols[i % 4].text_input(label, key=col)

    st.subheader("Full lab report")
    st.caption("Stored for the soil-composition engine; not read by the KB yet.")
    cols2 = st.columns(4)
    for i, (col, label) in enumerate(_FULL_LAB):
        raw[col] = cols2[i % 4].text_input(label, key=col)

    notes = st.text_area("Notes")
    submitted = st.form_submit_button("💾 Save soil test", type="primary")

if submitted:
    # Parse numerics; collect errors.
    values: dict[str, object] = {}
    errors: list[str] = []
    for col, label in _KB_CHEM + _FULL_LAB:
        try:
            v = _num(raw[col])
        except ValueError:
            errors.append(f'{label}: "{raw[col]}" is not a number')
            continue
        if v is not None:
            values[col] = v

    # Soft sanity check: sand + silt + clay should be ~100 when all given.
    texture = [values.get(k) for k in ("sand_pct", "silt_pct", "clay_pct")]
    if all(t is not None for t in texture):
        total = sum(float(t) for t in texture)  # type: ignore[arg-type]
        if abs(total - 100.0) > 2.0:
            st.warning(f"Sand + silt + clay = {total:.0f}% (expected ≈100%). Saved anyway.")

    if errors:
        st.error("Fix these and save again:\n\n- " + "\n- ".join(errors))
        st.stop()
    if not values:
        st.info("Nothing to save — enter at least one measurement.")
        st.stop()

    # Build the INSERT. Identifiers are from the trusted spec; values bound.
    fixed: dict[str, object] = {
        "tenant_id": tenant_id,
        "farm_id": farm_id,
        "sample_date": sample_date,
    }
    if plot_id:
        fixed["plot_id"] = plot_id
    if lab_name.strip():
        fixed["lab_name"] = lab_name.strip()
    if report_reference.strip():
        fixed["report_reference"] = report_reference.strip()
    if notes.strip():
        fixed["notes"] = notes.strip()

    all_vals = {**fixed, **values}
    names = list(all_vals)

    def _ph(name: str) -> str:
        if name in ("tenant_id", "farm_id"):
            return f"CAST(:{name} AS uuid)"
        if name == "sample_date":
            return f"CAST(:{name} AS date)"
        return f":{name}"

    sql = (
        f"INSERT INTO lab_soil_tests ({', '.join(names)}) "
        f"VALUES ({', '.join(_ph(n) for n in names)})"
    )
    db.execute_write(sql, all_vals)
    st.success(
        f"Saved soil test for **{farm_label}** "
        f"({plot_id if plot_id else 'whole farm'}), sampled {sample_date}. "
        f"{len(values)} measurement(s) recorded."
    )
    st.caption("The next ginger run reads the latest test for this farm.")

# ---- Recent tests for this farm ------------------------------------------
st.divider()
st.subheader("Recent tests — this farm")
recent = db.df(
    "SELECT sample_date, COALESCE(plot_id, '(whole farm)') AS plot, lab_name, "
    "soil_oc_pct, soil_ec, soil_zn_ppm, soil_fe_ppm, soil_s_ppm, soil_free_lime_pct "
    "FROM lab_soil_tests WHERE farm_id = CAST(:fid AS uuid) "
    "ORDER BY sample_date DESC LIMIT 20",
    {"fid": farm_id},
)
if recent.empty:
    st.info("No soil tests recorded for this farm yet.")
else:
    st.dataframe(recent, use_container_width=True, hide_index=True)
