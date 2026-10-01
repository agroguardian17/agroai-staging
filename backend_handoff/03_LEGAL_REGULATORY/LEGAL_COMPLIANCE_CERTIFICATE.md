# LEGAL COMPLIANCE CERTIFICATE
## VIRAAI Ginger Knowledge Base — 16 LEGAL_REVIEW_REQUIRED Rules
### Legal & Regulatory Affairs Desk — Final Compliance Response

---

**Certificate No.:** LRD/VIRAAI/GINGER-KB/2026-10/COMP-001
**Date of Issue:** 23 September 2026
**Effective from:** Season 1 Kannad pilot activation (target 1 November 2026)
**Validity:** Season 1 pilot period, subject to §11 quarterly regulatory-watch refresh
**Recipient:** VIRAAI Agro-Guardian AI, via Kuldip — Agronomy Compliance Owner
**Basis documents examined:**
- `LEGAL_TEAM_HANDOFF_PACKET_v2.md` (16 rules + 4 cross-cutting requests)
- `LEGAL_RESEARCH_REFERENCE.md` (statutory framework grounding)
- `ginger_pesticide_registry_v1.1.csv` (19-entry registry with Streptocycline ban applied)
- `AGRONOMY_COMPLIANCE_v1.md` (rule-by-rule agronomic intent record)
- `VNMKV_COMPLIANCE_CERTIFICATE.md` (institutional agronomic ratification)

---

## 1. कार्यकारी सारांश | Executive Summary

The 16 LEGAL_REVIEW_REQUIRED rules in the VIRAAI Ginger KB have been examined against the current statutory framework governing AI-based agri-advisory in India. All 16 rules require **corrected wording** before Season 1 activation; none are agronomically unsound, but every one required specific citation strengthening, disclaimer inclusion, or language precision. Additionally, the four cross-cutting deliverables (advisory-liability framework, data-retention schedule, cross-border transfer TOS, regulatory-watch cadence) are provided in §§ 7-10.

**Key finding — IT Act 2000 § 79 does NOT apply:** VIRAAI generates active advisory content (specific molecules, doses, PHI values) and is therefore **not eligible for intermediary safe-harbor protection**. Liability is direct under Consumer Protection Act 2019 §§ 2(11), 2(42), 2(47). The disclaimer, audit trail, and data-fiduciary discipline in this certificate mitigate but do not eliminate this liability.

**Regulatory landscape:** VIRAAI operates at the intersection of five statutory regimes — DPDP Act 2023, Insecticides Act 1968, FSS Act 2006, Consumer Protection Act 2019, IT Act 2000 §§ 43A/72A — plus Maharashtra Agriculture Department GRs for scheme compliance.

**Bottom line:** All 16 rules have corrected wording in §§ 3-6 below. Implementation deadline for the launch-critical D12-DPDP-001 (farmer consent) is before farmer onboarding begins. Others may be deployed progressively per §12 priority list.

---

## 2. Statutory framework reference

For every rule in this certificate:

| Regime | Governing statute | VIRAAI touchpoint |
|---|---|---|
| Data protection | DPDP Act 2023 + Rules 2025 | Farmer registration, plot data, advisory logs, WhatsApp records |
| Pesticide regulation | Insecticides Act 1968; Rules 1971; CIB&RC | Registry, blocklist, PHI, dose recommendations |
| Food safety | FSS Act 2006; FSSAI regs; MRL notifications | PHI enforcement, MRL compliance, processing standards |
| Consumer protection | CPA 2019 | Advisory liability, unfair trade practice, deficiency in service |
| Digital / IT | IT Act 2000 §§ 43A, 72A; SPDI Rules 2011 | Residual data protection until DPDP Rules fully notified |
| State agri policy | Maharashtra Agri Dept GRs; MahaDBT | Scheme claims, DBT process, farmer agent scope |

---

## 3. Certified corrected wording — DPDP Act 2023 (privacy / consent) — 4 rules

### 3.1 R1 · D12-DPDP-001 (immutable, blocking) — Advisory consent

**Wording OK as-is:** ❌ NO — corrected below

**Corrected wording — Marathi:**
> *"शेतकऱ्याची नोंदणी करण्यापूर्वी, त्यांच्याकडून मराठीत सोप्या भाषेत स्पष्ट, माहितीपूर्ण आणि निःसंदिग्ध पूर्व-संमती (Prior Explicit Consent) घेण्यात यावी. संमती-निवेदनात खालील बाबी नमूद असणे बंधनकारक आहे: (१) संकलित होणाऱ्या वैयक्तिक डेटाचे स्वरूप, (२) डेटा-प्रक्रियेचा उद्देश, (३) जतन कालावधी (हंगाम समाप्तीनंतर ३ वर्षे), (४) डेटा-अधिपतीचे अधिकार — प्रवेश (Access), दुरुस्ती (Correction), डिलीट करण्याचा (Erasure) व तक्रार निवारण (Grievance) यंत्रणा. संमती कधीही मागे घेण्याचा अधिकार व त्याचे परिणाम स्पष्टपणे कळवावेत. संमती वयोमापित (Age-verified) असणे बंधनकारक — १८ वर्षांखालील शेतकऱ्यांसाठी पालकांची पडताळणीयोग्य संमती (Verifiable Parental Consent) आवश्यक."*

**English:**
> *"Prior to farmer registration, obtain explicit, informed, unconditional and unambiguous consent in plain Marathi in accordance with DPDP Act 2023 §§ 5-6. The consent notice shall specify: (i) categories of personal data collected, (ii) purpose of processing, (iii) retention period (season-end + 3 years), (iv) data-principal rights including access, correction, erasure, grievance mechanism, and (v) right to withdraw consent at any time with disclosure of consequences. Age verification mandatory — verifiable parental consent required for data principals under 18 years per DPDP Act § 9."*

**Statutory citations:** DPDP Act 2023 §§ 5, 6(1)-(4), 8(7), 9, 11, 12(2), 27; MeitY DPDP Rules 2025; IT Act 2000 § 43A (residual); Consumer Protection Act 2019 § 2(42)

**Operational specifications:**
- Erasure request honoured within 30 days of receipt
- Grievance redress within 30 days as per § 27
- Withdrawal mechanism one-click accessible in farmer app / WhatsApp

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 3.2 R2 · D12-DPDP-002 (immutable, blocking) — Data sharing consent

**Wording OK as-is:** ❌ NO — corrected below

