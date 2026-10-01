# VIRAAI AGRO-GUARDIAN AI
## संयुक्त हस्तांतरण दस्तऐवज — Backend + Agronomy → Software / Product Team

**Version:** VJH-V1.0 (Joint Handoff)
**Date:** 21 September 2026
**Basis documents:**
- `KB_DB_STATUS.md` (backend-authored status audit, 2026-09-21)
- `AGRONOMIST_REVIEW.md` (backend-raised nine sign-offs, 2026-09-21)
- `AG-V2.0 Scientific Correction & Validation Edition` (agronomy-ratified scientific baseline, 2026-09-21)

**Status:** Joint sign-off pending on both sides. This document is the single reference the software / product team should treat as authoritative for what will and will not go into Season 1 pilot.

---

## 0. एक-ओळ सारांश | One-line summary

Software substantially wired आहे (309/346 fields, 377 rules ready). Backend ने raise केलेल्या 9 sign-offs वर agronomy team ची अंतिम भूमिका खाली दिली आहे; AG-V2.0 scientific validation ने चार आकड्यांना correction दिली आहे; एक critical food-safety gate implementation बाकी आहे. Season 1 पायलट activation लक्ष्य — **1 November 2026.**

---

## 1. मूलभूत तत्त्व | Foundational principle (AG-V2.0 §2)

Agro-Guardian मध्ये **कोणताही threshold फक्त एका संख्येवर आधारित अंतिम biological conclusion म्हणून वापरला जाणार नाही.** प्रत्येक trigger पुढील context सोबतच final decision पर्यंत पोहोचतो:

```
Rainfall + intensity + duration + antecedent soil moisture + soil texture +
drainage + slope + crop stage + crop sensitivity + temperature + humidity +
disease pressure
```

**Corollary for software team:** प्रत्येक single-value threshold `AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE` म्हणून tag केला पाहिजे. IMD, ICAR, VNMKV सारख्या institutional sources मधून घेतलेला value वेगळ्या tag ने ठेवायचा. **कोणतीही custom operational threshold institutional standard म्हणून presentation नाही.**

---

## 2. वैज्ञानिक स्रोतांची Hierarchy | Evidence hierarchy (AG-V2.0 §3)

Every field, threshold, and rule in the KB must carry a `source_tier` tag from this ladder:

| Tier | Source | Examples |
|:---:|---|---|
| **Level 1** | Official Govt / National Scientific Institution | IMD, ICAR, ICAR-IISR, ICAR-CTCRI, VNMKV, State Agri Universities |
| **Level 2** | Peer-reviewed scientific literature | Journal articles, validated crop models, experimental research |
| **Level 3** | Local experimental evidence | VNMKV OFT, KVK trials, farmer-field trials, VIRAAI field data |
| **Level 4** | VIRAAI derived rules | AI/ML or agronomic expert-derived thresholds |

**Rule:** Level 4 rule ला Level 1 institutional standard म्हणून **कधीही** दाखवले जाणार नाही.

**Backend implementation:** `_source_tier`, `_source_institution`, `_source_ref` metadata columns per rule/threshold — enforced at KB build time.

---

## 3. Nine sign-offs — finalised (AGRONOMIST_REVIEW corrections + AG-V2.0)

### 3.1 Overview table

