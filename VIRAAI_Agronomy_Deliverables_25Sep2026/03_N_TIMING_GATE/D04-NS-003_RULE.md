# D04-NS-003 — Nitrogen Timing Gate (late-stage N excess block)

**Purpose:** Block advisory or farmer proposal of nitrogen (urea, DAP-derived N, complex fertilizers) during G3-G4 stages when cumulative N applied already exceeds variety ceiling. Late-stage N excess causes rank vegetative growth, delayed rhizome maturation, increased bacterial-wilt susceptibility, and yield loss.

**Version:** 1.0
**Date:** 25 September 2026
**Author:** Kuldip — Agronomy Compliance Owner
**Domain:** D04 Nutrients
**Category:** NS (Nutrient Scheduling)
**Compliance:** COMPLIANT (VNMKV Package of Practices baseline + AICRP-Spices; variety-specific ceilings marked L4 VIRAAI-derived)
**Ref:** Backend agronomy-inputs request §3; Units convention 6b (per-acre); `variety_N_ceiling.csv`

---

## 1. Basis — VNMKV / AICRP-Spices standard N schedule

**Total N ceiling (Maharashtra baseline, matches AICRP-Spices Package of Practices):**
> 150 kg N/ha = **61 kg N/acre** (Mahima; other varieties derived)

**Split schedule (baseline — per Maharashtra recommendation):**

| Application timing | DAP | kg/ha (baseline) | kg/acre (converted, Mahima) |
|---|:---:|:---:|:---:|
| Basal (at planting) | 0 | 60 | **24** |
| First top-dress | 45 | 50 | **20** |
| Second top-dress | 120 | 40 | **17** (rounded from 16.2) |
| **Total** | — | **150** | **61** |

**Late-stage N cutoff: DAP 150.** No further N application permitted after DAP 150 (start of G4 rhizome-bulking). Rationale: N applied after DAP 150 promotes leaf-flush over rhizome-bulking, and increases free amino acid content in rhizome tissue → bacterial wilt susceptibility documented at VNMKV Parbhani.

---

## 2. Per-variety N ceilings (from `variety_N_ceiling.csv`)

| Variety | Total N ceiling (kg/acre) | Basal (DAP 0) | Top-dress 1 (DAP 45) | Top-dress 2 (DAP 120) | Source tier |
|---|:---:|:---:|:---:|:---:|:---:|
| **IISR-Mahima** | 61 | 24 | 20 | 17 | L3 (VNMKV baseline) |
| **IISR-Varada** | 55 | 22 | 18 | 15 | L4 (VIRAAI-derived, −10% from Mahima) |
| **Nadia (local)** | 52 | 21 | 17 | 14 | L4 (VIRAAI-derived, −15% from Mahima) |

L4 basis: matched to variety water-demand ratios in `variety_stage_water_target.csv`. Season 1 field data will re-calibrate; Season 2 targets may shift.

---

## 3. Rule anatomy

### Identification
- **Rule ID:** `D04-NS-003`
- **Rule name:** n_timing_late_stage_excess_gate
- **Rule type:** BLOCKING_GATE (blocks N application proposal in G3-G4 when ceiling exceeded)
- **Compliance tag:** `COMPLIANT`

### Trigger (v1.1 corrected — anticipated-sum check)
```
stage IN ['G3', 'G4']                                          -- DAP 91-210
AND proposed_n_application_kg_acre > 0
AND (
    (total_n_kg_acre_applied_since_dap_0 + proposed_n_application_kg_acre) > variety_N_ceiling_kg_acre
    OR (stage == 'G4' AND dap > 150)                           -- hard cutoff post-DAP-150
)
```

**v1.1 fix:** v1.0 checked only `total_applied > ceiling`, which would allow the proposal to push cumulative over the ceiling because the past-only sum hadn't yet exceeded it. Now checks `(past + proposed) > ceiling` so a farmer proposing 20 kg when 45 kg already applied (Mahima ceiling 61) is correctly blocked (65 > 61).

**Fields required:**
- `total_n_kg_acre_applied_since_dap_0` — running sum of all N events (basal + top-dresses + any supplementary) since planting, in kg N/acre
  - Aggregation: `SUM(event.n_kg_acre) OVER (plot_id, dap >= 0)`
  - N content computed from fertilizer product (urea 46% N, DAP 18% N, 10:26:26 = 10% N, etc.)
- `variety_N_ceiling_kg_acre` — lookup from `variety_N_ceiling.csv` by plot's variety
- `proposed_n_application_kg_acre` — from advisory queue or farmer scouting form
- `dap` — days after planting (from `planting_date`)
- `stage` — current phenological stage (from D01 lifecycle)