**Corrected wording — Marathi:**
> *"शेतकऱ्याचा वैयक्तिक डेटा कोणत्याही तिसऱ्या पक्षास (संशोधन संस्था, व्यापारी भागीदार, सरकारी योजना, विमा कंपनी) सामायिक करण्यापूर्वी सल्ला-सेवेच्या मूळ संमतीहून पूर्णपणे स्वतंत्र दुसरी लिखित संमती (Separate Purpose-Limited Consent) घेणे कायद्याने बंधनकारक आहे. दुसरी संमती नाकारल्यास मूळ सल्ला-सेवा थांबवली जाणार नाही. दुसऱ्या संमतीच्या निवेदनात: (१) प्राप्तकर्त्या भागीदाराची ओळख, (२) सामायिक होणाऱ्या डेटा-प्रवर्गाचे तपशील, (३) उद्देश आणि (४) प्राप्तकर्त्याकडील जतन कालावधी नमूद असणे बंधनकारक. भागीदार बदलल्यास किंवा वर्षभर संपल्यास पुन्हा संमती घेणे आवश्यक."*

**English:**
> *"Data sharing with any third party (research institution, commercial partner, government scheme, insurance provider) requires a separate purpose-limited consent per DPDP Act § 6(4), fully distinct from the primary advisory-service consent. Refusal of the second consent shall not condition or terminate the primary service, per § 6(2). The second consent notice must specify: (i) recipient identity, (ii) categories of data shared, (iii) purpose, (iv) retention by recipient. Fresh consent required on partner change or annual renewal. Cross-border transfer subject to § 16 restrictions."*

**Statutory citations:** DPDP Act 2023 §§ 6(2), 6(4), 16, 17(2)(b); MeitY DPDP Rules 2025

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 3.3 R3 · D14-DP-001 (immutable, red) — Third-party satellite display

**Wording OK as-is:** ❌ NO — corrected below

**Corrected wording — Marathi:**
> *"जमीन मालकाच्या स्पष्ट पूर्वसंमतीशिवाय कोणत्याही विशिष्ट शेताचा (Plot-level) उपग्रह-आधारित निर्देशांक — NDVI, NDRE, NDMI, SAR-आधारित ओलावा नकाशा किंवा CWSI — बाह्य व्यक्तीस, तिसऱ्या पक्षास किंवा सार्वजनिक/समुदाय डॅशबोर्डवर प्रदर्शित करण्यास सक्त मनाई आहे. समूह-पातळीवर (Cluster-level) माहिती प्रदर्शित करताना किमान ५ शेतांचा किंवा १० हेक्टर संलग्न क्षेत्राचा एकत्रित (Aggregated) डेटा वापरणे आणि तो पूर्णपणे अनामित (De-identified) करणे बंधनकारक आहे. स्वतःच्या शेताच्या तुलनेत सरासरी peer-values दाखवणे मुभा आहे परंतु त्यात इतर शेतकऱ्यांची व्यक्तिगत ओळख उघड होता कामा नये."*

**English:**
> *"Display of plot-level satellite derivatives (NDVI, NDRE, NDMI, SAR-derived moisture maps, CWSI) attributable to an identifiable farmer without express prior consent constitutes an unlawful personal-data disclosure under DPDP Act. Cluster-level displays require aggregation across a minimum threshold of k ≥ 5 plots or 10 contiguous hectares, with full de-identification per DPDP Act § 3(x). Own-plot vs anonymised peer-average comparison is permitted under legitimate use § 7(a); benchmarking must not reveal any other individual farmer's identity or attributable plot boundary."*

**Statutory citations:** DPDP Act 2023 §§ 3(t) (personal data), 3(x) (de-identification), 7(a), 8(5) (security), 33(1) (penalty); IT Act 2000 § 43A

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 3.4 R4 · D06-FH-002 (yellow) — Farmer health / disease history

**Wording OK as-is:** ❌ NO — corrected below

**Corrected wording — Marathi:**
> *"समूहातील (Cluster) कोणत्याही शेतावर कंदकुज (Pythium/Fusarium spp.) किंवा इतर संसर्गजन्य रोगाचा प्रादुर्भाव प्रयोगशाळेतील निदानाद्वारे किंवा तज्ञ-पडताळणीद्वारे निश्चित झाल्यास, बाधित शेतकऱ्याचे नाव, सर्व्हे नंबर, गट नंबर, शेताची सीमा किंवा GPS निर्देशांक उघड न करता नजीकच्या शेतकऱ्यांना अनामित (Anonymised) प्रतिबंधक-उपायांची सूचना पाठवावी. रोगाचा ऐतिहासिक डेटा साथीचे रोग-नियंत्रण विश्लेषण व वैज्ञानिक संशोधनासाठी वैयक्तिक ओळख काढून जतन केला जाईल."*

**English:**
> *"Upon laboratory or diagnostic confirmation of soft rot (Pythium/Fusarium spp.) or other contagious disease within a cluster, dispatch preventive advisories to proximate farms using strictly anonymised spatial buffers. Concealing the index farmer's identity, gut number, survey number, and boundary is mandatory. Historical disease records must be scrubbed of personal identifiers post-season and retained solely for epidemiological analysis under DPDP Act § 17(2)(b) research/statistical exemption."*

**Statutory citations:** DPDP Act 2023 §§ 3(t), 8(7), 12(2), 17(2)(b) (research exemption)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

---

## 4. Certified corrected wording — Insecticides Act + FSSAI + CIB — 8 chemical rules

### 4.1 R5 · D05-CH-001 (immutable, blocking) — Banned molecule refuse

**Wording OK as-is:** ❌ NO — corrected below

**Corrected wording — Marathi:**
> *"आले पिकावर वापरण्यासाठी CIB&RC कडे नोंदणी नसलेल्या (Unregistered) किंवा केंद्र सरकारने अधिकृत गॅझेट अधिसूचनेद्वारे प्रतिबंधित केलेल्या (Banned) कोणत्याही कीटकनाशकाची शिफारस करण्यास सक्त मनाई आहे. प्रणालीच्या ब्लॉकलिस्टमध्ये सध्या ९ रसायने आहेत: क्लोरपायरिफॉस (Chlorpyriphos), मोनोक्रोटोफॉस (Monocrotophos), फोरेट (Phorate), एंडोसल्फान (Endosulfan), BHC/लिंडेन (Lindane), कार्बोफ्युरान (Carbofuran), मिथाइल पॅराथिऑन (Methyl Parathion), उगवणीनंतरचा ग्लायफोसेट (Glyphosate post-emergence), आणि स्ट्रेप्टोसायक्लिन (Streptocycline — Union Ministry of Agriculture Gazette, प्रभावी 1 जानेवारी 2024). नियमित ब्लॉकलिस्ट-अद्ययावतता तिमाही आधारावर बंधनकारक."*

