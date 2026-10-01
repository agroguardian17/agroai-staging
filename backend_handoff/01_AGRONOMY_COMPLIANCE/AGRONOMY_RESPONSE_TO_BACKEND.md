# Agronomy team response to Backend
## KB + DB status audit + AGRONOMIST_REVIEW sign-offs

**Date:** 21 September 2026 · **From:** Kuldip (KB/Agronomy) · **To:** Backend team
**Re:** `KB_DB_STATUS.md` + `AGRONOMIST_REVIEW.md`

---

## 0. Executive summary — एक ओळीत

Software substantially complete आहे, मान्य आहे. आमच्याकडून **9 sign-offs + 4 datasets + 2 agronomy artifacts + 1 blocklist reconciliation** पुरवायचे आहेत. एक critical flag: **chlorpyriphos PHI ऐवजी D05-CH-001 blocklist gate** पहिले लागतो — त्यावर पहिले काम.

---

## 1. Nine sign-offs on `AGRONOMIST_REVIEW.md` — तात्काळ decisions

| # | Field | Backend's default | **Agronomy decision** | Reasoning |
|---|---|---|---|---|
| 1 | `soil_type` red→laterite | as proposed | ❌ **CHANGE**: red → `red_loam` (add this value to the enum) | Marathwada's "red" soils are Alfisols/Inceptisols — red loams — NOT true laterites. Laterite formation needs > 2000 mm rainfall + specific weathering (Konkan, Kerala, Chota Nagpur). Applying laterite assumptions (very low CEC, high P-fixation, low water holding) to Marathwada red loams gives wrong irrigation and P-dose advice. |
| 2 | `soil_texture_class` 3-class | as proposed | ✅ **OK for Phase 1** with note | Coarse but adequate for rule triggering. When plot has a lab texture (%sand/silt/clay), derived class should be OVERRIDDEN by lab result via a new `soil_texture_class_source` field — 'derived' vs 'lab'. Small backend addition. |
| 3 | `agro_climatic_zone` district map | as proposed | ⚠️ **OK as interim; VNMKV validation pending** | Mostly matches ICAR Zone 8 (Western Maharashtra Plateau) sub-zones. Ch. Sambhajinagar/Jalna/Beed = central ✓; Latur/Nanded/Parbhani/Hingoli = eastern ✓; Dharashiv = western/southern ✓. If zone table is Marathwada-only, restrict scope explicitly; if statewide, add Vidarbha/Konkan/Western Ghat zones. Flag as D14-OI-09 companion. |
| 4 | `prediction_stage` DAP cuts | `<0 pre, <90 g1_end, <200 mid, else pre_harvest` | ❌ **REVISE** to match D01 lifecycle rules | Current cuts collapse G1+G2 (the two most different vegetative sub-stages for irrigation and nutrient dosing) into one bucket. **Correct cut-points**:<br>• `<0`: pre_season<br>• `0-45`: g1_sprouting_establishment<br>• `45-120`: g2_vegetative<br>• `120-180`: g3_rhizome_formation<br>• `180-220`: g4_rhizome_maturation<br>• `>220`: pre_harvest_observation<br>Aligns with D01-STG-* rules and Kannad variety Mahim behaviour. |
| 5 | `phi_days_remaining` PHI table | mancozeb 7, copper 5, **chlorpyriphos 14**, imidacloprid 40, default 21 | 🚨 **CRITICAL FLAG** — see §2 | Chlorpyriphos is on D05-CH-001 BLOCKLIST for ginger; it should NEVER reach a PHI calculation. Presence of a PHI value implies chlorpyriphos is spray-able, contradicting the immutable KB rule. Code-vs-KB inconsistency, not just a value tweak. Full FSSAI-aligned PHI table by 30 Sep (§3.1). |
| 6 | `rainfall_deviation_pct` normals | Western 750 / Central 680 / Eastern 820 mm | ❌ **REPLACE with IMD district normals** | Direction right, values placeholder. Correct IMD 1991–2020 SW monsoon normals for pilot districts:<br>• Ch. Sambhajinagar: **726 mm**<br>• Jalna: 682 · Beed: 666 · Dharashiv: 632<br>• Latur: 807 · Nanded: 895 · Parbhani: 776 · Hingoli: 862<br>Full IMD dataset in §3.2. Switch from zone-averaged normal to **district-specific normal** — same code path, better fidelity. |
| 7 | `cyclone_alert_active` proxy | wind ≥ 60 km/h AND rain ≥ 50 mm | ⚠️ **RENAME + RELAX** | (a) Not a cyclone alert — **rename to `severe_weather_alert_active`** for honesty (removes false impression of official IMD warning). (b) Wind threshold too strict — Marathwada ginger-damaging events (Sep-Nov post-monsoon lows) deliver heavy rain WITHOUT 60 km/h wind but do actual damage during G4. Recommend:<br>**`wind ≥ 40 km/h OR rain ≥ 75 mm in 24h OR forecast rain > 100 mm cumulative 48h`**<br>OR-based, not AND. Ties into D07-CY-* rules. |
| 8 | `vafsa_state` | too_wet ≥ vwc_saturation, too_dry ≤ vwc_stress_threshold, else workable | ✅ **OK — approved** | Uses per-plot entered thresholds; no hardcoded agronomy assumption. Data-entry side must ensure `vwc_saturation` and `vwc_stress_threshold` populated per plot from D02 soil test + D03 water-holding derivation. Add validation: if either threshold null, `vafsa_state` = 'unknown', not silent fallback. |
| 9 | `stage_source = "calendar"` | as proposed | ✅ **OK for Phase 1** with future-flag | Calendar (DAP-based) staging right for now. In Phase 2 (post-season-1): add `stage_source` enum ('calendar', 'gdd', 'ndvi_curve_fit'), let D14-PH-002 supply override candidate. Log both, use calendar authoritative until Phase 2. Ties to D14-OI-08 (VNMKV phenology validation). |

