"""Crop Scouting — record a per-visit field observation (INSERT).

Time-series scouting log feeding the KB's D05 (pest) / D06 (disease) and growth
rules. One row per scouting visit per plot; the ginger engine reads the latest
row for the plot. Insert form (like the Lab Soil Test page), distinct from the
update-only Data Entry page.

Writes via db.execute_write; SQL identifiers come from the trusted field spec
below (which mirrors the crop_scouting columns and their KB enum values), and
every value is parameterized.
"""

from __future__ import annotations

from datetime import date

import db
import streamlit as st

st.title("🔎 Crop Scouting")
st.caption("Record a field scouting visit. Blank fields are stored as NULL (not observed).")

# (col, label, kind, enum_options|None, group) — mirrors crop_scouting columns.
FIELDS = [
    ("emergence_started", "emergence started", "bool", None, "Growth"),
    ("establishment_pct", "establishment pct", "number", None, "Growth"),
    ("tillers_per_plant", "tillers per plant", "number", None, "Growth"),
    ("flowering_observed", "flowering observed", "bool", None, "Growth"),
    ("central_shoot_dead", "central shoot dead", "bool", None, "Growth"),
    ("seed_sprouts_visible", "seed sprouts visible", "bool", None, "Growth"),
    ("shoot_borer_incidence_pct", "shoot borer incidence pct", "number", None, "Pest"),
    ("leaf_roller_incidence_pct", "leaf roller incidence pct", "number", None, "Pest"),
    ("rhizome_fly_incidence_pct", "rhizome fly incidence pct", "number", None, "Pest"),
    ("white_grub_suspected", "white grub suspected", "bool", None, "Pest"),
    ("nematode_suspected", "nematode suspected", "bool", None, "Pest"),
    ("leaf_caterpillar_observed", "leaf caterpillar observed", "bool", None, "Pest"),
    ("light_trap_installed", "light trap installed", "bool", None, "Pest"),
    ("light_trap_count_nightly", "light trap count nightly", "number", None, "Pest"),
    ("straight_line_holes_in_whorl", "straight line holes in whorl", "bool", None, "Pest"),
    ("stem_hole_with_webbing", "stem hole with webbing", "bool", None, "Pest"),
    ("exposed_rhizomes_observed", "exposed rhizomes observed", "bool", None, "Pest"),
    ("rot_incidence_pct", "rot incidence pct", "number", None, "Disease"),
    ("wilt_incidence_pct", "wilt incidence pct", "number", None, "Disease"),
    ("leaf_spot_incidence_pct", "leaf spot incidence pct", "number", None, "Disease"),
    ("wilt_while_green", "wilt while green", "bool", None, "Disease"),
    ("leaf_spot_rings_visible", "leaf spot rings visible", "bool", None, "Disease"),
    (
        "ooze_test_result",
        "ooze test result",
        "select",
        ["not_done", "milky_thread", "no_thread"],
        "Disease",
    ),
    ("rhizome_texture", "rhizome texture", "select", ["firm", "mushy_wet", "dry_rot"], "Disease"),
    ("rhizome_smell", "rhizome smell", "select", ["normal", "sour_foul", "faint"], "Disease"),
    (
        "stem_cut_colour",
        "stem cut colour",
        "select",
        ["brown_black", "greyish_yellow", "brown_vascular", "normal"],
        "Disease",
    ),
    (
        "stem_ooze_type",
        "stem ooze type",
        "select",
        ["none", "watery_foul", "milky_yellowish"],
        "Disease",
    ),
    ("soft_rhizome_found", "soft rhizome found", "bool", None, "Disease"),
    ("plant_pulls_easily", "plant pulls easily", "bool", None, "Disease"),
    ("shoot_pulls_out_easily", "shoot pulls out easily", "bool", None, "Disease"),
    (
        "leaf_yellowing_pattern",
        "leaf yellowing pattern",
        "select",
        [
            "uniform_old",
            "interveinal_new",
            "interveinal_old",
            "small_new_leaves",
            "margin_scorch",
            "with_soft_stem",
            "sudden_green_wilt",
            "none",
        ],
        "Disease",
    ),
    (
        "skin_scrape_result",
        "skin scrape result",
        "select",
        ["not_done", "peels_easily", "firmly_attached"],
        "Disease",
    ),
    ("sample_dig_120_done", "sample dig 120 done", "bool", None, "Growth"),
    ("sample_dig_180_done", "sample dig 180 done", "bool", None, "Growth"),
    ("standing_water_hours_observed", "standing water hours observed", "number", None, "Growth"),
    ("harvest_injury_observed", "harvest injury observed", "bool", None, "Growth"),
    ("moisture_pct_final", "moisture pct final", "number", None, "Growth"),
]


