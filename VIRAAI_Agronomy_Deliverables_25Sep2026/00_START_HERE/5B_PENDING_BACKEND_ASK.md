# 5-B: 42 Field-Dependent Firing-Intent Rules — Agronomy Ask to Backend

**Purpose:** Before Kuldip can author the remaining 42 field-dependent firing-intent rules, backend needs to share the working reference sheet. This document lists exactly what's needed and why.

**Date:** 25 September 2026
**From:** Kuldip — Agronomy Compliance Owner
**To:** Backend team (Abhinav @ GasView)
**Priority:** Launch-critical — 42 rules ~ 5-7 authoring days once inputs land; must complete before 25 October 2026 for Season 1 launch

---

## 1. Context

Backend agronomy-inputs request §5 (waterr.pdf review, 24 Sep 2026) referenced:

> *"43 field-dependent rules: for each — new field(s) name : type/enum + capture source (farmer app / scouting / ops / derived), canonical DSL trigger, delivery class, golden tests (fire + near-miss), final Marathi. **(The sheet lists all 53 new fields + suggested delivery classes as a starting point.)**"*

That **starting-point sheet is not yet shared with agronomy**. Without it, authoring these 42 rules from scratch would risk:
- Rule-ID conflicts with backend's intended IDs
- Field-name mismatches with schema-planning done in prior sessions
- Trigger-intent drift from what the firing-intent decision meeting agreed
- Duplicate rules if any of the 42 overlap with rules already in the KB

Kuldip explicitly won't fabricate rule bodies without the reference sheet — same class of internal-contradiction defect that Paths 1-4 review caught.

---

## 2. What's needed from backend (exact ask)

### 2.1 The firing-intent decision sheet itself

Either format works:
- Original `firing_intent_diagnostic_rules.xlsx` (referenced in Master Action List B5.1) — preferred
- Exported CSV
- Markdown table
- Google Sheet link with view access

### 2.2 Required columns / fields per rule

Each of the 42 rows should include:

| Column | Type | Example | Purpose |
|---|---|---|---|
| `rule_id` | string | `D01-EM-002` | Backend's intended ID (so Kuldip doesn't collide) |
| `intent_1_line` | string | "Detect delayed emergence beyond variety-typical" | What the rule is trying to detect |
| `draft_trigger_prose` | string | "emergence not observed by DAP 25 for Mahima" | Backend's draft trigger in plain language |
| `suggested_delivery_class` | enum | `EVENT` / `SILENT_GUARD` / `ONCE_UNTIL_RESOLVED` / `WINDOW` | Starting-point class |
| `suggested_new_fields` | list of {name, type} | `[{'emergence_observed_dap': 'int'}, {'emergence_confirmed_flag': 'bool'}]` | Fields backend expects to add |
| `severity_guess` | enum | `INFO` / `YELLOW` / `RED` | Backend's starting severity |
| `related_existing_rules` | list | `['D01-PH-004', 'D01-PW-001']` | For precedence planning |

### 2.3 Field-catalog cross-reference

The "53 new fields" list — either:
- Separate `firing_intent_new_fields.csv` with columns: `field_name`, `type`, `capture_source`, `used_by_rule_ids`, `default_value`, `nullable`
- OR embedded in the rules sheet as `suggested_new_fields` per row (per §2.2 above)

Kuldip needs this to check for duplicate field names, type conflicts with existing schema, and reasonable capture-source assignment.

---

## 3. What Kuldip will produce for each of the 42 rules

Once the sheet lands, Kuldip authors per rule:

| Deliverable | Format |
|---|---|
| Confirmed rule ID | Matches or corrects backend's intended ID |
| Formal DSL trigger | Full DSL syntax (no undefined fields) |
| Action block | Full pseudocode with severity + template + audit signals |
| Delivery class | Confirmed or revised from backend's starter |
| Marathi advisory template | Per rule's severity + scenario |
| Golden tests | 3-5 per rule: fire case + near-miss case + edge case |
| Precedence relations | Formal types only (SUPPRESSES / BUNDLES / SEQUENCES / ESCALATES / FEEDS) |
| Kannad context note | Where relevant |
| Compliance tag | COMPLIANT / CONDITIONAL / AGRO_GUARDIAN_CUSTOM(_OPERATIONAL_RULE) |
| Field definitions | Type + range + capture source + nullable/default |

Volume estimate: **42 rules × ~40 lines each ≈ 1,700 lines of authored spec**, split into 4 sub-batches of ~10 rules each for review-quality authoring.

---

## 4. Delivery timeline (once sheet lands)

| Milestone | Days after sheet lands | Deliverable |
|---|:---:|---|
| Batch 1 authored | +1 to +2 | ~10 rules |
| Batch 2 authored | +2 to +3 | ~10 rules |
| Batch 3 authored | +3 to +5 | ~10 rules |
| Batch 4 authored | +5 to +7 | ~12 rules |
| Consolidated review + final v1.0 | +7 | All 42 rules single doc |

**Backend needs sheet by 3 October 2026** to preserve 25 October integration deadline.

---

## 5. Alternative if sheet is unavailable

If the sheet doesn't exist in a shareable form:

**Fallback A — Backend & Kuldip joint working session:**
- 90-minute call
- Backend narrates each rule intent from their notes
- Kuldip authors 5-6 rules live per session
- Repeat 8 sessions = full 42

**Fallback B — Backend provides even a rough list of just rule IDs + 1-line intents:**
- Kuldip authors from rule ID + intent
- Marks unclear/inferred triggers as `[to confirm]` for backend review
- Slower iterations but doesn't block

**Fallback C — Deprioritize field-dependent rules from Season 1 launch:**
- Ship Season 1 with only the ~50 rules already authored (Water Budget + D03-WB + D04-NS + D06-BW + D08-WD + D02-LY + all covered rewrites + 5-A ready rules)
- 42 field-dependent rules become Season 2 launch scope
- Master Action List escalation policy A5 failure clause: "defer affected rules; system launches with reduced coverage"

---

## 6. Kuldip's readiness confirmation

- ✅ Authoring capacity: 10-12 rules per day at review-quality (per Paths 1-4 discipline standards)
- ✅ Marathi template pipeline established (per style-guide in `MARATHI_ADVISORY_TEMPLATES.md`)
- ✅ Precedence framework understood (formal types only; severity-conditional where relevant)
- ✅ Field-catalog awareness: existing fields cataloged in Water Budget v1.3 §2.2 and prior tracker work
- ✅ Quality checklist applied uniformly (per TRACK_A5_REMAINING_6_REWRITES.md verification pattern)

**Ready to start within 24 hours of sheet delivery.**

---

## 7. Signed request

Please share `firing_intent_diagnostic_rules.xlsx` (or equivalent) at earliest — this is the sole remaining launch-critical dependency on the agronomy side.

If format/access is an issue, Fallback A/B/C are on the table; Kuldip is flexible on process, not on quality.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
25 September 2026

*End of 5-B Backend Ask*
