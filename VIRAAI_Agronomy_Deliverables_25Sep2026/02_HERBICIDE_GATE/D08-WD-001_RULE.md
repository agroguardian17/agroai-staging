# D08-WD-001 — Registered-Herbicide Gate (rewritten per Track A5.1)

**Purpose:** Replace the v1.0 blanket-block ("no herbicides") with a positive-list gate. Non-selective / crop-damaging / not-registered-for-ginger herbicides remain BLOCKED. Off-label ICAR-IISR-recommended formulations require explicit CIB&RC label verification before permit. Default recommendation for Season 1 remains **manual + mulching** (VNMKV / AICRP standard).

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Domain:** D08 Weeds
**Category:** WD (Weed / Herbicide gate)
**Compliance:** COMPLIANT (positive-list gate + Insecticides Act 1968 + FSSAI MRL alignment)
**Ref:** Master Action List Track A5.1; Backend agronomy-inputs request §2; `registered_herbicide_registry_ginger_v1.0.csv`

---

## 1. Findings from research (basis for gate logic)

**Central finding (source: ICAR-IISR Kozhikode Cultivation Practices document, section on chemical weed control):**
> *"The chemical control measures included in the document are based on research and field studies undertaken by ICAR-IISR. The formulations may not be included in the list of approved pesticides for ginger by CIBRC."*

**This is ICAR-IISR's own acknowledgement that its herbicide recommendations may not be CIB&RC-registered for ginger.** The compliance-safe posture:

1. **Ginger has effectively NO CIB&RC-registered synthetic herbicides** with ginger-specific labels
2. **ICAR-IISR recommends 2 off-label formulations** (Oxyfluorfen pre-emergent, Quizalofop-ethyl post-emergent) but flags the CIB&RC gap
3. **VNMKV / AICRP-Spices Package of Practices for ginger** does NOT include chemical weed control — recommends hand weeding + earthing + mulching
4. **Insecticides Act 1968:** applying an unregistered pesticide to a crop for which no label exists is a regulatory violation regardless of efficacy

**Therefore the gate default must be BLOCK, with narrow explicit exceptions.**

---

## 2. Compliance-tier taxonomy

Registry (`registered_herbicide_registry_ginger_v1.0.csv`) tags each product with a `compliance_tier`:

| Tier | Meaning | Gate default |
|---|---|---|
| `L1_recommended_practice` | VNMKV/AICRP-endorsed, no regulatory risk (mulching, hand-weeding, green manure) | **PERMIT** — default recommendation |
| `L1_crop_damage_block` | Would damage ginger (2,4-D, non-selective sprayed post-emergence) | **HARD BLOCK** — never recommend even with override |
| `L1_nonselective_block` | Non-selective (Glyphosate, Paraquat); would kill ginger | **HARD BLOCK** for in-season; PERMIT only in explicit pre-plant fallow window with agronomist sign-off |
| `L1_not_for_ginger_block` | Registered for other crops (Atrazine for maize, Metribuzin for potato); not for ginger; farmer-confusion risk | **HARD BLOCK** |
| `L3_off_label_icar_recommended` | ICAR-IISR-recommended off-label (Oxyfluorfen, Quizalofop-ethyl) | **BLOCK by default**; PERMIT only after per-product CIB&RC label verification + agronomist sign-off logged |
| `L4_off_label_needs_verification` | Commonly used in India off-label (Pendimethalin) but no ginger-specific verification | **BLOCK by default**; PERMIT only after CIB&RC label verification |

---

## 3. Rule anatomy

### Identification
- **Rule ID:** `D08-WD-001`
- **Rule name:** herbicide_registered_ginger_gate
- **Rule type:** BLOCKING_GATE (herbicide recommendation cannot pass unless positive-list checked)
- **Compliance tag:** `COMPLIANT`
- **Supersedes:** D08-WD-001 v1.0 (blanket herbicide block)

### Trigger
```
farmer_or_advisory_proposes_herbicide = TRUE
AND crop = 'ginger'
```

The trigger fires whenever ANY of these events occurs:
- Farmer scouting form logs "planning to apply herbicide X"
- Advisory engine recommendation queue proposes a herbicide-based intervention
- Farmer app "Ask agronomist" query mentions a herbicide product name

