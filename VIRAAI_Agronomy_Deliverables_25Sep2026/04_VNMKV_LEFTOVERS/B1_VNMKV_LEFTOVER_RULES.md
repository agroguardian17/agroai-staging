# B1 VNMKV Leftover Rules — 3 rule bodies

**Purpose:** Author full KB anatomy for the three B1 items backend flagged as pending: D06-BW-001 (bacterial wilt rotation), D01-PW-001 (planting-window), and B1.6 basal ZnSO₄. All three carry VNMKV Parbhani sign-off from the VNMKV compliance certificate (24 Sep 2026).

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Ref:** Backend agronomy-inputs request §4; Master Action List Track B1.3/B1.4/B1.6; VNMKV Compliance Certificate v1.0

---

# Rule 1 (B1.3) — D06-BW-001 · Bacterial wilt rotation gate

## Identification
- **Rule ID:** `D06-BW-001` (existing rule — update body per VNMKV §4)
- **Rule name:** bacterial_wilt_rotation_history_gate
- **Domain:** D06 Diseases
- **Category:** BW (Bacterial Wilt — Ralstonia solanacearum)
- **Rule type:** BLOCKING_GATE (pre-planting blocker)
- **Compliance tag:** COMPLIANT (VNMKV certificate §4 confirms 5-year rotation minimum)
- **Change from prior version:** trigger threshold changed from `years_since_last_wilt < 3` to `years_since_last_wilt < 5` per VNMKV certificate

