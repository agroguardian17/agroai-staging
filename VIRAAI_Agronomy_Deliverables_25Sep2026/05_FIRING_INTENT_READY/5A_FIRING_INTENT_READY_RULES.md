# Firing-Intent Ready Rules (5) — Full KB Anatomy

**Purpose:** Complete KB anatomy (delivery class + golden tests + confirmed DSL + Marathi) for the 5 "ready" firing-intent rules per backend agronomy-inputs request §5-A: D01-PH-004, D02-DR-004, D02-ST-002, D03-SB-003, D02-LY-001.

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Ref:** Backend agronomy-inputs §5 (ready-rules list); Master Action List Track A5 (NON_COMPLIANT rewrites); VNMKV Compliance Certificate

---

## ⚠️ Reader note — trigger provenance

Each rule below marks its trigger as either:
- **`[confirmed from prior compliance work]`** — trigger settled during earlier session's tracker review, VNMKV cert, or Master Action List rewrite
- **`[inferred from ID + context]`** — trigger derived from ID pattern; backend to verify against firing-intent decision sheet before deploying

If any inferred trigger conflicts with backend's sheet, backend's sheet wins; I'll re-author on that basis.

---

# Rule 1 — D01-PH-004 · Late-planting phenology penalty (COMPLIANT rewrite)

## Identification
- **Rule ID:** `D01-PH-004`
- **Rule name:** phenology_late_planting_yield_context
- **Domain:** D01 Lifecycle
- **Category:** PH (Phenology)
- **Rule type:** ADVISORY (informational, not blocking)
- **Compliance tag:** COMPLIANT (rewritten from NON_COMPLIANT per Master Action List A5.5 — fixed 12.5% penalty removed)

## Trigger `[confirmed from prior compliance work — Master Action List A5.5]`
```
crop = 'ginger'
AND planting_date > DATE(season_start_year || '-06-15')     -- 2 weeks past on-window
AND stage IN ('G1', 'G2')                                    -- rule fires during early stages
AND cumulative_gdd_since_planting < variety_gdd_at_stage    -- growth lag confirmed
```

**v1.0 vs prior version:** Prior version emitted `yield_penalty_pct = 12.5` as a fixed number regardless of context. Rewrite removes that fixed penalty (was NON_COMPLIANT — insufficient basis for exact figure) and keeps the mechanism as a **contextual advisory** citing observed phenology lag + recommending mitigation.

## Action
```
emit advisory:
    message = 'phenology_lag_from_late_planting'
    template = D01_PH_TEMPLATE_1_LAG_CONTEXT
    severity = 'yellow'
    yield_impact_range = 'variable_10_to_20_pct'          -- context, NOT a fixed number
    contributing_signals = ['planting_date', 'gdd_lag', 'variety_baseline']
    mitigation_actions = ['variety_switch_short_duration', 'irrigation_readiness', 'basal_n_top_up']
```

## Delivery class
`ONCE_UNTIL_RESOLVED` — resolution when `cumulative_gdd_since_planting >= variety_gdd_at_stage - 20%` (GDD catch-up observed) OR farmer records mitigation-action-taken

## Precedence relations
- `D01-PW-001 SEQUENCES D01-PH-004` — planting-window warning fires at planting-date recording; phenology-lag fires later once GDD data confirms lag
- `D06-BW-001 SUPPRESSES D01-PH-004` — if plot wilt-blocked, phenology-lag advisory is moot

## Kannad note
Kannad Western Scarcity zone: late planting (>15 June) pushes G3 into November when temperature drops and GDD accumulation slows — phenology lag compounds. VNMKV OFT shows 10-20% yield variation range depending on rainfall carryover; no single fixed figure defensible.

## Marathi advisory template

**D01_PH_TEMPLATE_1_LAG_CONTEXT (YELLOW — contextual, no fixed %):**
```
⚠️ पिकाची वाढ अपेक्षित गतीने होत नाही

आपली माहिती:
- लागवडीची तारीख: {planting_date_mr}
- आजची अवस्था: {stage_mr}
- अपेक्षित GDD: {expected_gdd} | प्रत्यक्ष GDD: {actual_gdd}

काय दिसत आहे:
- लागवड उशिरा झाल्यामुळे तापमान-आधारित वाढ अपेक्षेपेक्षा मंद
- G3 (गड्डा-निर्मिती) अवस्था नोव्हेंबरच्या शेवटी येईल — तापमान कमी होते तेव्हा वाढ आणखी मंदावते
- उत्पादनावर परिणाम **variable** — 10 ते 20% कमी होऊ शकते, पण exact number देता येत नाही
  (कारण पावसाची carry-over, सिंचन-उपलब्धता, आणि मध्ये येणारे अन्य ताण — यांच्यावर अवलंबून)

आत्ता करा:
✅ सिंचन थांबवू नका — पावसाच्या शेवटी drip चालू ठेवा
✅ Basal N चा top-up आधीच पूर्ण असल्यास पुढच्या top-dress ला पुढे ढकलू नका
✅ Foliar spray (Zn, B) - micronutrient top-up विलंबाची भरपाई करते
```

