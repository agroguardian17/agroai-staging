# Agronomy Decisions — Response to KB Reconciliation Memo (26 Sep) + System Overview

**Date:** 26 September 2026 (evening)
**From:** Kuldip — Agronomy Compliance Owner
**To:** Backend team
**Ref:** `KB Reconciliation Memo — 25-Sep Agronomy Bundle vs Deployed Ginger KB`; `AgroGuardian Backend — System Overview for the Agronomy Team`
**Status:** All 6 decisions answered inline. Own drift also acknowledged (§8 below) with fix commitment.

---

## 0. Overall — grateful acknowledgement

The System Overview is exactly the ground truth I was authoring blind against. Everything in the 25-Sep bundle was written against an **assumed** schema (single soil field, L1-L4 tier system, `compliance_tag` on rules, DATE literals in DSL, FEEDS as a formal precedence type). The reconciliation memo maps the drift honestly rather than reject-and-return. This is exactly the AI-to-AI cross-validation model working — thank you.

**Two categories of response below:**
- **§1-6:** my decisions on the 6 questions raised in the memo
- **§7-8:** additional drift I now realize I introduced (severity vocabulary, source tier, precedence types, confidence threshold, push notifications) — with fix commitments

Data layer (three CSVs merged) — no action needed from my side, acknowledged deployed.

---

## 1. Decision D1 — Soil vocabulary

**Answer: (a) MAP the bundle's classes onto deployed `soil_type='vertisol'` + `soil_texture_class='heavy'`. Season 1 scope only.**

**Bundle → deployed mapping:**

| Bundle class | Deployed representation | Rationale |
|---|---|---|
| `vertisol` | `soil_type = 'vertisol'` | Direct match; already in soil_type enum |
| `heavy_clay` | `soil_texture_class = 'heavy'` | USDA-triangle class; distinct from soil-type morphology |
| `clay_loam_heavy` | `soil_texture_class = 'heavy'` (approximated) | Same tier for Season 1 purposes; refinement Season 2 |
| `sandy_loam` | `soil_type = 'sandy_loam'` OR `soil_texture_class = 'light'` | Depends on rule's semantic intent; case-by-case |
| `clay_loam` | `soil_texture_class = 'medium'` | Middle tier |

**Rule-by-rule application of the mapping:**

- **D03-DS-001:** trigger uses `soil_texture_class IN ('heavy_clay', 'vertisol', 'clay_loam_heavy')` — reduce to `soil_texture_class == 'heavy'` (matches deployed vocabulary; conservative — fires only on lab-confirmed heavy texture)
- **D02-LY-001, D08-LY-001:** trigger already uses `soil_type == 'vertisol'` (deployed vocabulary aligned)
- **D02-DR-004:** trigger's `soil_texture_class IN ('heavy_clay', 'vertisol', 'clay_loam_heavy')` → `soil_type = 'vertisol' OR soil_texture_class = 'heavy'` (union — catches both known-vertisol and lab-confirmed-heavy paths)
- **D02-ST-002 (lab reclassification):** deployed has percolation_class / bed_height_cm as soil fields, NOT sand/silt/clay % — so re-author the lab reclassification rule against `lab_soil_tests.percolation_class` field. I'll rework the rule spec accordingly (§8 commitment).

**Season 2 review:** if 5-class vocabulary would materially improve firing precision on non-Kannad expansion, revisit then with schema migration plan. Season 1 keeps existing vocabulary.

---

## 2. Decision D2 — `compliance_tag`

**Answer: KEEP compliance tags in the tracker only; NO KB schema change.**

**Rationale:**
- KB carries `review.outcome` + `status` (AGRONOMIST_REVIEWED, PHASE_1_RAW_UNVALIDATED, AUTHOR_DRAFT) which capture what compliance status means at runtime
- COMPLIANT / NON_COMPLIANT / CONDITIONAL / AGRO_GUARDIAN_CUSTOM / AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE is a **governance / audit-trail** concept; not needed by the engine at fire time
- No KB migration = no risk to Season 1 launch
- Compliance tracker (`review_tracker_ALL_completed_v1.xlsx` from earlier session work) is the authoritative source; A5 retags apply there