### Action — positive-list gate
```
proposed_product = normalize_herbicide_input(input)         -- fuzzy match to registry
lookup = registered_herbicide_registry_ginger.lookup(proposed_product)

IF lookup NOT FOUND:
    emit block_decision:
        message = 'unregistered_herbicide'
        template = D08_TEMPLATE_1_UNKNOWN   (Marathi below)
        severity = 'red'
        contributing_signals = ['herbicide_registry_no_match']
    log to agronomist_review_queue for potential registry add

ELIF lookup.compliance_tier IN ('L1_crop_damage_block', 'L1_not_for_ginger_block'):
    emit block_decision:
        message = 'hard_block_would_damage_or_illegal'
        template = D08_TEMPLATE_2_HARD_BLOCK
        severity = 'red'
        farmer_override_permitted = FALSE           -- hard block

ELIF lookup.compliance_tier = 'L1_nonselective_block':
    # v1.1 fix: non-selective herbicides get pre-plant fallow window exception
    IF plot_status = 'pre_planting'
       AND days_to_planting >= 7
       AND agronomist_pre_plant_signoff[proposed_product] = TRUE:
        emit permit_decision:
            message = 'nonselective_pre_plant_permit'
            template = D08_TEMPLATE_6_PREPLANT_PERMIT
            severity = 'yellow'
            timing_constraint = 'must_complete_at_least_7_days_before_planting'
            log to advisory_audit_trail with legal_flag = 'nonselective_pre_plant_agronomist_signed'
    ELSE:
        emit block_decision:
            message = 'nonselective_in_season_block'
            template = D08_TEMPLATE_2_HARD_BLOCK
            severity = 'red'
            farmer_override_permitted = FALSE       -- in-season non-selective = hard block

ELIF lookup.compliance_tier IN ('L3_off_label_icar_recommended',
                                'L4_off_label_needs_verification'):
    IF cib_rc_label_verified_by_agronomist[proposed_product] = TRUE:
        emit permit_decision:
            message = 'permit_at_label_timing'
            template = D08_TEMPLATE_3_PERMIT
            dose_per_acre = lookup.dose_per_acre_low..dose_per_acre_high
            timing = lookup.label_timing_stage + lookup.label_timing_dap_window
            phi_days = lookup.phi_days
            severity = 'yellow'
            log to advisory_audit_trail with legal_flag = 'off_label_verified'
    ELSE:
        emit block_decision:
            message = 'off_label_verification_required'
            template = D08_TEMPLATE_4_VERIFY
            severity = 'yellow'
            action_required = 'agronomist_cib_rc_label_check_before_permit'
            log to agronomist_review_queue

ELIF lookup.compliance_tier = 'L1_recommended_practice':
    emit permit_decision:
        message = 'recommended_practice'
        template = D08_TEMPLATE_5_RECOMMENDED
        severity = 'green'
        contributing_signals = ['vnmkv_aicrp_pop']
```

### New field required (per backend §2)
- **Field name:** `proposed_herbicide_input`
- **Type:** structured object:
  ```
  {
    product_name_free_text: string,      -- farmer's raw input
    active_ingredient: string OR null,   -- if farmer provides (rare)
    cib_rc_reg_number: string OR null,   -- from product label
    source: enum: 'farmer_scouting' / 'advisory_queue' / 'ask_agronomist'
  }
  ```
- **Capture source:**
  - Farmer app: text-input field with autocomplete against product_name registry
  - Scouting form: same field
  - Advisory queue: internal proposal object

### Confidence
- HIGH when product matches registry exactly (name normalization + fuzzy match ≥ 0.85 similarity)
- MEDIUM when partial match; require farmer confirmation of intended product
- LOW when no match; agronomist review triggered

### Severity map
| Compliance tier | Severity | Farmer override? |
|---|:---:|:---:|
| L1_recommended_practice | green | N/A (permit) |
| L1_crop_damage_block | red | ❌ Never |
| L1_nonselective_block | red | ❌ Never (in-season) |
| L1_not_for_ginger_block | red | ❌ Never |
| L3_off_label_icar_recommended | yellow (pending) → green (verified) | ❌ Requires agronomist verify, not farmer override |
| L4_off_label_needs_verification | yellow | ❌ Requires agronomist verify |
| Not in registry | red | ❌ Requires registry update + agronomist review |

### Precedence relations
- `D08-WD-001 SUPPRESSES all advisory-engine herbicide recommendations` (blocking gate — nothing passes without registry check)
- No BUNDLES with other D08 rules (D08-WD-001 is the master gate)
- `D08-WD-001 INFORMS D12-QA-*` (blocks feed QA queue for pattern analysis)

### Kannad note (kannad_note)
Kannad Western Scarcity zone: hand weeding + mulching is doubly recommended because mulch also conserves soil moisture — direct value in low-rainfall zone. Chemical herbicides risk moisture loss (soil surface disturbance from spray equipment traffic) and groundwater contamination (vertisol runoff patterns in monsoon).

### Marathi advisory templates (5 templates)

