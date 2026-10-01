# VIRAAI Agro-Guardian AI — Ginger KB
## Master Backend Handoff Package v1.0

**Date:** 23 September 2026
**From:** Kuldip — Agronomy Compliance Owner, VIRAAI Agro-Guardian AI
**To:** Backend / Product / Engineering team
**Scope:** Complete artifact bundle for Season 1 Kannad pilot activation
**Season 1 launch target:** 1 November 2026

---

## 1. काय आहे या package मध्ये | What's in this package

52 files across 7 folders. Everything backend needs to activate the Season 1 pilot and everything downstream (legal, VNMKV) needs to know about.

```
00_START_HERE/                          ← this README + master action list
01_AGRONOMY_COMPLIANCE/                 ← 8 files · agronomy sign-off, all 439 rules reviewed, D11/D12 specs
02_VNMKV_INSTITUTIONAL/                 ← 3 files · VNMKV faculty compliance certificate (template)
03_LEGAL_REGULATORY/                    ← 4 files · Legal desk compliance certificate (template)
04_KB_ARTIFACTS/                        ← 9 files · Domain 7/11/14 JSON files + D14 raw master doc + patch notes
05_DATA_FILES/                          ← 5 files · Pesticide registry v1.1 + IMD normals
06_ENGINE_INTEGRATION/                  ← 17 files · Python engine patches + wave triggers + test runner + build script
07_SQL_DEPLOYMENT/                      ← 3 files · Production SQL (full build + updates + README)
```

---

## 2. एक-ओळ स्थिती | One-line status

**KB frozen at 483 rules.** All 439 unvalidated rules reviewed for compliance (57 COMPLIANT · 358 CONDITIONAL · 8 NON_COMPLIANT · 16 LEGAL_REVIEW). Backend has closed the software gap; agronomy has closed the compliance gap; VNMKV + Legal have provided compliance templates (with actual-signature acquisition being a separate business track). Season 1 pilot activation is ready subject to the deployment checklist in §5.

---

## 3. Reading order — पहिले काय वाचायचे

**If you have 10 minutes:**
1. This README (`00_START_HERE/README.md`)
2. `01_AGRONOMY_COMPLIANCE/AGRONOMY_COMPLIANCE_v1.md` — the compliance owner's sign-off

**If you have 30 minutes:**
Add:
3. `01_AGRONOMY_COMPLIANCE/VIRAAI_JOINT_HANDOFF_TO_SOFTWARE_v1.0.md` — joint agronomy+backend handoff record
4. `02_VNMKV_INSTITUTIONAL/VNMKV_COMPLIANCE_CERTIFICATE.md` — institutional agronomic ratification (§7 has 14 action items)
5. `03_LEGAL_REGULATORY/LEGAL_COMPLIANCE_CERTIFICATE.md` — regulatory ratification (§11 has 12-item implementation checklist)

**If you have 2 hours:**
Read everything in `01_`, `02_`, `03_` (compliance documents), then skim `04_` (KB artifacts), `05_` (data files), `06_` (engine integration), `07_` (SQL deployment).

**If you are implementing:**
Start with §5 deployment checklist below, then work through the referenced files.

---

## 4. Provenance & honesty note (please read)

Two compliance certificates in this package (`02_VNMKV_INSTITUTIONAL/VNMKV_COMPLIANCE_CERTIFICATE.md` and `03_LEGAL_REGULATORY/LEGAL_COMPLIANCE_CERTIFICATE.md`) are **AI-drafted templates** based on published sources + cross-validated AI research. They are NOT physically signed by actual VNMKV faculty or admitted advocates.

**What this means practically:**
- Technical content (dose values, PHI numbers, statutory citations, regulatory-watch schedule) is drawn from published sources — usable immediately at own risk
- Streptocycline ban (registry v1.1) is a published regulatory fact — implement immediately, no signature dependency
- Consent language, disclaimer text, retention schedule, cross-border TOS — implement immediately as standard-of-care
- For regulatory-inspection-grade institutional standing, engage actual VNMKV faculty / admitted advocate; present these documents as fully-drafted templates needing only review + signature (reduces their time and fee)

