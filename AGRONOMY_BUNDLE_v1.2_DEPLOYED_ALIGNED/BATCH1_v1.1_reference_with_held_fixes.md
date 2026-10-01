# Batch 1 — 5 Ready-to-Wire Rules · Delivery Class Confirmations + Golden Tests

**Date:** 27 September 2026
**From:** Kuldip — Agronomy Compliance Owner
**To:** Backend team
**Ref:** `firing-intent.pdf` (backend wiring sheet) — Ready-to-wire section (5 rules, fields already exist)
**Purpose:** Answer backend's exact ask — confirm suggested delivery class + provide 1 fire + 1 near-miss golden test each. All 5 rules ready for CI-green PR upon backend integration.

**Discipline applied** (per 26-Sep drift acknowledgement): severity strict 4-value (info/yellow/red/blocking); no FEEDS precedence; no L1-L4 tiers (A/B/C source_class); no push_notification; deployed-vocabulary-aligned; Marathi native.

---

## Rule 1 — D01-PH-004 (agronomy · EVENT)

**Firing condition (deployed DSL, already agreed):**
```
flowering_observed == true AND dap >= 150
```

**Delivery class:** ✅ **CONFIRMED EVENT**
- Rationale: flowering observation is a discrete moment; message once at that moment. Re-fires only if farmer marks flowering false + true again (edit case).

**Severity:** `yellow`

**Source class:** `B` (VNMKV Package of Practices — G4 rhizome-fill N cutoff)

**Message intent (Marathi, final):**
> *"फुलोरा दिसला — गड्डा भरण्याची अवस्था सुरू. आत्ता नत्र (N) देऊ नका. उटाळणी (earthing up) पूर्ण करा + पालाश (K) टॉप-ड्रेस पूर्ण करा."*

**Golden tests:**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `flowering_observed=true, dap=155` | Fires; template emitted; severity=yellow |
| T2 | **NEAR-MISS** | `flowering_observed=true, dap=145` | Does NOT fire (dap<150; flowering-flag alone insufficient without dap threshold) |

**Precedence relations:** None new (D04-NS-003 already handles N-timing separately; this is a farmer-facing complement not a precedence-linked rule).

---

## Rule 2 — D02-DR-004 (agronomy · WINDOW)

**Firing condition (deployed DSL):**
```
percolation_class == "poor" AND planting_layout == "broad_ridge" AND dap < 15
```

**Delivery class:** ✅ **CONFIRMED WINDOW**
- Rationale: fires within the early-establishment window (DAP 0-14) for a plot that has poor drainage even under broad-ridge — repeated reminders across the window are appropriate; WINDOW's stage-window recurrence fits.

**Severity:** `yellow`