**D08_TEMPLATE_1_UNKNOWN (unknown product):**
```
⚠️ हे तणनाशक (herbicide) आपल्या registry मध्ये नाही

आपण सांगितलेले तणनाशक: {product_name_free_text}
सिस्टीम-मध्ये या उत्पादनाची माहिती नाही.

आत्ता करा:
- उत्पादनाच्या pack वरील label नीट पहा
- अद्रकीसाठी CIB&RC-registered आहे का तपासा
- Agronomist ला call करा — तो/ती registry मध्ये add करेल

तोपर्यंत सुरक्षित पर्याय:
✅ हातांनी तण काढणे (5-6 वेळा)
✅ मल्च टाकणे (15 टन प्रति एकर हिरवा पाला)
```

**D08_TEMPLATE_2_HARD_BLOCK (dangerous / illegal):**
```
🛑 हे तणनाशक वापरू नका — गंभीर धोका

उत्पादन: {product_name}
कारण: {reason_mr}

धोका:
{IF nonselective}- अद्रक पीक पूर्णपणे मरेल — हे non-selective आहे {ENDIF}
{IF crop_damage}- अद्रकाला थेट नुकसान होईल — फुटवा जळेल {ENDIF}
{IF not_registered}- अद्रकसाठी CIB&RC-मान्यता नाही; कायदेशीर उल्लंघन आहे (Insecticides Act 1968) {ENDIF}

पर्याय:
✅ हातांनी तण काढणे — VNMKV standard शिफारस
✅ मल्च टाकणे — तण + पाण्याची बचत दोन्ही
✅ शेतकरी helpline ला call करा: {helpline}
```

**D08_TEMPLATE_3_PERMIT (verified off-label permit):**
```
✅ हे तणनाशक वापरू शकता — VNMKV agronomist-verified

उत्पादन: {product_name} ({active_ingredient})
वेळ: {label_timing_stage_mr} — DAP {dap_window}
डोस (प्रमाण): {dose_low} ते {dose_high} {dose_unit} प्रति एकर
काढणीपूर्व दिवस (PHI): {phi_days}

⚠️ नोंद: हे उत्पादन ICAR-IISR ने अद्रकसाठी शिफारस केले आहे, पण CIB&RC-मान्यता 
अद्रक-specific नाही — म्हणून agronomist च्या verification नंतरच वापर.

Safety:
- Label वरील सर्व सुरक्षा सूचना पाळा
- Spray करताना PPE (mask + gloves) वापरा
- Container नष्ट करा — पिण्याच्या पाण्यापासून दूर
```

**D08_TEMPLATE_4_VERIFY (needs agronomist verification):**
```
🟡 तपासणी बाकी — agronomist च्या verification-ची वाट पहा

उत्पादन: {product_name}
Status: ICAR/off-label शिफारस — CIB&RC label तपासणी आवश्यक

तोपर्यंत:
- Agronomist verification पुढील ३ दिवसांत होईल
- verification झाल्यावर app मध्ये notification येईल
- तोपर्यंत हातांनी तण काढणे / मल्च टाकणे सुरू ठेवा

Query logged: {ticket_id}
```

**D08_TEMPLATE_6_PREPLANT_PERMIT (v1.1 — non-selective pre-plant fallow window permit):**
```
✅ लागवडीपूर्व fallow window मध्ये वापर मान्य — Agronomist-verified

उत्पादन: {product_name} ({active_ingredient})
Status: Non-selective herbicide — फक्त लागवडीच्या किमान ७ दिवसआधी + agronomist च्या स्पष्ट संमतीने

अटी:
- लागवडीच्या दिवसाच्या किमान ७ दिवसआधी spray पूर्ण करा
- शेत पूर्णपणे तयार (नांगरणी + नांगरून) — bare fallow असावे
- Spray नंतर ७ दिवस पाऊस नको (पाऊस झाल्यास timeline shift)
- अद्रकीचा एकही रोप, गड्डा किंवा बीज त्या दरम्यान शेतात असू नये

धोका जर या अटी पाळल्या नाहीत तर:
- अद्रक पीक पूर्णपणे मरेल — non-selective हा शब्द 'सर्व हिरवी वनस्पती मारते' असा अर्थ
- Recovery शक्य नाही

Safety:
- PPE (mask + gloves) आवश्यक
- Spray drift शेजारच्या पिकांवर जाऊ नये

Verification: Agronomist {agronomist_name} ने {signoff_date} रोजी सही केली आहे.
```

