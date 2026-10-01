# Agronomy Bundle v1.2 — Deployed-Aligned Fix Pack

**Date:** 28 September 2026
**From:** Kuldip — Agronomy Compliance Owner
**To:** Backend team
**Ref:** AGRONOMY_DECISIONS_v1.md §8 (26-Sep drift acknowledgement); KB Reconciliation Memo (26-Sep); System Overview (26-Sep)
**Status:** Delta patches to 25-Sep bundle rules — apply to unblock "PENDING-CLEAN KB PRs" per reconciliation memo §6 cluster 2 & 3.
**Format:** per-rule deltas showing old→new for each drift pattern. Backend applies to live rule definitions rather than replacing whole files.

---

## Global find/replace rules (apply everywhere)

Before per-rule patches, four global substitutions apply across every rule spec in the 25-Sep bundle:

### G1. Source tier: L1-L4 → A/B/C

| Old (25-Sep) | New (deployed) |
|---|---|
| `L1` (institutional/regulatory) | `A` |
| `L2` (peer-reviewed) | `A` or `B` (peer-reviewed institutional = A; other = B) |
| `L3` (VNMKV / local OFT) | `B` |
| `L4` (VIRAAI-derived) | `C` or `EST` (VIRAAI-derived from L2/L3 basis = C; extrapolated placeholders = EST) |

### G2. Severity: 5-value → strict 4-value

| Old (25-Sep) | New (deployed) |
|---|---|
| `info` | `info` (unchanged) |
| `normal` | `info` |
| `important` | `yellow` (with higher priority integer for message-sort) |
| `yellow` | `yellow` (unchanged) |
| `red` | `red` (unchanged) |
| `blocking` | `blocking` (unchanged) |

`urgency` field retired everywhere. Priority integer added to severity when tie-break needed.

### G3. Precedence relation: FEEDS/INFORMS removed

Every `X FEEDS Y` or `X INFORMS Y` declaration in the 25-Sep bundle is removed. Deployed KB has only 5 formal relations: SUPPRESSES, SUPERSEDES, BUNDLES, SEQUENCES, ESCALATES.

**Where I used FEEDS to feed the D11 yield model:** the actual mechanism is `yield_u_values.representative_rule_id` mapping (System Overview §7.2), not a precedence edge. Backend maps the rule ID directly in the yield-pipeline config; no KB precedence declaration needed.

### G4. Aspirational-feature flags removed

Every `push_notification = TRUE`, `agronomist_pre_plant_signoff[product] = TRUE`, `farmer_override_permitted = TRUE/FALSE` flag is removed from trigger DSL. These features are not implemented yet (System Overview §6.5). Retained as intent-notes in comments/basis prose only; not in triggers or actions the engine parses.

### G5. compliance_tag → tracker-only

`compliance_tag: COMPLIANT/CONDITIONAL/AGRO_GUARDIAN_CUSTOM(_OPERATIONAL_RULE)` — remove from rule JSON. Track only in `review_tracker_ALL_completed_v1.xlsx`. KB uses `review.outcome` + `status` (AGRONOMIST_REVIEWED, etc.) as it always has.

---

## Per-file fix deltas

### File 1: `01_WATER_BUDGET_CORE/1d_DECISION_ENGINE_THRESHOLDS_CONFIRM.md`

**Drift fixes:**

