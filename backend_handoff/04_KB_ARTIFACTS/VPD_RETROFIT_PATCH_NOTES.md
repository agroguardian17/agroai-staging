# VPD Retrofit — Patch Notes

**पॅच:** VPD (Vapour Pressure Deficit) retrofit for Domain 7
**Scope:** Ginger KB only. Additive-only. Zero existing rules edited.
**Date:** 2026-09-17
**Files touched:** 2 JSON + 1 new authoring file

---

## 1. काय बदललं (What changed)

### `Domain7_Rules_Ginger.json` — additions only

| Section | Addition |
|---|---|
| `_schema.additions.rule_categories_domain_7` | Nieuwe key `VP` = "vapour pressure deficit" |
| `_schema.additions.new_farm_brain_fields` | 3 new fields: `vpd_kpa`, `vpd_night_mean_kpa`, `spray_scheduled_today` |
| `_schema.additions.constants` | 5 new VPD thresholds (0.4 / 0.8 / 1.5 / 2.0 / 0.3 kPa) |
| `reference_data.vpd_context` | New explainer block — what VPD is, formula, bands, honest limits, why NOT used for irrigation (Penman-Monteith double-counting risk) |
| `rules[]` | 3 new rules appended: `D07-VP-001`, `D07-VP-002`, `D07-VP-003` |
| `open_items[]` | 1 new item `D07-OI-09` (VPD threshold calibration, season 1) |
| `summary` | Counters bumped: total_rules 35→38, by_category adds VP:3, etc. |
| `metadata.total_rules` | 35 → 38 |
| `metadata.review_log` | New `change_log` sub-list; existing tier_1 summary untouched |
| `next_steps[]` | 1 new entry (calibration follow-up) |

### `Domain11_Rules_Ginger.json` — one precedence entry added

| Change | Detail |
|---|---|
| `_schema.additions.precedence.graph` | 39 → 40 entries. New: `D07-VP-002 BUNDLES D07-HS-004` (both fire on the same spray event → single combined message) |

### `triggers_wave4_vpd.py` — new authoring file (not a runtime file)

Mirrors the 3 new triggers so `test_runtime_loader.py` sees no build-vs-KB drift. Runtime does not read this — architecture §11A: production reads from database.

---

## 2. काय बदललं नाही (What did NOT change)

- ❌ No existing D07 rule modified (byte-verified for all 35)
- ❌ No existing precedence entry modified (byte-verified for all 39)
- ❌ No changes to D01, D02, D03, D04, D05, D06, D08, D09, D10, D12, D13
- ❌ No immutable rule touched
- ❌ No trigger expression changed
- ❌ No delivery class changed
- ❌ No golden test changed

**Cross-domain safety confirmed** — VPD rules were considered for D03 (Water) irrigation refinement but explicitly **rejected** to avoid double-counting the same physical signal already inside `pan_evaporation_mm_day` (see architecture §4 and `reference_data.vpd_context.why_it_is_not_used_for_irrigation_here`).

---

## 3. नवीन 3 rules — quick reference

### `D07-VP-001` — VPD computation
- **Delivery:** SILENT_GUARD (zero farmer messages)
- **What it does:** Reads T + RH, computes and stores `vpd_kpa` daily. Also computes `vpd_night_mean_kpa` when hourly nighttime data is available.
- **Why:** Every downstream rule can then read the same value → count-once compliant.
- **Old rule impact:** None. Existing formulae untouched.

### `D07-VP-002` — Spray safety VPD guard
- **Delivery:** SILENT_GUARD (fires only when a spray is being recommended)
- **Fires when:** `spray_scheduled_today IS TRUE AND (vpd_kpa < 0.4 OR vpd_kpa > 2.0)`
- **What it does:** Blocks the spray and suggests a shifted window inside 0.8–1.5 kPa.
- **Old rule interaction:** `D07-HS-004` (temp>35 or rain forecast) — related via `BUNDLES`. Both fire together → **one combined message**, not two. `D07-HS-004` behaviour untouched.

### `D07-VP-003` — Leaf wetness confidence tag
- **Delivery:** SILENT_GUARD (no farmer message; internal tag only)
- **Fires when:** `vpd_night_mean_kpa < 0.3 AND fog_observed IS FALSE AND MONTH IN [DEC, JAN, FEB]`
- **What it does:** Tags tonight's estimated `leaf_wetness_hours` with high-confidence dew flag. This is the interim substitute for the unbought leaf wetness sensor (`D07-OI-05`).
- **Old rule impact:** `D07-HU-002` (winter foliar disease trigger) receives a richer confidence flag when this fires overnight — but its trigger, severity, and delivery are unchanged.

---

## 4. Verification — काय check केलं