| # | Field | Backend's default | **Final agronomy decision** | Source tier |
|:---:|---|---|---|:---:|
| 1 | `soil_type` red→laterite | as proposed | ❌ **CHANGE**: red → `red_loam` (add enum value) | L2 (soil taxonomy consensus) |
| 2 | `soil_texture_class` 3-class | as proposed | ✅ OK Phase 1 + `soil_texture_class_source` override field | L4 → L1 when lab present |
| 3 | `agro_climatic_zone` map | as proposed | ⚠️ Interim OK; VNMKV validation pending | L4 → L3 after VNMKV |
| 4 | `prediction_stage` DAP cuts | 4-bucket | ❌ **REPLACE** with 6-stage G0–G5 framework (§4) | L3 (AG-V2.0 §27) |
| 5 | `phi_days_remaining` PHI table | includes chlorpyriphos 14d | 🚨 **CRITICAL — blocklist gate first** (§5) | L1 (FSSAI/CIB) pending |
| 6 | `rainfall_deviation_pct` normals | Zone-averaged 750/680/820 mm | ❌ **REPLACE** with IMD Aurangabad (Chikalthana) **811.7 mm** annual + district-specific expansion (§6) | L1 (IMD 1991–2020) |
| 7 | `cyclone_alert_active` proxy | wind ≥ 60 AND rain ≥ 50 | ❌ **RENAME + RECLASSIFY** as `severe_weather_alert_active` — see §7 | L4 (custom) |
| 8 | `vafsa_state` | per-plot thresholds | ✅ Approved + null-guard | L1/L3 (per-plot data) |
| 9 | `stage_source = "calendar"` | constant | ✅ Phase 1 OK + Phase 2 enum future-flag | L4 |

**Tally:** 3 ✅ · 2 ⚠️ conditional · 3 ❌ replace · 1 🚨 critical

---

## 4. Corrected stage framework — Ginger (AG-V2.0 §27)

**Replaces** the 4-bucket cuts in `AGRONOMIST_REVIEW.md` item 4 AND my earlier informal counter-proposal. This is the **official operational stage model**:

| Stage | DAP range | Meaning |
|:---:|:---:|---|
| G0 | −60 to 0 | Pre-plant, land prep, seed rhizome |
| G1 | 0–35 | Sprouting, establishment |
| G2 | 35–90 | Vegetative growth |
| G3 | 90–150 | Rhizome formation begins |
| G4 | 150–210 | Rhizome maturation |
| G5 | 210–240 | Pre-harvest / harvest window |

**Source tag:** `AGRO_GUARDIAN_OPERATIONAL_STAGE_MODEL`
**Reference:** ICAR-IISR IISR-Mahima variety profile (maturity 200 days) + VNMKV KVK Sambhajinagar OFT (2024)
**Explicit disclaimer:** These are **not** universally validated biological boundaries across all varieties and agro-climatic conditions. Model carries `stage_source = "calendar"` (Phase 1); Phase 2 enum will add `"gdd"` and `"ndvi_curve_fit"` as override candidates.

**Backend action:** Update `_prediction_stage` function's DAP cut-points to match this table verbatim. Update D01 stage-rule DAP conditions to align.

---

## 5. 🚨 Critical food-safety gate — chlorpyriphos & the blocklist

**Problem (unchanged from earlier draft):** D05-CH-001 (immutable) blocks chlorpyriphos on ginger. But `_PHI_DAYS_BY_GROUP` lists chlorpyriphos = 14 days. If a farmer enters `pesticide_group: chlorpyriphos` (from mis-labelled bottle or off-market advice), the mapper computes `phi_days_remaining = 14` — which contradicts the immutable rule.

**Design pattern (backend, small implementation):**

```python
# Precondition — runs BEFORE PHI calculation
IF pesticide_group IN blocklist_for_crop:
    phi_days_remaining         = NULL
    phi_blocklist_hit          = TRUE                          # new field
    farmer_alert_type          = 'blocklisted_input_detected'  # existing D05 branch
    blocklist_reason           = blocklist_registry[pesticide_group].reason
    blocklist_source_ref       = blocklist_registry[pesticide_group].source_ref
ELSE:
    phi_days_remaining         = _PHI_DAYS_BY_GROUP.get(pesticide_group, 21)
```

**Same pattern applies** to any input the KB has an immutable "no" on: banned chemicals (FSSAI), unregistered varieties (Seed Act), etc. The mapper routes through a policy-check function, not the normal computation.

**Agronomy deliverable:** `ginger_pesticide_registry.csv` — see §9.1.
**Priority:** BEFORE season 1 pilot activation. Non-negotiable.

---

## 6. IMD rainfall normal — corrected authoritative value

### 6.1 Baseline (AG-V2.0 §4)

**Source:** India Meteorological Department, Pune — Climatological Tables 1991–2020
**Station:** Aurangabad (Chikalthana)
**Annual rainfall normal:** **811.7 mm**

Monthly (mm):

| Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | **Annual** |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 2.6 | 2.2 | 11.4 | 6.0 | 17.4 | 155.6 | 178.0 | 171.5 | 172.4 | 68.2 | 17.5 | 8.9 | **811.7** |

### 6.2 Metadata required with every stored value (AG-V2.0 §5)

```
source_institution     = IMD
station_name           = Aurangabad (Chikalthana)
latitude, longitude    = <station coords>
normal_period          = 1991–2020
measurement_method     = <station observation | interpolated | district average>
geographical_scope     = <station | district | zone>
```

**Backend action:** Extend `_ZONE_SEASON_RAIN_MM` to become `_STATION_RAINFALL_NORMAL` keyed by station code, with each value carrying the metadata block above. Ch. Sambhajinagar plots key to Chikalthana. Other Marathwada + expansion districts: agronomy provides in §9.2 CSV.

### 6.3 IMD rainfall category reference (AG-V2.0 §6)

For classifying 24-hour rainfall in every advisory:

| Category | 24-hour rainfall |
|---|:---:|
| Very Light | Trace–2.4 mm |
| Light | 2.5–15.5 mm |
| Moderate | 15.6–64.4 mm |
| Heavy | **64.5–115.5 mm** |
| Very Heavy | 115.6–204.4 mm |
| Extremely Heavy | ≥ 204.5 mm |

**Source tag on the category itself:** `IMD_OFFICIAL_CLASSIFICATION` (Level 1).

---

## 7. Weather-risk thresholds — corrected classification

### 7.1 What changed vs my earlier draft

The 75 mm rainfall / 40 km/h wind values I proposed **remain valid as operational triggers**, but AG-V2.0 §8, §15 correct their **classification** — they must not be presented as IMD standards.

### 7.2 75 mm rainfall — correct classification (AG-V2.0 §7–9)

- 75 mm sits in the **IMD Heavy Rainfall range** (64.5–115.5 mm).
- 75 mm is **NOT** the midpoint of that range (midpoint = 90 mm) — it is the **lower portion**.
- 75 mm is **NOT** an IMD crop-loss threshold; IMD does not issue a crop-loss threshold at all.
- 75 mm is usable as an Agro-Guardian custom trigger, tagged:

```
threshold_type    = AGRO_GUARDIAN_CUSTOM_RAIN_TRIGGER
source_tier       = L4
parameter         = rainfall_24h_mm
trigger_condition = >= 75
```

### 7.3 40 km/h wind — correct classification (AG-V2.0 §14–16)

- IMD thunderstorm classification uses **maximum surface wind gust in km/h**:

| Wind gust | IMD interpretation |
|---|---|
| < 40 km/h | Light thunderstorm |
| 41–61 km/h | Moderate thunderstorm |
| **62–87 km/h** | **Severe thunderstorm** |
| > 87 km/h | Very Severe thunderstorm |

- **40 km/h is NOT IMD Severe.** My earlier framing was wrong.
- 40 km/h is usable as an Agro-Guardian custom trigger for lodging risk, canopy damage, leaf tearing, mechanical stress, evapotranspiration spike, storm preparation — tagged:

```
threshold_type    = AGRO_GUARDIAN_CUSTOM_WIND_TRIGGER
source_tier       = L4
parameter         = wind_gust_kmph
trigger_condition = >= 40
validation_status = PENDING_CROP_SPECIFIC_VALIDATION
```

### 7.4 Rename `cyclone_alert_active` (AG-V2.0 §17)

**Old:** `cyclone_alert_active` (misleading — implies official IMD cyclone warning)
**New:** `severe_weather_alert_active` (honest — operational risk trigger)

**Rule form:**
```
IF rainfall_24h_mm >= 75 OR wind_gust_kmph >= 40
THEN severe_weather_alert_active = TRUE
     rule_tag = AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE
```

### 7.5 Two-track alert display (AG-V2.0 §47–48)

If the official IMD warning API is later integrated, the two must remain **separate fields**:

```
IMD_WARNING_LEVEL          ← from IMD API (Level 1)
VIRAAI_AGRO_RISK_LEVEL    ← from custom rules (Level 4)
```