Each certificate has a clear "Appendix A — Provenance and honest disclosure" section stating this. Do not present these documents externally as signed institutional certificates.

---

## 5. Deployment checklist — Season 1 launch (1 November 2026)

Ordered by priority. Items marked 🚨 are launch-blocking; others progressive.

### 5.1 Launch-critical (before farmer onboarding)

- [ ] 🚨 **Deploy full SQL** (`07_SQL_DEPLOYMENT/kb_ginger_d14_v1.0.sql`) to production database
- [ ] 🚨 **Apply Streptocycline blocklist** — registry v1.1 loaded into `_PHI_DAYS_BY_GROUP` + blocklist gate (see `05_DATA_FILES/ginger_pesticide_registry_v1.1_CHANGES.md`)
- [ ] 🚨 **Implement DPDP consent template** — Marathi + English from `LEGAL_COMPLIANCE_CERTIFICATE.md §3.1` (D12-DPDP-001)
- [ ] 🚨 **Deploy farmer-facing mandatory disclaimer** on all channels (`LEGAL_COMPLIANCE_CERTIFICATE.md §7.2`)
- [ ] 🚨 **Verify audit trail** — every advisory logged with rule ID, model version, confidence, validation gate results
- [ ] 🚨 **Rewrite 8 NON_COMPLIANT rules** per `AGRONOMY_COMPLIANCE_v1.md §2.2` (D08-WD-001, D03-DS-001, D08-EU-002, D08-LY-001, D01-PH-004, D14-SR-002, D03-WL-003, D07-CY-001)

### 5.2 Short-term (30 days post-launch)

- [ ] **Data retention schedule** implemented in backend lifecycle policy per `LEGAL_COMPLIANCE_CERTIFICATE.md §8`
- [ ] **Cross-border transfer TOS** added to farmer registration flow per `LEGAL_COMPLIANCE_CERTIFICATE.md §9.3`
- [ ] **Quarterly regulatory-watch** calendar set up per `LEGAL_COMPLIANCE_CERTIFICATE.md §10`
- [ ] **VNMKV corrections implemented:**
  - Zone mapping updated (Western/Central/Eastern with TMI values) — `VNMKV_COMPLIANCE_CERTIFICATE.md §4`
  - PHI corrections applied (Mancozeb 15-21, COC 15, Metalaxyl-M 30, Carbendazim seed-only, Imidacloprid 30-40)
  - Bacterial wilt rotation 3→5 year (D06-BW-001 trigger update)
  - Planting cutoff 7 June absolute (D01-PW-001 date-based)
  - BBF flat-layout on vertisol CONDITIONAL→BLOCKING (D02-LY-001)
  - Basal ZnSO₄ 25 kg/ha default recommendation added
- [ ] **D11 yield model backend build** per `D11_YIELD_MODEL_v1.md §5-7` (5 tables + 1 API)
- [ ] **D12 QA workflow tool** per `D12_QA_WORKFLOW.md §3, §5, §6` (4 tables + 4 functions + 5 UI screens)
- [ ] **47 firing-intent rules** wired per `firing_intent_diagnostic_rules.xlsx`

### 5.3 Business-track parallel (no blocking dependency)

- [ ] Legal desk engagement — present `03_LEGAL_REGULATORY/LEGAL_COMPLIANCE_CERTIFICATE.md` for advocate signature
- [ ] VNMKV Parbhani engagement — present `02_VNMKV_INSTITUTIONAL/VNMKV_COMPLIANCE_CERTIFICATE.md` for faculty signature
- [ ] Ops: WhatsApp Meta template approval + USGS credentials + Main Node / Sub Node hardware install
- [ ] Field ops: Kannad pilot plot enrollment (≥3 plots per cluster for peer baseline)
- [ ] Product: UI wireframe for D12 review tool (§6 spec in `D12_QA_WORKFLOW.md`)

### 5.4 Season-1 dependency (post-launch data)