**Action for A5 retags — tracker-only:**
- D08-EU-002 → CONDITIONAL (tracker only)
- D08-LY-001 → CONDITIONAL (tracker only; already intent-met in deployed KB)
- D14-SR-002 → AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE (tracker only)
- D03-WL-003 → AGRO_GUARDIAN_CUSTOM (tracker only)
- D07-CY-001 → AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE (tracker only)

No KB PR needed for any of these.

---

## 3. Decision D3 — ZnSO₄ rule id

**Answer: YES, use `D04-MC-005` for the basal ZnSO₄ rule.**

Existing `D04-MC-004` (heat/rain foliar spray) is legit and should not be overwritten. Bundle's B1_VNMKV_LEFTOVER_RULES.md will be re-tagged D04-MC-005 in the fix pack (§8).

**Precedence relations for D04-MC-005 remain:**
- SUPPRESSES D04-MC-005 (self) when soil test confirms Zn ≥ 0.6 ppm
- BUNDLES with D04-MC-003 (the existing conditional Zn rule) when both fire on unknown soil-test status
- SEQUENCES D04-NS-003 (unaffected — basal at DAP 0)

---

## 4. Decision D4 — D01-PW-001 date-literal

**Answer: (b) Add derived field `planting_doy` (integer, day-of-year 1-366).**

**Rationale:**
- MONTH IN [JUN, JUL] is coarse and misses the agronomic distinction between early-June and late-June planting
- Building full DATE-literal DSL support is a large parser change for one rule
- `planting_doy` is a cheap derived field (mapper computes from `plots.planting_date`); reusable by any future rule needing a day-precision date comparison

**Rewritten trigger:**
```
crop = 'ginger'
AND planting_doy IS NOT NULL
AND planting_doy > 158           -- June 7 = DOY 158 (non-leap year)
```

Leap-year handling: 2028 leap year DOY 158 = June 6 (one day off). Acceptable variance for Season 1-2; if precision matters more later, add `planting_doy_leap_adjusted` derived field.

**New field for backend to add to `_schema`:**
```
planting_doy:
  type: int
  derived: true
  source: "extract(doy from plots.planting_date)"
  nullable: true
  range: [1, 366]
```

---

## 5. Decision D5 — D04-NS-003 N-timing field model

**Answer: YES — redesign to use cumulative-N ledger + variety_n_ceiling lookup, replacing the deployed `dap>80 AND n_applied_kg_per_acre IS NOT NULL` trigger.**

**Rationale:**
- Deployed trigger is too broad — fires on any post-DAP-80 N application regardless of amount or variety
- New model (anticipated-sum vs variety ceiling) is precise + variety-aware + gives farmer actionable dose feedback
- `variety_n_ceiling` table is already seeded (migration 0052)

**Field reconciliation for backend:**

| Bundle field | Preferred deployed name | Type | Source |
|---|---|---|---|
| `total_n_kg_acre_applied_since_dap_0` | rename to `n_applied_kg_per_acre_cumulative` (aligns with existing `n_applied_kg_per_acre` naming pattern) | numeric | derived: `SUM(n_events.kg_per_acre) OVER (plot_id, dap >= 0)` |
| `proposed_n_application_kg_acre` | `n_proposed_kg_per_acre` (mirror existing pattern) | numeric | from advisory queue or farmer scouting form |
| (existing) `n_applied_kg_per_acre` | RETAIN — this is the per-event value | numeric | existing |

**Rewritten trigger (aligned to deployed vocabulary):**
```
crop = 'ginger'
AND stage IN ('G3', 'G4')
AND n_proposed_kg_per_acre > 0
AND (
    (n_applied_kg_per_acre_cumulative + n_proposed_kg_per_acre) > variety_n_ceiling_kg_per_acre
    OR (stage == 'G4' AND dap > 150)     -- hard cutoff
)
```

`variety_n_ceiling_kg_per_acre` is a lookup from the `variety_n_ceiling` table (migration 0052) via the mapper.

---

## 6. Decision D6 — Field reconciliation (wilt history)

**Answer: `years_since_last_wilt` is ADDITIVE, not a replacement — coexists with existing `field_history_wilt` and `previous_crops_3yr` fields.**