**Never merge these into one composite field.** Farmer message may cite both; database rows stay distinct.

---

## 8. New rule — D07-CY-WX-001

### 8.1 Reason (AG-V2.0 §20–21)

Current D07-CY-001 uses:
```
MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40
```

This is not identical to the 75 mm / 40 km/h OR rule agreed in §7 above. Rather than modify D07-CY-001 (which has its own history and golden tests), agronomy specifies a **new sibling rule**:

### 8.2 Proposed new rule

```
RULE_ID          = D07-CY-WX-001
CATEGORY         = CY
TRIGGER          = rainfall_24h_mm >= 75 OR wind_gust_kmph >= 40
ACTION           = weather_stress_risk = HIGH; issue severe-weather advisory
DELIVERY         = ONCE_UNTIL_RESOLVED
IMMUTABLE        = false
rule_type        = AGRO_GUARDIAN_CUSTOM
source_type      = AGRONOMY_DERIVED
source_tier      = L4
validation_status = PENDING_FIELD_VALIDATION
```

### 8.3 Golden tests required (AG-V2.0 §23)

Positive cases, negative cases, and boundary cases mandatory before production deployment:

| Boundary test | Rainfall | Wind | Expected |
|---|:---:|:---:|:---:|
| Rain just below | 74.9 mm | 20 km/h | FALSE |
| Rain at threshold | 75.0 mm | 20 km/h | TRUE |
| Rain just above | 75.1 mm | 20 km/h | TRUE |
| Wind just below | 30 mm | 39.9 km/h | FALSE |
| Wind at threshold | 30 mm | 40.0 km/h | TRUE |
| Wind just above | 30 mm | 40.1 km/h | TRUE |
| Both null | NULL | NULL | UNKNOWN |
| Rain null, wind trip | NULL | 45.0 km/h | TRUE |
| Rain trip, wind null | 80.0 mm | NULL | TRUE |

D07-CY-002 (drainage inspection reminder — `MONTH IN [OCT, NOV] AND STAGE IN [G3, G4]`) **stays as-is**. Weather-trigger and stage-trigger remain separate layers (AG-V2.0 §22).

---

## 9. Agronomy deliverables — with source references

Numbered by priority. Each carries an owner, target date, and Level-1 source reference.

### 9.1 FSSAI-aligned pesticide registry + blocklist
- **File:** `ginger_pesticide_registry.csv`
- **Columns:** `group`, `trade_names`, `crop_registered`, `registered_dose`, `phi_days`, `mrl_ppm`, `blocklist_reason_if_any`, `source_ref`
- **Source tier:** L1 (CIB registration + FSSAI MRL notifications) + L3 (VNMKV plant protection consult)
- **Owner:** Kuldip + VNMKV Parbhani
- **Target:** 30 September 2026
- **Blocks:** §5 blocklist gate, `phi_days_remaining` correction, D05 blocklist expansion

### 9.2 IMD district normals dataset
- **File:** `imd_district_normals_1991_2020.csv`
- **Baseline row (confirmed by AG-V2.0 §4):**

  | station | district | jan | feb | ... | dec | annual | source | period |
  |---|---|---|---|---|---|---|---|---|
  | Aurangabad (Chikalthana) | Ch. Sambhajinagar | 2.6 | 2.2 | ... | 8.9 | 811.7 | IMD | 1991–2020 |

- **Additional stations:** all Marathwada districts + expansion candidates (Nashik, Ahmadnagar, Solapur) — Kuldip to fetch from IMD Pune Climatological Tables
- **Source tier:** L1 (IMD)
- **Owner:** Kuldip
- **Target:** 25 September 2026
- **Blocks:** `rainfall_deviation_pct`

### 9.3 Stage cut-points already delivered
- **Content:** §4 above — official G0–G5 framework from AG-V2.0 §27
- **Source tier:** L3 (VNMKV + ICAR-IISR variety profile)
- **Owner:** Agronomy (delivered)
- **Target:** ✅ delivered in this document
- **Backend action:** wire immediately

