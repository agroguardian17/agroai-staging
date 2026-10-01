# Legal Team Handoff Packet v2 — VIRAAI Ginger KB
## 16 LEGAL_REVIEW_REQUIRED rules + companion legal research

**Date:** 2026-09-23
**From:** Kuldip — Agronomy Compliance Owner, VIRAAI Agro-Guardian AI
**To:** Legal / Regulatory desk (or third-party legal consultation)
**Deadline requested:** 15 October 2026 (Season 1 pilot activation dependency)
**Basis documents:**
- `AGRONOMY_COMPLIANCE_v1.md §2.3` — 16 rules routed out of agronomy scope
- `VNMKV_COMPLIANCE_CERTIFICATE.md` — regulatory updates (Streptocycline ban)
- `ginger_pesticide_registry_v1.1.csv` — updated 19-entry registry
- `LEGAL_RESEARCH_REFERENCE.md` — companion reference material (delivered alongside)

---

## 1. What agronomy has done / not done

**Done (by agronomy compliance owner):**
- Reviewed all 16 LEGAL_REVIEW_REQUIRED rules for **agronomic intent** — every gate they enforce is agronomically sound and functionally necessary
- Updated pesticide registry to v1.1 with Streptocycline ban applied per Union Ministry gazette (1 January 2024)
- Attached companion `LEGAL_RESEARCH_REFERENCE.md` — substantive legal grounding document covering DPDP Act 2023, Insecticides Act 1968, FSSAI regulations, MoEFCC bans, Maharashtra schemes, Consumer Protection Act 2019, IT Act 2000

**Not done — needs legal team:**
1. **Wording verification** — is the block/consent text legally defensible under current DPDP Act 2023, FSSAI regulations, CIB Insecticides Act, and applicable Maharashtra GRs?
2. **Reference citation update** — some rules cite general sources; production rules need specific Act section / Gazette number / GR number
3. **Sign-off** — one line per rule confirming the legal team owns the wording
4. **Liability framework** — how much residual liability sits with VIRAAI / farmer / label-maker for AI-advisory outcomes

**Nothing agronomy can decide on these 16.** Blocking Season 1 pilot activation until clearance received.

---

## 2. The 16 rules — clearance requests grouped by domain

### 2.1 DPDP Act 2023 (privacy / consent) — 4 rules

**Reference framework needed:**
- Digital Personal Data Protection Act 2023, specifically §§ 4-11 (grounds/consent/notice), §§ 12-16 (fiduciary obligations), § 20 (children under 18), § 27 (grievance)
- DPDP Rules 2025 as notified by MeitY
- IT Act 2000 §§ 43A + 72A (residual data-protection provisions still in force)
- Consumer Protection Act 2019 §§ 2(9), 2(47) (services & unfair trade practice)

#### R1 · D12-DPDP-001 (immutable, blocking) — Advisory consent

- **Current wording:** *"Obtain explicit consent in Marathi, in plain language, at registration. State the purpose, the retention period and the right to erasure."*
- **Farmer-facing intent:** Data-fiduciary notice + explicit consent per DPDP § 5-6
- **Legal questions:**
  1. Is the current Marathi consent template compliant with DPDP § 6 (specific, informed, unconditional, unambiguous consent)?
  2. What retention period should we state? Recommendation: end of season + 3 years (economics) + 7 years (regulatory audit) — please confirm/correct
  3. Is our right-to-erasure workflow sufficient to satisfy DPDP § 12(2)? Timeline requirements?
  4. Does the notice under § 5 (before or at time of consent) need any specific disclosures we're missing?
  5. Is farmer's WhatsApp number classifiable as "personal data" or "contact identifier"? Different consent thresholds?
- **Deliverable requested:** approved Marathi consent template + retention statement + erasure SOP + notice content spec
- **Sign-off form:** *"D12-DPDP-001 wording ratified per DPDP § 6 / § 12 — [name, designation, date, signature]"*

#### R2 · D12-DPDP-002 (immutable, blocking) — Data sharing consent

- **Current wording:** *"Require separate consent. Consent to receive advisory does not cover data sharing. Refusing the second consent must not stop the service."*
- **Legal questions:**
  1. Is a separate opt-in consent screen the correct implementation of purpose-limitation (DPDP § 6(4))?
  2. What must be disclosed to the farmer at the second consent — partner identities, data categories, retention, purpose?
  3. Are we obligated to renew this consent annually or on partner change?
  4. Cross-border data transfer implications if any research partner is outside India (DPDP § 16)?
  5. Data-sharing with government schemes (e.g., MSAMB, MMB) — different consent bar?
- **Deliverable requested:** approved Marathi sharing-consent template + partner disclosure list format + cross-border TOS
- **Sign-off form:** as R1

