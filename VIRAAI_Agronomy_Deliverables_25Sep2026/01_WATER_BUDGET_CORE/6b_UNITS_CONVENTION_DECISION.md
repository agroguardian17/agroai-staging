# Units Convention — Single Decision Across KB

**Purpose:** Backend flagged inconsistency — KB is "per-acre throughout", but water spec is per-plant and N spec is per-ha. This document pins ONE units convention for the entire engine to eliminate ambiguity.

**Version:** 1.0
**Date:** 25 September 2026
**Owner:** Kuldip — Agronomy Compliance Owner
**Ref:** Backend agronomy-inputs request §6 (cross-cutting units question)

---

## 1. The decision

**Primary storage unit for the KB and all rule bodies: PER-ACRE.**

Rationale: KB was authored per-acre throughout; farmers in Marathwada think in acres (गुंठा/एकर), not hectares; changing to per-ha would force retrofit of ~300+ rule DSLs. Per-acre stays.

**Exception: per-plant units for water-budget computations only** — because irrigation dose depends on plant count (not area alone), and D11 yield model consumes per-plant water deficit ratios.

---

## 2. Per-domain unit table

| Domain | Metric | Storage unit | Reason |
|---|---|:---:|---|
| **D01** Lifecycle | Plant count | plants/acre + plants/plot | Plot-level for engine, acre for KB rules |
| **D02** Soil | Amendments (compost, lime) | kg/acre | KB standard |
| **D03** Water | Cumulative water | L/plant/stage, L/plant/lifecycle | Per-plant for D11 feed |
| **D03** Water | Irrigation event dose | **L/plot** (computed from L/plant × plants) | Farmer needs plot-total to run drip |
| **D03** Water | Variety demand table | L/plant/day, L/plant/stage | Per-plant is variety-invariant metric |
| **D04** Nutrients | N, P, K, micronutrients | **kg/acre** | KB standard; convert from per-ha spec |
| **D04** Nutrients | Basal + top-dress doses | kg/acre per event | KB standard |
| **D05** Pests | Sprays | ml/acre or g/acre | KB standard |
| **D06** Diseases | Fungicides | g/acre or L/acre | KB standard |
| **D07** Weather | Rainfall | mm | Universal — no conversion |
| **D07** Weather | Temperature | °C | Universal |
| **D08** Weeds | Herbicides | ml/acre or g/acre | KB standard |
| **D09** Harvest | Yield | tonnes/acre + kg/plant | Both; farmer wants acre, D11 wants per-plant |
| **D10** Schemes | Subsidy calc | ₹/acre | KB standard, matches govt scheme docs |
| **D11** Yield model | Prediction output | tonnes/acre | Farmer-facing |
| **D11** Yield model | Internal deficit ratios | dimensionless (0-1) | Universal |
| **D12** QA | Advisory logs | per-advisory-record | N/A |
| **D13** Precision/site-index | Multipliers | dimensionless | Universal |
| **D14** Satellite | NDVI/NDRE/NDMI | dimensionless index | Universal |
| **D14** Satellite | Plot area | m² (derived) + acre (farmer display) | Backend computes m²; UI shows acre |

---

## 3. Conversion factors (backend implements once, uses everywhere)

| From | To | Factor |
|---|---|:---:|
| hectare | acre | × 2.47105 |
| acre | hectare | × 0.40469 |
| acre | m² | × 4046.86 |
| m² | acre | × 0.000247105 |
| kg/ha | kg/acre | × 0.40469 |
| L/ha | L/acre | × 0.40469 |
| L/plant × plants/acre | L/acre | direct multiply |

**Reference plant density (for per-plant ↔ per-acre conversions when plants/acre not yet computed):**
- Broad bed (recommended for Kannad): use **25,000 plants/acre** as default proxy
- Farmer-plot-specific: always use actual `plot_plants_estimated / plot_area_acre`

---

## 4. Specific spec fixes required by this decision

### 4.1 D04-NS-003 N-timing gate (per Abhinav's §3)
- **Old spec:** wrote N in kg/ha
- **New:** convert all N-ceiling numbers to **kg/acre** for the KB
- `total_n_kg_ha` field → **rename to `total_n_kg_acre`** in Domain 3/4 schemas
- Aggregation: sum of applied-N events since planting, in kg/acre

**Example conversion (typical ginger N-ceilings I'll author in item 3):**
- IISR-Mahima: 120 kg/ha → **≈ 49 kg/acre**
- IISR-Varada: 110 kg/ha → **≈ 45 kg/acre**
- Nadia (local): 100 kg/ha → **≈ 40 kg/acre**

### 4.2 B1.6 basal ZnSO₄ (per Abhinav's §4)
- Spec: 25 kg/ha
- **KB storage: 10 kg/acre** (25 × 0.40469 ≈ 10.1, round to 10 for farmer-friendly whole number)

### 4.3 Water-budget outputs
- Internal: per-plant (unchanged — this is the sensible base unit for per-plant dosing)
- Farmer-facing dose: **liters/plot** (backend multiplies per-plant × **plants_estimated**) — this is what farmer needs to run drip
  - **v1.1 typo fix:** v1.0 wrote "plots_estimated" which would produce drops, not liters; correct field is `plot_plants_estimated`
- D11 feed: per-plant deficit ratio (dimensionless, 0-1) — no unit ambiguity

### 4.4 Rain / ETc
- Rainfall: mm (universal)
- ETc: mm/day (universal)
- Conversion to volume: `mm × plot_area_m² = liters` (backend computes for water-balance)

---

## 5. Farmer-facing display

Regardless of internal storage, farmer sees:

| Metric | Farmer display |
|---|---|
| Plot area | **एकर (acre)** primary; hectare in tooltip |
| Water dose (event) | **लिटर (liters, plot-total)** primary; per-plant in evidence |
| Water cumulative | **लिटर per एकर + per झाड** |
| Nutrients | **किलो per एकर** |
| Yield prediction | **टन per एकर** |
| Sprays | **मिलीलिटर per एकर** |

---

## 6. Enforcement in engine

- All rule DSLs: use per-acre or per-plant only (no per-ha)
- Backend rule-loader: validate at load-time that no rule references `_kg_ha`, `_l_ha`, `_per_ha` suffixed fields; reject with clear error
- Any legacy spec fields with `_ha` suffix → deprecate + provide backward-compat conversion for one release, then remove

---

## 7. Sign-off

Units convention pinned as above. Backend authoritative reference for any KB rule authoring or spec question.

Applies immediately to items 2, 3, 4 (backend-pending agronomy work) and to Season 2 rule authoring.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

*End of Units Convention Decision v1.0*
