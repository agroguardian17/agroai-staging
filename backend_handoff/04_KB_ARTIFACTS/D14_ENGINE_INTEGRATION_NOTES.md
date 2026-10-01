# Domain 14 — Engine Integration Patch Notes

**Date:** 17 September 2026
**Author:** kb_author
**Scope:** engine-side wiring of Domain 14 immutable rules and precedence relations
**Approach:** additive edits at the end of two hardcoded structures; zero touches to any pre-existing entry

---

## 1. What changed | काय बदलले

Two files in `ginger/engine/` received additive edits:

| File | Structure | Before | After | New D14 entries |
|---|---|---:|---:|---:|
| `expert_override.py` | `IMMUTABLE` dict | 16 | **24** | 8 (7 POS + 1 DP) |
| `expert_override.py` | `load_rules() files` list | D1–D13 | **D1–D14** | Domain14 file added |
| `precedence.py` | `PRECEDENCE` list | 39 | **44** | 5 (3 BUNDLES + 2 SEQUENCES) |

Total changed lines across both files: **43** (17 in expert_override.py, 26 in precedence.py). Zero pre-existing entries were disturbed.

---

## 2. `expert_override.py` — IMMUTABLE additions | अपरिवर्तनीय नियम

8 D14 rule IDs added to the `IMMUTABLE` dict, each with a short reason string in the same style as the pre-existing 16:

```python
# --- D14 (Satellite & Remote Sensing) additions -------------------------
# prohibited customer claims — RAW MASTER §16.1, §5
'D14-POS-001': 'The underground rhizome is invisible to every current satellite...',
'D14-POS-002': 'Canopy senescence signals a stage window, not maturity precision...',
'D14-POS-003': 'Yield prediction is prohibited to customers under D12...',
'D14-POS-004': 'Plant count from 10 m Sentinel-2 pixels is not physically possible.',
'D14-POS-005': 'Cloud is a real problem; SAR reduces but does not eliminate the gap.',
'D14-POS-006': 'Sub-node sensors are the authority... Cardinal principle §1.4.',
'D14-POS-007': 'Satellite revisit is 5-20 days depending on cloud...',
# DPDP display guard
'D14-DP-001': 'Displaying a plot-level satellite derivative outside the plot owner without consent is a DPDP Act 2023 violation. Aggregate first.',
```

**One-line `load_rules()` fix:** the file list ran `range(2, 14)` (D2–D13). Extended to `range(2, 15)` (D2–D14) so `load_rules()` sees the fourteenth domain. Zero other logic in the function changed.

---

## 3. `precedence.py` — PRECEDENCE additions | precedence जोडणी

5 `Relation(...)` objects appended to the `PRECEDENCE` list, bilingual reason strings following the existing style. The set mirrors exactly what was added to Domain11's `_schema.additions.precedence.graph`:

| Subject | Relation | Object | Purpose |
|---|:---:|---|---|
| D14-NM-003 | **BUNDLES** | D03-SC-001 | canopy-moisture confirmation tag on irrigation rule |
| D14-LT-003 | **BUNDLES** | D03-SC-001 | thermal confirmation tag |
| D14-FU-002 | **BUNDLES** | D03-SC-001 | early-action-window leading indicator |
| D14-NV-004 | **SEQUENCES** | D06-DX-001 | sharp NDVI drop stages D06 differential |
| D14-SR-002 | **SEQUENCES** | D06-SW-003 | SAR standing water stages D06 saturation branch |

**Zero SUPPRESSES, zero SUPERSEDES.** Satellite never silences an agronomic domain.

---

## 4. Verification | पडताळणी

### 4.1 Complete test suite (post-integration)

```
═══ 1. json_to_sql (14 domains) ═══
  WROTE kb.sql  —  481 rules, 1291 KB   ✅

═══ 2. Trigger DSL — waves 1-5 ═══
  D14:       47/47 parse · 47/47 fields · 141/141 tests   ✅
  Waves 1-5: 235/235 parse · 235/235 fields · 587/587 tests   ✅

═══ 3. test_override.py ═══
  24 immutable रुल्स × 3 override प्रकार (DISABLE, SEVERITY, DELIVERY)   ✅
  सर्व पास — 16 pre-existing + 8 D14 immutable रुल्स every override refuse करतात

═══ 4. test_precedence.py ═══
  44 typed relations, 5 प्रकार   ✅
  सर्व पास — 39 pre-existing + 5 D14 relations resolve correctly
```

### 4.2 Golden resolver behavior — D14 precedence entries actually work

Four hand-run cases through `Precedence.resolve()`:

**Case 1** — D03-SC-001 fires + D14-NM-003 fires
```
issued:    ['D14-NM-003']
bundles:   {'D14-NM-003': ['D03-SC-001']}
```
D14-NM-003 travels bundled with D03-SC-001 — one message to the farmer, confidence tag attached. ✅

**Case 2** — D14-NV-004 fires alone (URGENT scout)
```
issued:    ['D14-NV-004']
waiting:   []
```
URGENT alert fires immediately; the D06 branch would wait if it also fired. Correct behavior. ✅

**Case 3** — D03-SC-001 + all three D14 BUNDLES (NM-003, LT-003, FU-002)
```
issued:    ['D14-FU-002', 'D14-NM-003', 'D14-LT-003']
bundles:   {'D14-NM-003': ['D03-SC-001'],
            'D14-LT-003': ['D03-SC-001'],
            'D14-FU-002': ['D03-SC-001']}
```
All three confidence tags stack onto the one D03 irrigation message. This is the design working as intended. ✅

**Case 4** — D14-SR-002 fires alone (URGENT standing water)
```
issued:    ['D14-SR-002']
waiting:   []
```
URGENT drainage advisory fires; D06 post-monsoon saturation branch staged (would wait if it also fires). ✅

### 4.3 Discipline invariants

- **IMMUTABLE dict:** 24 entries (16 pre + 8 D14). Pre-existing 16 disturbed: **0** ✅
- **PRECEDENCE list:** 44 relations (39 pre + 5 D14). Pre-existing 39 disturbed: **0** ✅
- **D14 SUPPRESSES targeting D06:** **0** ✅
- **D14 SUPERSEDES targeting D03:** **0** ✅

---

## 5. Regression coverage | regression coverage

D14 immutable rules and D14 precedence relations are now in the runtime code, not just the KB JSON. This means:

- Any future override attempt against a D14 immutable rule is refused at the code path level, exactly like the 16 pre-existing immutable rules. An agronomist cannot accidentally lift POS-001 (`"satellite detects rhizome rot"`) or DP-001 (`third-party display without consent`) at runtime.
- The precedence resolver correctly bundles the three D14→D03 confidence tags onto the one D03 irrigation message rather than emitting three separate satellite messages — the "one field visit, one message" principle held.
- The two D14→D06 SEQUENCES entries stage the differential branch when the D14 alert fires; both fire in order, satellite opens the investigation, D06 closes it.

Together with the 141 D14 golden tests and 5 D14 precedence entries in Domain11's JSON graph, the domain now has complete engine-side coverage.

---

## 6. Files delivered | पुरवलेल्या फाईल्स

| File | Kind |
|---|---|
| `expert_override.py` | patched engine module (24 IMMUTABLE entries, D14 loaded) |
| `precedence.py` | patched engine module (44 PRECEDENCE relations) |
| `expert_override_D14.patch` | unified diff — 17 lines vs the pre-integration file |
| `precedence_D14.patch` | unified diff — 26 lines vs the pre-integration file |
| `D14_ENGINE_INTEGRATION_NOTES.md` | this file |

The two `.patch` files show the exact lines added; if Kuldip prefers to apply the changes by hand rather than replace the files wholesale, the patches are the surgical form.

---

## 7. What's still on the engine side for later | engine मध्ये पुढे

Only two items remain from the original D14_PATCH_NOTES §8 list:

1. **`tests/regression_gate.py`** — its `coverage()` function still hardcodes waves 1–3. Needs to add waves 4 (VPD) and 5 (D14). Same pattern for both. Small, safe.
2. **`test_runtime_loader.py`** — needs the wave-5 file registered for the build-vs-KB drift check. Same pattern as the wave-4 VPD change would have needed.

Neither affects rule behavior, message delivery, or user-facing outputs. Both are internal quality gates. Ship them together whenever convenient.

---

## 8. Summary table | सारांश

| Metric | Pre-integration | Post-integration |
|---|---:|---:|
| IMMUTABLE dict size | 16 | **24** |
| D14 immutable IDs in code | 0 | **8** |
| PRECEDENCE list size | 39 | **44** |
| D14 precedence relations in code | 0 | **5** |
| Domains loaded by `load_rules()` | 13 | **14** |
| `test_override.py` result | ✅ | **✅** (now covers D14) |
| `test_precedence.py` result | ✅ | **✅** (now covers D14) |
| Trigger DSL result | ✅ | **✅** |
| json_to_sql result | ✅ | **✅** |
| Pre-existing entries touched | — | **0** |

**Status:** Domain 14 is fully wired into the ginger KB and its engine. Ready for Tier-1 review.

---

*End of D14 engine integration notes.*