| # | Check | Result |
|---|---|---|
| 1 | No existing D07 rule modified | ✅ byte-identical for all 35 |
| 2 | No existing precedence entry modified | ✅ byte-identical for all 39 |
| 3 | New DSL expressions use legal grammar only | ✅ IS TRUE / IS FALSE / MONTH IN / AND / OR / parens |
| 4 | Every new trigger field declared | ✅ 309 declared fields, zero undeclared references |
| 5 | Golden tests present, valid `expect` values | ✅ 12 new tests, all TRUE / FALSE / UNKNOWN |
| 6 | `kannad_note` > 20 chars | ✅ satisfies `rule_kannad_note_filled` constraint |
| 7 | Rule ID format valid | ✅ all `D07-...`, no `rule N` filler |
| 8 | No new immutable rule | ✅ immutable core stays at 16 |
| 9 | Only BUNDLES precedence added | ✅ BUNDLES cannot silence any existing rule (unlike SUPPRESSES / SUPERSEDES) |
| 10 | All new rules SILENT_GUARD | ✅ zero message-flood risk |
| 11 | JSON parseable | ✅ Domain 7: 148 KB, Domain 11: 154 KB |
| 12 | `D07-HS-004` (BUNDLES partner) untouched | ✅ byte-identical |
| 13 | `D07-HU-002` (leaf wetness rule augmented) untouched | ✅ byte-identical |
| 14 | Rule count 35 → 38 (+3) | ✅ |
| 15 | **`json_to_sql.py` VALIDATION PASSED** | ✅ 431 → 434 rules, 1144 KB SQL emitted clean |
| 16 | Regression gate — semantic suites | ✅ trigger DSL, precedence, override, runner, persistence — all pass |
| 17 | Regression gate — 240-day season simulation, all 5 scenarios | ✅ 130 / 128 / 131 / 135 / 120 messages, all within bounds |

### Expected "failures" (not semantic — authoring surface drift)

The regression gate's `test_runtime_loader` reports:
```
build 185 vs kb 188
फरक: [('D07-VP-002', 'BUNDLES', 'D07-HS-004')]
```

**This is expected per architecture §11A** — the .py authoring files (`triggers_wave1/2/3.py`, `precedence.py`) haven't been extended yet. Runtime does not read those files; it reads the database. The drift check is a CI signal for reconciliation.

**Fix:** Add `triggers_wave4_vpd.py` (provided) to the authoring wave imports.

---

## 5. Deploy steps

```bash
# 1. Replace the two knowledge base files
cp Domain7_Rules_Ginger.json  <your kb>/knowledge_base/
cp Domain11_Rules_Ginger.json <your kb>/knowledge_base/

# 2. Add the authoring file
cp triggers_wave4_vpd.py <your kb>/authoring/

# 3. Wire the new wave into the drift check (one-line edit in your test harness):
#    from triggers_wave4_vpd import TRIGGERS_W4
#    ALL_TRIGGERS.update(TRIGGERS_W4)

# 4. Run the gate
python3 regression_gate.py

# 5. Regenerate SQL
python3 json_to_sql.py --out agroguardian_ginger_kb.sql

# 6. Load into database
psql -d agroguardian -f agroguardian_ginger_kb.sql
```

---

## 6. Open follow-ups

1. **Season-1 calibration** (`D07-OI-09`) — thresholds 0.4 / 0.8 / 1.5 / 2.0 kPa are agronomic consensus for foliar crops; ginger-specific and Kannad-specific values may shift by 0.1–0.2 kPa in either direction after one season.
2. **Golden test coverage** — 12 new tests included. When Kuldip runs the T3/T4 expert review, VP-002 spray thresholds and VP-003 dew tag are the two lines to challenge.
3. **Downstream domain awareness** — D03 (Water), D05 (Pest), D06 (Disease), D08 (Cultivation) can *optionally* start reading `vpd_kpa` in their own future rule revisions. **Not required for this patch to be complete.**

---

## 7. Considered and skipped (why)

- **VPD-based irrigation trigger.** Rejected — Penman-Monteith already includes VPD via `pan_evaporation_mm_day`. A separate VPD irrigation rule would double-count the same physical signal (architecture §4 count-once enforcement).
- **VPD-based disease alert.** Rejected — existing `D07-HU-001` (RH>85, Aug/Sep), `D07-HU-002` (winter fog + leaf wetness), and `D07-HU-004` (soil-borne vs foliar season) already cover disease pressure. Adding a VPD alert would add message noise without new discrimination. VPD instead *augments* HU-002 via the SILENT_GUARD confidence tag (`D07-VP-003`).
- **Elevating VP-002 to SUPPRESS or SUPERSEDE HS-004.** Rejected — user directive is to preserve existing rule priority where the old rule remains important. HS-004 is already an expert-reviewed spray guard. BUNDLES is the safest relation: both fire, one combined message, neither silences the other.

---

## 8. Next candidate (Step 2 — Satellite Domain 14)

Per your working protocol, this file is delivery-complete. When you say "पुढे", we start Domain 14 as a **full RAW MASTER RESEARCH DOCUMENT** in the standard bilingual ~16-section format, followed by its JSON rule set. Scope will include NDVI / NDRE / NDWI / SAR soil moisture / LST — with the same additive discipline: never overrides ground-truth IoT sensors, only supplements them; and the honest-limit clause about NDVI's rhizome-rot blind spot (architecture §14 note) explicitly built in.