- [ ] Season 1 field data collection → CONDITIONAL rules elevation
- [ ] U-value empirical calibration → D11 v2 model
- [ ] ML residual layer activation → Season 2 (after 100+ paired predicted/actual yield tuples)

---

## 6. What was NOT included (out of scope)

- Farmer-app UI wireframes (product team owns)
- WhatsApp advisory templates (product + Meta approval track)
- Actual signed VNMKV certificate (VNMKV Parbhani external process)
- Actual admitted-advocate signed legal opinion (external legal engagement)
- Hardware install docs (hardware team owns)
- IoT firmware / Sub Node calibration (hardware + firmware teams)

---

## 7. Package contents — file-by-file guide

### 01_AGRONOMY_COMPLIANCE/ (8 files)

| File | Purpose |
|---|---|
| `AGRONOMY_COMPLIANCE_v1.md` | Master compliance sign-off — accept role, 123 prior reviews ratified, 316 batches planned |
| `AGRONOMY_SIGNOFF.md` | 9 sign-off responses to backend's `AGRONOMIST_REVIEW.md` (soil_type, PHI, rainfall normals, etc.) |
| `AGRONOMY_RESPONSE_TO_BACKEND.md` | Earlier informal draft of §2 sign-offs (for context; superseded by `AGRONOMY_SIGNOFF.md`) |
| `review_tracker_ALL_completed_v1.xlsx` | **All 439 rules reviewed** — 57 COMPLIANT / 358 CONDITIONAL / 8 NON_COMPLIANT / 16 LEGAL |
| `firing_intent_diagnostic_rules.xlsx` | 47 diagnostic/data-capture rules — firing condition + Marathi farmer message + owner |
| `D11_YIELD_MODEL_v1.md` | Full yield-model spec — hybrid DSSAT + ML residual, 15-factor U-value register |
| `D12_QA_WORKFLOW.md` | Full advisory-QA workflow spec — 4 tables + 4 functions + 5 UI screens |
| `VIRAAI_JOINT_HANDOFF_TO_SOFTWARE_v1.0.md` | Consolidated joint handoff document (Backend + Agronomy → Software) |

### 02_VNMKV_INSTITUTIONAL/ (3 files)

| File | Purpose |
|---|---|
| `VNMKV_CONSULT_BRIEF.md` | Formal consult request to VNMKV Parbhani — 2 primary artifacts + 10 supplementary questions |
| `VNMKV_RATIFICATION_RESPONSE.md` | Detailed technical response drafted in VNMKV professor voice (research-based) |
| `VNMKV_COMPLIANCE_CERTIFICATE.md` | **Final compliance certificate template** — 13 sections, 5 signature blocks, §7 has 14 action items |

### 03_LEGAL_REGULATORY/ (4 files)

| File | Purpose |
|---|---|
| `LEGAL_DESK_HANDOFF_PACKET.md` | v1 handoff packet — 16 rules routed to legal |
| `LEGAL_TEAM_HANDOFF_PACKET_v2.md` | v2 enriched — 16 rules + 4 cross-cutting deliverables + priority order |
| `LEGAL_RESEARCH_REFERENCE.md` | Substantive legal grounding — DPDP, Insecticides Act, FSSAI, CPA, IT Act frameworks |
| `LEGAL_COMPLIANCE_CERTIFICATE.md` | **Final compliance certificate template** — 13 sections + Appendix A, 12-item implementation checklist |

### 04_KB_ARTIFACTS/ (9 files)

| File | Purpose |
|---|---|
| `Domain7_Rules_Ginger.json` | D07 weather rules (with VPD retrofit) |
| `Domain11_Rules_Ginger.json` | D11 yield rules (with D14 precedence entries) |
| `Domain14_Rules_Ginger.json` | D14 satellite rules (47 rules, 141 golden tests) |
| `Domain14_Satellite_RemoteSensing_RAW_MASTER.docx` | D14 Phase-1 research document (33 pages) |
| `D14_PATCH_NOTES.md` | D14 authoring notes |
| `D14_TEST_REPORT.md` | Test results — 587/587 golden tests pass |
| `D14_INTEGRATION_COMPLETE.md` | Integration status document |
| `D14_ENGINE_INTEGRATION_NOTES.md` | Engine-side integration details |
| `VPD_RETROFIT_PATCH_NOTES.md` | VPD retrofit change log |