### 9.4 Soil-type enum extension
- **Content:** add `red_loam` as distinct value; add `soil_texture_class_source` field
- **Source tier:** L2 (soil taxonomy)
- **Owner:** Agronomy specifies, backend implements
- **Target:** 24 September 2026

### 9.5 Severe-weather threshold table
- **Content:** confirmed in §7 above
- **Source tier:** L4 (custom operational)
- **Owner:** Agronomy (delivered)
- **Target:** ✅ delivered in this document
- **Backend action:** implement D07-CY-WX-001 as §8

### 9.6 Agro-climatic zone / district table
- **Content:** VNMKV-validated district → zone mapping
- **Source tier:** L1 (VNMKV agromet division) after validation
- **Owner:** Kuldip → VNMKV Parbhani
- **Target:** 15 October 2026
- **Interim:** current mapping OK

### 9.7 Yield model definition (D11 — largest artifact)
- **File:** `D11_YIELD_MODEL_v1.md`
- **Architecture (from AG-V2.0 §35–37):** **Hybrid** — process-based DSSAT baseline + ML residual correction. NOT pure DSSAT, NOT pure ML.
  ```
  Y_final = Y_DSSAT + ML_residual_correction
  ```
- **Ginger baseline:** IISR-Mahima variety, reference maturity 200 days, reference yield 23.2 t/ha (ICAR-IISR profile), local baseline 23.10 t/ha (VNMKV KVK Sambhajinagar OFT, 20 trials, 2024)
- **Cassava baseline (if in scope for Season 1):** DSSAT MANIHOT-Cassava (crop code CS, ICASA code CSV, default CSYCA); CTCRI Sree Vijaya / Sree Jaya / Sree Harsha variety profiles as parameter estimation input — but explicitly **CTCRI variety profile ≠ DSSAT genetic coefficients** (AG-V2.0 §32); each variety needs its own calibrated coefficient set (§34)
- **U-value register:** 11–15 yield-limiting factors ranked by expected yield-cost, each with EST value for Phase 1, replaced by empirical means after Season 1
- **Gap attribution:** estimated vs achievable yield split into "explained" (sum of observed u-values) and "unexplained residual"; residual > 25% flags for agronomist review
- **Source tier:** L1 (ICAR-IISR/CTCRI variety data) + L2 (DSSAT documentation) + L3 (VNMKV OFT) + L4 (ML residual layer)
- **Owner:** Kuldip + agronomy team
- **Target:** 15 October 2026 (v1 draft)

### 9.8 Advisory-QA workflow spec (D12 — 8 fields)
- **File:** `D12_QA_WORKFLOW.md`
- **Content:** 3-state alert classification, weekly bias-observation call format, 6-value non-compliance enum, WhatsApp photo labelling into D06 differential categories, cluster assignment rules (8–12 plots, 3 km + variety + planting-week bucket)
- **Owner:** Kuldip
- **Target:** 10 October 2026

### 9.9 Field data-entry cadence
- **Content:** minimum data-entry checklist per plot at 5 timepoints — pre-plant, DAP 30, DAP 90, DAP 150, harvest
- **Owner:** Field ops; agronomy sets schedule
- **Target:** 24 September 2026

### 9.10 Percolation test protocol
- **Content:** two-paragraph field-test SOP: 30 cm pit, saturate, time water-level drop from top mark to 5 cm below; classify `rapid < 30 min`, `moderate 30–90 min`, `slow > 90 min`
- **Source tier:** L2 (soil physics standard)
- **Owner:** Agronomy specifies, field ops executes
- **Target:** 24 September 2026 (trivial)

---

## 10. Yield model architecture — hybrid design (AG-V2.0 §36)

Recommended pipeline for the software team to implement:

```
                 ┌──────────────────┐
                 │ Weather Forecast │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │ Soil Sensors     │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │ Satellite Data   │
                 └────────┬─────────┘
                          │
        ┌─────────────────▼────────────────────┐
        │ Process-Based Crop Model              │
        │ DSSAT / crop-specific model           │
        └─────────────────┬────────────────────┘
                          │
        ┌─────────────────▼────────────────────┐
        │ Observed Field Data                   │
        │ Yield / Phenology / Soil / Weather   │
        └─────────────────┬────────────────────┘
                          │
                 ┌────────▼─────────┐
                 │ AI/ML Correction │
                 │ / Residual Model │
                 └────────┬─────────┘
                          │
                 ┌────────▼─────────┐
                 │ Yield Prediction │
                 └──────────────────┘
```

