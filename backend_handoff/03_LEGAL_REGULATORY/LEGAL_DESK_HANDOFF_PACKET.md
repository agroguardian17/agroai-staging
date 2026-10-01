# Legal Desk Handoff Packet — VIRAAI Ginger KB
## 16 LEGAL_REVIEW_REQUIRED rules — clearance request

**Date:** 2026-09-23
**From:** Kuldip — Agronomy Compliance Owner
**To:** Legal / Regulatory desk (via product lead)
**Deadline requested:** 15 October 2026 (Season 1 pilot activation dependency)
**Basis:** `AGRONOMY_COMPLIANCE_v1.md §2.3` — 16 rules routed out of agronomy scope

---

## 1. What agronomy has done / not done

**Done:** Reviewed every one of the 16 rules for **agronomic intent** — all 16 are agronomically sound and functionally necessary. The gates they enforce (consent, food-safety block, scheme pre-sanction) are correct.

**Not done — needs legal/regulatory desk:**
1. **Wording verification** — is the block/consent text legally defensible under current DPDP Act 2023, FSSAI 2011 rules, CIB Insecticides Act, and applicable Maharashtra GRs?
2. **Reference citation update** — some rules cite general sources; production rules need specific Act section / Gazette number / GR number.
3. **Sign-off** — one line per rule confirming the legal team owns the wording.

**Nothing agronomy can decide on these 16.** Blocking Season 1 pilot activation until clearance received.

---

## 2. The 16 rules — clearance requests

### 2.1 DPDP Act 2023 (privacy / consent) — 4 rules