**Summary:** 3 ✅ approved · 3 ⚠️ conditional · 2 ❌ change required · 1 🚨 critical

---

## 2. Critical flag — chlorpyriphos PHI vs D05-CH-001 blocklist

**Problem:** Item 5 lists `chlorpyriphos: 14 PHI days`. But D05-CH-001 (immutable rule) blocks chlorpyriphos on ginger. Two things are simultaneously true in the code:

- KB rule: "chlorpyriphos on ginger → refuse recommendation" (immutable)
- PHI table: "if chlorpyriphos is used, wait 14 days before harvest" (implies it CAN be used)

**Why it matters:** If a farmer enters `pesticide_group: chlorpyriphos` in Season Records (from mis-labelled bottles or off-market advice), the mapper will happily compute `phi_days_remaining = 14` and pass it to the engine. The engine then has to detect the entry is a policy violation. That gate should fire BEFORE the PHI calculation.

**Fix (backend side, small):**
```python
IF pesticide_group IN blocklist_for_crop:
    phi_days_remaining = NULL
    phi_blocklist_hit = TRUE                          # new field
    farmer_alert_type = 'blocklisted_input_detected'  # existing D05 branch
ELSE:
    phi_days_remaining = _PHI_DAYS_BY_GROUP.get(group, 21)
```

**Fix (agronomy side):** Deliver full FSSAI-blocklisted-and-registered PHI table for ginger as one integrated document (§3.1).

**Priority:** BEFORE season 1 pilot. Food safety.

---

## 3. What agronomy will deliver — timeline

Numbered by priority + backend dependency:

### 3.1 FSSAI-aligned PHI + blocklist table for ginger
- **Owner:** Kuldip + VNMKV Parbhani plant protection consult
- **Deliverable:** `ginger_pesticide_registry.csv` — columns: `group`, `trade_names`, `crop_registered`, `registered_dose`, `phi_days`, `mrl_ppm`, `blocklist_reason_if_any`, `source_ref` (CIB reg / FSSAI notification / GAP)
- **Target:** 30 September 2026
- **Blocks:** field #5, chlorpyriphos flag above, D05 blocklist expansion

### 3.2 IMD district normals dataset
- **Owner:** Kuldip
- **Deliverable:** `imd_district_normals_1991_2020.csv` — monthly + seasonal normals for all Marathwada districts + placeholder rows for pilot expansion (Nashik, Ahmadnagar, Solapur)
- **Target:** 25 September 2026
- **Blocks:** field #6

### 3.3 Growth-stage cut-point table (aligned with D01 rules)
- **Owner:** Agronomy team
- **Deliverable:** `ginger_stage_cutpoints_mahim.csv` — DAP ranges per stage for Mahim (Kannad standard), one placeholder row per additional variety
- **Target:** 24 September 2026
- **Blocks:** field #4