### Action (v1.1 corrected — RED cutoff evaluated FIRST)
```
# v1.1 fix: evaluate hard-cutoff FIRST so a post-DAP-150 proposal always gets RED,
# never a YELLOW that would allow farmer override. v1.0 had YELLOW branch first,
# which would silently mask the DAP-150 hard cutoff for over-ceiling proposals in G4.

IF stage == 'G4' AND dap > 150 AND proposed_n_application_kg_acre > 0:
    emit block_decision:
        message = 'post_150_dap_n_hard_cutoff'
        template = D04_TEMPLATE_2_POST_150_BLOCK
        severity = 'red'
        farmer_override_permitted = FALSE            -- hard block
        contributing_signals = ['dap_cutoff']
        block_reason = f'DAP={dap} > 150 hard cutoff; proposed {proposed_n_application_kg_acre} kg/acre denied regardless of cumulative'

ELIF stage IN ['G3', 'G4'] AND (total_n_applied + proposed_n) > ceiling:
    emit block_decision:
        message = 'late_stage_n_excess_block'
        template = D04_TEMPLATE_1_EXCESS_BLOCK
        severity = 'yellow'
        farmer_override_permitted = TRUE (with agronomist notification)
        contributing_signals = ['n_cumulative_ledger', 'stage_context']
        block_reason = f'Cumulative N would reach {total_n_applied + proposed_n} kg/acre (past {total_n_applied} + proposed {proposed_n}); ceiling {ceiling} kg/acre'
```

### Severity map
| Condition | Severity | Override |
|---|:---:|:---:|
| G3-G4 + cumulative exceeds ceiling | YELLOW | Farmer permitted (agronomist notified) |
| G4 + DAP > 150 (any N proposal) | RED | Not permitted; hard cutoff |

### Precedence relations
- `D04-NS-003 SUPPRESSES advisory-engine N recommendations in G3-G4 when ceiling breached`
- `D04-NS-003 BUNDLES D06-BW-001` (bacterial wilt rotation) — if plot has wilt history AND N excess, message notes compounding risk
- Does not conflict with D04-MC-003 (basal micronutrients — different fertilizer class)
- Does not affect D04 phosphorus / potassium rules

### Confidence
- HIGH when `total_n_applied` ledger complete (all events logged)
- MEDIUM when farmer manually entered historical events (may miss some)
- LOW when ledger sparse (< 2 events logged for plot with DAP > 90 — suspicious)

### Kannad note (kannad_note)
Kannad Western Scarcity zone: monsoon-withdrawal in October coincides with G3 peak. Farmers sometimes apply "insurance" late N thinking to boost rhizome fill — this is exactly the pattern this rule blocks. VNMKV Parbhani has documented 15-20% yield loss when N applied post-DAP-150.

### Marathi advisory templates

**D04_TEMPLATE_1_EXCESS_BLOCK (yellow — cumulative exceeds ceiling):**
```
⚠️ थांबा — नत्र (N) पुरेसा दिला गेला आहे

आतापर्यंत दिलेला नत्र: {total_n_applied} किलो/एकर
वाणाचे कमाल प्रमाण: {variety_N_ceiling} किलो/एकर

आत्ता आणखी नत्र देऊ नका — कारण:
- जास्त नत्र → गळ वाढते पण गड्डा तयार होत नाही
- पिकावर जिवाणू-मर (bacterial wilt) चा धोका वाढतो
- उत्पादन 15-20% कमी होऊ शकते

पर्याय:
✅ पोटॅशियम (K) टाकू शकता — गड्डा भरणीसाठी उपयुक्त
✅ Micronutrient spray (Zn/B) फायद्याचे
✅ मल्च टाकल्यास N-नष्ट होत नाही

Agronomist ला call करा — तुमच्या शेतासाठी exact strategy साठी.
```

**D04_TEMPLATE_2_POST_150_BLOCK (red — hard cutoff):**
```
🛑 नत्र (N) देऊ नका — DAP {dap} झाले

अद्रकीच्या {stage_mr} अवस्थेत आणि 150 DAP नंतर नत्र देणे बंद.

कारण:
- गड्डा-भरणीच्या अवस्थेत नत्र → पालेजाळी वाढते
- गड्ड्याची साल कमजोर होते, storage life कमी
- जिवाणू-मर चा गंभीर धोका (VNMKV Parbhani documented 15-20% yield loss)

आत्ता focus:
✅ पाणी-व्यवस्थापन (सिंचन शिफारसीप्रमाणे)
✅ Potash spray (K) — गड्डा घन होण्यासाठी
✅ रोग-निरीक्षण (जिवाणू-मर लक्षणे)

पुढील N वेळापत्रक: पुढच्या हंगामासाठीच.
```