**Rationale:**
- Existing fields likely capture: `field_history_wilt` (boolean or categorical: yes/no/unknown), `previous_crops_3yr` (list of prior crops for rotation compliance)
- New `years_since_last_wilt` captures **precision** (integer years) needed for the 5-year rotation gate
- Farmer capture question: *"या शेतात कधी बॅक्टेरियल-मर आली होती का? असल्यास किती वर्षांपूर्वी?"* — sets `field_history_wilt = 'yes'` AND `years_since_last_wilt = <int>` in one interaction
- If farmer says "no" → `field_history_wilt = 'no'` AND `years_since_last_wilt = NULL_NEVER` (sentinel; distinct from `NULL_UNKNOWN`)
- Backend can preserve `previous_crops_3yr` for existing use cases (D08 rotation rules, etc.)

**Backend to confirm:** existing type of `field_history_wilt` (bool vs categorical). If bool, `years_since_last_wilt` is a companion; if already integer years, alias to unified name.

**Rule access pattern (unchanged conceptually):**
- D06-BW-001 reads `years_since_last_wilt` for the 5-year rotation gate
- Other D06 or D08 rules can continue reading `field_history_wilt` / `previous_crops_3yr` unchanged

---

## 7. Additional decisions inferred from System Overview (not in memo but material)

Reading the System Overview surfaced these follow-on questions I should answer while at it:

**D7 — `push_notification = TRUE` in bundle's D03-WB-002 (red urgency)**
System Overview §6.5: "No urgency tiers, no push. Every advisory goes out identically (one WhatsApp template), regardless of severity/confidence."

**Answer:** Retract the `push_notification = TRUE` flag from D03-WB-002 spec. All water-budget red-urgency messages currently go through the same daily-composed WhatsApp path as any other advisory. Farmer sees "urgency = red" in message content but no push priority elevation until push tiers land. Update rule spec accordingly.

**D8 — `urgency` field in bundle**
Bundle used `urgency = 'normal' / 'important' / 'red'`. Deployed severity enum: **info / yellow / red / blocking** (only 4 values).

**Answer:** Retire `urgency` as a separate field. Map bundle values:
- `normal` → deployed severity `info` or `yellow` (per context)
- `important` → `yellow` (with higher priority number for message ordering)
- `red` → `red`
- Blocking rules use `blocking` severity, not `urgency='red' + block_flag`

Sort order in message-composition is `(severity_rank, -priority)` per System Overview §5.2. Bundle's urgency tiers get expressed via `severity` + `priority` (integer for tie-break).

---

## 8. My own drift — acknowledged with fix commitments

Beyond the 6 memo questions, System Overview reveals **5 additional drift patterns I introduced** that need cleanup across the 25-Sep bundle:

| # | Drift I introduced | Where it appears | Fix commitment |
|:-:|---|---|---|
| **DR1** | Used `FEEDS` as a formal precedence relation | D03-ST-001, D02-ST-002, D08-EU-002 (feeds D11), D03-WB-005, several others | Retract. Deployed uses only 5 formal types (SUPPRESSES/SUPERSEDES/BUNDLES/SEQUENCES/ESCALATES); yield-model feeding is via the yield pipeline (System Overview §7), not precedence. Rules re-authored to drop FEEDS clauses; D11 factor-7 mapping happens via `yield_u_values.representative_rule_id` reference, not a precedence edge. |
| **DR2** | Used L1/L2/L3/L4 source tiers | Every rule's basis section; variety CSVs | Retract. Deployed uses `source_class ∈ {A, B, C}` (plus EST, VERIFY, FIELD). Mapping:<br>• L1 (institutional/regulatory) → **A**<br>• L2 (peer-reviewed) → **A** or **B**<br>• L3 (VNMKV/local OFT) → **B**<br>• L4 (VIRAAI-derived) → **C** or **EST**<br>All 25-Sep rule bodies to be re-tagged with A/B/C source_class. |
| **DR3** | Used `urgency = 'important'` as a distinct severity tier | D03-WB advisories, D01-PH-004, D04-NS-003, several templates | Retract. Deployed severity is 4-value strict: info / yellow / red / blocking. Mapping: `important` → **yellow with higher priority integer**. Message templates keep "important"/"urgent" as farmer-facing language, but the severity field takes only the 4 legal values. |
| **DR4** | Confidence gate `>= 0.60` (later revised to 0.40) for D03-WB rules | 1d, 1f, D03-WB rules body | Retract both my numbers. Deployed engine uses `<0.72` as the "guidance only" note threshold (System Overview §5.6); UNKNOWN inputs never fire (three-valued logic already handles absence). No separate "admission gate" needed — rules simply return UNKNOWN when inputs are missing. Water-budget rules to be re-authored without confidence-gate DSL clauses; the engine's own three-valued logic + guidance-only tag handles it. |
| **DR5** | `push_notification = TRUE`, `agronomist_pre_plant_signoff[product] = TRUE`, other aspirational flags in pseudocode | D03-WB-002, D08-WD-001 non-selective branch, D06-BW-001 override | Retract per System Overview §6.5 ("NOT implemented yet"). Farmer-override flags remain in spec-as-intent but not in deployable trigger DSL. Backend implements when the feature ships. |

