# Domain 14 — Test Report
## Post-JSON Test Suite Results

**Date:** 17 September 2026
**Suites run:** 4 (json_to_sql, trigger DSL golden tests, precedence validation, expert override)
**Result:** ✅ **all pass**

---

## 1. Summary | सारांश

| Suite | Scope | Result |
|---|---|:---:|
| `json_to_sql_with_d14.py` | 14 domains × 481 rules → SQL emit | ✅ 481 rules, 1291 KB, 0 errors |
| `run_d14_trigger_tests.py` (D14 only) | 47 rules parse + fields + 141 golden tests | ✅ **47/47 · 47/47 · 141/141** |
| `run_d14_trigger_tests.py` (waves 1–5) | 235 rules parse + fields + 587 golden tests | ✅ **235/235 · 235/235 · 587/587** |
| D11 precedence structural validation | 45 entries, subject/object real, no forbidden directions | ✅ all 45 valid; 0 D14→D06 SUPPRESSES, 0 D14→D03 SUPERSEDES |
| `test_precedence.py` (engine-side) | 39 hardcoded relations, 5 relation types | ✅ सर्व पास |
| `test_override.py` | 16 pre-existing immutable rules resist all overrides | ✅ सर्व पास |

---

## 2. Findings and fixes | तपासणी दरम्यान सापडलेल्या चुका आणि सुधारणा

The DSL test runner caught **three real bug classes** in the Phase-1 JSON that had passed the schema validator but not the DSL parser. All fixed silently before delivery. This is exactly the value of running the test suite before shipping — schema validation is not enough.

### 2.1 SQL-style `=` vs DSL `==` (22 rules)

**Class:** rules used `field = 'value'` (SQL equality) where the DSL grammar requires `field == 'value'` (Python-style equality).

**Rules affected:** NV-001, NR-001/002, NM-001, NM-002/003, SR-001, LT-002/003, PH-003, FU-001..005, PL-004, POS-001..007

**Fix:** mechanical `=` → `==` substitution in JSON expressions and wave5 authoring surface, in both places, keeping parity.

### 2.2 Composite comparison `field < baseline − 0.10` (2 rules)

**Class:** NR-003 and FU-004 used `ndre_mean < plot_ndre_baseline_regional - 0.10` — a right-hand side with binary arithmetic that the DSL grammar rejects (RHS must be a literal, not an expression).

**Fix:** followed the existing `plot_ndvi_gap_regional` pattern — added `plot_ndre_gap_regional` as a new derived farm_brain field. NR-003 and FU-004 now read `plot_ndre_gap_regional < -0.10`, semantically identical, syntactically legal.

### 2.3 `field IS NOT NULL` on `None` returns FALSE, not UNKNOWN (3 D14 tests + 3 pre-existing D07-VP tests)

**Class:** golden tests for LT-001, PL-003, DP-002, SR-001 (D14) and D07-VP-001 × 2 (pre-existing wave 4) expected `UNKNOWN` when the tested field was `None`. But the DSL engine treats `IS NOT NULL` semantically — returns `FALSE` when the field is absent, never `UNKNOWN`. The three-valued logic applies to comparisons (`x > 5` when `x=None` → `UNKNOWN`), not to null-existence predicates.

Also caught: D07-VP-003 test used `'current_month': 'JAN'` where the DSL expects an integer (`1`).

**Fix:** all 7 test expectations corrected. These were bugs in my test authoring, not in the rule expressions or the engine.

### 2.4 What did NOT need fixing

- `_schema.additions.new_farm_brain_fields` — all 43 declared fields matched what the expressions actually reference
- Bilingual content, kannad_note, source_class, delivery, immutable — no changes required
- D11 precedence entries — all 5 D14 additions structurally valid, no forbidden relations
- Existing D01–D13 rules — untouched, still passing all their own tests

---

## 3. What the test suite proved | चाचणी संचाने काय सिद्ध केले

### 3.1 Every D14 expression is syntactically legal DSL

All 47 rules parse cleanly against the same grammar the runtime engine uses. Zero deferred parse errors.