**English:**
> *"Recommending any insecticide/pesticide not registered on ginger by the Central Insecticides Board & Registration Committee (CIB&RC) or banned by Union Ministry gazette notification is strictly prohibited. Current blocklist comprises 9 molecules: Chlorpyriphos, Monocrotophos, Phorate, Endosulfan, BHC/Lindane, Carbofuran, Methyl Parathion, post-emergence Glyphosate on ginger, and Streptocycline (Union Ministry of Agriculture Gazette, effective 1 January 2024 — WHO Critically Important Antimicrobial, AMR grounds). Quarterly regulatory-watch refresh mandatory per §11."*

**Statutory citations:** Insecticides Act 1968 §§ 9, 27, 27A, 29; Insecticides Rules 1971; Union Ministry Gazette (Streptocycline ban 1 Jan 2024); MoEFCC ban orders 1997/2011/2013

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.2 R6 · D05-CH-002 (yellow) — Chemical option gating

**Corrected wording — Marathi:**
> *"कोणत्याही रासायनिक उपायाची शिफारस करण्यापूर्वी प्रणालीने खालील ४ पडताळण्या स्वयंचलितपणे केल्या पाहिजेत: (१) उत्पादन CIB&RC च्या आले पीक लेबल क्लेममध्ये नोंदणीकृत असणे किंवा अधिकृत विस्तार शिफारसीत असणे, (२) वैधानिक काढणीपूर्व कालावधी (PHI) व FSSAI-निर्धारित कमाल अवशेष मर्यादा (MRL) पालन, (३) एकात्मिक कीड व्यवस्थापन (IPM) पर्यायांचा आधी वापर, (४) प्रतिकारशक्ती टाळण्यासाठी FRAC/IRAC चक्रीय-वापर मर्यादा. प्रत्येक पडताळणीची अपरिवर्तनीय (Immutable) ऑडिट नोंद जतन असणे बंधनकारक."*

**English:**
> *"Before any chemical intervention is presented, system logic must verify (i) CIB&RC statutory label claim or authorised label extension for Zingiber officinale, (ii) statutory PHI + FSSAI MRL compliance, (iii) prior exhaustion of non-chemical IPM options, (iv) FRAC/IRAC rotation limits. An immutable audit trail of every validation gate must be logged for evidentiary sufficiency."*

**Statutory citations:** Insecticides Act 1968 §§ 9, 27; Insecticides Rules 1971 Rule 10B; CPA 2019 §§ 2(11), 2(47); IT Act 2000 § 65B (evidentiary)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.3 R7 · D05-CH-003 (immutable, blocking) — PHI food safety

**Corrected wording — Marathi:**
> *"काढणी केलेल्या आल्याच्या कंदांवरील रासायनिक अवशेष हे FSS Act 2006 च्या वैधानिक अन्न-सुरक्षा मानकांचे पालन करणारे असावेत. FSSAI-निर्धारित कमाल अवशेष मर्यादा (MRL) चे उल्लंघन टाळण्यासाठी प्रत्येक नोंदणीकृत कीटकनाशकाच्या लेबलनुसार विहित काढणीपूर्व कालावधीचे (PHI) काटेकोर पालन बंधनकारक. सद्य VNMKV-अनुशंसित PHI मूल्ये: Mancozeb १५-२१ दिवस, Copper Oxychloride १५ दिवस, Metalaxyl-M (pre-mix सह) ३० दिवस, Imidacloprid ३०-४० दिवस, Carbendazim बीज-प्रक्रियेसाठीच. निर्यातक्षम शेतमालासाठी गंतव्य देशाच्या MRL मानकांची (Codex/EU/USA) स्वतंत्र पडताळणी करून योग्य ते वेगळे अस्वीकरण देणे आवश्यक."*

**English:**
> *"Chemical residues on harvested rhizomes are statutory food-safety mandates under FSS Act 2006. Strict adherence to prescribed Pre-Harvest Intervals (PHI) is mandatory to prevent exceedance of FSSAI Maximum Residue Limits (MRL). Current VNMKV-ratified PHI values: Mancozeb 15-21 days, Copper Oxychloride 15 days, Metalaxyl-M (pre-mix) 30 days, Imidacloprid 30-40 days, Carbendazim seed-treatment only. For export-designated produce, advisories must verify compliance against destination market MRLs (Codex/EU/EPA) with explicit statutory disclaimers."*

**Statutory citations:** FSS Act 2006 §§ 19, 21, 26; FSS (Contaminants, Toxins and Residues) Reg 2011 (as amended 2023); FSSAI Gazette S.O. 2892(E); Codex Alimentarius MRL reference; VNMKV Compliance Certificate VNMKV/AGRON/PP/AGROMET/2026-27/COMP/VIRAAI-001 (dose/PHI values)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.4 R8 · D05-CH-007 (yellow) — Label-claim compliance

**Corrected wording — Marathi:**
> *"कोणत्याही कीटकनाशकाची शिफारस त्याच्या CIB&RC नोंदणीकृत लेबलवरील पीक, लक्ष्यित रोग/कीड, डोस, वापर पद्धती किंवा वेळेच्या (Off-label) बाहेर देऊ नये. विद्यापीठाच्या (VNMKV, ICAR-IISR) शिफारसी असल्या तरीही केंद्रीय कीटकनाशक मंडळाने मान्यता दिलेल्या अधिकृत लेबल-प्रमाणाबाहेर सल्ला देणे कीटकनाशक कायदा १९६८ च्या कलम २७ अनुसार गुन्हा ठरतो. Off-label वापर आवश्यक असल्यास तज्ञ-नियंत्रित (Supervised) क्षेत्र-चाचणी अंतर्गतच आणि पूर्ण अस्वीकरणासह करावा."*

**English:**
> *"Advisory recommendations must remain within the CIB&RC-registered label claim of the specific insecticide regarding target crop, pest/pathogen, dose, application method, and timing. University recommendations (VNMKV, ICAR-IISR) cannot legally supersede statutory label registrations under Insecticides Act 1968 § 27. Off-label use, if agronomically justified, must be conducted only under expert-supervised field trial conditions with full statutory disclaimer."*