### Tests (5 goldens)

| # | Setup | Expected |
|:-:|---|---|
| T1 | Mahima, DAP 100 (G3), total_n=45, proposed=20 | **BLOCK YELLOW** (past+proposed = 65 > 61 ceiling) — v1.1 anticipated-sum fix confirmed |
| T2 | Mahima, DAP 100 (G3), total_n=40, proposed=15 | Allow (40+15=55 < 61) — no block |
| T3 | Mahima, DAP 160 (G4), total_n=50, proposed=5 | **BLOCK RED** (post-150 cutoff evaluated FIRST regardless of ceiling — v1.1 precedence fix) |
| T3b | Mahima, DAP 160 (G4), total_n=80, proposed=10 | **BLOCK RED** (post-150 cutoff still fires; NOT falls through to YELLOW even though ceiling also breached) — v1.1 precedence fix |
| T4 | Mahima, DAP 60 (G2), total_n=45, proposed=30 | Rule does not fire (stage=G2, not in [G3,G4]) — pass through to other D04 checks |
| T5 | Varada, DAP 120 (G3), total_n=50, proposed=10 | BLOCK YELLOW (50+10=60 > Varada ceiling 55) |

---

## 4. Backend implementation checklist

- [ ] Add rule to `Domain4_Rules_Ginger.json` under `_rules[]`
- [ ] Add new field `total_n_kg_acre_applied_since_dap_0` to farm_brain schema (derived, aggregated from N event ledger)
- [ ] Add lookup table `variety_N_ceiling` seeded from `variety_N_ceiling.csv`
- [ ] Extend farmer-app N-application log form to capture `fertilizer_product`, `dose_kg_or_bags`, `n_content_pct` (derived from product) — feeds cumulative ledger
- [ ] Wire N-application ledger to trigger `compute_total_n_applied()` on every N-event log
- [ ] Add 2 Marathi templates (D04-1 excess, D04-2 post-150 cutoff)
- [ ] Add 5 golden tests
- [ ] Precedence declaration in `_precedence[]`

**Estimated backend integration effort:** 4-6 hours (rule + field aggregation + templates + tests).

---

## 5. Units convention — reference

All values in this rule use **kg N/acre** (per units decision 6b).

Backend fertilizer-to-N conversion (backend calculates once):
| Fertilizer | N content % | Example: bag → N |
|---|:---:|---|
| Urea | 46% | 1 bag (50 kg) = 23 kg N |
| DAP (18-46-0) | 18% | 1 bag (50 kg) = 9 kg N |
| 10:26:26 | 10% | 1 bag (50 kg) = 5 kg N |
| 12:32:16 | 12% | 1 bag (50 kg) = 6 kg N |
| 20:20:0:13 | 20% | 1 bag (50 kg) = 10 kg N |
| Ammonium sulphate | 21% | 1 bag (50 kg) = 10.5 kg N |

Farmer app should show both: fertilizer dose (bags) + derived N (kg N/acre).

---

## 6. Season 1 impact assessment

**Farmer-facing impact:**
- Silent for most farmers who follow VNMKV schedule (basal 24 + top-dress 20 + top-dress 17 = 61 kg/acre exact ceiling → no breach)
- Fires only if farmer applies "insurance" N above ceiling OR misjudges DAP boundary
- Hard-block (post-150) protects against common late-N mistake

**Agronomist workload:**
- Yellow blocks generate agronomist notifications → weekly digest bucket
- Expected volume: ~10-15% of Kannad pilot plots may hit yellow block once during season

---

## 7. Sign-off

Rule is compliance-safe (VNMKV baseline honored), variety ceilings honestly tagged as L4 VIRAAI-derived pending Season 1 calibration. Hard cutoff at DAP 150 has direct VNMKV Parbhani field evidence.

Any Season 2 recalibration will be driven by empirical yield-N-response data collected during Season 1 (Track D5).

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

---

## Sources

- [AICRP-Spices — Package of Practices Ginger (PDF)](https://aicrps.res.in/Extension%20Pamphlets/Ginger/English/Package%20of%20practices%20Ginger.pdf) — Maharashtra N schedule 150 kg/ha (60 basal + 50 at 45 DAP + 40 at 120 DAP)
- [ICAR-IISR Kozhikode — Ginger Cultivation Practices (PDF)](https://spices.res.in/storage/app/public/pdfs/GINGER/3ENG.pdf) — state-wise N recommendations (Kerala 70, Karnataka 100, Odisha 125, HP 100, Chhattisgarh 150 kg/ha)
- VNMKV Parbhani OFT records (internal) — bacterial-wilt susceptibility correlation with post-DAP-150 N application

*End of D04-NS-003 Rule v1.0*
