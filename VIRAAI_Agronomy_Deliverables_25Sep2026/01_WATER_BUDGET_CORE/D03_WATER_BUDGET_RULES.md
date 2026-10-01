# D03-WB — Water Budget Rules (8 rules)

**Purpose:** Water-budget-based irrigation advisory rules. **Complementary** to existing VWC-based D03 rules (D03-MN-002, D03-MN-004, D03-DS-001) and satellite fusion rules (D14-FU-001, D14-FU-002). All precedence relations declared explicitly to prevent collision.

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Domain:** D03 Water & Irrigation
**Category:** WB (Water Budget)

---

## 0. Collision-avoidance framework (mandatory reading)

**Ground-truth precedence hierarchy (from all prior compliance work — unchanged):**

```
VWC probe (physical sensor) > Water-budget (extrapolated) > Satellite context
```

**How D03-WB rules avoid collision with existing rules:**

| Existing rule | Collision risk | Resolution declared in each D03-WB rule |
|---|---|---|
| D03-MN-002 (VWC saturation "don't water") | High — WB might say "irrigate" while probe says saturated | `D03-MN-002 SUPPRESSES D03-WB-*` (all irrigation-recommending WB rules) |
| D03-MN-004 (VWC low "give water") | Medium — WB might duplicate the message | `D03-WB-001 BUNDLES D03-MN-004` (single farmer message) |
| D03-DS-001 (drainage stress) | Low — different trigger domain (drainage vs deficit) | No relation needed; both can fire independently |
| D14-FU-001 (satellite-VWC fusion) | Low — satellite is lowest precedence | `D03-WB-* SEQUENCES D14-FU-001` (WB decides first, satellite corroborates) |
| D14-FU-002 (sub-node low + canopy healthy) | Medium — WB might contradict "hold" advice | `D14-FU-002 SUPPRESSES D03-WB-001` (early-warning rule wins for holding action) |

**Standard firing gate (prepended to every WB rule except WB-006):**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
```

This gate keeps WB rules dormant until:
1. Hardware flow-telemetry field lands in sub-node MQTT + readings ingestion
2. Farmer geometry + sensor position captured (raises confidence above 0.60)

WB-006 (sensor-gap alert) is exempt from confidence gate — it's a hardware-health rule.

---

## 1. D03-WB-001 — Moderate deficit → recommend irrigation

**Purpose:** Standard irrigation trigger based on quantitative water accounting.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND stage_water_deficit_L_per_plant > stage_water_target_L_per_plant × 0.25
AND days_since_last_irrigation >= 2
AND vwc_status != 'saturated'                    -- D03-MN-002 override
```

**Action:**
```
emit irrigation_recommendation:
    dose_L_per_plot = variety_stage_per_event_target × plot_plants_estimated
    duration_min = dose_L_per_plot ÷ (avg_pipe_flow_L_per_min × total_drip_pipes_in_plot)
    urgency = 'normal'
    template = 'irrigation_normal' (Marathi Template 1)
    contributing_signals = ['water_budget', 'vwc_probe' IF vwc_status == 'low']
```

**Severity:** YELLOW (normal)

**Basis:** L3 (VNMKV OFT variety-stage water demand) + FAO-56 methodology (water balance ETc − effective rain − irrigation)

**Kannad note:** Western Scarcity zone default 2-day gap is tighter than typical 4-5 days elsewhere; matches observed Kannad ETc during G2-G4.

**Marathi advisory:** Template 1 (सामान्य सिंचन शिफारस) — if VWC also low → Template 2 (दोन्ही signals सहमत)

**Precedence relations:**
- `D03-MN-002 SUPPRESSES D03-WB-001` (saturation veto)
- `D03-WB-001 BUNDLES D03-MN-004` (both fire on stress → one farmer message; contributing_signals lists both)
- `D14-FU-002 SUPPRESSES D03-WB-001` (early-warning "hold" wins)