#### R3 · D14-DP-001 (immutable, red) — Third-party satellite display

- **Current wording:** *"Displaying a plot-level satellite derivative outside the plot owner without consent is a DPDP Act 2023 violation. Aggregate first."*
- **Legal questions:**
  1. Is plot-level NDVI on a cluster dashboard a personal-data disclosure under DPDP if the plot maps to a named farmer?
  2. At what aggregation level (cluster of 3? 5? 8?) does the display cease to be personal data — legal threshold for "de-identification" under DPDP § 3(x)?
  3. Is farmer-to-farmer benchmarking (own plot vs anonymised peer) allowed under legitimate use § 7(a) or § 7(b)?
  4. Satellite imagery from Sentinel/Landsat is public — but our plot-attributed derivative — where does personal data start?
- **Deliverable requested:** minimum aggregation threshold + peer-comparison disclosure text
- **Sign-off form:** as R1

#### R4 · D06-FH-002 (yellow) — Farmer health / disease history data

- **Current wording:** *"Soft rot confirmed on any plot within the cluster → notify plot owners of preventive drenching."*
- **Legal questions:**
  1. Does disease history at a farm count as farmer-attributable personal data under DPDP?
  2. Can cluster notifications name the source plot? (Usually no; confirm and specify anonymisation shape)
  3. What retention applies to disease history — same as advisory or longer for epidemiological pattern analysis?
  4. Is aggregate disease-cluster data (used for research) exempt under DPDP § 17(2)(b) — public interest / research?
- **Deliverable requested:** notification template + retention rule + research-exemption applicability
- **Sign-off form:** as R1

---

### 2.2 FSSAI / CIB&RC / MRL (food safety + pesticide registration) — 8 rules

**Reference framework needed:**
- Insecticides Act 1968 & amendments; Insecticides Rules 1971
- Central Insecticides Board & Registration Committee (CIB&RC) registered crop-input list — current version
- FSSAI Gazette notifications on MRLs — specifically S.O. 2892(E) 2011 as amended
- FSSAI (Contaminants, Toxins and Residues) Regulations 2011 + 2023 amendment
- Union Ministry of Agriculture gazette notifications on bans (chlorpyriphos, monocrotophos, endosulfan, streptocycline)
- WHO Codex Alimentarius MRL where applicable for export

#### R5 · D05-CH-001 (immutable, blocking) — Banned molecule refuse

- **Current wording:** *"BHC and monocrotophos are banned or restricted. No agronomic judgement changes that."*
- **Agronomy update:** Registry v1.1 now blocks 9 molecules including **Streptocycline (1 Jan 2024 gazette ban)**
- **Legal questions:**
  1. Confirm current list of molecules banned under Insecticides Act 1968 amendments as of 2026-09
  2. Is our current blocklist (9 entries in `ginger_pesticide_registry_v1.1.csv`) complete against the CIB registered-crops list for ginger?
  3. Any pending ban proposals we should pre-implement for future-proofing?
  4. Is the "not registered on ginger" logic legally sufficient basis for blocking, or do we need an explicit ban notification per molecule?
- **Deliverable requested:** current CIB banned-list snapshot + gap analysis vs our blocklist + pre-implementation recommendations
- **Sign-off form:** *"Ginger pesticide blocklist ratified per Insecticides Act as of [date] — [signature]"*

#### R6 · D05-CH-002 (yellow) — Chemical option gating

- **Current wording:** *"Before any chemical option is presented, verify CIB label + PHI + IPM alternatives + FRAC/IRAC rotation."*
- **Legal questions:**
  1. Is our CIB-label-verification workflow (mapper → registry lookup → block if unregistered) legally sufficient?
  2. Do we need a formal audit trail of every chemical shown/blocked? Retention period for audit trail?
  3. Advisory-based liability — if a farmer follows our label-verified recommendation and residue exceeds MRL, who is liable — VIRAAI / label-holder / farmer?
- **Deliverable requested:** audit log requirement statement + liability framework
- **Sign-off form:** as R5

#### R7 · D05-CH-003 (immutable, blocking) — PHI food safety

- **Current wording:** *"Residue on a harvested rhizome is a food safety matter, not an agronomic preference."*
- **Agronomy update:** Registry v1.1 has VNMKV-ratified PHI values (Mancozeb 15-21, COC 15, Metalaxyl-M 30, Carbendazim seed-only, Imidacloprid 30-40)
- **Legal questions:**
  1. Do our v1.1 PHI values match current FSSAI MRL enforcement thresholds?
  2. Export-market MRLs (EU, USA, Japan, Middle East) additionally required for produce we may export?
  3. Codex Alimentarius reference MRLs where FSSAI is silent?
  4. Farmer disclaimer text if produce is domestic-only vs export-eligible