**Fix pack commitment:** I will produce **`AGRONOMY_BUNDLE_v1.2_DEPLOYED_ALIGNED.zip`** containing all 25-Sep authored rules re-expressed against actual deployed vocabulary. Target: **28 September 2026 EOD**. This unblocks the "PENDING-CLEAN KB PRs" cluster in memo §6 without further schema/vocab decisions from Kuldip.

---

## 9. Path forward — accepting memo §6 cluster order

Backend's proposed rollout is agronomically sound:

**Cluster 1 (tracker-only, no code):** A5 retags — D08-EU-002, D08-LY-001, D14-SR-002, D03-WL-003, D07-CY-001. Approved to proceed immediately.

**Cluster 2 (PENDING-CLEAN KB PRs, after v1.2 fix pack lands 28 Sep):** D01-PH-004, D03-SB-003, D02-LY-001 trigger authoring, D08-WD-001 registry-driven, D06-BW-001 (after wilt field reconcile). Approved.

**Cluster 3 (after D1 soil vocab mapping locked):** D03-DS-001, D02-DR-004, D02-ST-002 (needs re-author against percolation_class), D03-WL-003 trigger difference to review. My D1 answer above locks the mapping; proceed.

**Cluster 4 (after D3):** D04-MC-005 ZnSO₄ (renumbered). Approved.

**Cluster 5 (after D4):** D01-PW-001 with `planting_doy > 158` trigger. Approved once `planting_doy` derived field ships.

**Cluster 6 (after hardware):** 8 D03-WB rules + D03-ST-001. Confidence gate DSL clause removed per DR4; three-valued logic + guidance-only tag handles it.

---

## 10. Kannad pilot geometry data (my earlier commitment)

System Overview §4.1 confirms `plots` table already carries the fields I need to enter: polygon (plot_polygon_wkt), area_acre, dripper_lph, has_drip. I'll enter my Kannad plot's data directly via the farmer-app plot-setup flow once I confirm login credentials with your side. Original 10-Oct deadline holds.

---

## 11. What I still need from backend (§9 acknowledgement handoff)

- ✅ Approval of D1-D6 answers above (or counter-proposals)
- ✅ Confirmation that DR1-DR5 drift-fixes in §8 are correct interpretations of the System Overview
- ⏳ **`firing_intent_diagnostic_rules.xlsx`** (or equivalent) for the 42 field-dependent rules — this is the sole remaining sheet I need to complete Track A2. Same ask as `5B_PENDING_BACKEND_ASK.md` in the 25-Sep bundle.
- ⏳ Existing type of `field_history_wilt` (boolean vs integer years) for D6 finalization

---

## 12. Sign-off

The reconciliation memo + System Overview together are exactly the reference material that would have prevented every vocabulary/schema drift the 25-Sep bundle introduced. Publishing the System Overview to the agronomy team as a standing artifact would prevent recurrence for Season 2 rule authoring. Recommend it becomes part of the standard onboarding pack for any future agronomist joining VIRAAI.

All 6 decisions answered. 5 drift-patterns acknowledged with fix pack committed for 28 Sep. Ready to proceed on cluster 1 tracker-only edits immediately; cluster 2 onwards after fix-pack lands.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
26 September 2026

*End of Agronomy Decisions v1.0*
