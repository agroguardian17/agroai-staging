# KB Reconciliation Memo — 25 Sep Agronomy Bundle vs Deployed Ginger KB

**Date:** 26 September 2026
**From:** Backend
**To:** Kuldip — Agronomy Compliance Owner
**Re:** `VIRAAI_Agronomy_Deliverables_25Sep2026/` — what integrated cleanly, and the KB-rule conflicts that need agronomy decisions before any rule edits

---

## 1. TL;DR

The bundle splits into two halves:

- **Data lookup tables — DONE.** The three CSV-backed tables are unambiguous and vocabulary-independent; they're merged/in-flight (§2).
- **KB rule edits — HELD pending your decisions.** Every rule the bundle "rewrites" **already exists** in the deployed KB, and the deployed KB has **already been through a `VIRAAI_AGRONOMY_REVIEW` dated 2026-09-22** that flagged the same defects the bundle fixes — but resolved them (or is about to) using a **different field vocabulary and rule-map** than the bundle assumes. Applying the bundle verbatim would collide rule-ids, fork the soil vocabulary, and reference DSL features and a `compliance_tag` field that don't exist. Details in §3–§4.

Nothing below is a criticism of the agronomy work — it's high quality. The gap is that the bundle was authored against an *assumed* schema, and the live KB evolved differently. This memo is the mapping so we can converge.

---

## 2. Data layer — applied (no decisions needed)

| Deliverable | Table / migration | Status |
|---|---|---|
| `variety_stage_water_target.csv` | re-seed `variety_stage_water_target` (0051): 3 varieties, G0–G5+LIFECYCLE, DAP bands | merged + deployed |
| `variety_N_ceiling.csv` | `variety_n_ceiling` (0052): Mahima 61 / Varada 55 / Nadia 52 kg N/acre, DAP-150 cutoff | merged |
| `registered_herbicide_registry_ginger_v1.0.csv` | `registered_herbicide_registry` (0053): 13 entries, 6 compliance tiers | in CI |

These are keyed by variety/product and are read *by* the rules — so they're correct regardless of how the rule reconciliation below resolves.

---

## 3. Cross-cutting decisions (these block ALL the KB rule edits)

### D1 — Soil vocabulary (the big one)
The deployed KB has **two different soil fields**, not one:

| Field | Values in use | Rules using it |
|---|---|---|
| `soil_type` | `'vertisol'`, … | D02-LY-001, D08-LY-001 |
| `soil_texture_class` | `'heavy'`, `'medium'`, `'light'` | D03-DS-001 |

The bundle assumes a single `soil_texture_class ∈ {vertisol, heavy_clay, clay_loam_heavy, sandy_loam, clay_loam}`. That vocabulary matches **neither** deployed field.
**Decision needed:** Do we (a) map the bundle's soil classes onto the existing `soil_type='vertisol'` / `soil_texture_class='heavy'` vocabulary and keep triggers as-is, or (b) migrate the KB to the bundle's richer 5-class vocabulary (touches every soil rule, its fields, and its golden tests — a large cross-cutting change)? Recommend (a) for Season 1.

### D2 — `compliance_tag` has no home in the KB
There is **no `compliance_tag` field on any rule** in the runtime KB (0 occurrences). COMPLIANT / NON_COMPLIANT / CONDITIONAL / AGRO_GUARDIAN_CUSTOM live only in the separate compliance tracker. The KB does carry `review.outcome` (`conditional`/…) and `status` (`AGRONOMIST_REVIEWED`).
**Decision needed:** The A5 "retag to COMPLIANT/CUSTOM" work is a **tracker edit, not a code change** — confirm we update the compliance tracker doc, and (optionally) whether you want a `compliance_tag` added to the rule schema as a first-class field. Recommend: keep it in the tracker; no schema change for Season 1.

### D3 — `D04-MC-004` rule-id collision
The bundle's basal-ZnSO₄ rule claims id `D04-MC-004`. **That id is already taken** by a live micronutrient heat/rain spray rule (`air_temp_max_c > 35 OR forecast_rain_48h_mm > 5`).
**Decision needed:** Assign the ZnSO₄ rule a new id — recommend **`D04-MC-005`**.