### 3.2 Every field is declared

The 47 expressions reference exactly the fields declared in `_schema.additions.new_farm_brain_fields` (plus synthetic and D07-shared fields). No hidden dependencies, no undeclared assumptions.

### 3.3 Every trigger produces the intended truth value

141 golden tests × 47 rules = every rule has ≥ 2 test contexts covering fire / not-fire / near-miss / null-input. All 141 evaluate as expected. The three-valued logic (TRUE / FALSE / UNKNOWN) is used correctly throughout.

### 3.4 No D14 rule can silence a D03 sub-node moisture rule or a D06 disease rule

Structural precedence audit: 0 `SUPPRESSES` from D14 → D06, 0 `SUPERSEDES` from D14 → D03. Kuldip's Sep-17 discipline held to the letter.

### 3.5 No regression in D01–D13

Waves 1–3 run inside the same test suite (235 rules together): every one of the 446 pre-existing golden tests still pass. Adding D14 did not break anything.

### 3.6 Existing engine safeguards remain intact

- `test_precedence.py`: 39 typed relations correctly resolve, 5 relation types work as documented, ambiguous cases correctly escalate to differential-diagnosis path
- `test_override.py`: all 16 pre-existing IMMUTABLE rules refuse every kind of override attempt (DISABLE, SEVERITY, DELIVERY)

---

## 4. Known engine-integration gap | engine मध्ये पुढे काय जोडायचे

The D14 JSON has **8 immutable rules** (7 POS + DP-001) but `expert_override.IMMUTABLE` in `engine/expert_override.py` still lists only the 16 pre-existing immutable IDs. This means:

- **The KB says these 8 are immutable** ✓ — visible in JSON, gated at authoring
- **The engine does not yet know they are immutable** — an override attempt against them would currently be accepted

This is engine-integration surface, not a KB gap. Fix is a mechanical addition to the `IMMUTABLE` dict — same pattern as VPD retrofit. Listed as item 2 in D14_PATCH_NOTES.md §8.

Same shape for `precedence.PRECEDENCE` code list vs D11 precedence graph — the JSON has the 5 new D14 entries; the code list does not yet. Neither test suite covers the D14 entries as a result. Adding them is the next engine step.

---

## 5. Files updated in this test-run pass | या टप्प्यात बदललेल्या फाईल्स

| File | Change |
|---|---|
| `Domain14_Rules_Ginger.json` | 22 rules: `=` → `==` · NR-003, FU-004 reformulated with `plot_ndre_gap_regional` · 4 golden tests: `UNKNOWN` → `FALSE` for `IS NOT NULL` on `None` · 1 new declared field `plot_ndre_gap_regional` |
| `triggers_wave5_d14.py` | mirrored all JSON expression fixes; identical parity check (47 = 47, 0 mismatches) |
| `triggers_wave4_vpd.py` | pre-existing bugs from Step 1 delivery fixed: 2 `IS NOT NULL` tests → `FALSE`, 1 `current_month` string → integer |
| `run_d14_trigger_tests.py` | new deliverable — runs all 587 golden tests across waves 1–5, reports D14-only and full-KB results side by side |

---

## 6. Next actions | पुढील पावले

1. **Kuldip review of the JSON rule set** — 47 rules; the same Sunday-morning read pattern that worked for VPD retrofit
2. **Engine integration (small, mechanical):**
   - add 8 D14 rule IDs to `engine/expert_override.py::IMMUTABLE` dict
   - add 5 D14 precedence entries to `engine/precedence.py::PRECEDENCE` list as `Relation()` objects
   - after both, `test_override.py` and `test_precedence.py` gain D14 coverage
3. **Season-1 field data slot (OI-09):** the falsifiable rhizome-rot lead-time test (RAW MASTER §5.6) — result determines whether any D14 rule can ever be strengthened for rot detection or the blind spot is fundamental
4. **Phase-2 pass in Q4** — elevate 6-8 rules from SRC-EST to SRC-Q using season-1 empirical baselines

---

*End of D14 test report.*
