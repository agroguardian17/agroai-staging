"""Season & Scheme Records — upsert per-season economics/operations and
per-farmer scheme state (one row each; INSERT ... ON CONFLICT DO UPDATE).

Feeds the KB's D13 (economics), D03/D05/D06/D08 (operations) and D10 (schemes)
rules. Season tables key on the plot's active season; the scheme table keys on
the farm's owner. Writes via db.execute_write; identifiers come from the trusted
spec below, values parameterized.
"""

from __future__ import annotations

from datetime import datetime

import db
import streamlit as st

st.title("📋 Season & Scheme Records")
st.caption(
    "Update the season economics/operations and farmer scheme records. Blank = leave unchanged."
)

# {table: (key_col, [(col,label,widget,options|None), ...])}
_SPECS = {
    "season_economics": [
        ["breakeven_price_per_quintal", "breakeven price per quintal", "number", None],
        ["breakeven_yield_quintal", "breakeven yield quintal", "number", None],
        ["cash_flow_gap_months", "cash flow gap months", "number", None],
        ["cash_outflow_to_date", "cash outflow to date", "number", None],
        ["ceiling_quintal_per_acre", "ceiling quintal per acre", "number", None],
        ["cost_drainage", "cost drainage", "number", None],
        ["cost_earthing_labour", "cost earthing labour", "number", None],
        ["cost_harvest_transport", "cost harvest transport", "number", None],
        ["cost_micronutrients", "cost micronutrients", "number", None],
        ["cost_mulch", "cost mulch", "number", None],
        ["cost_seed", "cost seed", "number", None],
        ["cost_seed_treatment_planting", "cost seed treatment planting", "number", None],
        ["crop_loan_taken", "crop loan taken", "bool", None],
        ["drip_annual_share", "drip annual share", "number", None],
        ["drip_capital_cost", "drip capital cost", "number", None],
        ["drip_life_years", "drip life years", "number", None],
        ["grade_a_pct", "grade a pct", "number", None],
        ["grade_b_pct", "grade b pct", "number", None],
        ["grade_c_pct", "grade c pct", "number", None],
        ["graded_separately", "graded separately", "bool", None],
        ["intercrop_revenue", "intercrop revenue", "number", None],
        ["interest_cost", "interest cost", "number", None],
        ["land_rent_or_opportunity", "land rent or opportunity", "number", None],
        ["mulch_material_price_per_tonne", "mulch material price per tonne", "number", None],
        ["mulch_quantity_t_per_acre", "mulch quantity t per acre", "number", None],
        ["net_return_per_acre", "net return per acre", "number", None],
        ["sale_market", "sale market", "text", None],
        ["sale_price_per_quintal", "sale price per quintal", "number", None],
        ["seed_opportunity_cost", "seed opportunity cost", "number", None],
        [
            "seed_retained_or_purchased",
            "seed retained or purchased",
            "select",
            ["retained", "purchased", "mixed"],
        ],
        ["total_cost_per_acre", "total cost per acre", "number", None],
        ["transport_cost_per_quintal", "transport cost per quintal", "number", None],
    ],
    "season_operations": [
        ["basal_k_kg_per_acre", "basal k kg per acre", "number", None],
        ["basal_p_kg_per_acre", "basal p kg per acre", "number", None],
        ["castor_bait_prepared_date", "castor bait prepared date", "date", None],
        ["castor_bait_units_per_acre", "castor bait units per acre", "number", None],
        ["drip_runtime_min", "drip runtime min", "number", None],
        ["ethephon_spray_count", "ethephon spray count", "number", None],
        ["fertigation_active", "fertigation active", "bool", None],
        ["fertigation_last_ec_response", "fertigation last ec response", "number", None],
        ["herbicide_post_emergent_date", "herbicide post emergent date", "date", None],
        ["herbicide_pre_emergent_date", "herbicide pre emergent date", "date", None],
        ["irrigation_applied_litres_today", "irrigation applied litres today", "number", None],
        ["kulav_passes", "kulav passes", "number", None],
        ["last_fungicide_date", "last fungicide date", "date", None],
        ["last_fungicide_group", "last fungicide group", "text", None],
        ["last_insecticide_date", "last insecticide date", "date", None],
        ["last_insecticide_group", "last insecticide group", "text", None],
        ["metarhizium_kg_per_acre", "metarhizium kg per acre", "number", None],
        ["naa_spray_count", "naa spray count", "number", None],
        ["weeding_count", "weeding count", "number", None],
    ],
    "farmer_schemes": [
        [
            "cgwb_block_category",
            "cgwb block category",
            "select",
            ["safe", "semi_critical", "critical", "over_exploited", "unverified"],
        ],
        ["cibrc_list_checked_date", "cibrc list checked date", "date", None],
        ["data_review_due", "data review due", "date", None],
        ["drip_subsidy_pct_applicable", "drip subsidy pct applicable", "number", None],
        ["drought_prone_listed", "drought prone listed", "select", ["yes", "no", "unverified"]],
        ["farm_pond_planned", "farm pond planned", "bool", None],
        ["farmer_category", "farmer category", "select", ["small_marginal", "other", "unverified"]],
        ["geo_tagging_done", "geo tagging done", "bool", None],
        ["kvk_contacted", "kvk contacted", "bool", None],
        [
            "pmfby_notified_for_ginger",
            "pmfby notified for ginger",
            "select",
            ["yes", "no", "unverified"],
        ],
        ["pre_sanction_date", "pre sanction date", "date", None],
        ["pre_sanction_received", "pre sanction received", "bool", None],
        [
            "priority_category",
            "priority category",
            "select",
            [
                "martyr_family",
                "suicide_affected",
                "bpl",
                "widow_or_deserted",
                "small_marginal",
                "other",
            ],
        ],
        ["research_centre_contacted", "research centre contacted", "bool", None],
        ["scale_of_finance_per_acre", "scale of finance per acre", "number", None],
        ["seed_supplier_identified", "seed supplier identified", "bool", None],
        ["soil_lab_selected", "soil lab selected", "text", None],
        ["subsidy_applied_date", "subsidy applied date", "date", None],
        ["subsidy_documents_ready", "subsidy documents ready", "bool", None],
        [
            "subsidy_lottery_result",
            "subsidy lottery result",
            "select",
            ["pending", "selected", "not_selected", "not_applied"],
        ],
        ["subsidy_scheme_applied", "subsidy scheme applied", "text", None],
    ],
}
_TABLES = {
    "season_economics": ("season_id", "Economics (D13)"),
    "season_operations": ("season_id", "Field operations (D03/D05/D06/D08)"),
    "farmer_schemes": ("farmer_id", "Govt schemes & subsidy (D10)"),
    "farmer_consent": ("farmer_id", "Consent & data governance (DPDP)"),
}


