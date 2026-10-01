# Decision-Engine Thresholds — Agronomy Confirmation

**Purpose:** Extract from Water Budget v1.3 §5.2 pseudocode the exact numeric thresholds backend needs, each explicitly confirmed by agronomy. This is a standalone confirm block — no derivation, no discussion, just the pinned numbers.

**Version:** 1.0
**Date:** 25 September 2026
**Owner:** Kuldip — Agronomy Compliance Owner
**Ref:** Water Budget v1.3 §5.2 decision algorithm; Backend agronomy-inputs request §1d

---

## 1. Per-stage deficit thresholds

| Stage | Trigger condition | Urgency | Rule |
|---|---|:---:|---|
| **G3** | `stage_water_deficit_L_per_plant > stage_water_target × 0.40` | **RED** | D03-WB-002 |
| **G3** | `stage_water_deficit_L_per_plant > stage_water_target × 0.30 OR days_gap ≥ 3` | important | D03-WB-001 (G3 branch) |
| **G3** | `stage_water_deficit_L_per_plant > stage_water_target × 0.20 OR days_gap ≥ 2` | **normal** (v1.1 fix — missing tier added) | D03-WB-001 (G3 low branch) |
| **G2** | `stage_water_deficit_L_per_plant > stage_water_target × 0.50` | **RED** | D03-WB-002 (G2 branch) |
| **G2** | `stage_water_deficit_L_per_plant > stage_water_target × 0.45` | important | D03-WB-001 (G2 branch) |
| **G2** | `stage_water_deficit_L_per_plant > stage_water_target × 0.35 OR days_gap ≥ 5` | normal | D03-WB-001 (G2 low branch) |
| **G4** | `stage_water_deficit_L_per_plant > stage_water_target × 0.50` | **RED** | D03-WB-002 (G4 branch) |
| **G4** | `stage_water_deficit_L_per_plant > stage_water_target × 0.45` | important | D03-WB-001 (G4 branch) |
| **G4** | `stage_water_deficit_L_per_plant > stage_water_target × 0.35 OR days_gap ≥ 5` | normal | D03-WB-001 (G4 low branch) |
| **G1** | `days_since_last_irrigation ≥ 2` | normal | D03-WB-001 (G1 branch — days-based, not deficit-based) |
| **G5** | Any deficit | **STOP** (no irrigation) | D03-WB-008 (senescence) |

**✅ CONFIRMED by agronomy 25 Sep 2026.**

Rationale: G3 (rhizome initiation) tightest thresholds — VNMKV documented 15-25% yield loss at ≥40% deficit. G2/G4 buffered (0.50 vs 0.40) as vegetative and bulking stages have some resilience. G1 gap-based because early-establishment doses are small, deficit % not yet meaningful. G5 hard stop for skin cure.

---

## 2. Days-since-irrigation triggers

| Stage | `days_since_last_irrigation` trigger | Action |
|---|:---:|---|
| G1 | ≥ 2 days | Normal irrigation trigger (frequency-based, per D03-WB-001) |
| G2 | ≥ 5 days OR deficit ≥ 35% | Normal irrigation trigger |
| G3 | ≥ 3 days OR deficit ≥ 30% | Important irrigation trigger |
| G4 | ≥ 5 days OR deficit ≥ 35% | Normal irrigation trigger |
| G5 | — (no upper bound; skip irrigation) | No trigger |

**✅ CONFIRMED.**

---

## 3. Rain override

| Parameter | Value |
|---|:---:|
| Rain forecast window | 48 hours |
| Rain amount threshold | ≥ **25 mm** |
| Exclusion stage | G5 (already stopped) |
| Action | Suppress all irrigation triggers for 48h; farmer message "आज सिंचन नको" |

**✅ CONFIRMED.**

Rationale: 25 mm in 48h ≈ full irrigation-event equivalent for G2-G4 stages on vertisol; further irrigation would over-saturate. Below 25 mm treated as supplementary only.

---

## 4. Heat modifier

| Parameter | Value |
|---|:---:|
| Trigger temperature | `air_temp_max_c > 35°C` |
| Applicable stages | G2, G3, G4 (active growth) |
| Dose multiplier | **× 1.15** |
| Urgency bump | +1 tier (normal → important; important → red) |
| Not applicable | G1 (small doses already; heat rare in early season) and G5 (stopped) |

**✅ CONFIRMED.**

Rationale: >35°C in Marathwada correlates with 15-20% higher ETc; matches VNMKV OFT observations at Parbhani. Urgency bump ensures farmer acts same-day rather than deferring.

---

## 5. VWC precedence override (cardinal)

| VWC status | Water-budget signal | Decision |
|---|---|---|
| `saturated` | Any | **VWC wins — do NOT irrigate**, whatever water-budget says |
| `low` | Any | Both signals contribute; BUNDLES precedence |
| `ok` | Deficit | Water-budget fires with normal urgency; message notes VWC ok |
| `ok` | Over-irrigation | Investigation flag (Template 6); no auto-recommendation |

**✅ CONFIRMED.** (Also captured in §5.3 conflict-resolution matrix; repeated here because it overrides all thresholds above.)

---

## 6. Firing gate (applies to all D03-WB rules except WB-006 and WB-008) — v1.1 corrected

```
flow_telemetry_present = TRUE
AND water_budget_confidence >= 0.40           -- admission gate lowered per §8 tier logic
```

**✅ CONFIRMED (v1.1 correction — v1.0 gate was 0.60, contradicting §8's 0.40-0.59 tier; now unified: admission = 0.40, tier-based output above).**

---

## 7. G5 stop rule

| Parameter | Value |
|---|:---:|
| Stage trigger | `stage == 'G5'` (DAP ≥ 210) |
| Action | Suppress all irrigation triggers; emit Marathi Template 8 (काढणीची तयारी) |
| Duration | Until harvest (typically DAP 210-240) |
| Exception | Farmer manual override permitted; system logs but does not push back |

**✅ CONFIRMED.**

Rationale: Skin cure requires 15-20 days without irrigation before harvest; premature harvest with wet skin reduces storage life 30-40%.

---

## 8. Confidence tier behavior (v1.1 unified with §6 gate)

| Condition | System behavior |
|---|---|
| `water_budget_confidence < 0.40` | **Signal dropout** — WB rules do NOT fire (fails §6 admission gate); VWC + weather signals carry recommendation; farmer message tagged "guidance only" |
| `water_budget_confidence 0.40-0.59` | WB rules **DO fire** with `dose_confidence_note = 'moderate'`; recommendations emitted with lower-confidence tag |
| `water_budget_confidence ≥ 0.60` | Full water-budget signal in play; recommendations at full confidence |

**✅ CONFIRMED (v1.1 — logic now consistent between §6 gate and §8 tiers).**

---

## Sign-off

All decision-engine numeric thresholds above are agronomy-confirmed for Season 1 Kannad pilot. Backend may treat these values as authoritative and implement without further clarification.

Any revision post-Season 1 will be driven by empirical calibration from field data (Track D5-D7 per Master Action List).

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

*End of Decision-Engine Thresholds Confirmation v1.0*