**Reference framework needed:**
- Digital Personal Data Protection Act 2023, specifically §§ 6 (consent), 7 (legitimate use), 8 (data fiduciary obligations), 11 (right to erasure), 20 (children's data)
- Rules under DPDP Act (as notified from time to time by MeitY)

#### R1 · D12-DPDP-001 (immutable, blocking) — Advisory consent

- **Current wording:** *"Obtain explicit consent in Marathi, in plain language, at registration. State the purpose, the retention period and the right to erasure."*
- **Legal questions:**
  1. Is the current Marathi consent template compliant with DPDP §6 (explicit, informed, free consent)?
  2. What retention period should we state for farmer records (recommendation: end of season + 3 years for economics + 7 years for regulatory)?
  3. Is our right-to-erasure workflow (§ in product spec) sufficient to satisfy DPDP §11?
- **Deliverable requested:** approved Marathi consent template + retention statement + erasure SOP
- **Sign-off form:** *"D12-DPDP-001 wording ratified per DPDP §6/§11 — [name, date, signature]"*

#### R2 · D12-DPDP-002 (immutable, blocking) — Data sharing consent

- **Current wording:** *"Require separate consent. Consent to receive advisory does not cover data sharing. Refusing the second consent must not stop the service."*
- **Legal questions:**
  1. Is a separate opt-in consent screen the correct implementation of DPDP purpose-limitation (§8)?
  2. What must be disclosed to the farmer at the second consent (partner identities, data categories, retention)?
  3. Are we obligated to renew this consent annually or on partner change?
- **Deliverable requested:** approved Marathi sharing-consent template + partner disclosure list format
- **Sign-off form:** as above

#### R3 · D14-DP-001 (immutable, red) — Third-party satellite display

- **Current wording:** *"Displaying a plot-level satellite derivative outside the plot owner without consent is a DPDP Act 2023 violation. Aggregate first."*
- **Legal questions:**
  1. Is plot-level NDVI on a cluster dashboard a personal data disclosure under DPDP if the plot maps to a named farmer?
  2. At what aggregation level (cluster of 3? 5? 8?) does the display cease to be personal data?
  3. Is farmer-to-farmer benchmarking (own plot vs anonymised peer) allowed under legitimate use (§7)?
- **Deliverable requested:** minimum aggregation threshold + peer-comparison disclosure text
- **Sign-off form:** as above

#### R4 · D06-FH-002 (yellow) — Farmer health / disease history data

- **Current wording:** *"Soft rot confirmed on any plot within the cluster → notify plot owners of preventive drenching."*
- **Legal questions:**
  1. Does disease history at a farm count as farmer-attributable personal data under DPDP?
  2. Can cluster notifications name the source plot (usually no; confirm)?
  3. What retention applies to disease history — same as advisory or longer for epidemiological pattern analysis?
- **Deliverable requested:** notification template + retention rule
- **Sign-off form:** as above

---

### 2.2 FSSAI / CIB&RC / MRL (food safety + pesticide registration) — 8 rules

**Reference framework needed:**
- Insecticides Act 1968 & CIB&RC registered crop-input list (Central Insecticides Board, current version)
- FSSAI Gazette notifications on MRLs (specifically S.O. 2892(E) 2011 as amended)
- FSSAI regulations on residues in raw agricultural produce (2023 update)

#### R5 · D05-CH-001 (immutable, blocking) — Banned molecule refuse

- **Current wording:** *"BHC and monocrotophos are banned or restricted. No agronomic judgement changes that."*
- **Legal questions:**
  1. Confirm current list of molecules banned under Insecticides Act 1968 amendments as of 2026-09 (BHC ✓, monocrotophos ✓, endosulfan ✓, phorate?, methyl parathion?).
  2. Is our current blocklist (see `ginger_pesticide_registry.csv`, 7 CONFIRMED_BLOCKLIST entries) complete against the CIB registered-crops list for ginger?
- **Deliverable requested:** current CIB banned-list snapshot + gap analysis vs our blocklist
- **Sign-off form:** *"Ginger pesticide blocklist ratified per Insecticides Act as of [date] — [signature]"*

#### R6 · D05-CH-002 (yellow) — Chemical option gating

- **Current wording:** *"Before any chemical option is presented, verify CIB label + PHI + IPM alternatives + FRAC/IRAC rotation."*
- **Legal questions:**
  1. Is our CIB-label-verification workflow (mapper → registry lookup → block if unregistered) legally sufficient?
  2. Do we need a formal audit trail of every chemical shown/blocked (recommendation: yes; confirm)?
- **Deliverable requested:** audit log requirement statement
- **Sign-off form:** as above

#### R7 · D05-CH-003 (immutable, blocking) — PHI food safety

- **Current wording:** *"Residue on a harvested rhizome is a food safety matter, not an agronomic preference."*
- **Legal questions:**
  1. What are current FSSAI MRL values for the 11 registered chemicals in our registry (see `ginger_pesticide_registry.csv`)?
  2. Are export-market MRLs (EU, USA, Japan) additionally required for produce we may export?
- **Deliverable requested:** current FSSAI MRL table for ginger + export-market variance table
- **Sign-off form:** as above

#### R8 · D05-CH-007 (yellow) — Label-claim compliance

- **Current wording:** *"Do not recommend a product outside its label crop/dose/timing."*
- **Legal questions:**
  1. What is our liability if farmer follows our recommendation and MRL exceeds FSSAI limit (assumption: system carries advisory liability; verify)?
  2. Is the current disclaimer text in advisories sufficient to shift residual liability to farmer's own compliance?
- **Deliverable requested:** approved disclaimer text + liability framework
- **Sign-off form:** as above

#### R9 · D05-CH-008 (red) — Blocklist-hit alert

- **Current wording:** *"Warn farmer; do not advise harvest/sale on that basis; direct to agronomist."*
- **Legal questions:**
  1. Are we obligated to report the blocklist-hit to any authority (MMB / APEDA)?
  2. Is our record-keeping of blocklist events (`phi_blocklist_hit = TRUE` events in advisory_log) sufficient audit trail?
- **Deliverable requested:** reporting obligation clarification + audit log spec
- **Sign-off form:** as above

#### R10 · D06-CH-001 (immutable, blocking) — Fungicide-vs-bacterium block

- **Current wording:** *"No fungicide has activity against a bacterium. Offering one wastes money while the pathogen spreads."*
- **Legal questions:**
  1. Any consumer protection / misleading advertisement risk if we historically recommended fungicide for bacterial wilt (Season 0 legacy)?
  2. Do we need to flag past advisories for revision?
- **Deliverable requested:** legacy-advisory disclosure statement (if any)
- **Sign-off form:** as above

#### R11 · D06-CH-002 (yellow) — Fungicide gating

- **Current wording:** *"Fungicide only presented after differential diagnosis excludes bacteria."*
- **Legal questions:** same as R6 (audit trail sufficiency)
- **Sign-off form:** as above

#### R12 · D09-PR-002 (immutable, red) — SO2 fumigation caution

- **Current wording:** *"SO2 residue limits are unverified. Until they are, this method is not first choice."*
- **Legal questions:**
  1. Current FSSAI SO2 residue limit for dried ginger (recommendation: check FSSAI 2.9.10)?
  2. Export-market SO2 tolerances (EU 150 mg/kg?, USA?, Middle East?)?
  3. Should we permit SO2 fumigation for export produce only with certified operator, or block entirely?
- **Deliverable requested:** SO2 limits + operator-certification requirement + export vs domestic decision
- **Sign-off form:** as above

---

### 2.3 Maharashtra government schemes — 5 rules

**Reference framework needed:**
- Current Maharashtra Agriculture Department Government Resolutions (GRs) for each scheme
- PMKSY / PM-KMY / NHM / RKVY / NMSA scheme operational guidelines
- Ministry of Agriculture, GoI notifications for centrally-sponsored schemes

#### R13 · D10-SUB-002 (immutable, blocking) — Pre-sanction gate

- **Current wording:** *"Work started before pre-sanction is not eligible for subsidy."*
- **Legal questions:**
  1. Current Maharashtra Agri Dept GR reference for the pre-sanction process (which year's GR is authoritative)?
  2. Any exceptions (emergency planting due to weather, etc.)?
  3. Is the "pre-sanction letter" a physical document, DBT portal entry, or both?
- **Deliverable requested:** authoritative GR number + workflow verification
- **Sign-off form:** *"D10-SUB-002 verified against Maharashtra GR [number/date] — [signature]"*

#### R14 · D10-PMKSY-001 through D10-PMKSY-004 (info to yellow) — PMKSY drip subsidy claims

- **Current wording (composite):** Drip installation subsidy claims per PMKSY guidelines.
- **Legal questions:**
  1. Current PMKSY per-hectare subsidy rate for Maharashtra (SC/ST/other categories)?
  2. Ginger's eligibility category (horticulture / high-value crop)?
  3. Documentation checklist per current portal (Mahaagri.gov.in)?
- **Deliverable requested:** current subsidy rate + eligibility category + document checklist
- **Sign-off form:** as above

#### R15 · D10-NHM-* (planning content) — NHM scheme guidance

- **Legal questions:**
  1. Ginger's coverage under current NHM operational guidelines?
  2. Cluster/FPO requirements for NHM eligibility?
- **Deliverable requested:** NHM eligibility snapshot
- **Sign-off form:** as above

#### R16 · Others (D10-RKVY, D10-NMSA — planning content, low risk)

- **Legal questions:** minimal — confirm scheme names + current operational status
- **Deliverable requested:** one-line scheme-active-yes/no confirmation
- **Sign-off form:** as above

---

## 3. Deliverable format requested from Legal Desk

For each of the 16 rules, one row in this response table:

| Rule ID | Wording OK as-is? | Corrected wording (Marathi + English) | Reference citation | Sign-off name + date |
|---|:---:|---|---|---|
| D12-DPDP-001 | Y/N | ... | DPDP Act 2023 §... | ... |
| ... | ... | ... | ... | ... |

Backend applies the corrected wording verbatim via KB rewrite pipeline; nothing gets reworded again downstream.

---

## 4. Reference documents legal desk will need

Attached separately by product/ops team:
- `ginger_pesticide_registry.csv` — the 19-entry registry from agronomy (delivered 2026-09-23)
- `AGRONOMY_COMPLIANCE_v1.md` — full compliance record with each rule's agronomic intent
- Current KB rule JSON snapshots for the 16 rules
- Existing farmer consent screens (product design)
- Existing WhatsApp advisory templates (Meta approved / pending)
- Any historical legal opinions on file for VIRAAI / Agro-Guardian

---

## 5. Deadline & escalation

- **Requested completion:** 15 October 2026
- **Blocks:** Season 1 pilot activation (target 1 November 2026)
- **Escalation path:** if any of the 16 rules cannot be cleared by 15 Oct, defer that rule's advisory delivery in Season 1 (rule remains inactive; system continues without it). Only D12-DPDP-001 is truly launch-blocking — cannot onboard farmers without consent template.

---

## 6. What agronomy commits to on our side

- Zero re-review of legal wording once returned — legal's word is final on wording
- If legal recommends removing a rule entirely, agronomy accepts and documents the agronomic gap in `AGRONOMY_COMPLIANCE_v1.md` open items
- Any future rule with legal/regulatory scope will be routed through legal desk pre-authoring, not post-authoring

---

## 7. Sign-off from agronomy on this packet

Prepared and delivered by Kuldip — Agronomy Compliance Owner, 2026-09-23.

Legal desk owns response and clearance. Agronomy will implement the returned wording without amendment.

— Kuldip
Agronomy Compliance Owner
VIRAAI / Agro-Guardian AI

*End of Legal Desk Handoff Packet v1.0*