def _num(raw: str):
    raw = (raw or "").strip()
    return None if raw == "" else float(raw)


def _pdate(raw: str):
    raw = (raw or "").strip()
    if raw == "":
        return None
    return datetime.strptime(raw, "%Y-%m-%d").date()


# ---- Farm -> plot/season + owner resolution ------------------------------
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
season_id = None
if not plots.empty:
    plot_id = st.selectbox("Plot", plots["plot_id"].tolist())
    srow = db.fetch_row(
        "SELECT season_id::text AS season_id FROM crop_seasons "
        "WHERE plot_id = :pid AND season_status = 'active' ORDER BY sowing_date DESC LIMIT 1",
        {"pid": plot_id},
    )
    season_id = srow["season_id"] if srow else None
owner = db.fetch_row(
    "SELECT farmer_id::text AS farmer_id FROM farms WHERE farm_id = CAST(:fid AS uuid)",
    {"fid": farm_id},
)
farmer_id = owner["farmer_id"] if owner else None

key_values = {"season_id": season_id, "farmer_id": farmer_id}
if season_id is None:
    st.info("No active season for this plot — economics/operations need an active Ginger season.")


def _render(col: str, label: str, widget: str, options, keyp: str):
    k = f"{keyp}.{col}"
    if widget == "bool":
        return st.selectbox(label, ["—", "Yes", "No"], key=k)
    if widget == "select":
        return st.selectbox(label, ["—", *options], key=k)
    return st.text_input(label, key=k, help="YYYY-MM-DD" if col.endswith("_date") else None)


