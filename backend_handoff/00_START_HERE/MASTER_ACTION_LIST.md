# Master Action List — Backend Team
## Season 1 Launch (1 November 2026) — Deployment Sequence

**Prepared:** 23 September 2026
**Owner:** Kuldip → Backend Team
**Total actions:** 32 items across 4 tracks

---

## Track A — Launch-critical (must complete before farmer onboarding)

### A1. Database deployment (Day 0)

- [ ] **A1.1** Apply `07_SQL_DEPLOYMENT/kb_ginger_d14_v1.0.sql` to production Postgres
  - Expected: 481 rules loaded, 14 domains, 1291 KB, atomic transaction
  - Rollback: `BEGIN; \i kb_ginger_d14_v1.0.sql; ROLLBACK;` (before COMMIT)
  - Verify: `SELECT COUNT(*) FROM kb_rules; -- expect 481`
- [ ] **A1.2** Apply `07_SQL_DEPLOYMENT/kb_ginger_d14_updates_v1.0.sql` (cosmetic D07 counter)
- [ ] **A1.3** Load `ginger_pesticide_registry_v1.1.csv` into `_PHI_DAYS_BY_GROUP` map
- [ ] **A1.4** Wire blocklist gate: 9 molecules block PHI calc + emit `phi_blocklist_hit = TRUE`

### A2. Engine integration (Day 1-2)

- [ ] **A2.1** Deploy patched engine files from `06_ENGINE_INTEGRATION/`:
  - `expert_override.py` (24 IMMUTABLE)
  - `precedence.py` (45 relations)
  - `notification_policy.py` (202 DELIVERY entries)
  - `runtime_loader.py` (14 domains)
- [ ] **A2.2** Deploy wave triggers (`triggers_wave4_vpd.py` + `triggers_wave5_d14.py`)
- [ ] **A2.3** Run drift check: `python3 test_runtime_loader.py` — expect all 4 sets match
- [ ] **A2.4** Run trigger tests: `python3 run_d14_trigger_tests.py` — expect 587/587 pass

### A3. DPDP compliance implementation (Day 3-5)

- [ ] **A3.1** Deploy Marathi consent template from `LEGAL_COMPLIANCE_CERTIFICATE.md §3.1` (D12-DPDP-001) at farmer registration
- [ ] **A3.2** Deploy mandatory farmer disclaimer from `LEGAL_COMPLIANCE_CERTIFICATE.md §7.2` on ALL advisory channels (WhatsApp, app, print)
- [ ] **A3.3** Implement age verification at enrollment (< 18 requires parental consent per DPDP § 9)
- [ ] **A3.4** Implement erasure request workflow — 30-day fulfillment SLA
- [ ] **A3.5** Implement withdrawal-of-consent — one-click accessible

### A4. Advisory audit trail (Day 3-5)

- [ ] **A4.1** Every advisory logged with rule ID, rule version, model version, confidence, validation gate results
- [ ] **A4.2** Immutable log storage (cryptographic hash chain OR append-only DB table)
- [ ] **A4.3** Retention: advisory logs 3 years, blocklist-hit events 7 years, farm/land records active + 3 years

### A5. NON_COMPLIANT rules rewrite (Day 5-14)

Rewrite these 8 rules per `AGRONOMY_COMPLIANCE_v1.md §2.2`:
- [ ] **A5.1** D08-WD-001 — replace blanket herbicide block with registered-herbicide-list gate
- [ ] **A5.2** D03-DS-001 — fix trigger to include `soil_texture_class == 'heavy'`
- [ ] **A5.3** D08-EU-002 — remove fixed 12.5% yield penalty, keep mechanism as CONDITIONAL
- [ ] **A5.4** D08-LY-001 — condition broad-ridge yield claim on soil/slope/drainage context
- [ ] **A5.5** D01-PH-004 — remove fixed 12.5% penalty
- [ ] **A5.6** D14-SR-002 — retag as `AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE`, drop unsupported prose
- [ ] **A5.7** D03-WL-003 — retag AGRO_GUARDIAN_CUSTOM, drop "more severe" comparison
- [ ] **A5.8** D07-CY-001 — retag AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE

---

## Track B — Short-term (30 days post-launch)

### B1. VNMKV-directed KB updates

- [ ] **B1.1** Update zone mapping per `VNMKV_COMPLIANCE_CERTIFICATE.md §4` (Western/Central/Eastern with TMI values)
- [ ] **B1.2** Update PHI values in registry per §5.2: Mancozeb 15-21, COC 15, Metalaxyl-M 30, Carbendazim seed-only, Imidacloprid 30-40
- [ ] **B1.3** Change D06-BW-001 trigger from `years_since_last_wilt < 3` to `< 5`
- [ ] **B1.4** Change D01-PW-001 late-planting from `MONTH IN [JUN, JUL]` to `planting_date > 2026-06-07`
- [ ] **B1.5** Move D02-LY-001 flat-layout-on-vertisol from CONDITIONAL to BLOCKING
- [ ] **B1.6** Add basal ZnSO₄ 25 kg/ha as default D02/D04 recommendation for Kannad plots
- [ ] **B1.7** Update site-index for Kannad = 0.75-0.85 (Western Scarcity zone)

### B2. Legal certificate implementation