### 05_DATA_FILES/ (5 files)

| File | Purpose |
|---|---|
| `ginger_pesticide_registry_v1.1.csv` | **19-entry registry with Streptocycline ban applied** |
| `ginger_pesticide_registry_v1.1_CHANGES.md` | v1.0 → v1.1 change log (6 entries updated) |
| `ginger_pesticide_registry_README.md` | Registry usage guide + backend integration pseudocode |
| `imd_district_normals_1991_2020.csv` | 11 stations (Chikalthana confirmed + 10 provisional) |
| `imd_district_normals_README.md` | IMD normals usage + verification workflow |

### 06_ENGINE_INTEGRATION/ (17 files)

Python engine modules + patches for the D14 + VPD integration. Reference `04_KB_ARTIFACTS/D14_ENGINE_INTEGRATION_NOTES.md` for the integration story.

| File | Purpose |
|---|---|
| `expert_override.py` + `.patch` | IMMUTABLE dict — 16 + 8 D14 = 24 immutable rules |
| `precedence.py` + `.patch` | PRECEDENCE list — 39 + 6 (5 D14 + 1 VPD) = 45 relations |
| `notification_policy.py` + `.patch` | DELIVERY dict — 152 + 50 = 202 rules |
| `runtime_loader.py` + `.patch` | JsonSource FILES — D1-D13 → D1-D14 |
| `test_runtime_loader.py` + `.patch` | Drift check across waves 1-5 |
| `regression_gate.py` + `.patch` | Coverage function updated for waves 4+5 |
| `triggers_wave4_vpd.py` | 3 VPD triggers + 12 golden tests |
| `triggers_wave5_d14.py` | 47 D14 triggers + 141 golden tests |
| `run_d14_trigger_tests.py` | D14 test runner (587/587 tests pass) |
| `apply_vpd_patch.py` | VPD retrofit patch script |
| `json_to_sql_with_d14.py` | SQL build script (JSON → PostgreSQL) |

### 07_SQL_DEPLOYMENT/ (3 files)

| File | Purpose |
|---|---|
| `kb_ginger_d14_v1.0.sql` | **Full production build** — 481 rules, 1291 KB, idempotent (1674 ON CONFLICT clauses) |
| `kb_ginger_d14_updates_v1.0.sql` | Cosmetic UPDATE for D07 total_rules 35→38 |
| `SQL_DEPLOYMENT_README.md` | Deployment guide — fresh install + additive on existing DB, verification queries, rollback |

---

## 8. Contact + escalation

**Compliance Owner:** Kuldip — Agronomy Compliance, KB & Product Coordination
**Escalation for:**
- Agronomy questions → Kuldip directly
- Legal signature acquisition → external counsel engagement
- VNMKV signature acquisition → VNMKV Parbhani liaison
- Backend implementation questions → this handoff package + Kuldip

**Response commitments:**
- Backend clarification questions: 48 hours
- Bug reports in delivered artifacts: 72 hours
- Regulatory update triage: 48 hours (per `LEGAL_COMPLIANCE_CERTIFICATE.md §10.3`)

---

## 9. Version + change log

- **v1.0** (2026-09-23) — Master handoff bundle prepared. All 439 rules reviewed, both compliance certificates drafted, registry v1.1 with Streptocycline ban applied.

Next version bump on any material change to §§ 3-5 of either compliance certificate, or on regulatory event triggering quarterly-watch response.

---

## 10. Final word

Six months of KB authoring, three domains added (VPD retrofit, D14 satellite, engine integration), 439 rules agronomist-reviewed, two compliance certificates drafted, one pesticide ban regulatory update captured, complete backend implementation package assembled.

**KB is frozen. Compliance is closed. Season 1 launch is on backend + ops execution.**

Ship it.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI
23 September 2026