with st.form("season_scheme"):
    raw: dict[str, dict[str, object]] = {t: {} for t in _SPECS}
    for table, fields in _SPECS.items():
        keycol, title = _TABLES[table]
        st.subheader(title)
        if key_values[keycol] is None:
            st.caption("No target row key available — this section will be skipped.")
        cols = st.columns(3)
        for i, (col, label, widget, options) in enumerate(fields):
            with cols[i % 3]:
                raw[table][col] = (widget, _render(col, label, widget, options, table))
    submitted = st.form_submit_button("💾 Save all", type="primary")

if submitted:
    errors: list[str] = []
    saved: list[str] = []
    for table, fields in _SPECS.items():
        keycol, title = _TABLES[table]
        keyval = key_values[keycol]
        if keyval is None:
            continue
        vals: dict[str, object] = {}
        for col, label, _widget, _o in fields:
            w, rv = raw[table][col]
            if w == "bool":
                if rv != "—":
                    vals[col] = rv == "Yes"
            elif w == "select":
                if rv != "—":
                    vals[col] = rv
            elif col.endswith("_date"):
                try:
                    d = _pdate(rv)
                except ValueError:
                    errors.append(f'{title} / {label}: "{rv}" is not YYYY-MM-DD')
                    continue
                if d is not None:
                    vals[col] = d
            else:
                try:
                    n = _num(rv)
                except ValueError:
                    errors.append(f'{title} / {label}: "{rv}" is not a number')
                    continue
                if n is not None:
                    vals[col] = n
        if not vals:
            continue
        params = {
            "tenant_id": tenant_id,
            keycol: keyval,
            **vals,
            "farmer_consent": [
                ["consent_advisory", "consent advisory", "bool", None],
                ["consent_research", "consent research", "bool", None],
                ["consent_date", "consent date", "text", None],
                [
                    "third_party_share_consent_given",
                    "third party share consent given",
                    "bool",
                    None,
                ],
                ["data_retention_until", "data retention until", "text", None],
                ["deletion_requested", "deletion requested", "bool", None],
                ["cluster_anonymised", "cluster anonymised", "bool", None],
                ["sat_attribution_shown", "sat attribution shown", "bool", None],
                [
                    "sat_public_display_context",
                    "sat public display context",
                    "select",
                    ["own_plot", "cluster_aggregate", "third_party"],
                ],
            ],
        }
        names = ["tenant_id", keycol, *vals.keys()]

        def _ph(n: str) -> str:
            return (
                f"CAST(:{n} AS uuid)" if n in ("tenant_id", "season_id", "farmer_id") else f":{n}"
            )

        setcols = ", ".join(f"{c} = EXCLUDED.{c}" for c in vals)
        sql = (
            f"INSERT INTO {table} ({', '.join(names)}) "
            f"VALUES ({', '.join(_ph(n) for n in names)}) "
            f"ON CONFLICT ({keycol}) DO UPDATE SET {setcols}, updated_at = NOW()"
        )
        db.execute_write(sql, params)
        saved.append(f"{title}: {len(vals)} field(s)")

    if errors:
        st.error("Fix these and save again:\n\n- " + "\n- ".join(errors))
    elif saved:
        st.success("Saved:\n\n- " + "\n- ".join(saved))
    else:
        st.info("Nothing to save — every field was left blank.")