**Guardrails for the ML layer (AG-V2.0 §51–52):**
- Temporal split: training / validation / test on separate seasons (e.g. train 2022–2024, validate 2025, test 2026)
- Field-level split alongside temporal — never train and test on the same plots
- **No data leakage** — any field that becomes known only after harvest cannot be a model input for pre-harvest predictions

**Every prediction ships with (AG-V2.0 §49):**
```
prediction_value
confidence
data_quality
model_version
source
validation_status
```

**Validation metrics (AG-V2.0 §50):** MAE, RMSE, R², MAPE (where meaningful), bias.

---

## 11. Waterlogging + disease-risk architecture (AG-V2.0 §12, §43, §45)

Not to be simplified into single-rainfall triggers. Composite models:

**Waterlogging risk:**
```
WATERLOGGING_RISK = f(
    rainfall_24h, rainfall_intensity, rainfall_72h,
    antecedent_VWC, soil_texture, infiltration_rate,
    drainage_class, slope, bed_height, water_table, crop_stage
)
→ VERY_LOW | LOW | MODERATE | HIGH | VERY_HIGH
```

**Ginger root/rhizome rot risk:**
```
ROT_RISK = f(
    rainfall, soil_VWC, drainage, soil_temperature,
    waterlogging_duration, crop_stage, previous_disease_history
)
```

**75 mm rainfall is upstream trigger only** — not automatic diagnosis. AG-V2.0 §13 explicitly rejects the earlier "75 mm → 48–72h anoxia → certain rot" causal claim as unscientific for universal use.

**Two-stage architecture:**
```
Stage 1: 75 mm rainfall → root-zone stress alert
Stage 2: soil moisture + drainage + duration → waterlogging probability
Stage 3: waterlogging + susceptible stage + pathogen presence → rot risk
```

---

## 12. Sensor calibration — VWC vs ADC vs EC (AG-V2.0 §39–41)

Three commonly-confused sensor concepts, **kept strictly distinct** in the KB:

| Field | Meaning | Unit |
|---|---|---|
| `sensor_raw_adc` | Capacitive sensor's raw electrical response | ADC counts |
| `soil_vwc_pct` | Volumetric Water Content = volume of water / total soil volume × 100 | % |
| `soil_ec_dS_m` | Electrical Conductivity of soil solution | dS/m |

**Never treat ADC as VWC.** Calibration model required:
```
VWC = a × ADC + b              # linear
VWC = f(ADC, texture, T, EC)   # nonlinear
```

Calibration model version, per-plot coefficients, and calibration date all stored per plot.

---

## 13. What backend still needs to do

Consolidated list, in priority order, from all of the above:

| # | Task | Blocks | Target |
|:---:|---|---|:---:|
| B1 | Blocklist gate before PHI calc (§5) | food safety, Season 1 launch | 30 Sep |
| B2 | Replace `_ZONE_SEASON_RAIN_MM` with `_STATION_RAINFALL_NORMAL` + metadata (§6) | rainfall deviation accuracy | 30 Sep |
| B3 | Rename `cyclone_alert_active` → `severe_weather_alert_active` throughout code + KB (§7.4) | naming honesty | 24 Sep |
| B4 | Implement new rule D07-CY-WX-001 with 9 boundary golden tests (§8) | severe-weather advisory | 30 Sep |
| B5 | Update `_prediction_stage` DAP cuts to G0–G5 (§4) | stage-conditioned rules | 24 Sep |
| B6 | Add `red_loam` to `soil_type` enum + `soil_texture_class_source` field (§3.1 rows 1–2) | soil advice correctness | 24 Sep |
| B7 | Add source-tag metadata columns (`_source_tier`, `_source_institution`, `_source_ref`) to `kb_rules` and threshold tables (§2) | honest presentation | 7 Oct |
| B8 | Add `phi_blocklist_hit`, `blocklist_reason`, `blocklist_source_ref` fields (§5) | food-safety trace | 30 Sep |
| B9 | Two-track alert fields — `IMD_WARNING_LEVEL` separate from `VIRAAI_AGRO_RISK_LEVEL` (§7.5) | future IMD API integration | 15 Oct |
| B10 | Wire 11 D11 yield-model fields per §10 hybrid architecture | end-of-season yield output | 25 Oct (after §9.7) |
| B11 | Build D12 QA workflow tool from §9.8 spec | advisory self-QA | 25 Oct |
| B12 | Multi-crop schema extension — cassava (crop code CS) alongside ginger | multi-crop Phase 1 | if in Season 1 scope |