| Section | Old | New | Rationale |
|---|---|---|---|
| §6 Firing gate | `flow_telemetry_present = TRUE AND water_budget_confidence >= 0.40` | **Removed entirely** — no firing gate DSL clause; three-valued logic handles missing inputs (they evaluate UNKNOWN, don't fire) | Deployed engine per System Overview §5.6 uses `<0.72` as "guidance only" note threshold; no admission gate |
| §8 Confidence tier behavior | 3-tier admission/moderate/full | **Simplified to 2 states:** `<0.72` = engine tags "guidance only" in farmer message; `>=0.72` = normal message. No rule-level DSL gating. | Aligns with deployed §5.6 |
| Various | `urgency = 'important'` | `severity = 'yellow' + priority_int` | G2 |

**Kept:** all numeric deficit/gap/rain/heat thresholds (they're agronomic content, not vocabulary).

---

### File 2: `01_WATER_BUDGET_CORE/1f_D03-WB_DELIVERY_CLASS_TAGGING.md`

**Drift fixes:**

| Item | Old | New |
|---|---|---|
| D03-WB-002 | `push_notification = TRUE` on RED urgency | **Removed** — no push notification field until feature ships (System Overview §6.5). Message goes out via standard daily-composed WhatsApp path. |
| ONCE_UNTIL_RESOLVED ladder | Frequency-based reminder pattern | **Corrected:** deployed ladder is (0, 7, 21, 45, 90) days RAISING SEVERITY not frequency (System Overview §5.4). |
| Any WINDOW rule reminder count | Not specified | Deployed default: WINDOW = up to 3 spaced overdue reminders (§5.4). |

**Kept:** all delivery-class assignments (SILENT_GUARD, EVENT, ONCE_UNTIL_RESOLVED, WINDOW mappings correct as-authored).

---

### File 3: `01_WATER_BUDGET_CORE/D03_WATER_BUDGET_RULES.md` (8 D03-WB rules)

**Global changes (all 8 rules):**

| Old | New |
|---|---|
| Trigger prefix `flow_telemetry_present = TRUE AND water_budget_confidence >= 0.60` | **Removed** — engine's three-valued logic on `plot_total_flow_L_per_event IS NULL` handles absence automatically |
| Precedence `FEEDS D11-YM-*` (WB-005) | Removed — D11 factor mapping via `yield_u_values.representative_rule_id` per System Overview §7.2 |
| `contributing_signals` list in action | Retained as evidence metadata; not treated as precedence edge |
| `urgency` field | Removed everywhere; use `severity` (info/yellow/red/blocking) only |
| `push_notification = TRUE` on WB-002 red | Removed (§6.5) |

**Per-rule severity mappings:**

| Rule | Old severity | New severity |
|---|:---:|:---:|
| D03-WB-001 | `yellow` (normal) | `yellow` |
| D03-WB-002 | `red` (with important-tier language) | `red` (priority=90) |
| D03-WB-003 | `yellow` | `yellow` |
| D03-WB-004 | `yellow` | `yellow` |
| D03-WB-005 | `INFO` (silent guard) | `info` |
| D03-WB-006 | `red` | `red` (priority=95 — hardware alert) |
| D03-WB-007 | `important` | `yellow` (priority=80) |
| D03-WB-008 | `blocking` | `blocking` |

**Precedence retained (all use formal types):** all SUPPRESSES / BUNDLES / SEQUENCES / ESCALATES declarations from v1.1 unchanged.

**Note:** all 8 rules remain gated on hardware — flow-telemetry field must land in `node_sensor_readings` before any wire; keep in reconciliation-memo cluster 6.

---

### File 4: `01_WATER_BUDGET_CORE/D03-ST-001_RULE.md`

**Drift fixes:**

| Item | Old | New |
|---|---|---|
| Trigger prefix `flow_telemetry_present = TRUE AND water_budget_confidence >= 0.60` | **Removed** — three-valued logic handles it |
| Precedence `FEEDS D11-YM-007` | Removed. Instead: backend adds row to `yield_u_values` table: `factor_key='drought_fill_G3G4', representative_rule_id='D03-ST-001'` (System Overview §7.2). This is the actual mechanism. |
| Basis `L3 + L4` source tier | `B` (VNMKV OFT basis) + `EST` (drought-loss extrapolation) per G1 |
| `compliance_tag: COMPLIANT` | Removed from rule JSON; tracker-only per G5 |

**Kept:** all agronomic content — deficit_ratio formula, DAP>60 threshold, G3-G4 aggregation window, Kannad note.

---

### File 5: `01_WATER_BUDGET_CORE/MARATHI_ADVISORY_TEMPLATES.md`

**Drift fixes:**

| Item | Old | New |
|---|---|---|
| Template 3 (RED urgency): "लाल इशारा" | Retained (Marathi language for farmer clarity — not the severity enum) |
| Templates referencing urgency tiers | Retained in farmer-facing prose; not in engine severity field |
| `push_notification: TRUE` metadata | Removed from template metadata |

**Note:** deployed default template is `agroguardian_advisory_v2` with single `{{1}}` body param (System Overview §6.4). My 10 templates are content-only; backend fits each into that template pattern with disclaimer appended. No per-severity WhatsApp template variants (System Overview §6.5).

---

### File 6: `02_HERBICIDE_GATE/D08-WD-001_RULE.md`

**Drift fixes:**

| Item | Old | New |
|---|---|---|
| `compliance_tag: COMPLIANT` | Removed per G5 |
| Basis source tiers L1/L2/L3/L4 across 13 registry entries | Map to A/B/C per G1 (also apply to `registered_herbicide_registry_ginger_v1.0.csv` — see File 12) |
| Pseudocode `agronomist_pre_plant_signoff[product] = TRUE` | Retained as intent-note in basis; removed from DSL — replaced by manual agronomist override via ops channel (until feature ships) |
| Pseudocode `farmer_override_permitted = FALSE` for hard blocks | Removed as DSL flag (§6.5). Hard-block behavior encoded via `severity: blocking`; deployed engine treats blocking as farmer-cannot-override by default per System Overview §5.5. |

**Kept:** positive-list gate logic, 6 compliance tiers (naming stays; they're logical categories not KB tags), all 6 Marathi templates including Template 6 pre-plant permit.

---

### File 7: `03_N_TIMING_GATE/D04-NS-003_RULE.md`

**Drift fixes:**

| Item | Old | New |
|---|---|---|
| Field name `total_n_kg_acre_applied_since_dap_0` | `n_applied_kg_per_acre_cumulative` (D5 answer, deployed naming pattern) |
| Field name `proposed_n_application_kg_acre` | `n_proposed_kg_per_acre` (D5 answer) |
| `compliance_tag: COMPLIANT` | Removed per G5 |
| Basis `L3 + L4` | `B` (VNMKV) + `C` (VIRAAI-derived variety ratios) |
| Aspirational: `farmer_override_permitted = TRUE`, agronomist notification workflow | Removed from DSL; retained in basis prose as intent |

**Kept:** anticipated-sum trigger logic, RED-first evaluation order, hard cutoff DAP 150, variety ceiling lookup — all agronomic corrections from v1.1 review unaffected.

---

### File 8: `03_N_TIMING_GATE/variety_N_ceiling.csv` — **RE-ISSUED (see file 12 below)**

---

### File 9: `04_VNMKV_LEFTOVERS/B1_VNMKV_LEFTOVER_RULES.md`

**Per-rule fixes:**

**D06-BW-001:**
- `compliance_tag: COMPLIANT` → removed (G5)
- Basis: L3 → **B** (VNMKV cert §5)
- Field: `years_since_last_wilt` → **kept as-is** (per KB memo D6 confirmed: additive int companion to existing `field_history_wilt` boolean on `crop_seasons`)
- Aspirational: `agronomist_override_signed` → moved to basis as intent-note; removed from DSL

**D01-PW-001:**
- Trigger: `planting_date > DATE(season_start_year || '-06-07')` → **`planting_doy > 158`** (D4 answer, per firing-intent sheet confirmation that `planting_doy` derived int is added; June 7 = DOY 158)
- No DATE literal or `||` in DSL (deployed grammar doesn't support them)

**D04-MC-004 → D04-MC-005 (RENAMED per D3):**
- All references to `D04-MC-004` in this file for the ZnSO₄ rule → **`D04-MC-005`**
- Precedence relations updated: `D04-MC-005 SUPPRESSES D04-MC-005` (self-suppresses on adequate soil-test); `D04-MC-003 BUNDLES D04-MC-005` (both fire on deficient soil-test)
- `compliance_tag` removed (G5)
- Basis: L3 → **B**
- Field `agro_climatic_zone` — kept, backend to source from Maharashtra agro-climatic zones GIS layer (or farmer-declared enum fallback)

---

### File 10: `05_FIRING_INTENT_READY/5A_FIRING_INTENT_READY_RULES.md`

**Superseded by:** `BATCH1_5_READY_RULES_CONFIRMATIONS.md` v1.1 (27-Sep, held #1 + held #2 fixes already applied). The 5-A file is now historical reference only; use the newer file for wiring.

Deltas applied in the newer file (v1.1 patch already delivered):
- D02-LY-001 split into D02-LY-001 (blocking retained) + D02-LY-002 (yellow prompt new)
- D03-SB-003 uses new `previous_stage` derived field with defensive NULL guard
- All severity/source-tier/precedence corrections applied

---

### File 11: `06_TRACK_A5_REWRITES/TRACK_A5_REMAINING_6_REWRITES.md`

**Per-rule fixes:**

**D03-DS-001 (A5.2):**
- Trigger: `soil_texture_class IN ('heavy_clay', 'vertisol', 'clay_loam_heavy')` → **`soil_texture_class == 'heavy'`** (D1 answer — deployed uses 3-value enum heavy/medium/light)
- `emitter_pattern != 'inline_pressure_compensated'` clause → keep, but backend to declare `emitter_pattern` field in `_schema` before parse (or drop this clause if not in scope Season 1)
- `compliance_tag` removed (G5)

**D08-EU-002 (A5.3):**
- `compliance_tag: CONDITIONAL` → removed (G5); tracker retag only
- `yield_impact: 'variable_10_to_15_pct_range'` → retained as message content; removed as separate DSL field
- Precedence `FEEDS D11-YM-*` → removed; D11 mapping via `yield_u_values` config
- Basis: L3 → **B**

**D08-LY-001 (A5.4):**
- Backend memo confirms deployed intent already matches ("DONE-ish; 3-tier is optional enhancement"). 3-tier context advisory (strong/moderate/marginal) can be deferred to Season 2 as authored `D08-LY-002`, `D08-LY-003` if backend prefers not to overwrite the existing single-tier rule. Recommend: **keep deployed as-is; author 3-tier version as Season 2 enhancement** — no v1.2 change needed.
- `compliance_tag` removed (G5); tracker retag only

**D14-SR-002 (A5.6), D03-WL-003 (A5.7), D07-CY-001 (A5.8):**
- All three: `compliance_tag` retag → **tracker-only** per G5 (backend memo confirms "DONE — tracker retag")
- No KB rule change; no DSL edit; no golden-test change

---

### File 12: `03_N_TIMING_GATE/variety_N_ceiling.csv` — RE-ISSUED with A/B/C source_class

Full file re-issue (short — 3 data rows):

```csv
variety,total_n_ceiling_kg_per_acre,total_n_baseline_kg_per_ha,basal_dap_0_kg_per_acre,top_dress_45_dap_kg_per_acre,top_dress_120_dap_kg_per_acre,late_stage_n_cutoff_dap,g3_g4_excess_pct_threshold,source_class,notes
IISR-Mahima,61,150,24,20,17,150,0.00,B,"VNMKV Package of Practices baseline 150 kg/ha = 60.7 kg/acre (rounded 61). Ceiling = exact baseline conversion, NO safety margin. v1.2 fix: source_class L3 → B per deployed vocabulary."
IISR-Varada,55,135,22,18,15,150,0.00,C,"VIRAAI-derived: Mahima baseline × 0.90. v1.2 fix: source_class L4 → C per deployed vocabulary."
Nadia-local,52,128,21,17,14,150,0.00,C,"VIRAAI-derived: Mahima baseline × 0.85. v1.2 fix: source_class L4 → C per deployed vocabulary."
```

**Note:** `variety_stage_water_target.csv` (0051 migration, merged already) — same fix needed for its `source_tier` column: L3→B for all rows. Backend applies inline; agronomy signs off.

---

## Data-tier update — `variety_stage_water_target.csv`

The 0051-merged CSV has `source_tier` column set to `L3` across all rows. **Update inline to `B`** — same tier, deployed vocabulary. Also for `registered_herbicide_registry_ginger_v1.0.csv` (0053), `compliance_tier` column stays as-is (those are logical categories `L1_recommended_practice`, `L1_hard_block`, etc. — internal naming for gate logic, not deployed KB source tiers).

---

## Applied 6 decisions from AGRONOMY_DECISIONS_v1.md — inline confirmation

| # | Decision | Applied where |
|:-:|---|---|
| D1 | Soil vocab map | File 11 (D03-DS-001 trigger), Files 1/3 (any water-budget rules referencing soil texture) |
| D2 | compliance_tag tracker-only | All files — G5 global |
| D3 | ZnSO₄ id D04-MC-005 | File 9 (B1_VNMKV_LEFTOVER_RULES) |
| D4 | planting_doy > 158 (not DATE literal) | File 9 (D01-PW-001) |
| D5 | Cumulative-N ledger field renames | File 7 (D04-NS-003) |
| D6 | years_since_last_wilt additive to field_history_wilt | File 9 (D06-BW-001) — confirmed unchanged from v1.1 |

---

## Applied 5 drift patterns from AGRONOMY_DECISIONS_v1.md §8 — inline confirmation

| # | Drift | Applied where |
|:-:|---|---|
| DR1 | FEEDS precedence removed | Files 4 (D03-ST-001), 3 (D03-WB-005), 11 (D08-EU-002) — all replaced with `yield_u_values` config mechanism |
| DR2 | L1-L4 → A/B/C | G1 global; File 12 CSV re-issued |
| DR3 | 'important' severity → yellow+priority | G2 global |
| DR4 | Confidence gate ≥0.60 removed | Files 1, 3, 4 — replaced with engine's `<0.72` guidance-only note |
| DR5 | push_notification/agronomist_signoff/farmer_override flags removed | Files 2 (D03-WB-002), 6 (D08-WD-001), 9 (D06-BW-001), 7 (D04-NS-003) |

---

## Backend integration checklist

Per reconciliation memo §6 cluster 2 & 3 rollout order:

**Cluster 2 (PENDING-CLEAN, dependency-free):**
- [ ] Apply File 11 D03-DS-001 trigger fix (soil vocab)
- [ ] Apply File 9 D06-BW-001 (Case C NULL bypass + basis prose)
- [ ] Apply File 9 D01-PW-001 (with new `planting_doy` derived field)
- [ ] Apply File 9 D04-MC-005 (renamed from D04-MC-004; new derived field `agro_climatic_zone`)
- [ ] Apply File 7 D04-NS-003 (with N-field renames)
- [ ] Apply File 6 D08-WD-001 (drift fixes; registry data-tier update inline)

**Cluster 3 (after D1 soil vocab lock — this fix pack IS the D1 lock):**
- [ ] Apply File 11 D02-DR-004, D02-ST-002 (via Batch 1 already wired), D03-WL-003 trigger reconcile

**Cluster 1 (tracker-only, no code):**
- [ ] Confirm A5 retags in `review_tracker_ALL_completed_v1.xlsx` for D08-EU-002, D14-SR-002, D07-CY-001, D08-LY-001

**Cluster 6 (post-hardware):**
- [ ] Apply File 3 D03-WB-001..008 (with confidence gate removed; hardware-gated as before)
- [ ] Apply File 4 D03-ST-001 (add `yield_u_values` config entry: `representative_rule_id='D03-ST-001'` for `factor_key='drought_fill_G3G4'`)

---

## Sign-off

All drift patterns and D1-D6 decisions inline. Every rule now uses deployed vocabulary: A/B/C source_class, 4-value severity, 5 formal precedence relations, no compliance_tag, no aspirational-feature flags, no confidence-gate DSL, no DATE literal.

Backend can proceed with cluster 2 immediately.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
28 September 2026

*End of v1.2 Deployed-Aligned Fix Pack*
