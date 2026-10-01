# Agronomy sign-off — response to `AGRONOMIST_REVIEW.md` + `KB_DB_STATUS.md`

**Date:** 21 September 2026 · **From:** Kuldip (Agronomy) · **To:** Backend

Three items you asked for: the nine sign-offs (§1), the yield model definition (§2), the advisory-QA workflow (§3).

---

## 1. Nine sign-offs

Row-by-row response. Where the value changes, apply the "New value" column exactly.

| # | Field | Verdict | New value / instruction |
|:---:|---|:---:|---|
| 1 | `soil_type` red→laterite | ❌ change | `red → red_loam` (add `red_loam` as a new enum value; keep `laterite` for actual laterite districts, none of which we onboard in Season 1) |
| 2 | `soil_texture_class` 3-class | ✅ OK for Phase 1 | Add a companion field `soil_texture_class_source` with values `derived` / `lab`. When a lab texture (sand/silt/clay %) is entered, the lab-derived class must override the soil-type derivation. |
| 3 | `agro_climatic_zone` map | ⚠️ OK interim | Current mapping stands for Phase 1. VNMKV Parbhani validation pending — expected by 15 Oct. No code change now. |
| 4 | `prediction_stage` DAP cuts | ❌ change | Replace 4-bucket with the 6-stage operational model:<br>`< 0` → `G0` (pre-plant)<br>`0–35` → `G1` (sprouting/establishment)<br>`35–90` → `G2` (vegetative)<br>`90–150` → `G3` (rhizome formation)<br>`150–210` → `G4` (rhizome maturation)<br>`210–240` → `G5` (pre-harvest)<br>`> 240` → `pre_harvest_observation`<br>Tag as `AGRO_GUARDIAN_OPERATIONAL_STAGE_MODEL`. |
| 5 | `phi_days_remaining` PHI table | 🚨 critical | Two changes: **(a) remove `chlorpyriphos: 14`** from `_PHI_DAYS_BY_GROUP` entirely — chlorpyriphos is on the D05-CH-001 blocklist for ginger and must never reach a PHI calculation; **(b)** wire a blocklist gate that runs **before** the PHI lookup (pattern below). Full FSSAI/CIB-verified PHI CSV coming by 30 Sep — until then, keep the conservative 21-day default for anything unlisted, and the confirmed values (mancozeb 7, copper 5, imidacloprid 40) stand. |
| 6 | `rainfall_deviation_pct` normals | ❌ change | Replace `_ZONE_SEASON_RAIN_MM` with a station-level table. Anchor value for Ch. Sambhajinagar plots: **IMD Aurangabad (Chikalthana) 1991–2020 annual = 811.7 mm**. Other Marathwada districts + monthly breakdown coming as `imd_district_normals_1991_2020.csv` by 25 Sep. Every stored normal must carry `source_institution`, `station_name`, `normal_period`, `geographical_scope` metadata alongside the value. |
| 7 | `cyclone_alert_active` proxy | ❌ change | Three changes: **(a) rename** to `severe_weather_alert_active` throughout code and KB — it is not an IMD cyclone warning; **(b)** change AND to **OR** and revise thresholds: `rainfall_24h_mm ≥ 75 OR wind_gust_kmph ≥ 40`; **(c)** tag as `AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE`, source_tier L4. If IMD warning API is integrated later, keep `IMD_WARNING_LEVEL` as a **separate** field — never merge with `VIRAAI_AGRO_RISK_LEVEL`. |
| 8 | `vafsa_state` | ✅ OK | Approved as designed. Add null-guard: if `vwc_saturation` or `vwc_stress_threshold` is null, `vafsa_state = 'unknown'` — not a silent fallback to `workable`. |
| 9 | `stage_source = "calendar"` | ✅ OK for Phase 1 | Correct as long as staging stays calendar-based. In Phase 2, promote to enum (`calendar` / `gdd` / `ndvi_curve_fit`); D14-PH-002 curve-fit will supply an override candidate then. No change now. |