---

## 14. Ops / hardware / delivery items (unchanged from KB_DB_STATUS §4)

| Task | Owner | Target |
|---|---|:---:|
| WhatsApp Business credentials + Meta template approval | Ops / admin | before Season 1 |
| USGS credentials + Landsat LST job switch on | Ops | before D14-LT rules fire |
| Main Node weather station install (Kannad pilot) | Hardware install | before season |
| Sub Node sensor install (Kannad pilot) | Hardware install | before season |
| Enroll ≥ 3 plots per cluster | Field ops | rolling; peer baseline needs this |

---

## 15. Multi-crop scope note

**System-level change since KB was authored:** VIRAAI Agro-Guardian AI is no longer ginger-only. AG-V2.0 §30–34 introduces **cassava** as a second crop, using DSSAT MANIHOT-Cassava as the process-based baseline, with CTCRI variety profiles (Sree Vijaya, Sree Jaya, Sree Harsha) as calibration inputs.

**Backend action needed:** confirm whether cassava is in Season 1 scope or Season 2. If Season 1, the KB gets a Domain 15 (Cassava-specific) and the schema needs `crop_code` as a first-class column. Agronomy is ready to author Domain 15 on the same anatomy as Domain 14 (satellite) once the software-side scope decision lands.

---

## 16. Deployment gates for Season 1 pilot

Season 1 activation is blocked until **all** of these are green:

- [ ] §5 blocklist gate implemented + `ginger_pesticide_registry.csv` loaded
- [ ] §4 G0–G5 stage cut-points wired
- [ ] §6 IMD Chikalthana 811.7 mm normal wired with metadata
- [ ] §7 severe-weather rename applied throughout
- [ ] §8 D07-CY-WX-001 built + all 9 boundary tests pass
- [ ] §9.1 pesticide registry signed off by agronomy
- [ ] §9.9 field data-entry checklist active on Kannad pilot plot
- [ ] WhatsApp Meta template approval received
- [ ] Sub Node + Main Node hardware installed at Kannad pilot
- [ ] Agronomist + Backend joint sign-off (§17)

Yield-model output (§9.7 / B10) is a Season 1 mid-season deliverable — not a launch gate.

---

## 17. Joint sign-off

By signing below, both leads confirm that the KB, mapper, engine, and this handoff document are aligned; that the values in §3, §4, §6, §7 are the authoritative ones; and that the checklist in §16 is the complete precondition set for Season 1 activation.

| Role | Name | Date | Signature |
|---|---|:---:|---|
| Agronomy lead | Kuldip | 2026-__-__ | ______________ |
| Backend lead | ________ | 2026-__-__ | ______________ |
| Product / Ops lead | ________ | 2026-__-__ | ______________ |

---

## 18. Document version control

- **V1.0** (2026-09-21) — first joint handoff; consolidates KB_DB_STATUS, AGRONOMIST_REVIEW, AG-V2.0
- Future versions bump on any change to §3, §4, §6, §7 values or §16 gate list
- Change log lives at the bottom of the file; every future edit appends a dated bullet

---

**Note on AG-V2.0 source document:** the copy shared with agronomy runs to §52; the truncation at "F..." mid-sentence (data-leakage example continues) does not affect any value or rule cited above. Kuldip to append §52-end sections in v1.1 if they add operational bindings.

*End of joint handoff document.*
