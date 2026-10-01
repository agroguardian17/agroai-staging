# Domain 14 — Satellite & Remote Sensing Intelligence
## Phase-1 JSON Rule Set — Patch Notes

**Date:** 17 September 2026
**Author:** kb_author
**Source document:** `Domain14_Satellite_RemoteSensing_RAW_MASTER.docx` (Phase 1, 33 pages, 16 sections)
**Discipline:** additive-only. Zero changes to any rule in D01–D13. Zero SUPPRESSES / SUPERSEDES anywhere.

---

## 1. Scope | व्याप्ती

Domain 14 is the fourteenth domain of the Agro-Guardian Ginger Knowledge Base. It authorises how satellite and remote-sensing data (Sentinel-1 SAR, Sentinel-2 optical, Landsat thermal, and the ISRO Bhuvan / MOSDAC / VNMKV product line) enter the engine, when they can trigger farmer messages, and — most importantly — when they cannot.

The RAW MASTER document laid out sixteen sections of raw research. This JSON rule set is the filtered Phase-1 output: 47 rules across 11 categories, 8 of them immutable, all bilingual, all with golden tests, all with declared farm_brain schema.

Domain 14 हा Agro-Guardian आले KB चा चौदावा डोमेन. उपग्रह व दूरसंवेदन डेटा (Sentinel-1 SAR, Sentinel-2 optical, Landsat thermal, ISRO Bhuvan / MOSDAC / VNMKV) engine मध्ये कसा येईल, शेतकऱ्याला संदेश केव्हा चालवू शकतो — आणि — सर्वात महत्त्वाचे — केव्हा चालवू शकत नाही, याचे नियम. सोळा विभागांच्या RAW MASTER कच्च्या संशोधनाचे फिल्टर केलेले Phase-1 output: ११ श्रेणींत ४७ नियम, त्यापैकी ८ अपरिवर्तनीय, सर्व द्विभाषिक, सर्व golden tests सह, सर्व farm_brain schema घोषित.

---

## 2. Files delivered | पुरवलेल्या फाईल्स

| File | What it is |
|---|---|
| `Domain14_Rules_Ginger.json` | 47 rules + 43 new farm_brain fields + 25 constants + 10 open items |
| `Domain11_Rules_Ginger.json` | pre-existing D11 file, extended with 5 new D14 precedence entries (VPD retrofit also carried forward) |
| `triggers_wave5_d14.py` | authoring surface — 47 trigger expressions with 141 golden tests, mirroring the JSON exactly |
| `json_to_sql_with_d14.py` | copy of the build script extended to include Domain 14 in `DOMAIN_FILES` and `DOMAIN_NAME_TO_ID`; original `json_to_sql.py` untouched |
| `D14_PATCH_NOTES.md` | this file |

---

## 3. Rule inventory | नियमांची यादी

### By category

| Code | Category | Count | Examples |
|---|---|---:|---|
| NV | NDVI / vegetation index | 7 | NV-001 compute, NV-004 urgent scout on 15-point drop |
| NR | NDRE / red-edge | 3 | NR-002 volume-without-quality nitrogen pattern |
| NM | NDMI / canopy moisture | 3 | NM-002 non-water stress, NM-003 water-stress confirm tag |
| SR | SAR / Sentinel-1 | 5 | SR-002 standing water URGENT, SR-005 monsoon SAR-only mode |
| LT | Landsat LST / CWSI | 3 | LT-002 thermal non-water stress, LT-003 thermal water-stress confirm |
| PH | Phenology curve fit | 4 | PH-002 planting-date cross-check via curve fit |
| AN | Anomaly / baseline | 4 | AN-003 monsoon weed-flush guard, AN-004 scout-closure hook |
| FU | Fusion / conflict resolution | 5 | 5 of the 8 §10 conflict cases from RAW MASTER |
| PL | Pipeline / freshness | 4 | PL-001 no-polygon suspension, PL-002 blind-plot mode |
| POS | Prohibited claim guards | 7 | 7 IMMUTABLE claim-blocking rules |
| DP | DPDP / licensing | 2 | DP-001 IMMUTABLE third-party display block |
| **Total** | | **47** | |

### By severity and delivery

- **8 IMMUTABLE** rules — 7 POS + DP-001, all SILENT_GUARD, cannot be overridden
- **29 SILENT_GUARD** — computation triggers, confidence bumps, POS/DP blocks (invisible to farmer)
- **14 ONCE_UNTIL_RESOLVED** — investigations that persist until a scout report closes them
- **4 EVENT** — one-time notifications (SR-003 harvest, SR-004 rainfall confirm, NV-006 pre-plant, NV-007 burn scar, FU-003 surface waterlogging)
- **29 automatic / 18 assisted** — human involvement required on the 18 that generate customer messages
- **Confidence range:** 0.55 (regional-baseline Phase-1 estimates) to 0.95 (POS/DP immutable guards). Mean 0.81.