- [ ] **B2.1** Deploy 15 corrected rules from `LEGAL_COMPLIANCE_CERTIFICATE.md §§ 3-5` (D12-DPDP-002, D14-DP-001, D06-FH-002, D05-CH-001..008, D06-CH-001/002, D09-PR-002, D10-SUB-002, D10-PMKSY-*, D10-NHM-*)
- [ ] **B2.2** Implement data retention schedule per §8 (6 categories)
- [ ] **B2.3** Add cross-border TOS to farmer registration per §9.3
- [ ] **B2.4** Set up quarterly regulatory-watch calendar per §10

### B3. D11 yield model backend build

Per `D11_YIELD_MODEL_v1.md`:
- [ ] **B3.1** Create 5 tables: `variety_potential`, `yield_u_values`, `site_index_config`, `yield_prediction_log`, `yield_actual`
- [ ] **B3.2** Seed `variety_potential` (5 varieties), `yield_u_values` (15 factors), `site_index_config` (heuristic multipliers)
- [ ] **B3.3** Build `predict_yield(plot_id, as_of_dap)` API per §7
- [ ] **B3.4** Implement bootstrap CI (Monte Carlo, 1000 draws) per §4
- [ ] **B3.5** Farmer-facing output format per §8 (band + top-3 factors, never single number)

### B4. D12 QA workflow backend build

Per `D12_QA_WORKFLOW.md`:
- [ ] **B4.1** Create 4 tables: `advisory_classification`, `non_compliance_reason`, `bias_observation`, `photo_label` + `cluster_config`
- [ ] **B4.2** Build 4 functions: `classify_advisory`, `capture_non_compliance`, `assign_cluster`, weekly digest generator
- [ ] **B4.3** Build review UI per §6 (5 screens)
- [ ] **B4.4** Set up Sunday 18:00 IST cron for weekly digest

### B5. Firing-intent rules wiring

- [ ] **B5.1** Wire 47 diagnostic/data-capture rules from `firing_intent_diagnostic_rules.xlsx` — set firing conditions + farmer messages
- [ ] **B5.2** Wire `soil_texture_class_source` field re-derivation on lab entry

---

## Track C — Business track (parallel, no launch blocking)

- [ ] **C1** Legal desk engagement — present `LEGAL_COMPLIANCE_CERTIFICATE.md` to admitted advocate for review + signature
- [ ] **C2** VNMKV Parbhani engagement — present `VNMKV_COMPLIANCE_CERTIFICATE.md` to faculty for review + signature
- [ ] **C3** WhatsApp Meta template approval — submit disclaimer + consent templates
- [ ] **C4** USGS credentials for Landsat LST job
- [ ] **C5** Main Node + Sub Node hardware install at Kannad pilot plots
- [ ] **C6** Kannad pilot plot enrollment — ≥3 plots per cluster for peer baseline
- [ ] **C7** D12 QA workflow UI wireframe (product design, feeds back to B4.3)
- [ ] **C8** Farmer-app plot polygon capture UX (blocks D14 rules)
- [ ] **C9** DPDP consent flow UX design (visual layer over A3.1)

---

## Track D — Season 1 field data (post-launch dependency)

- [ ] **D1** Season 1 field data collection SOP execution
- [ ] **D2** Empirical U-value calibration data submission → VNMKV agromet cell (post-harvest March-April 2027)
- [ ] **D3** Anonymised aggregate field data → VNMKV per §11 commitment
- [ ] **D4** Joint VNMKV post-season review meeting (May 2027)
- [ ] **D5** ML residual model training (activate when 100+ paired (predicted, actual) yield tuples available)
- [ ] **D6** CONDITIONAL rules elevation to COMPLIANT based on empirical data
- [ ] **D7** Registry v1.2 with any new regulatory notifications from quarterly watch

---

## Timeline summary

```
Day 0-2       [Track A1-A2]     DB + Engine deploy               ← 🚨 blocker
Day 3-5       [Track A3-A4]     DPDP + Audit trail               ← 🚨 blocker
Day 5-14      [Track A5]        8 NON_COMPLIANT rewrites         ← 🚨 blocker
Day 14-30     [Track B1-B5]     VNMKV updates + D11/D12 build    ← short-term
Parallel      [Track C]         Legal/VNMKV/ops/hardware         ← non-blocking
Nov 2026 →    [Track D]         Season 1 field data              ← ongoing
Mar-Apr 2027  [Track D5-D7]     Empirical calibration + v1.2     ← Season 2 prep
```

**Launch date target:** 1 November 2026
**Full-hybrid model target:** Season 2 activation (June 2027)

---

## Failure-mode escalation

If any Track A item cannot complete by launch date:
- **A1-A2 failure:** blocks launch entirely — escalate to Backend Lead + Kuldip
- **A3 failure (DPDP):** blocks farmer onboarding — legal fallback needed
- **A4 failure (audit trail):** blocks launch — no advisory can go out without audit
- **A5 failure (NON_COMPLIANT rewrite):** defer affected rules; system launches with reduced coverage

If Track B slips by 30 days: acceptable; document in monthly review.
If Track C slips: business track, product/ops owns.
If Track D delayed: Season 2 model activation slips.

---

## Sign-off

Prepared by Kuldip — Agronomy Compliance Owner, 2026-09-23.

Backend team to acknowledge receipt and confirm timeline commitments per Track A.

— Kuldip