## New field required
- **Field name:** `years_since_last_wilt`
- **Type:** `integer` (nullable — NULL means no known wilt history OR farmer hasn't confirmed)
- **Range:** 0 to 25 (values beyond 25 collapsed to 25 = "long-cleared")
- **Capture source:** Farmer scouting form at plot setup — question: *"या शेतात कधी बॅक्टेरियल-मर (कंद कूज) आला होता का? असल्यास किती वर्षांपूर्वी?"*
- **Follow-up capture:** Neighbour-plot inquiry — if farmer says "I don't know" but neighbour plots have wilt history, add note to `wilt_neighbour_history_flag`

## Trigger (v1.1 corrected — NULL bypass loophole closed)
```
crop = 'ginger'
AND (
    -- Case A: known recent wilt → block at pre-planting
    (plot_status = 'pre_planting' AND years_since_last_wilt IS NOT NULL AND years_since_last_wilt < 5)
    OR
    -- Case B: history unknown at pre-planting → soft prompt only
    (plot_status = 'pre_planting' AND years_since_last_wilt IS NULL)
    OR
    -- Case C (v1.1 NEW): plot transitioning to 'planted' while history STILL unknown → HARD BLOCK
    -- Farmer cannot skip the prompt to bypass the quarantine protocol
    (plot_status_transition = 'pre_planting → planted' AND years_since_last_wilt IS NULL)
)
```

**v1.1 fix — NULL bypass closed:** v1.0 allowed farmers to ignore the soft prompt (Case B) and proceed to planting without ever answering the question. Case C now blocks the plot-status transition itself until the field is answered — either as a number ≥ 5 (green pass) or with agronomist_override (in which case the block clears with legal_flag = 'wilt_history_bypassed_by_agronomist').

## Action (v1.1 updated with Case C block)
```
# Case A: known recent wilt at pre-planting
IF years_since_last_wilt IS NOT NULL AND years_since_last_wilt < 5 AND plot_status = 'pre_planting':
    emit blocking_advisory:
        message = 'wilt_rotation_insufficient_block'
        template = D06_BW_TEMPLATE_1_BLOCK
        severity = 'red'
        farmer_override_permitted = TRUE     -- with explicit agronomist consult
        contributing_signals = ['plot_wilt_history']
        require_agronomist_consult = TRUE

# Case B: history unknown at pre-planting — soft prompt
IF years_since_last_wilt IS NULL AND plot_status = 'pre_planting':
    emit soft_prompt:
        message = 'wilt_history_prompt'
        template = D06_BW_TEMPLATE_2_PROMPT
        severity = 'yellow'
        prompt_screen_id = 'wilt_history_capture'

# Case C (v1.1 NEW): history STILL unknown when farmer attempts to record planting
IF years_since_last_wilt IS NULL AND plot_status_transition = 'pre_planting → planted':
    emit blocking_transition:
        message = 'wilt_history_capture_mandatory_before_planting'
        template = D06_BW_TEMPLATE_3_MANDATORY_CAPTURE
        severity = 'red'
        block_state_transition = TRUE                  -- plot_status cannot advance to 'planted'
        farmer_override_permitted = TRUE               -- but requires explicit agronomist signoff
        agronomist_override_legal_flag = 'wilt_history_bypassed_by_agronomist'
```

## Delivery class
- `ONCE_UNTIL_RESOLVED` — resolution condition = `years_since_last_wilt >= 5 OR agronomist_override_signed = TRUE`

## Precedence relations
- `D06-BW-001 SUPPRESSES D01-PW-001` (bacterial-wilt gate is pre-planting; planting-window rule doesn't need to fire if plot is already blocked from planting)
- `D06-BW-001 BUNDLES D04-NS-003` (if plot has recent wilt + late-N excess history, message notes compounding risk in agronomist consult)
- No conflict with other D06 rules (rot vs wilt are separate categories)

## Severity map
| years_since_last_wilt | Severity | Override |
|---|:---:|:---:|
| 0-2 | RED | Requires agronomist consult; strongly discourage |
| 3-4 | RED | Requires agronomist consult; may permit with strict prophylactic protocol |
| 5+ | GREEN | Permit; no action |
| NULL | YELLOW | Soft prompt to capture data |

## Kannad note
Kannad Western Scarcity zone: Ralstonia solanacearum persists in vertisol for 5-7 years in India documented literature; VNMKV Parbhani OFT confirms 5-year rotation as minimum for Marathwada clay soils. Neighbour-plot wilt history matters — same aquifer + shared drainage = shared inoculum risk.

## Marathi advisory templates

**D06_BW_TEMPLATE_1_BLOCK (RED — recent wilt history):**
```
🛑 या शेतात नुकतीच जिवाणू-मर आली होती — यंदा अद्रक लावू नका

आपल्या माहितीप्रमाणे: शेतात {years_since_last_wilt} वर्षांपूर्वी जिवाणू-मर (bacterial wilt / कंद कूज) होती.

VNMKV Parbhani शिफारस: किमान 5 वर्षे fallow किंवा non-solanaceous पीक-पाळी.

कारण:
- Ralstonia solanacearum जिवाणू मातीत 5-7 वर्षे टिकतो
- यंदा अद्रक लावले तर पीक-हानी 40-60% पर्यंत जाऊ शकते
- शेजारच्या शेतांना पण प्रादुर्भाव पसरू शकतो

पर्याय:
✅ यंदा जोवारी / बाजरी / मका सारखी पीक-पाळी करा
✅ Fallow ठेवा (हिरवळीचे खत — डायंचा, सन-हेंप — मातीचे आरोग्य सुधारते)
✅ 5 वर्षांनंतर अद्रक परत लावता येईल

Agronomist ला call करा — विशिष्ट प्लॉटसाठी strategy साठी.
```

**D06_BW_TEMPLATE_2_PROMPT (YELLOW — history unknown):**
```
📋 एक महत्त्वाची माहिती हवी आहे

आपल्या शेताविषयी: **या शेतात कधी अद्रकीला जिवाणू-मर (bacterial wilt / कंद कूज) आली होती का?**

का विचारतोय:
- जिवाणू-मर आलेल्या शेतात परत लगेच अद्रक लावले तर मोठी हानी होते
- मातीत हा जिवाणू 5-7 वर्षे टिकतो
- VNMKV Parbhani शिफारस: किमान 5 वर्षे थांबावे

तुमचे उत्तर:
[ ] कधी आली नाही
[ ] आली होती — किती वर्षांपूर्वी? _____ वर्ष
[ ] माहीत नाही — शेजाऱ्यांकडे विचारून सांगेन
```

**D06_BW_TEMPLATE_3_MANDATORY_CAPTURE (v1.1 — RED, Case C block on planting transition):**
```
🛑 लागवडीची नोंद पूर्ण होऊ शकत नाही — एक उत्तर बाकी आहे

आपण लागवडीची नोंद करत आहात, पण एका प्रश्नाचे उत्तर देणे बाकी आहे:

**या शेतात मागील 5 वर्षांत जिवाणू-मर (bacterial wilt / कंद कूज) आली होती का?**

हा प्रश्न आपण आधी skip केला होता. लागवडीची नोंद पूर्ण करण्याआधी हे उत्तर आवश्यक आहे —
कारण नुकत्याच wilt-आलेल्या शेतात अद्रक लागवड म्हणजे 40-60% पीक-हानीचा गंभीर धोका.

तुमचे उत्तर:
[ ] कधी आली नाही → लागवडीची नोंद पुढे जाईल
[ ] 5 वर्षांहून जास्त पूर्वी आली होती → लागवडीची नोंद पुढे जाईल
[ ] मागील 5 वर्षांत आली होती → लागवड न करण्याची शिफारस + agronomist consult
[ ] अजूनही माहीत नाही → agronomist ला call करा; त्यांच्या signoff-नंतरच पुढे जाता येईल
```

## Tests (5 goldens)

| # | Setup | Expected |
|:-:|---|---|
| T1 | years_since_last_wilt = 2, plot_status = 'pre_planting' | RED block; template 1; agronomist_consult required |
| T2 | years_since_last_wilt = 5, plot_status = 'pre_planting' | Passes (no block) |
| T3 | years_since_last_wilt = 4, plot_status = 'pre_planting' | RED block; template 1 |
| T4 | years_since_last_wilt = NULL, plot_status = 'pre_planting' | YELLOW prompt; template 2 |
| T5 | years_since_last_wilt = 2, plot_status = 'growing' | Rule does not fire (not pre-planting; too late to block) |
| T6 (v1.1) | years_since_last_wilt = NULL, plot_status_transition = 'pre_planting → planted' | Case C fires: BLOCK state transition; template 3; agronomist signoff required |
| T7 (v1.1) | years_since_last_wilt = NULL, agronomist_override_signed = TRUE, transition attempted | Transition permitted; legal_flag = 'wilt_history_bypassed_by_agronomist' logged |

---

# Rule 2 (B1.4) — D01-PW-001 · Late planting window warning

## Identification
- **Rule ID:** `D01-PW-001` (existing rule — update trigger per VNMKV §4)
- **Rule name:** planting_window_late_warning
- **Domain:** D01 Lifecycle
- **Category:** PW (Planting Window)
- **Rule type:** ADVISORY (soft warning; not blocking)
- **Compliance tag:** COMPLIANT
- **Change from prior version:** trigger changed from `MONTH IN [JUN, JUL] AND plot_status = 'unplanted'` to `planting_date > DATE '2026-06-07'` — direct date comparison

## Backend dependency — DSL date-literal support
Backend must add DSL support for date literals:
- Syntax proposal: `DATE 'YYYY-MM-DD'` (SQL-style) OR `d'YYYY-MM-DD'` (short form)
- Operators: `>`, `<`, `>=`, `<=`, `=`, `BETWEEN d'YYYY-MM-DD' AND d'YYYY-MM-DD'`
- Existing `MONTH IN [JUN, JUL]` idiom retained for other rules that use it
- Season-year variable: `season_start_year` (from a config file — e.g., 2026 for Season 1) so rules can compute `DATE (season_start_year || '-06-07')` if backend prefers dynamic

**Backend Q for agronomy:** Do you (Kuldip) want the date hard-coded per season (`d'2026-06-07'`), OR derived dynamically from `season_start_year` config?

**Kuldip's answer:** Use **dynamic** — `DATE(season_start_year || '-06-07')` — so the rule survives Season 2 without KB edit. Backend maintains `season_start_year` in config.

## Trigger
```
crop = 'ginger'
AND planting_date IS NOT NULL
AND planting_date > DATE(season_start_year || '-06-07')
```

Interpretation for Season 1 (2026):
```
planting_date > DATE '2026-06-07'
```

## Action
```
emit advisory:
    message = 'late_planting_window_warning'
    template = D01_PW_TEMPLATE_1_LATE
    severity = 'yellow'
    contributing_signals = ['planting_date']
    action_hints = ['variety_selection_favours_short_duration',
                    'irrigation_readiness_check',
                    'harvest_may_slip_to_march_2027']
```

## Delivery class
- `EVENT` — fires once at planting-date recording (not repeated daily)

## Precedence relations (v1.1 clarified)
- `D06-BW-001 SUPPRESSES D01-PW-001` **only when D06-BW-001 emits a BLOCKING action** (Case A red block or Case C mandatory-capture block). A D06-BW-001 soft prompt (Case B, yellow) does NOT suppress D01-PW-001 — both can co-fire (unknown wilt history + late planting = farmer sees both prompts). Backend precedence engine checks emitted severity, not just rule-fired status.
- No conflict with other D01 rules (stage-progression is separate from planting-date warning)

## Severity map
| planting_date lag | Severity |
|---|:---:|
| ≤ 7 June (inclusive; on-window) | Silent (no fire — trigger uses `>`, not `>=`, so June 7 exact silently passes) |
| 8-15 June | YELLOW — mild caution |
| 16-30 June | YELLOW — stronger caution + variety recommendation |
| July onwards | RED — significant window loss; recommend defer to next season |

*(Backend implements as one rule with severity tiers based on days-late. v1.1 clarification: silent pass for June 7 IS intended behavior — no on-window log emitted from this rule. If backend wants an "on-window" positive log for audit, add it as a separate silent-guard rule D01-PW-002; not needed for Season 1.)*

## Kannad note
Kannad Western Scarcity zone: monsoon-window planting best captured pre-rain (first week June); post-monsoon-onset planting causes root-anchoring issues due to saturated vertisol. VNMKV Parbhani OFT: on-window plots yield 15-25% higher than 2-week-late plots.

## Marathi advisory template

**D01_PW_TEMPLATE_1_LATE (YELLOW):**
```
⚠️ लागवडीला उशीर झाला आहे

आपली लागवड तारीख: {planting_date_mr}
शिफारस केलेली अंतिम तारीख: {season_start_year}-06-07

काय होऊ शकते:
- गड्डा-निर्मिती (G3) ऑक्टोबरच्या शेवटी येईल — तापमान कमी होते तेव्हा वाढ मंदावते
- काढणी मार्च 2027 पर्यंत पुढे जाऊ शकते (सामान्य फेब्रुवारी)
- उत्पादन 15-25% कमी होण्याचा धोका (VNMKV OFT observations)

आत्ता करा:
✅ Short-duration variety प्राधान्य — Varada (215 दिवस) किंवा Nadia (200-210 दिवस); Mahima (240 दिवस) टाळा जर शक्य असेल
✅ सिंचनाची तयारी पक्की करा — पावसाच्या शेवटी irrigation दुहेरी महत्त्वाचे
✅ Basal खतं आत्ताच द्या — विलंबाची भरपाई फार होणार नाही
✅ Agronomist ला call करा — तुमच्या शेतासाठी संकुचित strategy साठी
```

## Tests (5 goldens)

| # | Setup | Expected |
|:-:|---|---|
| T1 | planting_date = 2026-05-30 | Does not fire (on-window) |
| T2 | planting_date = 2026-06-07 | Does not fire (exactly on cutoff — cutoff is exclusive) |
| T3 | planting_date = 2026-06-10 | Fires YELLOW; template 1 |
| T4 | planting_date = 2026-07-15 | Fires RED (July onwards tier) |
| T5 | planting_date = NULL | Does not fire (no data) |

---

# Rule 3 (B1.6) — D04-MC-004 · Basal ZnSO₄ recommendation for Kannad plots

## Identification
- **Rule ID:** `D04-MC-004` (new rule — MC = Micronutrient category, next in sequence after existing D04-MC-003)
- **Rule name:** basal_znso4_kannad_default
- **Domain:** **D04 Nutrients** (chosen over D02 because Zn is a micronutrient fertilizer, not a soil amendment; aligns with existing D04-MC-003)
- **Category:** MC (Micronutrient)
- **Rule type:** RECOMMENDATION (default advisory at plot setup)
- **Compliance tag:** COMPLIANT (VNMKV soil-test findings for Kannad zone Zn-deficiency)

## New field required
- **Field name:** `agro_climatic_zone`
- **Type:** `enum` — values: `western_scarcity` / `central_maharashtra` / `assured_rainfall` / `moderate_high_rainfall` / `high_rainfall` / `sub_montane`
- **Capture source:** Auto-derived by backend from plot polygon centroid + Maharashtra agro-climatic zones GIS layer; farmer-readable label shown in app
- **Kannad classification:** `western_scarcity` (per VNMKV certificate §4 zone mapping)

## Trigger
```
crop = 'ginger'
AND plot_status = 'pre_planting'
AND agro_climatic_zone = 'western_scarcity'
AND basal_znso4_applied_kg_acre IS NULL   -- not yet recorded
```

## Action
```
emit recommendation:
    message = 'basal_znso4_kannad_default'
    template = D04_MC_TEMPLATE_1_ZNSO4
    severity = 'green'                       -- recommendation, not warning
    dose_kg_per_acre = 10                    -- 25 kg/ha × 0.40469 ≈ 10.1, rounded to 10
    timing = 'basal_at_planting_dap_0'
    contributing_signals = ['agro_climatic_zone', 'soil_zn_default_deficiency']
```

## Delivery class + resolution tiers (v1.1 corrected — partial-dose warning tier added)
- Base class: `ONCE_UNTIL_RESOLVED`
- **Three-tier resolution logic:**
  - `basal_znso4_applied_kg_acre >= 9` → **FULLY RESOLVED** (within ±10% of 10 kg/acre recommendation); rule silent
  - `basal_znso4_applied_kg_acre 5-8` → **PARTIAL RESOLUTION**: rule escalates to WARNING severity, new message emitted advising supplementary dose to reach 10 kg/acre total
  - `basal_znso4_applied_kg_acre < 5` OR `NULL` → **UNRESOLVED**: original recommendation stays active; re-fires weekly until DAP 0 (planting window closes)
  - **After DAP 0 (basal window missed):** rule pauses; supplementary Zn foliar spray recommendation emitted from a separate D04-MC-005 rule (Season 2 authoring)

**v1.1 fix:** v1.0 treated 5-8 kg as "unresolved" silently, so a farmer applying half-dose received no feedback about the underdose. Now WARNING tier explicitly nudges to top up.

## Precedence relations (v1.1 corrected — separate BUNDLES vs SUPPRESSES)

Three distinct interaction cases with D04-MC-003 (existing conditional Zn rule), each with its own precedence relation:

| Situation | Precedence relation | Behavior |
|---|---|---|
| **Soil test done, Zn ADEQUATE (≥ 0.6 ppm DTPA)** | `D04-MC-003 SUPPRESSES D04-MC-004` | D04-MC-004 does not fire — soil evidence proves default zone assumption wrong for this specific plot |
| **Soil test done, Zn DEFICIENT (< 0.6 ppm)** | `D04-MC-003 BUNDLES D04-MC-004` | Both would fire; produce ONE farmer message combining conditional evidence + zone default; higher confidence |
| **No soil test done, Kannad zone** | (D04-MC-003 does not fire; D04-MC-004 fires alone) | Zone-based default recommendation delivered |

- `D04-MC-004 SEQUENCES D04-NS-003` — Zn application is basal (DAP 0), so it doesn't touch N-cutoff-at-DAP-150 rule
- No conflict with D02 (soil amendment) rules — Zn is a nutrient application, not amendment

**v1.1 fix:** v1.0 used "COMPLEMENTS" (an informal descriptor, not a formal precedence type) alongside BUNDLES — these are not the same thing. Backend precedence engines recognize SUPPRESSES / BUNDLES / SEQUENCES / ESCALATES as formal types. "COMPLEMENTS" removed; behavior split into SUPPRESSES (adequate) vs BUNDLES (deficient) based on soil-test evidence.

## Kannad note
Kannad Western Scarcity zone (TMI < 40%): vertisol soils are commonly Zn-deficient due to (a) high pH (7.5-8.5) fixing Zn in unavailable form, (b) low organic matter reducing chelation, (c) intensive cropping depleting available Zn. VNMKV Parbhani soil surveys 2019-2023: 68% of tested plots in Kannad taluka showed Zn below critical threshold (0.6 ppm DTPA-extractable). Basal ZnSO₄ 10 kg/acre = ~2.3 kg Zn/acre, sufficient for one-season correction.

## Marathi advisory template

**D04_MC_TEMPLATE_1_ZNSO4 (GREEN — recommendation at plot setup):**
```
✅ मूलभूत खत शिफारस — Zinc Sulphate (ZnSO₄)

लागवडीच्या वेळी basal म्हणून द्या:
💊 **ZnSO₄ 10 किलो प्रति एकर** (जमिनीत मिसळून, लागवडीपूर्वी)

का:
- Kannad भागातील काळी माती Zn-कमी आहे (VNMKV survey: 68% प्लॉट Zn-कमी)
- Zinc-कमी → गड्डा-निर्मिती कमी, उत्पादन 10-15% कमी
- एका हंगामासाठी 10 किलो/एकर पुरेसे

कधी:
- लागवडीच्या 1-3 दिवसआधी
- अन्य basal खतांसोबत (DAP, MOP) मिसळून
- शेत नांगरून तयार असताना

नोंद:
- मातीचे परीक्षण केले असेल आणि Zn पुरेसा असेल तर वगळा (D04-MC-003 rule वेगळी सूचना देईल)
- ZnSO₄ हेप्टाहायड्रेट (21% Zn) form पसंत — market मध्ये स्वस्त + effective
```

## Tests (5 goldens)

| # | Setup | Expected |
|:-:|---|---|
| T1 | Kannad plot, pre_planting, no ZnSO₄ recorded | Fires GREEN; template 1; dose 10 kg/acre |
| T2 | Kannad plot, farmer already recorded 10 kg/acre | Does not fire (resolved) |
| T3 | Kannad plot, farmer recorded 5 kg/acre (partial-dose) | Fires WARNING (v1.1) — new message advises top-up to 10 kg/acre |
| T3b (v1.1) | Kannad plot, farmer recorded 9 kg/acre | FULLY RESOLVED — rule silent |
| T4 | Pune plot (not Kannad zone), pre_planting | Does not fire (zone mismatch) |
| T5 (v1.1 corrected) | Kannad plot + soil test showing Zn = 0.8 ppm (adequate) | `D04-MC-003 SUPPRESSES D04-MC-004` — D04-MC-004 does NOT fire; farmer sees only D04-MC-003's message ("Soil test shows adequate Zn; basal ZnSO₄ not required this season") |
| T5b (v1.1) | Kannad plot + soil test showing Zn = 0.4 ppm (deficient) | Both D04-MC-003 AND D04-MC-004 would fire → BUNDLES; single farmer message combining zone default + soil-test evidence |

---

## Summary — 3 rules delivered

| Rule ID | Type | Trigger | Farmer-facing | Delivery class |
|---|:---:|---|:---:|:---:|
| D06-BW-001 | Blocking gate | `years_since_last_wilt < 5` at pre-planting | RED + agronomist consult | ONCE_UNTIL_RESOLVED |
| D01-PW-001 | Advisory | `planting_date > DATE(year||'-06-07')` | YELLOW/RED tiered | EVENT |
| D04-MC-004 | Recommendation | Kannad zone + no ZnSO₄ recorded | GREEN | ONCE_UNTIL_RESOLVED |

**Backend fields added:** 3 new — `years_since_last_wilt` (int), `planting_date` (date; already exists as concept but confirm date-literal DSL support), `agro_climatic_zone` (enum, auto-derived from polygon), `basal_znso4_applied_kg_acre` (numeric; captured at nutrient log)

**New DSL feature request:** date literal `DATE 'YYYY-MM-DD'` + `season_start_year` config variable — backend implementation, small parser change

**Precedence relations added:** 5 (BW-001↔PW-001 SUPPRESSES, BW-001↔NS-003 BUNDLES, MC-004↔MC-003 COMPLEMENTS/BUNDLES, MC-004↔NS-003 SEQUENCES)

**Marathi templates added:** 4 (BW-001 block, BW-001 prompt, PW-001 late, MC-004 ZnSO₄)

**Golden tests total:** 15 (5 per rule)

---

## Backend implementation checklist

- [ ] Add D06-BW-001 rule body update (5 → threshold change) to `Domain6_Rules_Ginger.json`
- [ ] Add D01-PW-001 rule body update (date-literal trigger) to `Domain1_Rules_Ginger.json`
- [ ] Add D04-MC-004 new rule to `Domain4_Rules_Ginger.json`
- [ ] Add DSL parser support: `DATE 'YYYY-MM-DD'` literal + comparison operators
- [ ] Add `season_start_year` config variable to engine runtime
- [ ] Add 3 new fields to farm_brain schema: `years_since_last_wilt`, `agro_climatic_zone`, `basal_znso4_applied_kg_acre`
- [ ] Wire `agro_climatic_zone` auto-derivation from plot polygon centroid + Maharashtra agro-climatic zones GIS layer (needs GIS layer sourced — VNMKV Parbhani + Maharashtra Agriculture Department publish this)
- [ ] Add 4 Marathi templates
- [ ] Add 5 precedence relations
- [ ] Add 15 golden tests

**Estimated backend integration effort:** 5-7 hours (rules + DSL date-literal + GIS zone derivation + templates + tests).

**Note on GIS zone layer:** If backend can't source Maharashtra agro-climatic-zones GIS shapefile immediately, fall back to `agro_climatic_zone` as farmer-declared enum (dropdown at plot setup) with the 6 zone options. Kuldip will provide the GIS shapefile via VNMKV request in parallel — target 5 October 2026.

---

## Sign-off

All three rules carry direct VNMKV certificate authority (§4 zone mapping, §5 wilt-rotation extension). D04-MC-004 supported by VNMKV Parbhani soil-survey data (68% Zn-deficient in Kannad).

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

---

## Sources

- VNMKV Compliance Certificate v1.0 (24 Sep 2026) — §4 zone mapping, §5 wilt-rotation extension to 5 years, §5.2 planting-window revision
- [AICRP-Spices — Package of Practices Ginger](https://aicrps.res.in/Extension%20Pamphlets/Ginger/English/Package%20of%20practices%20Ginger.pdf) — variety duration references, planting-window Maharashtra guidance
- VNMKV Parbhani Soil Survey 2019-2023 (internal reference cited in compliance certificate) — Kannad Zn-deficiency 68% prevalence
- Master Action List Track B1.3, B1.4, B1.6 (23 Sep 2026)

*End of B1 VNMKV Leftover Rules v1.0*