- **Deliverable requested:** current FSSAI MRL table for ginger + export-market variance table + domestic/export disclaimer templates
- **Sign-off form:** as R5

#### R8 · D05-CH-007 (yellow) — Label-claim compliance

- **Current wording:** *"Do not recommend a product outside its label crop/dose/timing."*
- **Legal questions:**
  1. Off-label advisory — even with VNMKV backing — legally defensible? (Ex: Metalaxyl-M has various formulations; some ginger-labelled, some not)
  2. Liability transfer via disclaimer — how much residual sits with VIRAAI?
  3. Prescription-like advisory — do we need an agri-technologist certification for our recommendations to carry legal weight?
- **Deliverable requested:** approved disclaimer text + liability framework + certification requirement (if any)
- **Sign-off form:** as R5

#### R9 · D05-CH-008 (red) — Blocklist-hit alert

- **Current wording:** *"Warn farmer; do not advise harvest/sale on that basis; direct to agronomist."*
- **Agronomy update:** Registry v1.1 blocklist gate enforces this for 9 molecules including Streptocycline
- **Legal questions:**
  1. Are we obligated to report blocklist-hit events to any authority (MMB / APEDA / State Agri Dept)?
  2. Data-retention for blocklist-hit records — what period, what format?
  3. Whistleblower protections if farmer or system reports illegal input?
  4. Recall obligations if farmer has already harvested crop treated with banned molecule?
- **Deliverable requested:** reporting obligation clarification + audit log spec + recall SOP
- **Sign-off form:** as R5

#### R10 · D06-CH-001 (immutable, blocking) — Fungicide-vs-bacterium block

- **Current wording:** *"No fungicide has activity against a bacterium. Offering one wastes money while the pathogen spreads."*
- **Legal questions:**
  1. Any consumer protection / misleading advertisement risk if we historically recommended fungicide for bacterial wilt (Season 0 legacy)?
  2. Do we need to flag past advisories for revision + notify affected farmers?
- **Deliverable requested:** legacy-advisory disclosure statement (if any)
- **Sign-off form:** as R5

#### R11 · D06-CH-002 (yellow) — Fungicide gating

- **Current wording:** *"Fungicide only presented after differential diagnosis excludes bacteria."*
- **Legal questions:** same as R6 (audit trail sufficiency + liability)
- **Sign-off form:** as R5

#### R12 · D09-PR-002 (immutable, red) — SO2 fumigation caution

- **Current wording:** *"SO2 residue limits are unverified. Until they are, this method is not first choice."*
- **Legal questions:**
  1. Current FSSAI SO2 residue limit for dried ginger (recommendation: check FSSAI regulation 2.9.10)?
  2. Export-market SO2 tolerances (EU 150 mg/kg; USA; Middle East)?
  3. Should we permit SO2 fumigation for export produce only with certified operator, or block entirely?
  4. Occupational-safety obligations (Factories Act) if farmer or processor uses SO2?
- **Deliverable requested:** SO2 limits + operator-certification requirement + export vs domestic decision + occupational safety note
- **Sign-off form:** as R5

---

### 2.3 Maharashtra government schemes — 5 rules

**Reference framework needed:**
- Current Maharashtra Agriculture Department Government Resolutions (GRs) for each scheme
- PMKSY / PM-KMY / NHM / RKVY / NMSA scheme operational guidelines (Ministry of Agriculture, GoI, latest circulars)
- DBT Maharashtra portal current specifications
- Right to Information Act 2005 (if we surface scheme-status data to farmer)

#### R13 · D10-SUB-002 (immutable, blocking) — Pre-sanction gate

- **Current wording:** *"Work started before pre-sanction is not eligible for subsidy."*
- **Legal questions:**
  1. Current Maharashtra Agri Dept GR reference for pre-sanction process — which GR is authoritative?
  2. Any exceptions (emergency planting due to weather, etc.)?
  3. Is the "pre-sanction letter" a physical document, DBT Maharashtra portal entry, or both?
  4. Are we obligated to file scheme applications on behalf of farmer, or only advise?
- **Deliverable requested:** authoritative GR number + workflow verification + agent-vs-advisor scope clarification
- **Sign-off form:** *"D10-SUB-002 verified against Maharashtra GR [number/date] — [signature]"*

#### R14 · D10-PMKSY-001 through D10-PMKSY-004 (info to yellow) — PMKSY drip subsidy claims