### 3.4 Soil-type enum extension request
- **Owner:** Agronomy specifies, backend implements
- **Deliverable:** enum includes `red_loam` distinct from `laterite`; texture override via `soil_texture_class_source`
- **Target:** 24 September 2026
- **Blocks:** fields #1, #2

### 3.5 Severe-weather threshold table
- **Owner:** Agronomy team
- **Deliverable:** confirm OR-based threshold in §1 item 7; rename `cyclone_alert_active` → `severe_weather_alert_active` throughout
- **Target:** 24 September 2026
- **Blocks:** field #7

### 3.6 Agro-climatic zone / district table (VNMKV validation)
- **Owner:** Kuldip → VNMKV Parbhani consultation
- **Deliverable:** validated district → zone mapping; decide zone-table scope (Marathwada-only vs Maharashtra-statewide)
- **Target:** 15 October 2026 (external touchpoint)
- **Blocks:** field #3 — interim mapping OK meanwhile

### 3.7 Yield model definition (D11 — biggest agronomy artifact)
- **Owner:** Kuldip + agronomy team; VNMKV / ICAR-CTCRI reference lit review
- **Deliverable:** `D11_YIELD_MODEL_v1.md` covering:
  - **Yield estimation method** — DSSAT-style stage-wise multiplicative model with per-stage water/nutrient/pest deficit coefficients. Adopt ICAR-CTCRI Trivandrum's ginger yield model as baseline, re-calibrate to Kannad via season-1 data.
  - **U-value register** — 11-15 yield-limiting factors ranked by expected yield cost in ginger (soft rot > drainage failure > K deficiency > rhizome fly > seed vigour > drought during rhizome fill > excess N > frost/heat stress > weeds > chlorophyll loss > etc.). Each with EST u-value (0-1 fraction of yield potential lost) for Phase 1, replaced with empirical means after season 1.
  - **Yield-gap attribution** — estimated yield vs. achievable yield (variety potential × site index), split gap into (a) sum of u-values for factors observed, and (b) "unexplained residual." Residual > 25% flags for agronomist review.
- **Target:** 15 October 2026 (v1 draft); Phase 2 recalibration after season 1
- **Blocks:** 11 D11 fields, entire yield-prediction domain
- **This is the single highest-leverage deliverable from agronomy.**

### 3.8 Advisory-QA workflow spec (D12)
- **Owner:** Kuldip
- **Deliverable:** `D12_QA_WORKFLOW.md` covering:
  - Alert classification — 3 states: `confirmed_true_positive`, `false_positive`, `unresolved`. Farmer + agronomist joint; disagreement → agronomist wins.
  - Bias observation intake — weekly agronomist call with 3-5 random farmers reviewing week's advisories; observations into `bias_observation` table.
  - Non-compliance reason capture — 6-value enum: `already_done`, `cost_barrier`, `unavailable_input`, `disagreed`, `forgot`, `other`. Free-text alongside.
  - Photo upload + labelling — WhatsApp forwarded photos into labelling backlog; labels are D06 differential categories.
  - Cluster assignment — 8-12 plots per cluster; on enrollment, geographic proximity within 3 km AND variety AND planting-week bucket.
- **Target:** 10 October 2026
- **Blocks:** 8 D12 fields

### 3.9 Field data entry cadence — plot enrollment plan
- **Owner:** Field ops (agronomy sets schedule)
- **Deliverable:** minimum data entry checklist per plot at 5 timepoints (pre-plant, DAP 30, DAP 90, DAP 150, harvest)
- **Target:** 24 September 2026
- **Blocks:** most of 377 ready rules stay quiet without this

### 3.10 One-off percolation test protocol
- **Owner:** Agronomy specifies, field ops executes
- **Deliverable:** two-paragraph protocol (dig 30cm pit, saturate, time water-level drop from top mark to 5cm below; classify as `rapid < 30 min`, `moderate 30-90 min`, `slow > 90 min`)
- **Target:** 24 September 2026 (trivial)
- **Blocks:** `percolation_class`, `percolation_time_hours` fields

---

## 4. Priority order for backend

Recommended sequencing so we don't idle each other:

**Week 1 (22-28 Sep) — parallel**
| Backend does | Agronomy does |
|---|---|
| Add `red_loam` to soil_type enum + `soil_texture_class_source` field | Deliver §3.2 IMD normals, §3.3 stage cutpoints, §3.5 severe-weather thresholds |
| Rename `cyclone_alert_active` → `severe_weather_alert_active`, OR-based logic | Deliver §3.10 percolation protocol, §3.9 data entry checklist |
| Wire the blocklist gate (§2) as precondition to PHI calc | Deliver §3.1 PHI + blocklist registry |