**D08_TEMPLATE_5_RECOMMENDED (recommended practice):**
```
✅ तण-व्यवस्थापन शिफारस — VNMKV / AICRP standard

{IF option = hand_weeding}
हातांनी तण काढणे:
- लागवडीनंतर 4-6 आठवडे शेत स्वच्छ ठेवा
- 5-6 वेळा हातांनी तण काढा (तणाच्या तीव्रतेप्रमाणे)
- मल्च टाकण्यापूर्वी प्रत्येक वेळी तण काढा
- 45 आणि 90 DAP ला earthing करा
{ENDIF}

{IF option = mulching}
मल्च शिफारस:
- लागवडीनंतर लगेच: 15 टन/एकर हिरवा पाला (शेवगा, मंडपाच्या पानांचा पाला, etc.)
- 44-60 DAP: पुनरावृत्ती 7.5 टन/एकर
- 90-120 DAP: पुनरावृत्ती 7.5 टन/एकर
- फायदा: तण नियंत्रण + मातीत ओलावा टिकतो {IF plot.agro_climatic_zone IN ('western_scarcity', 'central_maharashtra') THEN "(पाणी-टंचाईच्या भागात दुहेरी फायदा)"}
{ENDIF}

{IF option = green_manure}
हिरवळीचे खत आंतरपीक:
- बेडच्या मध्ये (interspaces) डायंचा किंवा सन-हेंप पेरा
- 45 DAP ला जमिनीत टाका
- फायदा: तण दमन + नत्र-स्थिरीकरण
{ENDIF}
```

### Tests (5 goldens)

| # | Setup | Expected |
|:-:|---|---|
| T1 | Product = "Roundup" | HARD BLOCK; template 2; farmer_override_permitted=FALSE |
| T2 | Product = "Stomp" (Pendimethalin); no agronomist verification | BLOCK (template 4); ticket logged |
| T3 | Product = "Stomp"; `cib_rc_label_verified_by_agronomist['Stomp']=TRUE` | PERMIT (template 3) with dose 1.0-1.3 L/acre, pre-emergent DAP 0-3 |
| T4 | Product = "Manual/Mechanical" (exact registry key match) | PERMIT (template 5, hand_weeding option); no fuzzy fallback needed |
| T4b | Product = "Hand weeding" (farmer free-text) | Fuzzy match → "Manual/Mechanical"; PERMIT (template 5); log fuzzy_match_confidence |
| T5 | Product = "Xyloherb 45" (not in registry) | BLOCK (template 1); agronomist review queue populated |

---

## 4. Gate logic decision summary (backend implementation checklist)

- [x] Positive-list gate replaces v1.0 blanket-block
- [x] Registry data file authored (`registered_herbicide_registry_ginger_v1.0.csv`, 13 entries)
- [x] 6 compliance tiers defined (L1 permit, L1 hard-blocks × 3 categories, L3 off-label ICAR, L4 unverified)
- [x] `proposed_herbicide_input` field spec provided
- [x] `cib_rc_label_verified_by_agronomist[]` per-product boolean field (agronomist-writable)
- [x] 5 Marathi templates authored
- [x] 5 golden tests with fire + near-miss cases
- [x] Precedence declaration: SUPPRESSES all advisory-engine herbicide proposals
- [x] Farmer override permitted only for L3/L4 tiers after agronomist verify — never for L1_*_block tiers
- [x] Season 1 Kannad default = hand weeding + mulching (green tier)

---

## 5. Sign-off

Gate logic is compliance-safe: **default BLOCK**, positive-list PERMIT only after per-product CIB&RC verification. Season 1 Kannad pilot proceeds on VNMKV-standard hand-weeding + mulching, so this rule effectively has zero farmer-facing impact during Season 1 unless a farmer explicitly asks about a herbicide.

Any Season 2 expansion to permit off-label ICAR formulations requires:
1. Formal CIB&RC label verification per product (Legal desk sign-off)
2. Agronomist verification checkbox set in registry
3. Field trial validation on 3+ pilot plots

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

---

## Sources

- [ICAR-IISR Kozhikode — Ginger Cultivation Practices (PDF)](https://spices.res.in/storage/app/public/pdfs/GINGER/3ENG.pdf) — chemical control disclaimer verbatim quote; Oxyfluorfen + Quizalofop-ethyl recommendations
- [AICRP-Spices — Package of Practices Ginger (PDF)](https://aicrps.res.in/Extension%20Pamphlets/Ginger/English/Package%20of%20practices%20Ginger.pdf) — hand-weeding + mulching + earthing standard; no herbicide recommendation
- [IIHR / KVK Kodagu — Ginger Package of Practices (PDF)](https://kvkkodagu.iihr.res.in/Package%20of%20Practices/Ginger%20%28English%29.pdf) — mulching + weeding schedule
- [CIB&RC — Department of Chemicals and Petrochemicals](https://chemicals.gov.in/cibrc) — regulatory registry authoritative source
- Insecticides Act 1968 — off-label pesticide application regulatory framework

*End of D08-WD-001 Rule v1.0*