**Blocklist gate pattern (row 5, backend implementation):**
```
IF pesticide_group IN blocklist_for_crop:
    phi_days_remaining   = NULL
    phi_blocklist_hit    = TRUE
    farmer_alert_type    = 'blocklisted_input_detected'
ELSE:
    phi_days_remaining   = _PHI_DAYS_BY_GROUP.get(group, 21)
```

Same pattern applies to any input the KB has an immutable "no" on.

**Tally:** 3 ✅ · 1 ⚠️ · 4 ❌ · 1 🚨

---

## 2. Yield model definition (D11 — unblocks 11 fields)

### Architecture

**Hybrid model:** process-based DSSAT baseline + ML residual correction. Not pure DSSAT, not pure ML.

```
Y_final = Y_DSSAT + ML_residual_correction
```

**Process baseline** — DSSAT-family stage-wise multiplicative crop model. For ginger: adapt the ICAR-IISR IISR-Mahima variety profile (200-day reference maturity, 23.2 t/ha reference yield) as the parameter starting point; VNMKV KVK Sambhajinagar OFT (2024, 20 trials, 23.10 t/ha) as local calibration anchor. Not a pure DSSAT cassava-style module (ginger has no official DSSAT module), so it runs as a custom stage-multiplier engine.

**ML residual layer** — starts from Season 2 onward, once we have one season's paired (predicted, actual) yield data. Phase 1 = process baseline only, ML residual = zero.

### Yield-estimation method

At any point in the season, produce:

```
Y_predicted = Y_potential(variety, site) × ∏ (1 − u_i × I_i)
```

- `Y_potential` = variety potential × site index (soil/climate ceiling)
- `u_i` = the U-value of yield-limiting factor `i` (0–1, fraction of yield lost if the factor is fully expressed)
- `I_i` = intensity in this season (0–1, how strongly the factor has actually expressed)

Ship three outputs with every prediction:
- Point estimate
- 90 % confidence band
- Per-factor attribution list (which factors are pulling the estimate down and by how much)

### U-value register (Phase 1, EST)

Twelve factors ranked by expected yield-cost in Kannad ginger. Each `u_i` is my author estimate (source_tier L4) — replaced with empirical means after Season 1.

| Rank | Factor | u_i (EST) | Sub-node / signal |
|:---:|---|:---:|---|
| 1 | Soft rot (Pythium) | 0.60 | D06 rot signal + drainage |
| 2 | Drainage failure / waterlogging > 48h | 0.35 | D03 saturation-hours + SAR |
| 3 | Bacterial wilt (once present) | 0.50 | D06 wilt differential |
| 4 | K deficiency uncorrected | 0.20 | D04 K budget |
| 5 | Rhizome fly damage | 0.15 | D05 scouting |
| 6 | Seed rhizome vigour poor | 0.15 | D01 emergence data |
| 7 | Drought during rhizome fill (G3–G4) | 0.20 | D03 stress-days |
| 8 | Excess N late (> 80 DAP) | 0.08 | D04 N schedule |
| 9 | Heat stress > 35 °C sustained | 0.10 | D07 heat-days |
| 10 | Weed pressure uncontrolled | 0.10 | D08 weed report |
| 11 | Micronutrient (Zn/Fe) lock-out | 0.08 | D04 leaf tissue / D14 NR |
| 12 | Nematode pressure | 0.12 | D06 nematode signal |

### Yield-gap attribution

```
Gap = Y_potential − Y_predicted
Explained = Σ (u_i × I_i × Y_potential) for factors with I_i > 0.2
Unexplained = Gap − Explained
```

If `Unexplained / Gap > 0.25`, flag the plot for agronomist review — the model is missing something.

### What backend needs to build

- One function `predict_yield(plot_id, dap) → {point, ci_low, ci_high, attribution[]}`
- One table `yield_u_values` seeded with the 12 rows above; column `source_tier` = `L4` for all Phase 1 rows
- One table `yield_prediction_log` capturing every prediction with `model_version`, `data_quality`, `confidence`, timestamp
- The 11 D11 fields fill from these three

### What agronomy delivers next on this

