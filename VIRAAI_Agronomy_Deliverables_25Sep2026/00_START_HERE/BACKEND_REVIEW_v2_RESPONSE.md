# Agronomy Response to Backend Review v2 (Paths 1-4)

**Date:** 25 September 2026 (evening)
**From:** Kuldip — Agronomy Compliance Owner
**To:** Backend reviewer + team
**Ref:** Backend review of Paths 1-4 deliverables (25 Sep 2026)
**Status:** All 15 findings across 4 paths accepted; source files patched in place (v1.0 → v1.1). Response summary below.

---

## Overall

Excellent review — 15 legitimate defects caught, several material (would have crashed backend or delivered wrong answers to farmers). All accepted. Source files updated in place; version tags bumped to v1.1 with `v1.1 fix:` markers at each change so backend can diff cleanly.

---

## Path 1 — 4 fixes (files: 1d, 1f, 6b)

| # | Finding | Fix | File |
|:-:|---|---|---|
| P1.1 | §6 gate (0.60) contradicts §8 tier (0.40-0.59 "recommendations still emitted") — §8 was dead code | **Lowered §6 admission gate to 0.40**; §8 tier logic now unified: <0.40 dropout, 0.40-0.59 fires with 'moderate' tag, ≥0.60 full confidence | `1d_DECISION_ENGINE_THRESHOLDS_CONFIRM.md` §6+§8 |
| P1.2 | G3 stage missing Normal tier (had only RED + important) | **Added G3 Normal: deficit ≥ 0.20 OR days_gap ≥ 2** (tighter than G2/G4's 0.35 because G3 is highest sensitivity) | `1d_DECISION_ENGINE_THRESHOLDS_CONFIRM.md` §1 |
| P1.3 | WB-008 resolution hardcodes `bed_center_spacing_cm IS NOT NULL` — furrow farmers would never resolve | **Method-conditional DSL:** `(broad_bed/raised_bed AND bed_center_spacing_cm IS NOT NULL AND rows_per_bed IS NOT NULL) OR (furrow/flat AND furrow_center_spacing_cm IS NOT NULL)` | `1f_D03-WB_DELIVERY_CLASS_TAGGING.md` §D03-WB-008 resolution |
| P1.4 | §4.3 typo — "per-plant × plots_estimated" (would produce drops) | **Corrected to "per-plant × plants_estimated"** with explicit note that `plot_plants_estimated` is the field | `6b_UNITS_CONVENTION_DECISION.md` §4.3 |

**Locked G3 Normal deficit threshold: 0.20** (or `days_gap ≥ 2`). Chose 0.20 because G3 sensitivity means even modest deficit warrants a nudge; matches internal ladder relative to G2/G4 (0.35 Normal / 0.45 Important / 0.50 RED → G3 0.20 / 0.30 / 0.40 pattern).

---

## Path 2 — 6 fixes (files: registry CSV, D08-WD-001)

| # | Finding | Fix | File |
|:-:|---|---|---|
| P2.1 | Line 7 `2,4-D` unquoted → CSV parser splits into 17 fields | **Wrapped in quotes:** `"2,4-D","2,4-D Amine Salt 58 SL"` | `registered_herbicide_registry_ginger_v1.0.csv` line 7 |
| P2.2 | Non-selective grouped with hard-block in pseudocode; taxonomy said pre-plant fallow permit possible | **Split logic:** `L1_nonselective_block` gets separate branch — permit ONLY if `plot_status='pre_planting' AND days_to_planting ≥ 7 AND agronomist_pre_plant_signoff[product]=TRUE`; else in-season hard block | `D08-WD-001_RULE.md` pseudocode + new Template 6 |
| P2.3 | Template 3 "दोस्ती" (friendship) → should be "डोस" (dose) | **Changed to "डोस (प्रमाण)"** — real embarrassing typo, thanks for catching | `D08-WD-001_RULE.md` Template 3 |
| P2.4 | Template 4 "verification आत 3 दिवसांत" awkward | **Changed to "verification पुढील ३ दिवसांत होईल"** | `D08-WD-001_RULE.md` Template 4 |
| P2.5 | Template 5 hardcodes "Kannad-साठी" — breaks scaling | **Made zone-conditional:** `{IF plot.agro_climatic_zone IN ('western_scarcity', 'central_maharashtra') THEN "(पाणी-टंचाईच्या भागात दुहेरी फायदा)"}` — dynamic per farmer's zone | `D08-WD-001_RULE.md` Template 5 |
| P2.6 | Test T4 uses "Hand weeding" but registry has "Manual/Mechanical" | **Split into T4 (exact match "Manual/Mechanical") + T4b (fuzzy match "Hand weeding" → validates fuzzy fallback separately)** | `D08-WD-001_RULE.md` Tests |

---

## Path 3 — 5 fixes (files: variety_N_ceiling CSV, D04-NS-003)

| # | Finding | Fix | File |
|:-:|---|---|---|
| P3.1 | Trigger checked `cumulative > ceiling` — allowed proposal to push cumulative over | **Anticipated-sum check:** `(total_applied + proposed) > ceiling` — T1 now correctly blocks Mahima at 45+20=65 > 61 | `D04-NS-003_RULE.md` Trigger |
| P3.2 | YELLOW check before RED cutoff — post-DAP-150 in G4 would silently downgrade to YELLOW | **Order reversed:** DAP > 150 hard cutoff evaluated FIRST; ceiling breach ELIF second. Added T3b golden test to confirm (post-150 + ceiling breach = still RED) | `D04-NS-003_RULE.md` Action |
| P3.3 | CSV note "baseline + 10% safety margin" contradicts value 61 (exact baseline conversion) | **Removed misleading note.** Ceiling = exact baseline conversion (no margin). If we ever add margin later, it'll be an explicit column with clear math. | `variety_N_ceiling.csv` notes column |
| P3.4 | `block_reason` log missing `proposed_n_application_kg_acre` — confusing when past sum alone < ceiling | **Updated log format:** `f'Cumulative N would reach {total_n_applied + proposed_n} kg/acre (past {total_n_applied} + proposed {proposed_n}); ceiling {ceiling} kg/acre'` | `D04-NS-003_RULE.md` Action |
| P3.5 | Template 1 mixes English "Variety" + "limit" with Marathi | **Changed to native Marathi:** "वाणाचे कमाल प्रमाण" | `D04-NS-003_RULE.md` Template 1 |

---

## Path 4 — 6 fixes (file: B1_VNMKV_LEFTOVER_RULES)

| # | Finding | Fix | File section |
|:-:|---|---|---|
| P4.1 | D06-BW-001 NULL bypass loophole — farmer could ignore soft prompt and plant anyway | **Added Case C:** blocks `pre_planting → planted` state transition when `years_since_last_wilt IS NULL`. Farmer must answer or get agronomist signoff. Added Template 3 for mandatory-capture message + tests T6, T7 | `D06-BW-001` Trigger, Action, Template 3, Tests |
| P4.2 | D01-PW-001 precedence unclear on whether SUPPRESSES requires BLOCK action from BW-001 or any fire | **Clarified:** SUPPRESSES applies only when D06-BW-001 emits **BLOCKING action** (Case A or Case C). Soft prompt (Case B, yellow) does NOT suppress → both rules can co-fire (unknown wilt + late planting = farmer sees both). Backend precedence engine checks emitted severity, not just rule-fired status. | `D01-PW-001` Precedence section |
| P4.3 | Severity map has "≤ 7 June (on-window)" tier but trigger uses `>` (not `>=`) so June 7 exact silently passes | **Clarified:** silent pass IS intended for June 7. Added note: "If backend wants explicit on-window log for audit, add separate silent-guard rule D01-PW-002; not needed for Season 1." | `D01-PW-001` Severity Map |
| P4.4 | D04-MC-004 says COMPLEMENTS D04-MC-003 AND BUNDLES — two different types | **Split into 3 distinct cases with formal precedence types:**<br>• Soil test + Zn adequate → **SUPPRESSES**<br>• Soil test + Zn deficient → **BUNDLES**<br>• No soil test + Kannad zone → D04-MC-004 fires alone<br>"COMPLEMENTS" removed (not a formal precedence type). | `D04-MC-004` Precedence section |
| P4.5 | Test T5 said "D04-MC-003 SUPPRESSES D04-MC-004" but precedence declared BUNDLES — test-vs-declaration mismatch | **Fixed with restructured precedence:** T5 now correctly reflects SUPPRESSES for adequate-soil case; added T5b for deficient-soil BUNDLES case | `D04-MC-004` Tests + Precedence |
| P4.6 | Resolution threshold ≥ 8 kg treats 5 kg as silently "unresolved" — farmer applying half-dose gets no feedback | **Three-tier resolution:** ≥9 kg FULLY RESOLVED; 5-8 kg PARTIAL (fires WARNING to top up); <5 kg or NULL UNRESOLVED (recommendation re-fires weekly). Added T3b for full-resolution case. | `D04-MC-004` Delivery class + Tests |

---

## Summary count

- **Total findings addressed:** 15
- **Material defects (would break backend or mislead farmers):** 7 (P1.1, P1.3, P1.4, P2.1, P2.2, P3.1, P3.2, P4.1)
- **Marathi/UX defects:** 4 (P2.3, P2.4, P2.5, P3.5)
- **Documentation/precedence clarity:** 4 (P1.2, P4.2, P4.3, P4.4, P4.5, P4.6, P3.3, P3.4)

- **Files updated in place (v1.0 → v1.1):** 7
  - `1d_DECISION_ENGINE_THRESHOLDS_CONFIRM.md`
  - `1f_D03-WB_DELIVERY_CLASS_TAGGING.md`
  - `6b_UNITS_CONVENTION_DECISION.md`
  - `registered_herbicide_registry_ginger_v1.0.csv`
  - `D08-WD-001_RULE.md`
  - `variety_N_ceiling.csv`
  - `D04-NS-003_RULE.md`
  - `B1_VNMKV_LEFTOVER_RULES.md` (Path 4 — three rules updated)

---

## Locked decisions requiring no further review

- **G3 Normal deficit threshold: 0.20** (or `days_gap ≥ 2`)
- **Confidence admission gate: 0.40** (with tier-based output above; ≥0.60 = full confidence)
- **N ceiling values: exact baseline conversion** (no safety margin) — Mahima 61, Varada 55, Nadia 52 kg/acre
- **D04-MC-004 partial-dose warning tier: 5-8 kg/acre range** triggers top-up warning
- **D06-BW-001 Case C:** plot-status transition to 'planted' blocked when `years_since_last_wilt IS NULL`

---

## Sign-off

Reviewer's technical depth caught defects a single-author review would have missed. This is exactly the AI-to-AI cross-validation model working as intended for a farmer-safety-critical system. All 15 findings applied; files ready for backend integration.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026, 20:00 IST

*End of Backend Review v2 Response*