### D4 — DATE DSL literal does not exist
The trigger DSL (`engine/trigger_dsl.py`) supports numbers, quoted strings, enum words, `IN`/`BETWEEN`/`IS`/`DURATION`/`WITHIN`/`MONTH IN`/`STAGE IN` — but **no `DATE` literal, no `||`, no functions**. So D01-PW-001's `planting_date > DATE(season_start_year || '-06-07')` is not expressible.
**Decision needed:** Either (a) keep D01-PW-001 on the existing `MONTH IN [JUN, JUL]` idiom (already deployed), or (b) we add a derived integer field `planting_doy` (day-of-year) so you can write `planting_doy > 158`, or (c) we build DATE-literal support into the DSL (largest option). Recommend (b) if a hard date is required; else (a).

### D5 — New fields the bundle introduces
Fields the bundle needs that must be declared in a JSON `_schema` before their rules can parse: `years_since_last_wilt`, `agro_climatic_zone`, `basal_znso4_applied_kg_acre`, `emitter_pattern`, `proposed_herbicide_input`, `total_n_kg_acre_applied_since_dap_0`, `proposed_n_application_kg_acre`, `plot_status`, `plot_status_transition`, plus the whole water-budget field set (gated — §5). Adding fields is cheap; but note several duplicate existing concepts under different names (e.g. bundle `dripper_flow_lph` vs deployed `dripper_lph`; bundle N fields vs deployed `n_applied_kg_per_acre`).

---

## 4. Rule-by-rule reconciliation

Legend: **DONE** = deployed KB already satisfies the bundle's intent · **PENDING-CLEAN** = safe to apply once D1–D5 resolved · **NEEDS-DECISION** = depends on a cross-cutting decision · **BLOCKED** = needs hardware/DSL.