Full spec doc `D11_YIELD_MODEL_v1.md` by 15 Oct with the site-index formula, per-stage weighting for `I_i`, and confidence-band derivation. What's above is sufficient for backend to start wiring today.

---

## 3. Advisory-QA workflow (D12 — unblocks 8 fields)

### The workflow, one page

**Weekly review call** — every Monday, agronomist calls 3–5 randomly-selected pilot farmers. Reviews every advisory that fired in that farmer's plot over the past week. Two outputs per advisory:

1. **Classification** — one of three states:
   - `confirmed_true_positive` — advisory correct, farmer agrees or field evidence confirms
   - `false_positive` — advisory fired but was wrong on inspection
   - `unresolved` — cannot decide yet, revisit next week

2. **If farmer did NOT act on the advisory** — reason from a 6-value enum:
   - `already_done` (farmer had already handled it)
   - `cost_barrier` (input too expensive)
   - `unavailable_input` (input not available locally)
   - `disagreed` (farmer's own judgement said no)
   - `forgot`
   - `other` (free-text alongside)

### Bias observations

Same weekly call captures agronomist's observations about **patterns** — advisories the system is systematically over-issuing, under-issuing, or getting subtly wrong. Free-text row in a `bias_observation` table. One row per observation, tagged with domain and rule_id if identifiable. Read weekly by the KB author for next-round rule tuning.

### Photo upload + labelling

Farmer sends symptom photos on WhatsApp. Photos flow into a labelling backlog. Labels are D06 differential-diagnosis categories (soft rot / bacterial wilt / rhizome fly / heat scorch / Zn deficiency / other / cannot-tell-from-photo). Agronomist labels 10–20 per week; labels feed future auto-diagnosis training but do NOT drive current advisories.

### Cluster assignment

- Cluster size: **8–12 plots**
- Assignment on enrollment
- Rule: geographic proximity within **3 km** AND same variety AND same planting-week bucket (7-day window)
- Plots that cannot meet all three: assign to nearest cluster with a `cluster_fit_score` < 1.0, flag for solo baseline treatment (D14 rules degrade confidence accordingly)

### What backend needs to build

Four tables + one small review UI:

| Table | Rows written by | Purpose |
|---|---|---|
| `advisory_classification` | agronomist via review UI | one row per (advisory_id, week) with classification + note |
| `non_compliance_reason` | farmer via WhatsApp reply / agronomist during call | one row per advisory the farmer did not act on |
| `bias_observation` | agronomist via review UI | free-text pattern notes |
| `photo_label` | agronomist via review UI | one row per photo, with D06 category |

**Review UI:** simple weekly list per farmer — advisories that fired, buttons for the three classifications, dropdown for non-compliance reason, free-text for bias, thumbnail grid for photos with label dropdown. Rough wireframe from backend would help before I write the field-level spec.

### Cluster assignment code

One function `assign_cluster(plot_id) → cluster_id | new_cluster`. Runs at plot enrollment. Uses the three rules above; if no cluster qualifies, spawn a new one seeded with this plot.

### What agronomy delivers next on this

Field-level spec `D12_QA_WORKFLOW.md` by 10 Oct — depends on the UI wireframe above landing first. The four table shapes and the four data flows in this section are enough for backend to start scaffolding.

---

## 4. Priority order (for backend planning)

1. **This week (22–28 Sep):** rows 1, 2, 4, 6, 7, 8, 9 of §1 — small edits, big correctness improvements
2. **By 30 Sep:** row 5 blocklist gate + first draft of yield-model tables (§2)
3. **By 10 Oct:** QA workflow tool wireframe from backend → I finalise `D12_QA_WORKFLOW.md`
4. **By 15 Oct:** `D11_YIELD_MODEL_v1.md` full spec + VNMKV zone validation returned (row 3)
5. **By 30 Sep:** `ginger_pesticide_registry.csv` (row 5)
6. **By 25 Sep:** `imd_district_normals_1991_2020.csv` (row 6)

Season 1 pilot activation target unchanged: **1 November 2026.**

— Kuldip
Knowledge Base, Agronomy, and Product Coordination
Agro-Guardian AI