- **Current wording (composite):** Drip installation subsidy claims per PMKSY guidelines
- **Legal questions:**
  1. Current PMKSY per-hectare subsidy rate for Maharashtra (SC/ST/OBC/general category variance)?
  2. Ginger's eligibility category (horticulture / high-value crop / general agriculture)?
  3. Documentation checklist per current portal (Mahaagri.gov.in) — form numbers, attachment types, upload specifications?
  4. GST implications on subsidised inputs?
- **Deliverable requested:** current subsidy rate + eligibility category + document checklist + GST note
- **Sign-off form:** as R13

#### R15 · D10-NHM-* (planning content) — NHM scheme guidance

- **Legal questions:**
  1. Ginger's coverage under current NHM operational guidelines?
  2. Cluster/FPO requirements for NHM eligibility — minimum farmer count, minimum land area?
  3. Post-harvest infrastructure subsidies applicable to ginger processing?
- **Deliverable requested:** NHM eligibility snapshot + FPO requirements + post-harvest scheme map
- **Sign-off form:** as R13

#### R16 · Others (D10-RKVY, D10-NMSA — planning content, low risk)

- **Legal questions:** minimal — confirm scheme names + current operational status + any ginger-specific overlays
- **Deliverable requested:** one-line scheme-active-yes/no confirmation per scheme + ginger overlay note
- **Sign-off form:** as R13

---

## 3. Deliverable format requested from Legal Desk

For each of the 16 rules, one row in this response table:

| Rule ID | Wording OK as-is? | Corrected wording (Marathi + English) | Reference citation (Act § / Gazette / GR) | Sign-off name + date |
|---|:---:|---|---|---|
| D12-DPDP-001 | Y/N | ... | DPDP Act 2023 §... | ... |
| ... | ... | ... | ... | ... |

Backend applies the corrected wording verbatim via KB rewrite pipeline; nothing gets reworded again downstream.

Plus, four cross-cutting deliverables:
1. **Advisory-liability framework** — VIRAAI vs farmer vs label-holder allocation
2. **Data-retention schedule** — per data category, retention period, deletion trigger
3. **Cross-border data-transfer TOS** — if research partners are outside India
4. **Regulatory-watch cadence** — how often to refresh gazette-driven changes (recommendation: quarterly)

---

## 4. Reference documents attached

- `LEGAL_RESEARCH_REFERENCE.md` — substantive legal grounding covering DPDP Act 2023, Insecticides Act 1968, FSSAI regulations, MoEFCC ban notifications, Maharashtra schemes, Consumer Protection Act 2019, IT Act 2000 (delivered alongside this packet)
- `ginger_pesticide_registry_v1.1.csv` — updated 19-entry registry with Streptocycline ban applied
- `AGRONOMY_COMPLIANCE_v1.md` — full agronomy compliance record with each rule's agronomic intent
- `VNMKV_COMPLIANCE_CERTIFICATE.md` — VNMKV faculty ratification with regulatory updates
- Current KB rule JSON snapshots for the 16 rules (available on request)
- Existing farmer consent screens (product design; separate file)
- Existing WhatsApp advisory templates (Meta approved / pending; separate file)

---

## 5. Deadline & escalation

- **Requested completion:** 15 October 2026
- **Blocks:** Season 1 pilot activation (target 1 November 2026)
- **Launch-critical only:** Of the 16 rules, only **D12-DPDP-001** is truly launch-blocking — cannot onboard farmers without consent template. All others can be deferred (rule remains inactive; system continues without it) if legal cannot clear by 15 Oct
- **Escalation:** if legal desk unable to complete by 15 Oct, priority order for resolution:
  1. D12-DPDP-001 (farmer consent)
  2. D05-CH-* rules 5-9 (food safety chemicals — regulatory compliance)
  3. D12-DPDP-002 (data sharing)
  4. D14-DP-001 (satellite display)
  5. D06-FH-002 (disease-history data)
  6. D06-CH-001, D06-CH-002 (fungicide gating)
  7. D09-PR-002 (SO2 fumigation)
  8. D10-* (scheme rules — advisory only, low urgency)

---

## 6. What agronomy commits to on our side

- Zero re-review of legal wording once returned — legal's word is final on wording
- If legal recommends removing a rule entirely, agronomy accepts and documents the agronomic gap in `AGRONOMY_COMPLIANCE_v1.md` open items
- Any future rule with legal/regulatory scope will be routed through legal desk pre-authoring, not post-authoring
- Regulatory-watch discipline: quarterly refresh of blocklist entries against current CIB and MoEFCC gazettes (agronomy owns the notification; legal owns the response)

---

## 7. Sign-off from agronomy on this packet

Prepared and delivered by Kuldip — Agronomy Compliance Owner, 2026-09-23.

Legal desk owns response and clearance. Agronomy will implement the returned wording without amendment.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI

*End of Legal Team Handoff Packet v2.0*