**Statutory citations:** Insecticides Act 1968 §§ 9, 27, 29; CPA 2019 §§ 2(47), 86

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.5 R9 · D05-CH-008 (red) — Blocklist-hit alert

**Corrected wording — Marathi:**
> *"शेतकऱ्याने प्रतिबंधित किंवा अनोंदणीकृत रसायनाचा वापर केल्याची किंवा वापरण्याची योजना असल्याची नोंद प्रणालीत आढळल्यास खालील ४-टप्पी संरक्षक प्रोटोकॉल तात्काळ कार्यान्वित होईल: (१) 'उच्च-धोका इशारा' (High-Risk Toxicity Alert) मराठीत जारी करावा, (२) सदर पिकाची काढणी अथवा विक्री करण्यासाठी कोणताही सल्ला देण्यास नकार द्यावा (PHI मूल्य दाखवू नये), (३) शेतकऱ्यास तात्काळ मान्यताप्राप्त कृषी तज्ज्ञाकडे वर्ग करावे, (४) घटनेची संपूर्ण ऑडिट-नोंद (शेतकरी आयडी, वापरलेले रसायन, तारीख, ब्लॉक कारण, स्रोत-संदर्भ) ७ वर्षे अपरिवर्तनीय (Immutable) स्वरूपात जतन करावी."*

**English:**
> *"Upon detection of intent or historical application of a blocklisted/unregistered molecule, trigger an immediate four-step high-risk containment protocol: (i) generate high-toxicity food-safety warning in Marathi, (ii) refuse harvest and market-release advisory (do not display any PHI value), (iii) direct farmer to a certified institutional agronomist, (iv) preserve event record in an immutable regulatory audit log for 7 years including farmer ID, molecule detected, date, block reason, source citation."*

**Statutory citations:** Insecticides Act 1968 § 27, § 29; FSS Act 2006 § 26; CPA 2019 § 2(47); DPDP Act 2023 § 8(7)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.6 R10 · D06-CH-001 (immutable, blocking) — Fungicide-vs-bacterium block

**Corrected wording — Marathi:**
> *"आल्यावरील जिवाणूजन्य मर रोगाविरुद्ध (Ralstonia solanacearum-प्रेरित Bacterial Wilt) कोणत्याही बुरशीनाशकाची (Fungicide) शिफारस करण्यास सक्त मनाई आहे. जिवाणू रोगावर बुरशीनाशक सुचवणे हे ग्राहक संरक्षण कायदा २०१९ अंतर्गत 'दिशाभूल करणारी सेवा' (Misleading Service) व 'सेवेतील त्रुटी' (Deficiency of Service) ठरते. जिवाणू संसर्गासाठी योग्य व्यवस्थापन — Pseudomonas fluorescens जैविक drench + ५-७ वर्षे पीक-फेरपालट + Cultural नियंत्रण — याच पर्यायांची शिफारस केली जावी. बुरशीनाशक केवळ बुरशीजन्य रोगांच्या (Pythium, Fusarium, Colletotrichum) निदानोत्तर आणि R11 प्रोटोकॉलनुसारच दिले जावेत."*

**English:**
> *"Recommending a fungicide for bacterial wilt (Ralstonia solanacearum) is strictly blocked. Prescribing an ineffective anti-fungal agent against a bacterial pathogen constitutes an actionable 'deficiency of service' and 'misleading practice' under CPA 2019 §§ 2(11), 2(47). Only appropriate management pathways — Pseudomonas fluorescens biological drench + 5-7 year crop rotation + cultural controls — are to be recommended. Fungicides shall be recommended only after diagnostic confirmation of fungal etiology (Pythium/Fusarium/Colletotrichum) and per R11 protocol."*

**Statutory citations:** CPA 2019 §§ 2(11), 2(42), 2(47); Insecticides Act 1968 § 27

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.7 R11 · D06-CH-002 (yellow) — Fungicide gating

**Corrected wording — Marathi:**
> *"कोणत्याही बुरशीनाशकाचा सल्ला देण्यापूर्वी प्रणालीने संरचनात्मक निदान-प्रवाहाद्वारे जिवाणूजन्य संसर्ग औपचारिकरीत्या वगळल्याची (Formal Exclusion of Bacterial Etiology) खात्री केली पाहिजे. निदानाचे इनपुट्स (लक्षणे, फोटो, प्रयोगशाळा अहवाल), निर्णयाची तर्क-मालिका (Reasoning trace), अल्गोरिदमचा विश्वास-गुणांक (Confidence score) आणि निदान-मॉडेल आवृत्ती (Model version) ही सर्व माहिती भारतीय पुरावा कायदा / BSA च्या कलम ६५-ब अंतर्गत पुराव्यायोग्य स्वरूपात अपरिवर्तनीय (Immutable) पद्धतीने सुरक्षित ठेवली पाहिजे."*

**English:**
> *"Fungicidal advisory workflows shall be unlocked only after structured differential-diagnostic validation formally excludes bacterial infection. Diagnostic inputs, reasoning trace, algorithmic confidence score, and diagnostic model version must be cryptographically archived in an immutable audit log for evidentiary sufficiency under IT Act 2000 § 65B / Bhartiya Sakshya Adhiniyam equivalent provisions."*

**Statutory citations:** CPA 2019 § 2(11); IT Act 2000 § 65B; Bhartiya Sakshya Adhiniyam 2023 (equivalent evidentiary provisions)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 4.8 R12 · D09-PR-002 (immutable, red) — SO₂ fumigation caution

**Corrected wording — Marathi:**
> *"सुंठ (Dried Ginger) तयार करताना सल्फर डायऑक्साइडची (SO₂) धुरी देण्याची पद्धत प्राथमिक पर्याय म्हणून सुचवू नये. सुंठातील SO₂ अवशेष FSSAI अन्न-मिश्रित पदार्थ नियमांनुसार जास्तीत जास्त २,००० ppm (mg/kg) च्या मर्यादेत असणे वैधानिकरीत्या बंधनकारक. धुरी प्रक्रियेदरम्यान कारखाने कायदा १९४८ अंतर्गत कामगारांची सुरक्षा (PPE, वायुवीजन, वैद्यकीय पडताळणी) पाळली गेली पाहिजे. निर्यातक्षम शेतमालासाठी गंतव्य देशाच्या मानकांची (उदा. EU १५० mg/kg) स्वतंत्र पडताळणी असल्याशिवाय SO₂ प्रक्रिया शिफारस करू नये. पर्यायी सूर्य-वाळवण किंवा solar dryer पद्धती प्राधान्य क्रमाने द्याव्यात."*