| Rule | Deployed trigger / severity | 22-Sep review already did | Bundle asks for | Verdict |
|---|---|---|---|---|
| **D03-DS-001** (A5.2) | `has_drip AND drip_lateral_spacing_ft IS NULL AND soil_texture_class=='heavy'` · red | Added soil gate (`=='heavy'`) | soil ∈ {vertisol,heavy_clay,clay_loam_heavy} + `dripper_lph>4` / `spacing>40` / `emitter_pattern!=PC` | **NEEDS-DECISION (D1)** — intent already met; bundle wants richer hardware checks + new vocab/field |
| **D08-EU-002** (A5.3) | `flowering_observed AND earthing_up_date IS NULL` · red | **Removed** fixed 12.5% penalty | remove 12.5%, add variable range | **DONE** (tracker retag only) |
| **D08-LY-001** (A5.4) | `soil_type=='vertisol' AND has_drip AND planting_layout!='broad_ridge'` · red | Made layout benefit conditional | 3-tier context advisory | **DONE-ish** — intent met; 3-tier is enhancement (NEEDS-DECISION if desired) |
| **D14-SR-002** (A5.6) | SAR standing-water signal · red | Converted to calibrated signal + field confirm | retag CUSTOM + drop precision prose | **DONE** (tracker retag) |
| **D03-WL-003** (A5.7) | `MONTH IN [OCT,NOV] AND forecast_rain_48h_mm>40` · red | Flagged threshold source; rewrite pending | retag CUSTOM + drop "more severe" | **NEEDS-DECISION** — deployed trigger differs from bundle's `vwc_saturation_days_running>=3`; pick one |
| **D07-CY-001** (A5.8) | `MONTH IN [OCT,NOV] AND forecast_rain_48h_mm>40` · red | Flagged non-IMD threshold | retag CUSTOM only | **DONE** (tracker retag); trigger already deployed |
| **D01-PH-004** (5A) | *(no trigger yet)* · yellow | Removed 12.5% penalty | GDD-lag advisory trigger | **PENDING-CLEAN** — needs trigger authored; `cumulative_gdd`/`variety_gdd` fields |
| **D02-DR-004** (5A) | *(no trigger yet)* · yellow | Intent sound; CONDITIONAL | drainage pre-plant trigger | **NEEDS-DECISION (D1)** — bundle uses vertisol/slope vocab; deployed fields are `percolation_class`/`bed_height_cm` |
| **D02-ST-002** (5A) | *(no trigger yet)* · yellow | CONDITIONAL (L4) | soil-texture lab reclassify (silent) | **NEEDS-DECISION (D1)** — deployed fields are `percolation_*`, not sand/silt/clay% |
| **D03-SB-003** (5A) | *(no trigger yet)* · info | CONDITIONAL | battery-low advisory | **PENDING-CLEAN** — needs `sub_node_battery_pct` field + trigger |
| **D02-LY-001** (5A) | *(no trigger)* · **blocking** | already BLOCKING (#87) | blocking flat-on-vertisol | **DONE** (severity already blocking) — trigger authoring still pending |
| **D06-BW-001** (B1.3) | *(no trigger)* · red | CONDITIONAL | wilt `<5yr` + NULL-bypass close | **PENDING-CLEAN** — deployed fields `field_history_wilt`/`previous_crops_3yr` vs bundle `years_since_last_wilt`; reconcile field then author |
| **D01-PW-001** (B1.4) | `planting_date IS NULL AND MONTH IN [JUN,JUL] AND dap IS NULL` · blocking | Flagged 7-June cutoff as non-universal | date-literal cutoff | **BLOCKED (D4)** — DSL has no DATE |
| **D04-MC-004** (B1.6) | `air_temp_max_c>35 OR forecast_rain_48h_mm>5` · info | — | **basal ZnSO₄** (different rule!) | **NEEDS-DECISION (D3)** — id collision; assign D04-MC-005 |
| **D04-NS-003** (§3) | `dap>80 AND n_applied_kg_per_acre IS NOT NULL` · red | Flagged >80 DAP / u=0.08 as non-universal | anticipated-sum vs variety ceiling + DAP-150 | **NEEDS-DECISION** — redesign uses new N fields + `variety_n_ceiling` (now seeded); confirm field model |
| **D08-WD-001** (A5.1/§2) | `(emergence_started OR dap>=15) AND herbicide_post_emergent_date IS NULL` · blocking | Flagged as too-broad; rewrite pending | positive-list registry gate | **PENDING-CLEAN** — registry table now seeded; needs `proposed_herbicide_input` field + trigger redesign; large but self-contained |

---

## 5. Water-Budget rules — BLOCKED on hardware (unchanged)

The 8 `D03-WB-*` rules and `D03-ST-001` are all fire-gated on `flow_telemetry_present`, which still does not exist in the readings model. They also reference the full water-budget field set. **Held** per Water-Budget v1.3 §9 until the flow-telemetry field lands. (Also: the bundle's D03-WB rule bodies say confidence gate `≥0.60` while §1d v1.1 lowered it to `0.40` — use 0.40 when we author them.)

---

## 6. Suggested path once decisions land

1. **Tracker-only (no code):** apply the A5 retags in the compliance tracker — D08-EU-002, D14-SR-002, D07-CY-001 (already DONE in KB), plus D08-LY-001.
2. **PENDING-CLEAN KB PRs** (one cluster per PR, each: edit JSON + `authoring/triggers_wave*.py` + golden tests → regen `agroguardian_ginger_kb.sql` → KB-reload migration): D01-PH-004, D03-SB-003, D02-LY-001 trigger, D08-WD-001 (registry-driven), D06-BW-001 (after field reconcile).
3. **After D1 (soil vocab):** D03-DS-001, D02-DR-004, D02-ST-002, D03-WL-003.
4. **After D3:** ZnSO₄ as D04-MC-005.
5. **After D4:** D01-PW-001 (or keep the deployed MONTH idiom).
6. **After hardware:** the water-budget suite.

---

## 7. Questions for Kuldip (the decisions)

1. **Soil vocab (D1):** map the bundle's soil classes onto deployed `soil_type='vertisol'` / `soil_texture_class='heavy'` (recommended, Season 1), or migrate the KB to the 5-class vocabulary?
2. **compliance_tag (D2):** keep COMPLIANT/CUSTOM/etc. in the compliance tracker (recommended), or add it as a KB rule field?
3. **ZnSO₄ id (D3):** OK to author the basal-ZnSO₄ rule as **D04-MC-005** (since D04-MC-004 is a live spray rule)?
4. **D01-PW-001 date (D4):** keep the deployed `MONTH IN [JUN,JUL]` window, add a `planting_doy` integer field for a hard cutoff, or ask backend to build DATE-literal DSL support?
5. **N-timing (D04-NS-003):** confirm the field model — do you want the cumulative-N ledger (`total_n_kg_acre_applied…` + `proposed_n…` + `variety_n_ceiling` lookup) to replace the deployed `dap>80 AND n_applied_kg_per_acre` trigger?
6. **Field reconciliation (D6):** for D06-BW-001, is `years_since_last_wilt` (int) additive to, or a replacement for, the deployed `field_history_wilt` / `previous_crops_3yr`?

Once 1–6 are answered, the KB PRs in §6 can proceed one cluster at a time, each validated against the drift + 600-golden-test gates before merge.