**Tests (5 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | deficit=30%, gap=3d, vwc=low → BUNDLES with D03-MN-004; one message | Fires; template 2 |
| T2 | deficit=30%, gap=3d, vwc=saturated | SUPPRESSED by D03-MN-002; no message |
| T3 | deficit=20%, gap=3d, vwc=low | Does not fire (deficit < 25%); D03-MN-004 fires alone |
| T4 | deficit=30%, gap=1d, vwc=ok | Does not fire (gap < 2d) |
| T5 | confidence=0.55 | Dormant (below gate) |

**Confidence:** Inherits `water_budget_confidence`; if VWC also contributes, use max(vwc.confidence, wb.confidence × 0.90).

---

## 2. D03-WB-002 — Severe deficit → RED urgency

**Purpose:** Critical irrigation trigger for G3 rhizome-fill window.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND (
    (stage == 'G3' AND stage_water_deficit_L_per_plant > stage_water_target_L_per_plant × 0.40)
    OR (stage IN ('G2', 'G4') AND stage_water_deficit_L_per_plant > stage_water_target_L_per_plant × 0.50)
)
AND vwc_status != 'saturated'
```

**Action:**
```
emit irrigation_recommendation:
    dose_L_per_plot = variety_stage_per_event_target × plot_plants_estimated × 1.10  -- catch-up dose
    duration_min = dose_L_per_plot ÷ (avg_pipe_flow_L_per_min × total_drip_pipes_in_plot)
    urgency = 'red'
    template = 'irrigation_red' (Marathi Template 3)
    push_notification = TRUE                     -- immediate WhatsApp push
    contributing_signals = ['water_budget', 'stage_context', 'vwc_probe' IF vwc_status == 'low']
```

**Severity:** RED (critical)

**Basis:** L3 (VNMKV OFT — G3 water sensitivity documented at 15-25% yield loss on ≥40% deficit); L2 (Sivakumar & Shanthi 2019, "Water stress effects on Zingiber officinale yield components")

**Kannad note:** G3 window in Kannad = mid-September to mid-November. Peak rhizome-fill overlaps late monsoon withdrawal — pond water reserve critical.

**Marathi advisory:** Template 3 (लाल इशारा)

**Precedence relations:**
- `D03-MN-002 SUPPRESSES D03-WB-002` (saturation veto — probe still wins even on red)
- `D03-WB-002 BUNDLES D03-MN-004` (single red-urgency message)
- `D03-WB-002 ESCALATES D03-WB-001` (severe overrides moderate — do not fire both)

**Tests (5 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | G3, deficit=45%, vwc=low | Red fires; template 3; push_notification=TRUE |
| T2 | G3, deficit=45%, vwc=saturated | Suppressed |
| T3 | G3, deficit=35% | WB-001 fires (moderate), not WB-002 |
| T4 | G2, deficit=45% | Does not fire (G2 threshold is 50%) |
| T5 | G4, deficit=55%, vwc=ok | Fires with red |

**Confidence:** Same as WB-001.

---

## 3. D03-WB-003 — Over-irrigation warning

**Purpose:** Detects excess irrigation per event; recommends reduction to prevent rhizome rot.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND per_plant_dose_L_last_event > variety_max_per_event_L
AND stage != 'G5'                                -- G5 gets its own stop rule (WB-008)
```

**Action:**
```
emit irrigation_recommendation:
    message = "over_irrigation_warning"
    reduce_next_dose_by_pct = 30
    urgency = 'normal'
    template = 'over_irrigation' (see Marathi note below)
    contributing_signals = ['water_budget']
```

**Severity:** YELLOW

**Basis:** L3 (VNMKV OFT — over-irrigation on vertisol increases bacterial wilt R. solanacearum and Pythium myriotylum incidence — ~10-15% yield loss risk documented at Parbhani trials); L1 (Insecticides Act contexts on drainage stress)

**Kannad note:** Vertisol drainage is slow (0.5-2 cm/hr); over-irrigation stays in root zone longer than in sandy/loam soils. Kannad-specific caution.

**Marathi advisory (inline — add to Template repository as Template 11):**
```
⚠️ जास्त पाणी — पुढच्या वेळी कमी करा

आजच्या event ला: {per_plant_dose_L_last_event} लिटर/रोप दिले
शिफारस: {variety_max_per_event_L} लिटर/रोप पेक्षा जास्त नको

पुढच्या सिंचनाला ~30% कमी दोस्ती द्या.
जास्त पाणी → गड्डा-कूज आणि जिवाणू-मर धोका (काळ्या मातीत विशेषतः).
```

**Precedence relations:**
- No SUPPRESSES needed — this is a post-event warning, not an irrigation trigger
- Does not conflict with WB-001/WB-002 (fires after event, not before)
- `D03-WB-003 INFORMS D03-WB-007` (feeds cumulative over-irrigation aggregate)

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | Last event = 5.0 L/plant, max = 4.0 L/plant | Fires |
| T2 | Last event = 3.5 L/plant, max = 4.0 L/plant | Does not fire |
| T3 | Last event = 5.0 L/plant, stage = G5 | Does not fire (WB-008 handles G5) |

**Confidence:** Inherits `water_budget_confidence`.

---

## 4. D03-WB-004 — Under-irrigation event correction

**Purpose:** Detects insufficient dose in a just-completed event; recommends supplementary.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND per_plant_dose_L_last_event < variety_min_per_event_L
AND days_since_last_irrigation <= 1              -- event was today or yesterday
AND stage IN ('G2', 'G3', 'G4')                  -- only in active-demand stages
AND vwc_status != 'saturated'
```

**Action:**
```
emit irrigation_recommendation:
    supplementary_dose_L = (variety_min_per_event_L - per_plant_dose_L_last_event) × plot_plants_estimated
    duration_min_supplementary = supplementary_dose_L ÷ (avg_pipe_flow_L_per_min × total_drip_pipes_in_plot)
    urgency = 'normal'
    template = 'supplementary_irrigation' (inline below)
    contributing_signals = ['water_budget']
```

**Severity:** YELLOW

**Basis:** L3 (VNMKV OFT — dose insufficiency in active stages carries forward as cumulative deficit); FAO-56 water balance methodology.

**Kannad note:** Common cause of under-dose in Kannad = pond running low + farmer rationing; system flags it so farmer can plan supplemental source.

**Marathi advisory (Template 12):**
```
💧 सिंचन कमी झाले — पुरवणी द्या

आजच्या event ला: {per_plant_dose_L_last_event} लिटर/रोप मिळाले
आवश्यक होते: किमान {variety_min_per_event_L} लिटर/रोप

पुरवणी सिंचन आजच द्या:
💧 पाणी: {supplementary_dose_L} लिटर
⏱️ वेळ: {duration_min_supplementary} मिनिटे

पाणी कमी असल्यास पंप-दाब किंवा drippers तपासा.
```

**Precedence relations:**
- `D03-MN-002 SUPPRESSES D03-WB-004` (saturation veto)
- `D03-WB-004 SEQUENCES D03-WB-001` (post-event correction runs before next-day deficit check)

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | Last event=0.5 L/plant, min=1.5 L/plant, G3, gap=1d | Fires |
| T2 | Last event=2.0 L/plant, min=1.5 L/plant | Does not fire |
| T3 | Last event=0.5 L/plant, G1 | Does not fire (only G2-G4) |

**Confidence:** Inherits.

---

## 5. D03-WB-005 — Daily silent guard (D11 feeder — cumulative demand tracking)

**Purpose:** Silent daily aggregation — no farmer message. Tracks `avg_daily_water_L_per_plant` vs variety demand curve; feeds D11 yield model.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND cron_daily_run = TRUE                        -- fires once per day at 05:00 IST
```

**Action:**
```
emit d11_input:
    avg_daily_water_L_per_plant = plot_total_flow_L_cumulative ÷ plot_plants_estimated ÷ dap
    variety_daily_demand_curve_L = lookup(variety, stage, dap)
    daily_deficit_ratio = 1 - min(1, avg_daily_water_L_per_plant / variety_daily_demand_curve_L)
    log to farm_brain.d11_daily_water_log
```

**Severity:** INFO (silent — no farmer message)

**Basis:** L3 (VNMKV OFT + FAO-56); serves D11 yield model factor-7 supplement (D03-ST-001 is the primary factor-7 rule).

**Kannad note:** Season 1 baseline data collection — this rule's daily log becomes calibration input for Season 2 U-value refinement.

**Marathi advisory:** None (silent).

**Precedence relations:**
- `D03-WB-005 FEEDS D11-YM-*` (data emit only, not decision)
- `D03-WB-005 COMPLEMENTS D03-ST-001` (WB-005 = daily cumulative; ST-001 = stage-band deficit)
- No conflict with any advisory rule (silent)

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | cumulative=150 L, plants=25000, DAP=100 | daily_avg=0.06 L/plant/day; deficit_ratio computed |
| T2 | Confidence=0.55 | Does not fire |
| T3 | Multiple runs same day | Fires once (cron-guarded) |

**Confidence:** Inherits; deficit_ratio emitted with confidence tag.

---

## 6. D03-WB-006 — Flow sensor gap alert (exempt from confidence gate)

**Purpose:** Hardware-health alert. Fires when water-flow sensor stops reporting.

**Trigger:**
```
days_since_last_flow_reading > 3
AND flow_telemetry_field_exists = TRUE           -- was working, now silent
```

**Note:** No `water_budget_confidence` gate — this rule IS the confidence-gap alert.

**Action:**
```
emit hardware_alert:
    message = 'sensor_gap'
    urgency = 'red'
    template = 'sensor_gap' (Marathi Template 7)
    contributing_signals = ['hardware_health']
    suspend_wb_dose_recommendations = TRUE       -- quantitative dose paused until sensor recovers
    keep_vwc_based_d03_rules_active = TRUE       -- VWC-based advisory continues
```

**Severity:** RED

**Basis:** Operational — VIRAAI Agro-Guardian AI custom operational rule.

**Kannad note:** Kannad plots in Western Scarcity zone; battery drain more common in high-heat months (April-May). Ensure spare batteries stocked.

**Marathi advisory:** Template 7 (Sensor गप्प आहे)

**Precedence relations:**
- `D03-WB-006 SUSPENDS D03-WB-001, D03-WB-002, D03-WB-003, D03-WB-004, D03-WB-005, D03-WB-007` (all WB rules requiring flow data pause)
- `D03-WB-006 DOES NOT SUSPEND D03-MN-*, D03-DS-*` (VWC-based rules continue firing per §5.5 graceful degradation)
- `D03-WB-006 BUNDLES D14-FU-001` (satellite fallback also triggers on sensor gap → single unified message)

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | Last reading 4 days ago | Fires |
| T2 | Last reading 2 days ago | Does not fire |
| T3 | flow_telemetry_field_exists=FALSE (never installed) | Does not fire (this rule is for regression, not absence) |

**Confidence:** N/A (hardware alert).

---

## 7. D03-WB-007 — Season-long over-irrigation flag

**Purpose:** Detects cumulative over-irrigation across the season; investigates drainage or drip issues.

**Trigger:**
```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.60
AND cumulative_lifecycle_water_L / plot_plants_estimated > variety_lifecycle_target_high × 1.20
AND dap >= 100                                   -- meaningful only after G3 starts
```

**Action:**
```
emit advisory:
    message = 'season_over_irrigation_investigate'
    urgency = 'important'
    template = 'season_over_irrigation' (inline below)
    reduce_remaining_stage_doses_by_pct = 20
    escalate_to_agronomist_scout = TRUE
    contributing_signals = ['water_budget', 'stage_context']
```

**Severity:** YELLOW → IMPORTANT

**Basis:** L3 (VNMKV OFT — Mahima lifecycle high-end 250 L/plant; +20% buffer = 300 L/plant threshold); L2 (Kandiannan et al 2011 on ginger water-stress-tolerance limits).

**Kannad note:** Vertisol drainage-slow — cumulative over-irrigation on Kannad plots correlates with increased Ralstonia solanacearum incidence.

**Marathi advisory (Template 13):**
```
⚠️ हंगामभर जास्त पाणी दिले जात आहे — तपासणी करा

आतापर्यंत रोपाला मिळालेले पाणी: {per_plant_cumulative_water_L} लिटर
Variety-चा target (उच्च मर्यादा): {variety_lifecycle_target_high} लिटर
जास्त: 20% पेक्षा जास्त

का तपासा:
- निचरा नीट होत आहे का (काळ्या मातीत slow असतो)
- Drippers कुठे leak आहेत का
- Duration शिफारसीपेक्षा जास्त चालवत आहात का

पुढील शिफारसी 20% कमी दोस्तीने येतील. 
Agronomist ला call करा — शेतफेरी करून drainage तपासू.
```

**Precedence relations:**
- `D03-WB-007 DOES NOT SUPPRESS other WB rules` (informational escalation, not veto)
- `D03-WB-007 SEQUENCES D03-WB-001, D03-WB-002` (season-total check runs after daily deficit computed)

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | Mahima, cumulative=310 L/plant, DAP=180 | Fires (310 > 250×1.2=300) |
| T2 | Mahima, cumulative=280 L/plant, DAP=180 | Does not fire |
| T3 | Mahima, cumulative=310 L/plant, DAP=80 | Does not fire (DAP < 100) |

**Confidence:** Inherits.

---

## 8. D03-WB-008 — Pre-planting geometry gate

**Purpose:** Blocks Season 1 pilot activation for a plot until planting geometry is captured.

**Trigger:**
```
dap < 0                                          -- pre-planting phase
AND planting_geometry_incomplete = TRUE          -- at least one geometry field NULL
```

**Note:** No `flow_telemetry_present` gate — this rule fires at plot setup, before hardware is expected to be reading.

**Action:**
```
emit blocking_prompt:
    message = 'geometry_incomplete_prompt'
    urgency = 'blocking'                         -- plot cannot activate for pilot
    template = 'geometry_prompt' (inline below)
    farmer_app_screen = 'planting_geometry_completion'
    contributing_signals = ['setup_gate']
```

**Severity:** BLOCKING

**Basis:** Operational — VIRAAI Agro-Guardian AI custom operational rule (data-capture gate).

**Kannad note:** Kannad pilot Season 1 requires complete geometry for D11 yield model validation.

**Marathi advisory (Template 14):**
```
📝 शेताची माहिती पूर्ण करा

आपले शेत सिस्टीम मध्ये register करण्यासाठी काही माहिती अजून बाकी आहे:
{IF planting_method IS NULL} - लागवडीची पद्धत {ENDIF}
{IF bed_center_spacing_cm IS NULL} - बेडमधील अंतर {ENDIF}
{IF plant_spacing_within_row_cm IS NULL} - रोपांमधील अंतर {ENDIF}
{IF total_drip_pipes_in_plot IS NULL} - Drip नळ्यांची संख्या {ENDIF}
{IF sensor_pipe_position IS NULL} - Sensor कुठे लावला {ENDIF}

अद्रकीची लागवड झाल्यावर सिंचन शिफारसी सुरू होण्यासाठी 
ही सर्व माहिती app मध्ये भरा.

App उघडा → "शेत setup पूर्ण करा" वर tap करा.
```

**Precedence relations:**
- `D03-WB-008 BLOCKS all D03-WB-* activation for this plot` (until geometry complete)
- Does not affect other plots or other rule domains

**Tests (3 goldens):**
| # | Setup | Expected |
|:-:|---|---|
| T1 | DAP=-5, planting_method=NULL | Fires; blocking |
| T2 | DAP=-5, all geometry filled | Does not fire |
| T3 | DAP=15 (post-planting), geometry NULL | Does not fire (WB-008 is pre-planting only; a different rule handles this case) |

**Confidence:** N/A (setup gate).

---

## Summary — collision matrix

| WB rule | Suppressed by | Bundles with | Sequences with | Escalates | Feeds |
|---|---|---|---|---|---|
| WB-001 | D03-MN-002, D14-FU-002 | D03-MN-004 | — | — | — |
| WB-002 | D03-MN-002 | D03-MN-004 | — | WB-001 | — |
| WB-003 | — | — | — | — | WB-007 |
| WB-004 | D03-MN-002 | — | WB-001 | — | — |
| WB-005 | — | — | — | — | D11-YM-*, D03-ST-001 |
| WB-006 | — | D14-FU-001 | — | — | (suspends WB-001..005, 007) |
| WB-007 | — | — | WB-001, WB-002 | — | — |
| WB-008 | — | — | — | — | (blocks WB-*, plot-level) |

**Total precedence relations added: 12 (all traceable to existing rule IDs; no orphan references).**

---

## Backend implementation ask

- Add 8 rules to `Domain3_Rules_Ginger.json` under `_rules[]`
- Add 12 precedence relations to `_precedence[]`
- Add 4 new Marathi templates (11-14) to advisory template repository
- Wire D03-WB-006 to hardware-health monitor (sensor last-reading tracker)
- Wire D03-WB-005 to D11 factor-7 daily consumer cron
- Wire D03-WB-008 to farmer app setup flow gate

**Estimated backend integration effort: 3-4 days** (rule declarations + precedence wiring + Marathi templates + 32 golden tests).

---

*End of D03-WB Water Budget Rules v1.0*