def _num(rawv: str):
    rawv = (rawv or "").strip()
    if rawv == "":
        return None
    return float(rawv)


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
if plots.empty:
    st.warning("This farm has no plots.")
    st.stop()
plot_id = st.selectbox("Plot", plots["plot_id"].tolist())

_GROUPS = ["Growth", "Pest", "Disease"]

with st.form("crop_scouting"):
    c1, c2, c3 = st.columns(3)
    scouting_date = c1.date_input("Scouting date", value=date.today(), format="YYYY-MM-DD")
    scouted_by = c2.text_input("Scouted by")
    growth_stage_observed = c3.text_input("Growth stage observed")

    raw: dict[str, object] = {}
    for group in _GROUPS:
        gfields = [f for f in FIELDS if f[4] == group]
        st.subheader(group)
        cols = st.columns(3)
        for i, (col, label, kind, opts, _g) in enumerate(gfields):
            slot = cols[i % 3]
            if kind == "bool":
                choice = slot.selectbox(label, ["—", "Yes", "No"], key=col)
                raw[col] = None if choice == "—" else (choice == "Yes")
            elif kind == "select":
                choice = slot.selectbox(label, ["—", *opts], key=col)
                raw[col] = None if choice == "—" else choice
            else:
                raw[col] = slot.text_input(label, key=col)

    notes = st.text_area("Notes")
    submitted = st.form_submit_button("💾 Save scouting", type="primary")

if submitted:
    values: dict[str, object] = {}
    errors: list[str] = []
    for col, label, kind, _opts, _g in FIELDS:
        v = raw[col]
        if kind == "number":
            try:
                v = _num(v)  # type: ignore[arg-type]
            except ValueError:
                errors.append(f'{label}: "{raw[col]}" is not a number')
                continue
        if v is not None:
            values[col] = v

    if errors:
        st.error("Fix these and save again:\n\n- " + "\n- ".join(errors))
        st.stop()

    # Resolve the active season for the plot (optional FK).
    srow = db.fetch_row(
        "SELECT season_id::text AS season_id FROM crop_seasons "
        "WHERE plot_id = :pid AND season_status = 'active' "
        "ORDER BY sowing_date DESC LIMIT 1",
        {"pid": plot_id},
    )
    fixed: dict[str, object] = {
        "tenant_id": tenant_id,
        "farm_id": farm_id,
        "plot_id": plot_id,
        "scouting_date": scouting_date,
    }
    if srow:
        fixed["season_id"] = srow["season_id"]
    if scouted_by.strip():
        fixed["scouted_by"] = scouted_by.strip()
    if growth_stage_observed.strip():
        fixed["growth_stage_observed"] = growth_stage_observed.strip()
    if notes.strip():
        fixed["notes"] = notes.strip()

    all_vals = {**fixed, **values}
    names = list(all_vals)

    def _ph(name: str) -> str:
        if name in ("tenant_id", "farm_id", "season_id"):
            return f"CAST(:{name} AS uuid)"
        if name == "scouting_date":
            return f"CAST(:{name} AS date)"
        return f":{name}"

    sql = (
        f"INSERT INTO crop_scouting ({', '.join(names)}) "
        f"VALUES ({', '.join(_ph(n) for n in names)})"
    )
    db.execute_write(sql, all_vals)
    st.success(
        f"Saved scouting for **{plot_id}** on {scouting_date}. "
        f"{len(values)} observation(s) recorded."
    )
    st.caption("The next ginger run reads the latest scouting row for this plot.")

# ---- Recent scoutings for this plot --------------------------------------
st.divider()
st.subheader("Recent scoutings — this plot")
recent = db.df(
    "SELECT scouting_date, scouted_by, rot_incidence_pct, wilt_incidence_pct, "
    "shoot_borer_incidence_pct, leaf_spot_incidence_pct, establishment_pct "
    "FROM crop_scouting WHERE plot_id = :pid ORDER BY scouting_date DESC LIMIT 20",
    {"pid": plot_id},
)
if recent.empty:
    st.info("No scouting recorded for this plot yet.")
else:
    st.dataframe(recent, use_container_width=True, hide_index=True)