## Golden tests (5)

| # | Setup | Expected |
|:-:|---|---|
| T1 | planting_date=2026-06-25, stage=G1, actual_gdd < expected_gdd | Fires YELLOW; template 1; no fixed % emitted |
| T2 | planting_date=2026-06-25, stage=G1, actual_gdd == expected_gdd | Does not fire (no lag confirmed) |
| T3 | planting_date=2026-06-01 (on-window), stage=G1 | Does not fire (not late) |
| T4 | planting_date=2026-06-25, stage=G3 | Does not fire (rule scope is G1/G2 only) |
| T5 | Any prior fire; farmer records mitigation-action | Resolved; rule silent |

---

# Rule 2 — D02-DR-004 · Drainage adequacy at pre-planting

## Identification
- **Rule ID:** `D02-DR-004`
- **Rule name:** drainage_pre_planting_adequacy_check
- **Domain:** D02 Soil
- **Category:** DR (Drainage)
- **Rule type:** ADVISORY (recommendation with farmer action)
- **Compliance tag:** COMPLIANT

## Trigger `[inferred from ID pattern + D02-DR-001..003 series]`
```
crop = 'ginger'
AND plot_status = 'pre_planting'
AND (
    soil_texture_class IN ('heavy_clay', 'vertisol')
    OR slope_pct < 0.5
    OR has_drainage_history_flag = FALSE
)
```

**Trigger interpretation:** DR-004 is likely the 4th drainage rule after DR-001 (basic drainage check), DR-002 (drainage-rate measurement), DR-003 (drainage-crop-compatibility). DR-004 fires at pre-planting to remind farmer of drainage prep specifically for waterlog-prone plots.

## Action
```
emit advisory:
    message = 'drainage_prep_recommendation'
    template = D02_DR_TEMPLATE_1_DRAINAGE_PREP
    severity = 'yellow'
    recommended_actions = ['bed_furrow_layout', 'field_slope_verify', 'outlet_channel_check']
    contributing_signals = ['soil_texture', 'slope', 'plot_history']
```

## Delivery class
`ONCE_UNTIL_RESOLVED` — resolution when `drainage_prep_confirmed = TRUE` (farmer confirms bed prep OR agronomist scouting confirms)

## Precedence relations
- `D02-DR-004 SEQUENCES D02-LY-001` — drainage check evaluated before layout rule (proper drainage informs layout choice)
- No conflict with other D02 rules (each addresses a distinct soil parameter)

## Kannad note
Kannad Western Scarcity zone: vertisol drainage rate is 0.5-2 cm/hr (slow). Rhizome rot from poor drainage documented at 20-30% yield loss on flat plots without bed-furrow. Drainage prep is the single most impactful pre-planting action.

## Marathi advisory template

**D02_DR_TEMPLATE_1_DRAINAGE_PREP:**
```
⚠️ लागवडीपूर्वी निचरा (drainage) तपासणी करा

आपल्या शेताची माहिती:
- मातीचा प्रकार: {soil_texture_mr}
- उतार: {slope_pct}%
- {IF has_drainage_history_flag = FALSE} - निचरा-नोंद उपलब्ध नाही {ENDIF}

काळ्या मातीत निचरा हळू (0.5-2 सेमी/तास) — पाणी साचून राहते. अद्रकीच्या गड्ड्याला हे धोकादायक:
- गड्डा-कूज (rhizome rot) — 20-30% पर्यंत उत्पादन-हानी
- जिवाणू-मर (bacterial wilt) चा प्रादुर्भाव वाढतो

लागवडीपूर्वी करा:
✅ **रुंद-बेड (broad-bed) पद्धत:** 90 सेमी बेड + 60 सेमी सरी — पाणी सरीत सोडते
✅ **शेताचा उतार तपासा:** 1-2% उतार असावा; पाणी एका दिशेने जाऊ शकेल
✅ **Outlet channel:** शेताच्या खालच्या बाजूला पाणी बाहेर जाण्याचा मार्ग तयार ठेवा
✅ लागवडीच्या 15 दिवसआधी बेड तयार करा — माती stable होते

Agronomist ला call करून scouting करा — तुमच्या शेतासाठी exact plan साठी.
```