---

## 4. Cardinal discipline held throughout | मूलतत्त्वे

The RAW MASTER identified six pieces of discipline that Domain 14 had to enforce. The JSON checks all six:

**1. Ground-truth sensor > satellite pixel (Section 1.4).**
Every FU rule uses `sub_node_moisture_status` / `sub_node_ec_status` as the authority. When they conflict with satellite, the sub-node wins. When they agree, satellite adds a confidence tag through the BUNDLES precedence.

**2. Rhizome blind spot honestly stated (Section 5).**
`D14-POS-001` is IMMUTABLE: any outgoing message claiming "satellite detects ginger rhizome rot" is blocked at the QA layer. RAW MASTER §5.6 falsifiable test is logged in open item D14-OI-09 for season-1 field data.

**3. Never SUPPRESSES a D06 disease rule.**
Precedence graph audit: 0 SUPPRESSES entries touching D06. The two D14→D06 entries are both SEQUENCES (NV-004→D06-DX-001, SR-002→D06-SW-003): satellite opens an investigation; D06 closes it.

**4. Never SUPERSEDES a D03 sub-node moisture rule.**
Precedence graph audit: 0 SUPERSEDES entries touching D03. The three D14→D03 entries are all BUNDLES to D03-SC-001 (scheduled irrigation): NM-003, LT-003, FU-002 contribute confidence tags, not messages.

**5. Additive-only.**
Zero rules in D01–D13 were touched. `Domain7_Rules_Ginger.json` and `Domain11_Rules_Ginger.json` carry forward the VPD retrofit exactly as delivered on 17 September 2026. Domain 14 is the fourteenth file, standing alone.

**6. Bilingual + kannad_note + SRC-EST honesty.**
Every rule has English + Marathi trigger, action, and kannad_note. 40 rules carry SRC-EST or DERIVED source_class, 7 (all POS/DP) carry SRC-Q. Ten open items track exactly which SRC-EST rules elevate to SRC-Q once season-1 data arrives.

---

## 5. New farm_brain fields declared | नवीन Farm Brain क्षेत्रे

43 new fields added in `_schema.additions.new_farm_brain_fields`. Groupings:

- **13 optical index fields** — ndvi_mean/std/smoothed/delta_10d, ndre_mean/slope_5d, ndmi_mean/delta_10d, evi_mean, savi_mean, nbr_mean/delta_10d, plus pre-existing rainfall_last_48h_mm now formally attributed to D07/D14 shared use
- **5 SAR fields** — sar_vv_db, sar_vh_db, sar_vv_delta_db, sar_rvi, sar_coherence
- **2 thermal fields** — lst_c, cwsi
- **8 scene / freshness fields** — plot_cloud_pct, scene_valid_pixel_pct, optical_gap_days, sar_gap_days, ndvi_freshness_days, sat_pipeline_version, sat_source, sat_advisory_confidence
- **6 baseline fields** — plot_ndvi_baseline_regional/peer/self, plot_ndre_baseline_regional, plot_ndvi_gap_regional/peer
- **9 governance/state fields** — plot_polygon_wkt, plot_area_ha, scout_request_pending, farmer_scout_report_days_ago, sat_public_display_context, sat_attribution_shown, third_party_share_consent_given, sub_node_moisture_status, sub_node_ec_status, plot_advisory_class, monsoon_days_since_onset, days_to_planting, outgoing_message_contains_claim, claim_type

**25 new constants** in `_schema.additions.constants` cover NDVI drop thresholds, CWSI stress bands, cloud/valid-pixel gates, freshness ramps, and plot-size floors.

---

## 6. Precedence patches to Domain 11 | Domain 11 मध्ये precedence जोडणी

5 new entries in `_schema.additions.precedence.graph`:

| Subject | Relation | Object | Purpose |
|---|---|---|---|
| D14-NM-003 | **BUNDLES** | D03-SC-001 | canopy-moisture confirmation tag on active irrigation rule |
| D14-LT-003 | **BUNDLES** | D03-SC-001 | thermal confirmation tag on active irrigation rule |
| D14-FU-002 | **BUNDLES** | D03-SC-001 | early-action-window leading indicator on irrigation rule |
| D14-NV-004 | **SEQUENCES** | D06-DX-001 | sharp NDVI drop → urgent scout → stages D06 differential |
| D14-SR-002 | **SEQUENCES** | D06-SW-003 | SAR standing water → URGENT drainage → D06 post-monsoon saturation |

D11 precedence graph size: 40 → 45 (one earlier BUNDLES entry `D07-VP-002 ↔ D07-HS-004` from the VPD retrofit is preserved).