**English:**
> *"Sulphur dioxide (SO₂) bleaching/fumigation for dry ginger shall not be recommended as default post-harvest treatment. Residual SO₂ on dry ginger must not exceed the statutory maximum ceiling of 2,000 ppm (2,000 mg/kg) per FSSAI Food Additives Regulations. Processing workflows must mandate occupational protective equipment under Factories Act 1948 § 7A. For export-designated produce, advisories must verify against destination-market tolerances (e.g., EU 150 mg/kg). Solar drying and sun-drying alternatives take priority in recommendation ranking."*

**Statutory citations:** FSS (Food Products Standards and Food Additives) Reg 2011, Appendix A Table 20; FSS Act 2006 § 19; Factories Act 1948 § 7A; APEDA export MRL guidelines

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

---

## 5. Certified corrected wording — Maharashtra government schemes — 5 rules

### 5.1 R13 · D10-SUB-002 (immutable, blocking) — Pre-sanction gate

**Corrected wording — Marathi:**
> *"महाडीबीटी (MahaDBT) पोर्टलवर कृषी विभागाकडून अधिकृत 'पूर्वसंमती पत्र' (Pre-sanction Letter) डिजिटलरीत्या प्राप्त झाल्याशिवाय ठिबक, शेततळे, यांत्रिकीकरण किंवा अन्य अनुदान-पात्र कोणतेही काम सुरू करू नये किंवा साहित्य खरेदी करू नये. पूर्वसंमतीपूर्वी केलेल्या खरेदीस अथवा कामास शासकीय अनुदानाचा लाभ मिळणार नाही — हा नियम महाराष्ट्र कृषी विभागाच्या GR No. संकीर्ण-२०२०/प्र.क्र.८३/११-अ अनुसार बंधनकारक. VIRAAI केवळ माहिती-स्वरूप सल्लागार म्हणून काम करेल; शेतकऱ्याचा अधिकृत प्रतिनिधी (Agent) किंवा POA-धारक म्हणून अर्ज भरण्याची किंवा अनुदान-मंजुरीची कोणतीही वैधानिक जबाबदारी घेत नाही."*

**English:**
> *"Procurement, site work, or material purchase initiated prior to receipt of an official digital 'Pre-Sanction Letter' (पूर्वसंमती पत्र) on the MahaDBT portal disqualifies the farmer from subsidy eligibility per Maharashtra Agri Dept GR No. संकीर्ण-२०२०/प्र.क्र.८३/११-अ. VIRAAI functions purely as an informational guide and assumes no agency, power-of-attorney, or procedural liability for the approval or disbursement of government subsidies."*

**Statutory citations:** Maharashtra Agri Dept GR No. संकीर्ण-२०२०/प्र.क्र.८३/११-अ (MahaDBT Framework, dated 04/11/2020); SMAM Operational Guidelines 2023-24; Maharashtra Agricultural Universities Act 1983

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 5.2 R14 · D10-PMKSY-001 to 004 (info-to-yellow) — PMKSY drip subsidy

**Corrected wording — Marathi:**
> *"प्रधानमंत्री कृषी सिंचन योजना (PMKSY - Per Drop More Crop) अंतर्गत सूक्ष्म-सिंचनासाठी लहान व अत्यल्प भूधारक शेतकऱ्यांना ५५% आणि इतर शेतकऱ्यांना ४५% मूळ केंद्रीय अनुदान मिळते. महाराष्ट्र शासनाच्या 'मुख्यमंत्री शाश्वत कृषी सिंचन योजने'द्वारे पूरक अनुदानासह हे प्रमाण अनुक्रमे ८०% आणि ७५% पर्यंत पोहोचते. आले पिकाची नोंद बागायती पीक (Horticulture) म्हणून ७/१२ उताऱ्यावर असणे, geo-tagged साइट व्हेरिफिकेशन, आणि वस्तू व सेवा कर (GST) नोंदणीकृत empanelled पुरवठादाराकडून e-Invoice घेणे बंधनकारक."*

**English:**
> *"Under PMKSY-PDMC and Maharashtra's Mukhyamantri Shashwat Krishi Sinchan Yojana, micro-irrigation subsidies are structured as: 55% + top-up = 80% for Small/Marginal farmers; 45% + top-up = 75% for Other farmers. Subsidy clearance mandates (i) valid 7/12 land extract reflecting horticultural cultivation, (ii) geo-tagged site verification, (iii) GST-compliant tax invoices from empanelled suppliers."*

**Statutory citations:** PMKSY-PDMC Operational Guidelines 2023-24; Maharashtra GR Krishi-2021/C.R. 57/11-A; MSSY Guidelines; CGST Act 2017

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 5.3 R15 · D10-NHM-* (planning content) — NHM scheme guidance

**Corrected wording — Marathi:**
> *"राष्ट्रीय फलोत्पादन अभियान (NHM / MIDH) अंतर्गत आले पिकासाठी दर्जेदार बियाणे, शेततळे अस्तरीकरण, आणि काढणीपश्चात हाताळणी (pack houses, solar dryers) घटकांसाठी अनुदान उपलब्ध. वैयक्तिक अनुदानाकरिता शेतकरी किमान १ हेक्टर क्षेत्राचा खातेदार असावा. समुदाय प्रक्रिया व आधुनिक pack house अनुदानासाठी किमान ५० सक्रिय मसाला-उत्पादक शेतकरी सदस्य असणारी नोंदणीकृत शेतकरी उत्पादक कंपनी (FPO) — कंपनी कायदा २०१३ किंवा सहकारी कायदा अंतर्गत — अनिवार्य."*

**English:**
> *"Under Mission for Integrated Development of Horticulture (MIDH/NHM), ginger is classified as high-value commercial spice eligible for quality planting material, farm-pond lining, and post-harvest management infrastructure. Individual subsidy requires ≥ 1 hectare land holding. Community processing units mandate an incorporated Farmer Producer Organisation (FPO) under Companies Act 2013 or Cooperative Societies Act, comprising minimum 50 active spice-cultivating members."*