## Golden tests (5)

| # | Setup | Expected |
|:-:|---|---|
| T1 | soil=vertisol, slope=0.3%, no drainage history | Fires YELLOW; all 3 signals contribute |
| T2 | soil=loam, slope=2%, drainage history YES | Does not fire (all 3 fail) |
| T3 | soil=vertisol, slope=2%, drainage history YES | Fires (vertisol alone triggers) |
| T4 | Any prior fire; drainage_prep_confirmed=TRUE | Resolved; silent |
| T5 | plot_status='growing' (past pre-planting) | Does not fire (out of scope) |

---

# Rule 3 — D02-ST-002 · Soil texture re-classification at lab entry

## Identification
- **Rule ID:** `D02-ST-002`
- **Rule name:** soil_texture_lab_reclassification
- **Domain:** D02 Soil
- **Category:** ST (Soil Texture)
- **Rule type:** DATA_INTEGRITY (silent guard — re-derives derived fields on lab data entry)
- **Compliance tag:** COMPLIANT

## Trigger `[confirmed from Master Action List B5.2 — soil_texture_class_source field re-derivation on lab entry]`
```
soil_lab_report_entered = TRUE                               -- event trigger: farmer/agronomist enters lab report
AND lab_report_contains_texture_data = TRUE
```

## Action
```
recompute:
    soil_texture_class = classify_from_lab(sand_pct, silt_pct, clay_pct)  -- USDA soil triangle
    soil_texture_class_source = 'laboratory_verified'                       -- promote from farmer-declared

re-evaluate downstream rules that reference soil_texture_class:
    - D02-DR-* (drainage)
    - D02-LY-001 (layout)
    - D03-DS-001 (drip system spec)
    - D03-WB-* (water budget confidence multiplier)

emit silent_log:
    message = 'soil_texture_reclassified'
    old_class = {previous_texture_class}
    new_class = {new_texture_class}
    source_change = 'farmer_declared → laboratory_verified'
    downstream_rules_re_evaluated = [list]
```

## Delivery class
`SILENT_GUARD` — no farmer message; internal data integrity operation. If farmer wants to see the reclassification, it appears in plot-details page.

## Precedence relations
- `D02-ST-002 FEEDS D02-DR-*, D02-LY-*, D03-DS-*, D03-WB-*` (data reclassification triggers downstream re-evaluation)
- Not a conflict rule; purely data-integrity

## Kannad note
Kannad plots often show vertisol characteristics visually but lab-tested clay% can reveal sub-classes (Typic vs Vertic Haplustepts) that matter for drainage rate. Lab-verified reclassification improves D03-WB confidence multiplier and D06-BW-001 risk estimates.

## Marathi note (internal — no farmer message)
"मातीचे परीक्षण report मिळाल्यावर, मातीचा प्रकार आपोआप update होतो. आधीच्या शिफारसी नव्या माहितीप्रमाणे re-evaluate होतील."

## Golden tests (3)

| # | Setup | Expected |
|:-:|---|---|
| T1 | Lab report entered with sand=25/silt=30/clay=45 | soil_texture_class='clay'; source='laboratory_verified'; downstream rules re-evaluated |
| T2 | Lab report entered with sand=60/silt=25/clay=15 | soil_texture_class='sandy_loam'; source='laboratory_verified'; downstream re-eval |
| T3 | Farmer edits declared texture (no lab report) | Rule does NOT fire (only lab-entry triggers; farmer edit is a different rule) |

---

# Rule 4 — D03-SB-003 · Sub-node battery-life advisory

## Identification
- **Rule ID:** `D03-SB-003`
- **Rule name:** subnode_battery_low_advisory
- **Domain:** D03 Water & Irrigation
- **Category:** SB (Sub-node hardware)
- **Rule type:** HARDWARE_ADVISORY
- **Compliance tag:** COMPLIANT

## Trigger `[inferred from ID + sub-node readings context]`
```
sub_node_battery_pct < 20
AND days_since_last_battery_alert > 7          -- prevent daily spam
```