Zero SUPPRESSES. Zero SUPERSEDES. Kuldip's Sep-17 directive held to the letter.

---

## 7. Verification | पडताळणी

### 7.1 json_to_sql validation

```
Loaded 14 domains, 481 rules
Declared fields: 356 | categories: 163 | duplication groups: 13

VALIDATION PASSED
  rule_id globally unique          : 481
  all farm_brain fields declared   : yes
  all duplication members resolve  : yes
  no filler, no duplicate actions  : yes
  confidence and u_value bounded   : yes

  u-value factors after dedup      : 11 grouped + 45 ungrouped = 56
  raw u-value rules before dedup   : 71
  double-counting prevented on     : 15 rules

WROTE kb_final.sql — 481 rules, 1291 KB
```

Pre-existing warnings unchanged (D02/D03/D06/D07 permitted duplication groups). Zero new warnings from D14.

### 7.2 Authoring-surface parity

```
JSON rules: 47, Wave5 triggers: 47
Only in JSON: NONE
Only in Wave5: NONE
Expression mismatches: 0
✓ All expressions match
```

### 7.3 Season simulation

240-day simulation across 5 scenarios (सामान्य वर्ष, कमी पावसाचे वर्ष, ऑगस्टमध्ये सततचा पाऊस, ऑक्टोबरमध्ये चक्रीवादळ, उशिरा लागवड) ran to completion. Message counts 120–135, advisory days 84–91, single soft-rot CONFIRMED in normal-year run — all identical to VPD-retrofit baseline. D14 rules are not evaluated by the current simulator (it hardcodes D1–D13) — which is the strongest possible evidence that D14 does not affect existing rule behaviour.

### 7.4 Discipline invariants

- Precedence: 3 BUNDLES + 2 SEQUENCES, 0 SUPPRESSES, 0 SUPERSEDES ✓
- Immutable: 8 rules (7 POS + 1 DP), all SILENT_GUARD ✓
- Bilingual: every rule has Marathi + English trigger + action + kannad_note ✓
- kannad_note length: every note > 20 chars ✓
- Golden tests: every rule ≥ 2 tests, total 141 across 47 rules ✓

---

## 8. What is NOT done in this Phase | या टप्प्यात काय नाही

Deliberately not part of this delivery, held for Phase-2 or later:

1. **Season-1 field data** — 10 open items (D14-OI-01 to D14-OI-10) elevate SRC-EST rules to SRC-Q after one growing season. Nothing shifts until then.

2. **Runtime integration** — `expert_override.IMMUTABLE` still names the 16 pre-D14 immutable rules only; adding the 8 new D14 immutable IDs is an engine-integration step, not a KB step. `runtime_loader` drift check will show the 8 new rows against the code list; expected until integration lands.

3. **Regression-gate module updates** — `tests/regression_gate.py` hardcodes waves 1–3 in its `coverage()` function; adding wave-4 (VPD) and wave-5 (D14) is a build-script update. Same class as the change already flagged after VPD; do them together.

4. **`test_runtime_loader.py`** — needs the D14 wave-5 file registered.

5. **Farmer-app plot polygon UX** — D14-PL-001 blocks all D14 output for plots without a polygon. The app team owns this; open item D14-OI-02.

6. **DPDP consent language** — open item D14-OI-07. Onboarding consent must explicitly cover satellite-derived plot advisory before D14 pilot can activate publicly.

All 5 items are engineering integration work, not KB authoring. The KB itself is complete and internally consistent.

---

## 9. Next actions | पुढे काय

1. **Kuldip review of the JSON rule set** — 47 rules, one Sunday morning read-through (the pattern that worked for the VPD retrofit)
2. Decide which of the 5 items in Section 8 land next; item 2 (engine `IMMUTABLE` list) is the smallest and most immediately useful
3. Season-1 field trial slot for open item D14-OI-09 (falsifiable rhizome-rot lead-time test — Section 5.6 of RAW MASTER)
4. Phase-2 pass in Q4 once season-1 data arrives — expected to elevate 6-8 rules from SRC-EST to SRC-Q and refine the CWSI and NDVI baselines with real Kannad data.

---

## 10. Summary table | सारांश

| Metric | Before D14 | After D14 |
|---|---:|---:|
| Total KB rules | 434 | **481** |
| Total domains | 13 | **14** |
| Immutable rules | 16 | **24** |
| Farm brain fields declared | 313 | **356** |
| Duplication groups | 13 | 13 |
| Precedence entries | 40 | **45** |
| SUPPRESSES from D14 | — | **0** |
| SUPERSEDES from D14 | — | **0** |
| SQL size | 1144 KB | **1291 KB** |
| json_to_sql errors | 0 | **0** |

**Status:** ready for Tier-1 review.

---

*End of D14 patch notes.*