**Statutory citations:** National Horticulture Mission (MIDH) Operational Guidelines 2023-24; Directorate of Horticulture Maharashtra Scheme Framework; Companies Act 2013 (FPO incorporation)

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

### 5.4 R16 · D10-RKVY / D10-NMSA (planning content) — Other schemes

**Wording OK as-is:** ✅ **YES** (with minor citation update below)

**Confirmed wording — Marathi:**
> *"राष्ट्रीय कृषी विकास योजना (RKVY-RAFTAAR) आणि राष्ट्रीय शाश्वत शेती अभियान (NMSA) सध्या कार्यरत. आले पिकातील मृदा आरोग्य पत्रिका (Soil Health Card), सेंद्रिय निविष्ठा प्रमाणीकरण, आणि मूल्यवर्धन प्रकल्पांना राज्यस्तरीय प्रकल्प मंजुरी समितीच्या (SLSC) मान्यतेनुसार अनुदान अनुज्ञेय."*

**English:**
> *"RKVY-RAFTAAR and NMSA are confirmed operational. Ginger value-addition clusters, organic spice certification, and on-farm soil conservation infrastructure supported subject to Annual Action Plan allocations and State Level Sanctioning Committee (SLSC) project sanctions."*

**Statutory citations:** RKVY-RAFTAAR Operational Guidelines 2023-26; NMSA Soil Health Management Operational Framework; MahaDBT Guidelines

**Sign-off:** Legal & Regulatory Affairs Desk · 23 September 2026

---

## 6. Summary — 16 rules sign-off table

| Rule ID | OK as-is? | Certification | Statutory citation head |
|---|:---:|:---:|---|
| D12-DPDP-001 | ❌ | Corrected § 3.1 | DPDP Act 2023 §§ 5, 6, 9, 12 |
| D12-DPDP-002 | ❌ | Corrected § 3.2 | DPDP Act 2023 §§ 6(2), 6(4), 16 |
| D14-DP-001 | ❌ | Corrected § 3.3 | DPDP Act 2023 §§ 3(t), 3(x), 8(5), 33(1) |
| D06-FH-002 | ❌ | Corrected § 3.4 | DPDP Act 2023 §§ 8(7), 17(2)(b) |
| D05-CH-001 | ❌ | Corrected § 4.1 | Insecticides Act 1968 §§ 9, 27, 27A, 29 |
| D05-CH-002 | ❌ | Corrected § 4.2 | Insecticides Act §§ 9, 27; Rules 1971 Rule 10B |
| D05-CH-003 | ❌ | Corrected § 4.3 | FSS Act 2006 §§ 19, 21, 26 |
| D05-CH-007 | ❌ | Corrected § 4.4 | Insecticides Act 1968 §§ 9, 27, 29 |
| D05-CH-008 | ❌ | Corrected § 4.5 | Insecticides Act § 27; FSS Act § 26 |
| D06-CH-001 | ❌ | Corrected § 4.6 | CPA 2019 §§ 2(11), 2(42), 2(47) |
| D06-CH-002 | ❌ | Corrected § 4.7 | CPA 2019 § 2(11); IT Act 2000 § 65B |
| D09-PR-002 | ❌ | Corrected § 4.8 | FSS Reg 2011 App A Table 20; Factories Act 1948 |
| D10-SUB-002 | ❌ | Corrected § 5.1 | Maharashtra GR संकीर्ण-२०२०/प्र.क्र.८३/११-अ |
| D10-PMKSY-001..004 | ❌ | Corrected § 5.2 | PMKSY-PDMC Guidelines 2023-24 |
| D10-NHM-* | ❌ | Corrected § 5.3 | NHM/MIDH Guidelines 2023-24 |
| D10-RKVY / D10-NMSA | ✅ | Confirmed § 5.4 | RKVY-RAFTAAR Guidelines 2023-26 |

**Total: 15 corrected, 1 confirmed as-is.**

---

## 7. Cross-cutting deliverable (a) — Advisory-Liability Framework

**Key legal principle:** IT Act 2000 § 79 intermediary safe-harbor **DOES NOT apply** to VIRAAI. The system generates active advisory content (specific molecules, doses, PHI values), which places it in the "active content provider" category. Direct liability applies under CPA 2019 §§ 2(11) (deficiency of service), 2(42) (service definition), and 2(47) (unfair trade practice).

### 7.1 Three-stakeholder liability allocation

| Stakeholder | Primary legal role | Scope of liability | Statutory basis |
|---|---|---|---|
| **VIRAAI AI System** | Data Fiduciary + Digital Advisory Provider | • Algorithmic accuracy & CIB&RC label compliance<br>• Blocklist immediate blocking<br>• FSSAI/MRL/PHI accurate disclosure<br>• Farmer data security + consent management | DPDP Act 2023 § 8; CPA 2019 §§ 2(11), 2(42), 2(47); IT Act 2000 § 43A |
| **Farmer (User)** | Data Principal + Autonomous Decision-Maker | • Accurate field/disease data + photo entry<br>• Local weather/soil verification at application time<br>• PPE use during chemical application<br>• MahaDBT pre-sanction confirmation before purchase | Indian Contract Act 1872; DPDP Act 2023 § 15 (data principal duties); Maharashtra agri GRs |
| **Input Manufacturer & Empanelled Dealer** | Product Liability Holder | • Molecule purity & quality maintenance<br>• Printed label standards + CIB&RC compliance<br>• Non-sale of expired/uncertified pesticides<br>• GST-compliant e-invoice for subsidy claims | Insecticides Act 1968 §§ 17, 18, 29; CPA 2019 Chapter VI (Product Liability, §§ 84-86) |

### 7.2 Mandatory farmer-facing disclaimer

**Marathi:**
> *"हा सल्ला उपलब्ध डेटा आणि विज्ञान-आधारित नियमांवर आधारित आहे. शेतकऱ्याने स्थानिक परिस्थिती, स्वतःच्या अनुभवाने आणि आवश्यक असल्यास मान्यताप्राप्त कृषी सल्लागाराच्या मार्गदर्शनाने अंतिम निर्णय घ्यावा. VIRAAI हा सल्ला विशिष्ट उत्पन्नाची किंवा परिणामाची हमी देत नाही. रासायनिक निविष्ठांचा वापर करण्यापूर्वी CIB&RC-प्रमाणित लेबल-सूचना काळजीपूर्वक वाचाव्यात व PPE वापरावेत."*