**Source class:** `B` (VNMKV OFT — broad-ridge on vertisol reduces but doesn't eliminate drainage risk in poor-percolation plots)

**Message intent (Marathi, final):**
> *"निचरा कमी — broad-ridge असला तरी वरंब्याखाली मुख्य चर (main furrow) तपासा. गरज असल्यास outlet चर खोदा. गड्डा-कूज टाळण्यासाठी DAP 15 च्या आत निचरा नीट करा."*

**Golden tests:**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `percolation_class="poor", planting_layout="broad_ridge", dap=10` | Fires; template emitted; severity=yellow |
| T2 | **NEAR-MISS** | `percolation_class="poor", planting_layout="broad_ridge", dap=20` | Does NOT fire (dap≥15; window closed) |

**Precedence relations:** None new. Note: D02-DR-004 does not conflict with D02-LY-001 — the latter fires pre-planting only.

---

## Rule 3 (v1.1 SPLIT per backend 27-Sep held-#2) — D02-LY-001 · Retained blocking gate + D02-LY-002 · New yellow prompt

**Background:** deployed D02-LY-001 is the #87 flat-on-vertisol blocking rule (wrong-layout gate). My v1.0 Batch-1 spec had a different intent (unset-layout prompt) but reused the same id. Backend flagged the id conflict — two genuinely different rules can't wear one id. Split confirmed as below.

---

### 3A — D02-LY-001 (RETAINED — deployed blocking intent, DSL made explicit)

**Firing condition (deployed DSL, explicit):**
```
soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout IS NOT NULL AND planting_layout != 'broad_ridge'
```

**Delivery class:** `ONCE_UNTIL_RESOLVED`
**Severity:** `blocking`
**Source class:** `B` (VNMKV Package of Practices — broad-ridge mandatory on vertisol+drip)

**Message intent (Marathi, final):**
> *"काळी माती + ठिबक — निवडलेली लागवड पद्धत ({planting_layout_mr}) चुकीची. Broad-ridge (60/40 cm) एकमेव VNMKV-शिफारस. Flat/इतर पद्धत → गड्डा-कूज + जिवाणू-मर गंभीर धोका. लागवडीपूर्वी पद्धत बदला."*

**Golden tests:**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `soil_type="vertisol", has_drip=true, planting_layout="flat"` | Fires; severity=blocking |
| T2 | **NEAR-MISS** | `soil_type="vertisol", has_drip=true, planting_layout="broad_ridge"` | Does NOT fire (compliant layout) |

**Precedence:** existing #87 semantics preserved.

---

### 3B — D02-LY-002 (NEW — unset-layout prompt, my original Batch-1 trigger verbatim)

**Firing condition (deployed DSL):**
```
soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout IS NULL AND dap IS NULL
```

**Delivery class:** `ONCE_UNTIL_RESOLVED`
- Ladder (0, 7, 21, 45, 90) escalates severity if farmer doesn't set `planting_layout`. Resolution = `planting_layout IS NOT NULL`.

**Severity:** `yellow` (starts; ladder-escalates over time until resolved)
**Source class:** `B`

**Message intent (Marathi, final):**
> *"काळी माती + ठिबक — लागवडीपूर्वी broad-ridge (60 सेमी बेड + 40 सेमी सरी) VNMKV शिफारस. Farmer app मध्ये लागवडीची पद्धत निवडा. सपाट (flat) लागवड निवडल्यास गड्डा-कूज धोका."*

**Golden tests:**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `soil_type="vertisol", has_drip=true, planting_layout=NULL, dap=NULL` | Fires; ladder starts at yellow |
| T2 | **NEAR-MISS** | `soil_type="vertisol", has_drip=true, planting_layout="broad_ridge", dap=NULL` | Does NOT fire (layout set — resolved) |

**Precedence:** `D02-LY-002 SEQUENCES D02-LY-001` — the prompt fires first on unset layout; if farmer sets a non-compliant layout, the retained blocking rule takes over. Cleanly separates "data-capture missing" (yellow prompt) from "farmer-choice wrong" (blocking gate).

---

## Rule 4 — D02-ST-002 (field_ops · ONCE_UNTIL_RESOLVED)

**Firing condition (deployed DSL):**
```
dap IS NULL AND percolation_time_hours IS NULL
```

**Delivery class:** ✅ **CONFIRMED ONCE_UNTIL_RESOLVED**
- Rationale: one-time pre-planting percolation test; resolution = `percolation_time_hours IS NOT NULL`. Ladder appropriate for follow-up if farmer doesn't complete test.

**Severity:** `yellow` (data-capture prompt, not agronomic warning)

**Source class:** `B` (VNMKV / AICRP-Spices Package of Practices — pre-plant percolation test protocol)

**Message intent (Marathi, final):**
> *"लागवडीपूर्वी एक-वेळेस percolation test करा: 20 सेमी खोल आणि 20 सेमी रुंद खड्डा खणा, पूर्ण पाण्याने भरा, किती वेळात मुरते ते नोंदवा (तासात). हा data drainage-सापेक्ष लागवड-सल्ल्यासाठी वापरला जातो."*

**Golden tests:**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `dap=NULL, percolation_time_hours=NULL` | Fires; template emitted; owner=field_ops queue |
| T2 | **NEAR-MISS** | `dap=NULL, percolation_time_hours=6.5` | Does NOT fire (test already done — resolved) |

**Precedence relations:** D02-ST-002 SEQUENCES D02-LY-001 (percolation test result should inform layout decision — order matters).

---

## Rule 5 (v1.1 CORRECTED per backend 27-Sep held-#1) — D03-SB-003 (auto · EVENT)

**Backend catch:** v1.0 trigger `current_stage != previous_stage` assumed `previous_stage` existed. It doesn't. DSL bare-word-as-string-literal trap would silently make it `current_stage != "previous_stage"` — firing on every plot every run. Fixed via option (A): declare `previous_stage` as a new derived field (added to catalog as 54th field).

**New field declaration (added to `firing_intent_53_field_catalog.csv`):**
```
previous_stage, enum, derived, nullable=true, default=null
  Notes: mapper persists current-run current_stage as previous_stage at run-close 
  for next-run diff; NULL on first-ever run for a plot
  Used by: D03-SB-003
```

**Firing condition (v1.1 corrected DSL):**
```
current_stage != previous_stage
AND previous_stage IS NOT NULL        -- suppress first-ever-run false positive
```

Second clause is defensive — three-valued logic already returns UNKNOWN when `previous_stage` is NULL (so rule wouldn't fire), but explicit guard makes intent obvious to future readers and to golden-test authors.

**Delivery class:** ✅ **CONFIRMED EVENT**
- Rationale: stage transition is a discrete event; auto rule updates moisture bands silently; farmer message optional per delivery-class definition.

**Severity:** `info` (informational; no action required)

**Source class:** `B` (VNMKV G0-G5 phenological classification)

**Message intent (Marathi, final):**
> *"पिकाची अवस्था बदलली — {previous_stage_mr} → {current_stage_mr}. Sub-node moisture-bands आपोआप update झाले. आत्ता कोणतीही कृती (action) नको; पुढील सिंचन-शिफारसी नव्या अवस्थेप्रमाणे येतील."*

**Golden tests (v1.1 updated):**

| # | Type | Setup | Expected |
|:-:|:-:|---|---|
| T1 | **FIRE** | `previous_stage="G1", current_stage="G2"` | Fires; template emitted; severity=info |
| T2 | **NEAR-MISS** | `previous_stage="G2", current_stage="G2"` | Does NOT fire (no transition) |
| T3 | **NEAR-MISS (v1.1 new)** | `previous_stage=NULL, current_stage="G0"` | Does NOT fire (first-ever-run guard) |

**Precedence relations:** None new. D03-SB-003 is silent for downstream advisory continuity — just marks the state change.

---

## Batch 1 summary — v1.1 updated per backend 27-Sep held-#1 + held-#2

| Rule | Delivery | Severity | Source | Tests | Precedence | Status |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| D01-PH-004 | EVENT | yellow | B | 2 | — | ✅ Wired PR #93 |
| D02-DR-004 | WINDOW | yellow | B | 2 | — | ✅ Wired PR #93 |
| **D02-LY-001** | ONCE_UNTIL_RESOLVED | **blocking** | B | 2 | — | ⏳ Next batch — retained deployed intent, explicit DSL |
| **D02-LY-002 (NEW)** | ONCE_UNTIL_RESOLVED | yellow (ladder) | B | 2 | SEQUENCES D02-LY-001 | ⏳ Next batch — my Batch-1 prompt as separate id |
| D02-ST-002 | ONCE_UNTIL_RESOLVED | yellow | B | 2 | SEQUENCES D02-LY-001 | ✅ Wired PR #93 |
| **D03-SB-003** | EVENT | info | B | **3** | — | ⏳ Next batch — needs `previous_stage` field declared |

**Totals (v1.1): 6 rules (was 5), 13 golden tests (was 10), 2 precedence edges (was 1), 6 Marathi templates (was 5), 1 new field (`previous_stage`).**

**Backend action items next batch:**
1. Declare `previous_stage` derived enum field + mapper persistence
2. Wire D02-LY-001 with explicit DSL (deployed intent, no behavior change)
3. Wire D02-LY-002 as new rule (my original Batch-1 prompt trigger verbatim)
4. Wire D03-SB-003 with corrected DSL (post `previous_stage` declaration)

---

*End of Batch 1 Confirmations v1.0*