**Week 2-3 (29 Sep - 12 Oct)**
| Backend does | Agronomy does |
|---|---|
| Ingest PHI registry into `_PHI_DAYS_BY_GROUP` map + blocklist gate | Deliver §3.8 D12 QA workflow spec |
| Ingest IMD normals as district lookup | Draft §3.7 yield model v1 |
| Apply revised stage cut-points | VNMKV Parbhani consult (§3.6) |

**Week 4+ (13-31 Oct)**
| Backend does | Agronomy does |
|---|---|
| Build D12 QA workflow tool from spec | Finalise §3.7 yield model, deliver |
| Wire 11 D11 yield-model fields | Field ops: start plot enrollment (≥3 per cluster) |
| Apply VNMKV-validated zone table | Season 1 pilot activation checklist |

**By 1 November 2026:** all 481 rules technically ready to fire; season 1 data starts flowing; Phase 2 recalibration slate opens.

---

## 5. Standing recommendations from agronomy — principles

Beyond immediate items, three principles for the collaboration going forward:

**5.1 Never invent an agronomy default silently.**
Where the mapper needs a value we haven't given you, the honest choice is:
- Leave the field NULL and let the engine handle via UNKNOWN three-valued logic, OR
- Use an obviously conservative default AND log it as `<field>_source = 'placeholder_pending_agronomist'`

The list in `AGRONOMIST_REVIEW.md` is the right pattern — keep it. Every new default applied without agronomist sign-off is a future silent-error risk.

**5.2 Blocklisted inputs must trigger a policy gate, not a value calculation.**
Item 5 above is one case; others exist (banned chemicals per FSSAI, unregistered varieties per Seed Act, etc.). Design pattern: whenever a farmer enters something the KB has an immutable "no" on, mapper routes through policy-check function, not normal computation. §2 sketches the fix for chlorpyriphos; adopt same pattern across board.

**5.3 Peer/regional baselines need not wait for 3 plots per cluster.**
Interim: use ICAR-CTCRI published NDVI curves for ginger G1-G5 stages as regional baseline seed, at reduced confidence (SRC-EST rather than SRC-Q). This lets the 5 D14 baseline-dependent rules (NV-003, NV-005, NR-003, PH-003, FU-004) fire with confidence ≤ 0.65 during season 1, rather than staying silent. As soon as 3+ peer plots enroll, peer baseline replaces the seed, confidence lifts to 0.75+. Small "seed-baseline table" backend addition that unlocks real satellite advisory in season 1.

---

## 6. What agronomy needs FROM backend

Symmetrical ask:

- **6.1 Data-entry UI dry-run** — working demo of the Data Entry, Lab Soil Test, Crop Scouting, and Season & Scheme Records pages, tested against my Kannad plot as first pilot user. Before we sign off any data-entry checklist (§3.9), we need to know the UI actually captures what our checklist asks for.
- **6.2 Alert display previews** — 3-5 sample advisory messages rendered exactly as they will appear on WhatsApp, so we can review Marathi phrasing before Meta template approval locks the text.
- **6.3 QA workflow tool wireframe** — before I write §3.8 in full, a rough UI wireframe of the review tool so my spec matches what backend will build.
- **6.4 Yield-prediction output format** — how you want the yield-model output structured (single number? point-estimate + 90% band? per-cause attribution list?). We'll design the model accordingly.

---

## 7. Kannad plot as first pilot — offer

For everything above where "we need real data first," my own Kannad plot can serve as pilot case #1 through season 1. That gets us:
- Real data flowing through the mapper
- Farmer-in-the-loop review of every advisory (I read every one before it goes)
- Weekly agronomy-backend review call on what fired, what should have, what didn't, what shouldn't have
- End-of-season yield-model calibration data point

If backend is game, I'll start enrolling my plot on 25 September and complete pre-plant + G0 data entry by 30 September, which lets the mapper start firing rules from planting week.

---

## 8. Bottom line — from agronomy

The KB is frozen at 481 rules, discipline held. Backend has closed the software gap to where remaining work is agronomy + ops. **The nine sign-offs above are our answer; three require software changes; one is a food-safety critical flag; the yield-model definition is our single largest deliverable — targeted for 15 October.**

We are aligned. Let's ship.

— Kuldip
Knowledge Base, Agronomy, and Product Coordination
Agro-Guardian AI

---

*End of agronomy response.*