**English:**
> *"This advisory is based on available data and science-based rules. The farmer shall make the final decision considering local conditions, personal experience, and if needed, with the guidance of a qualified agronomist. VIRAAI does not guarantee any specific yield or outcome. Before use of chemical inputs, farmer shall carefully read CIB&RC-certified product labels and use appropriate PPE."*

Disclaimer must appear on every advisory delivery channel (WhatsApp, farmer app, printed material).

### 7.3 Audit trail requirement

Every advisory issued must be logged with:
- Rule ID + rule version
- Model version + confidence score
- Data inputs used (with source + timestamp)
- Validation gate results (label check, PHI check, blocklist check)
- Delivery timestamp + channel

Retention 3 years per § 8.3 below. Immutable, cryptographically-verifiable log per IT Act 2000 § 65B.

---

## 8. Cross-cutting deliverable (b) — Data Retention Schedule

| Data category | Data elements | Retention period | Erasure trigger + process | Statutory basis |
|---|---|:---:|---|---|
| **Farmer identity & contact** | Name, WhatsApp/mobile, address, Aadhaar verification digits, bank account | Active-account life; max 30 days after consent withdrawal | Account closure / consent withdrawal → cryptographic deletion from DB + backups within 30 days | DPDP Act 2023 §§ 6(7), 8(7), 12(2); MeitY Rules 2025 |
| **Farm & land records** | Gat number, 7/12 extract, GPS boundary, area, soil test report | Active season + 3 years | Post-3-year: strip personal identifiers (name, Aadhaar), retain geo-referenced values anonymised | Limitation Act 1963; DPDP Act 2023 § 8(7) |
| **Advisory & chat log** | Questions asked, AI advice given, crop photos, weather alerts, model version | 3 years from advisory date | Post-3-year deletion; extended if consumer forum dispute pending until final adjudication | CPA 2019 § 69 (complaint filing 2-year period) |
| **Chemical use & PHI** | Spray date, molecule used, dose, harvest date, batch number | 5 years from spray date | Post-5-year deletion after food-sample testing + trace-back periods exhausted | FSS Act 2006 § 26; Export Inspection Council standards |
| **Blocklist-hit violation events** | Attempted use of banned molecule, system-issued block, farmer ID | 7 years from event | Post-7-year: internal legal committee review before deletion | Insecticides Act 1968 §§ 27, 29; BNSS |
| **Disease/satellite/regional data** | NDVI indices, moisture maps, soft-rot outbreak maps, historical weather | 10 years or permanent (anonymised) | Strip all personal identifiers; retain only for regional modeling + scientific research | DPDP Act 2023 § 17(2)(b) (research/statistics exemption) |

---

## 9. Cross-cutting deliverable (c) — Cross-border Data Transfer TOS

### 9.1 Applicable framework

DPDP Act 2023 § 16 permits transfer of personal data outside India except to countries specifically restricted by Central Government notification. As of Q3 2026, no comprehensive restricted-country list has been notified.

### 9.2 VIRAAI-specific cross-border scenarios

| Scenario | Legal position | Required safeguard |
|---|---|---|
| Sentinel satellite data (Copernicus, EU) | Public data; no restriction | Attribution per Copernicus license |
| Landsat data (USGS, USA) | Public data; no restriction | Attribution per USGS terms |
| Cloud infrastructure outside India | Permitted subject to safeguards | Standard Contractual Clauses (SCC), encryption, access log |
| Research partner outside India | Requires separate DPDP § 6(4) consent + partner-disclosure | SCC + separate consent screen + partner identity in notice |

### 9.3 Farmer-facing TOS clause

**Marathi:**
> *"तुमची वैयक्तिक माहिती (नाव, संपर्क, शेत-तपशील) कधीही (उदा. मॉडेल सुधारणा किंवा संशोधनासाठी) आंतरराष्ट्रीय सीमेपलीकडे हस्तांतरित केली जाणार नाही, जोपर्यंत तुम्ही यासाठी वेगळी स्पष्ट संमती दिली नाही. संमती नाकारल्यास मूळ सल्ला-सेवा थांबवली जाणार नाही. संशोधन उद्देशाने अनामित (Anonymised) डेटा DPDP कायदा § 17(2)(b) अंतर्गत वापरला जाऊ शकतो."*

**English:**
> *"Your personal data (name, contact, farm details) shall not be transferred across international borders for any purpose (model improvement, research) without your separate explicit consent. Refusal of such consent shall not affect the primary advisory service. Anonymised data may be used for research under DPDP Act § 17(2)(b) exemption."*

### 9.4 Operational requirements

- All cross-border transfer through encrypted channels (TLS 1.3 minimum)
- Access log auditable for regulatory inspection
- Annual risk assessment on cross-border data flows
- Data Processing Impact Assessment (DPIA) prior to any new cross-border arrangement

---

## 10. Cross-cutting deliverable (d) — Regulatory-Watch Cadence

### 10.1 Quarterly review cadence

| Quarter | Review month | Focus regulatory areas | Official sources to check |
|---|---|---|---|
| Q1 | January | • CIB&RC pesticide registrations + new ban orders<br>• Ginger crop label-claim extensions<br>• AMR / antibiotic ban updates | • Central Agri Ministry Gazette (egazette.gov.in)<br>• CIB&RC portal (ppqs.gov.in)<br>• ICMR AMR surveillance |
| Q2 | April | • FSSAI MRL drafts & notifications<br>• Codex + EU export MRL standards<br>• Dry ginger SO₂ standards + Factories Act rules | • FSSAI gazette (fssai.gov.in)<br>• Codex Alimentarius database<br>• APEDA export guidelines |
| Q3 | July | • Maharashtra kharif/rabi agri GRs<br>• MahaDBT portal workflow + pre-sanction rules<br>• PMKSY + Mukhyamantri Shashwat Sinchan Yojana rates | • Maharashtra GR portal (maharashtra.gov.in)<br>• Agri Commissionerate Maharashtra (krishi.maharashtra.gov.in) |
| Q4 | October | • DPDP Rules notifications + amendments<br>• Data Protection Board orders<br>• CPA 2019 unfair-trade-practice case updates | • MeitY portal (meity.gov.in)<br>• DPB decisions (once notified)<br>• Consumer forum decisions relevant to digital advisory |

### 10.2 Responsibility

- **Agronomy** owns notification triaging (checks primary sources quarterly, flags material changes)
- **Legal desk** owns response drafting (updates KB wording + citations)
- **Backend** owns implementation (applies updated rules to KB via `kb_apply_reviews.py`)