## Action
```
emit advisory:
    message = 'subnode_battery_low'
    template = D03_SB_TEMPLATE_1_BATTERY
    severity = 'yellow'
    days_to_dead_estimate = compute_battery_projection(current_pct, drain_rate_per_day)
    contributing_signals = ['hardware_health']
```

## Delivery class
`ONCE_UNTIL_RESOLVED` — resolution when `sub_node_battery_pct >= 40` (battery replaced/charged)

## Precedence relations
- `D03-SB-003 SEQUENCES D03-WB-006` — battery alert fires first; if farmer doesn't act, sensor eventually goes silent and WB-006 (sensor gap) fires
- No conflict with other D03 rules

## Kannad note
Kannad Western Scarcity zone: April-May heat months drain sub-node batteries faster (~15-20% faster drain rate observed). Ensure spare batteries stocked before summer.

## Marathi advisory template

**D03_SB_TEMPLATE_1_BATTERY:**
```
🔋 Sub-node ची battery कमी झाली आहे

आत्ताची battery: {battery_pct}%
अंदाजे किती दिवस चालेल: {days_to_dead_estimate} दिवस

आत्ता करा:
✅ शेतात जाऊन sub-node battery तपासा
✅ Solar panel वर धूळ किंवा पानं आहेत का बघा (charging कमी करते)
✅ Spare battery असल्यास बदला
✅ नाही तर - technician ला call करा: {helpline}

तोपर्यंत:
- Sensor readings कमी वेळा येतील — शिफारसी शक्य नाहीत
- Battery पूर्ण संपल्यास Sensor गप्प alert (D03-WB-006) येईल
```

## Golden tests (4)

| # | Setup | Expected |
|:-:|---|---|
| T1 | battery=15%, last alert 10 days ago | Fires YELLOW; template 1 |
| T2 | battery=15%, last alert 3 days ago | Does not fire (< 7 day cooldown) |
| T3 | battery=25% | Does not fire (above 20% threshold) |
| T4 | Fired earlier; farmer replaced → battery=90% | Resolved; silent |

---

# Rule 5 — D02-LY-001 · Flat-layout-on-vertisol BLOCKING gate

## Identification
- **Rule ID:** `D02-LY-001` (existing rule — escalation per VNMKV Compliance Certificate + Master Action List B1.5)
- **Rule name:** flat_layout_vertisol_block
- **Domain:** D02 Soil
- **Category:** LY (Layout)
- **Rule type:** BLOCKING_GATE (upgraded from CONDITIONAL to BLOCKING per B1.5)
- **Compliance tag:** COMPLIANT (VNMKV Certificate §5 escalation authority)
- **Change from prior version:** Severity upgraded CONDITIONAL → BLOCKING; farmer override still permitted but requires explicit agronomist sign-off

## Trigger `[confirmed from Master Action List B1.5 + VNMKV Compliance Certificate]`
```
crop = 'ginger'
AND plot_status = 'pre_planting'
AND planting_method = 'flat'
AND soil_texture_class IN ('heavy_clay', 'vertisol', 'clay_loam_heavy')
```

## Action
```
emit blocking_advisory:
    message = 'flat_layout_vertisol_block'
    template = D02_LY_TEMPLATE_1_FLAT_BLOCK
    severity = 'red'
    farmer_override_permitted = TRUE      -- with explicit agronomist sign-off
    agronomist_override_legal_flag = 'flat_layout_vertisol_farmer_choice_after_agronomist_consult'
    contributing_signals = ['planting_method', 'soil_texture_class']
    require_agronomist_consult = TRUE
```

## Delivery class
`ONCE_UNTIL_RESOLVED` — resolution when `planting_method` changed to `broad_bed` / `raised_bed` / `furrow` OR `agronomist_flat_layout_override_signed = TRUE`

## Precedence relations
- `D02-LY-001 SUPPRESSES all D03-WB-* dose recommendations while active` (until resolved or overridden) — because water-budget engine `vnmkv_compliance_flag = 'flat_layout_on_vertisol'` should not be treated as a normal plot
- `D02-DR-004 SEQUENCES D02-LY-001` — drainage check evaluated before layout block (informs the block message)
- `D02-LY-001 BUNDLES D02-DR-004` — if both fire, single message combines drainage + layout reasoning

## Kannad note
Kannad Western Scarcity zone: 92% of soils classified as vertisol (Marathwada Chief Soil Series data). Flat-layout ginger on vertisol in Kannad = documented 40-60% yield loss + severe rhizome rot risk. VNMKV Parbhani strongly recommends broad-bed as default.

## Marathi advisory template