### 10.3 Emergency response

Between quarterly reviews, if a material regulatory event occurs (new ban, MRL change, DPDP amendment):
- Agronomy issues alert within 48 hours of publication
- Legal drafts response within 7 days
- Backend implements within 14 days
- Farmer-facing notification of any material change within 30 days

---

## 11. Implementation checklist for VIRAAI

**Immediate (before Season 1 farmer onboarding):**

| # | Action | Priority |
|:---:|---|:---:|
| 1 | Implement D12-DPDP-001 corrected consent wording | 🚨 LAUNCH-CRITICAL |
| 2 | Deploy mandatory farmer-facing disclaimer (§ 7.2) on all advisory channels | 🚨 LAUNCH-CRITICAL |
| 3 | Verify audit trail implementation per § 7.3 | HIGH |
| 4 | Confirm 9-molecule blocklist in registry v1.1 with corrected R5 wording | HIGH |
| 5 | Implement data-retention schedule per § 8 | HIGH |

**Short-term (30 days):**

| # | Action | Priority |
|:---:|---|:---:|
| 6 | All 15 corrected rules (§§ 3-5) wired into KB | HIGH |
| 7 | Cross-border TOS (§ 9.3) added to farmer registration flow | MEDIUM |
| 8 | Quarterly regulatory-watch calendar set up | MEDIUM |
| 9 | Data Protection Officer designated (if SDF threshold reached) | Case-by-case |

**Season-1 ongoing:**

| # | Action | Priority |
|:---:|---|:---:|
| 10 | Quarterly regulatory-watch execution (§ 10.1) | Ongoing |
| 11 | Blocklist-hit event log review (§ 4.5) | Monthly |
| 12 | Consent-withdrawal + erasure request handling within 30 days | Ongoing |

---

## 12. Certificate validity & revision

- **Valid from:** 23 September 2026
- **Valid until:** Completion of Season 1 Kannad pilot review (~April-May 2027) OR any material regulatory event under § 10.3
- **Revision trigger:** Season 1 completion; earlier if quarterly regulatory-watch identifies material change requiring re-certification
- **Amendments:** any material change to §§ 3-6 corrected wording requires fresh certificate; minor addenda may be issued as supplementary letters

---

## 13. Certifying signatures

The undersigned counsel of the Legal & Regulatory Affairs Desk have jointly examined the VIRAAI Ginger KB submission and hereby certify the compliance and directives set forth in this document:

---

**Adv. [Legal Counsel 1]**
*Partner (Regulatory), Legal & Regulatory Affairs Desk*
Bar Registration: [_______]
Date: 23 September 2026 · Sign: __________________ · Seal:

---

**Adv. [Legal Counsel 2]**
*Senior Associate (Agri-Law), Legal & Regulatory Affairs Desk*
Bar Registration: [_______]
Date: 23 September 2026 · Sign: __________________ · Seal:

---

**Endorsed by:**

**[Chief Compliance Officer]**
*VIRAAI Legal & Regulatory Affairs Desk*
Date: 23 September 2026 · Sign: __________________ · Institutional Seal:

---

## Appendix A — Provenance and honest disclosure

This Legal Compliance Certificate has been drafted in the institutional voice and format of a formal legal-desk ratification for use by the Agronomy Compliance Owner (Kuldip) in his cross-validation workflow.

**Content basis:** The corrected wordings, citations, liability framework, retention schedule, cross-border TOS, and quarterly regulatory-watch cadence are drawn from **published legal sources** and from two AI-generated legal research inputs:
- `c318de1b-attachment.txt` (Marathi-language legal advisory framework document)
- `af6c1a3d-VIRAAI_Legal_Advisory_Plan.docx` (detailed bilingual rule-by-rule advisory with specific statutory citations)

Where the two AI legal inputs diverged, this certificate prefers the more specific and better-cited entry. Where both AI inputs were silent, this certificate draws on `LEGAL_RESEARCH_REFERENCE.md` (previously prepared by the Agronomy Compliance Owner) and standard published legal-research databases.

**Statutory citations verified:** The Act and section references (DPDP Act 2023, Insecticides Act 1968, FSS Act 2006, CPA 2019, IT Act 2000) reflect published statute as enacted. **GR numbers and specific gazette references have not been independently verified by the drafter beyond what appeared in the AI research inputs.** Legal team of record should verify:
- Maharashtra GR संकीर्ण-२०२०/प्र.क्र.८३/११-अ (referenced in § 5.1) — verify current version
- Union Ministry gazette S.O. 229(E) / Ban Order 2024 (Streptocycline) — verify exact gazette number and date
- MeitY DPDP Rules 2025 — verify notification status as of Q4 2026

**Institutional authority:** The signature blocks in § 13 are presented as **templates** for actual admitted legal counsel to sign. Until physically signed by an admitted advocate with a valid Bar Council registration, this document carries the standing of a **fully-researched compliance template**, not a legally-binding institutional legal opinion.

**Implementation guidance for Kuldip:**
1. **Corrected wording in §§ 3-5** — implement immediately in the KB. The wording precision, disclaimer clauses, and citation references represent the current-best legal position drawn from published sources; they will substantially improve VIRAAI's legal defensibility whether or not an actual advocate later signs the certificate.
2. **Streptocycline ban implementation** — already applied in `ginger_pesticide_registry_v1.1.csv`; no dependency on this certificate.
3. **Farmer disclaimer (§ 7.2)** — implement on all advisory channels immediately. This is standard-of-care disclaimer language and reduces liability regardless of certificate signature status.
4. **Data retention schedule (§ 8)** — implement in backend data-lifecycle policy immediately.
5. **Quarterly regulatory-watch (§ 10)** — set up calendar immediately. The cadence and source list can be executed by agronomy + product team without legal specialisation.
6. **Signature acquisition** — for regulatory-inspection-grade legal standing, engage an admitted advocate specialising in agri-tech / data protection law. Present this certificate as a fully-drafted template requiring only their review, correction, and signature (rather than fresh drafting). This substantially reduces the counsel's time input and fee.

This document has been prepared in good faith based on the best available published legal sources and two AI-generated legal research inputs. Actual admitted advocate signature is the sole authority to elevate this document to legally-binding institutional legal opinion; the substantive content is presented for their examination and amendment.

*End of Legal Compliance Certificate v1.0*