**D02_LY_TEMPLATE_1_FLAT_BLOCK (RED — vertisol flat-layout block):**
```
🛑 सपाट लागवड (flat) या मातीत टाळा

आपल्या शेतात:
- मातीचा प्रकार: **{soil_texture_mr}** (काळी माती / भारी मृद)
- निवडलेली पद्धत: **सपाट लागवड (flat)**

हे combination गंभीर धोका आहे:
- **गड्डा-कूज (rhizome rot):** पाणी साचून राहते; 40-60% पर्यंत पीक-हानी
- **जिवाणू-मर:** ओलावा जास्त राहणे → Ralstonia जिवाणू पसरतो
- **VNMKV Parbhani शिफारस:** काळ्या मातीत **कधीही सपाट लागवड नाही**

पर्याय (कोणताही निवडा):
✅ **रुंद बेड (broad-bed) — VNMKV सर्वोत्तम शिफारस:**
   - 90 सेमी बेड + 60 सेमी सरी
   - पाणी सरीत सोडते; गड्डा कोरडा राहतो
✅ **उंच बेड (raised-bed):**
   - 60 सेमी बेड + 60 सेमी सरी + बेड 15 सेमी उंच
   - पाणी निचरा जलद
✅ **सरी-वरंबा (furrow):**
   - 45 सेमी सरी अंतर
   - पारंपरिक पद्धत, drainage चांगला

Agronomist ला call करा — तुमच्या शेतासाठी सर्वोत्तम पद्धत निवडायला मदत करतील.
जर तरीही आपण flat layout ठेवायचा असेल — agronomist च्या सही-नंतरच लागवड नोंद होईल.
```

## Golden tests (5)

| # | Setup | Expected |
|:-:|---|---|
| T1 | planting_method='flat', soil='vertisol', pre_planting | Fires RED; blocking; agronomist consult required |
| T2 | planting_method='flat', soil='sandy_loam' | Does not fire (soil not vertisol) |
| T3 | planting_method='broad_bed', soil='vertisol' | Does not fire (method compliant) |
| T4 | planting_method='flat', soil='vertisol', agronomist_override_signed=TRUE | Resolved; legal_flag logged; plot proceeds with flat |
| T5 | plot_status='growing' (past pre-planting) | Does not fire (out of scope) |

---

## Summary — 5 rules delivered

| Rule ID | Domain | Delivery class | Severity | Precedence relations added |
|---|:---:|:---:|:---:|:---:|
| D01-PH-004 | D01 Lifecycle | ONCE_UNTIL_RESOLVED | YELLOW | 2 (SEQUENCES D01-PW-001, SUPPRESSED by D06-BW-001) |
| D02-DR-004 | D02 Soil | ONCE_UNTIL_RESOLVED | YELLOW | 1 (SEQUENCES D02-LY-001) |
| D02-ST-002 | D02 Soil | SILENT_GUARD | INFO | 1 (FEEDS downstream domains) |
| D03-SB-003 | D03 Water | ONCE_UNTIL_RESOLVED | YELLOW | 1 (SEQUENCES D03-WB-006) |
| D02-LY-001 | D02 Soil | ONCE_UNTIL_RESOLVED | RED (upgraded) | 3 (SUPPRESSES D03-WB-*, SEQUENCES D02-DR-004, BUNDLES D02-DR-004) |

**Golden tests total:** 22 across 5 rules
**Marathi templates added:** 5 (D01-PH-1, D02-DR-1, D03-SB-1, D02-LY-1; D02-ST-002 is silent)
**Precedence relations added:** 8

---

## Backend implementation checklist

- [ ] Add/update 5 rule bodies across `Domain1_Rules_Ginger.json`, `Domain2_Rules_Ginger.json`, `Domain3_Rules_Ginger.json`
- [ ] Add 5 Marathi templates to advisory template repository
- [ ] Add 8 precedence relations to `_precedence[]`
- [ ] Add 22 golden tests
- [ ] Verify inferred triggers (D02-DR-004, D03-SB-003) against backend's firing-intent decision sheet — flag discrepancies

**Estimated backend integration effort:** 3-4 hours (rules + templates + tests).

---

## Sign-off

5 rules delivered with full KB anatomy. Triggers marked `[confirmed]` are grounded in prior compliance work; triggers marked `[inferred]` need backend cross-check. All Marathi templates use plain conversational Marathi (per style guidance established in earlier UI/advisory work).

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

*End of Firing-Intent Ready Rules v1.0*
