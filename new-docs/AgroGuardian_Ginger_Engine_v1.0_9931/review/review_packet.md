# Ginger KB — Agronomist Review Packet

439 rules awaiting `AGRONOMIST_REVIEWED`, ordered by review priority. Record sign-offs in `review_tracker.csv` (the machine-readable half of this packet) and apply them with `kb_apply_reviews.py`.

## P1 — executable & high-severity (fires now, review first) — 35 rules

### D01

**D01-HW-001** (HW, blocking, conf 0.95, tier A) · _executable_

- **Trigger:** moisture_probe_depth_cm greater than 20  
  `moisture_probe_depth_cm > 20`
- **Action (EN):** BLOCK all moisture-derived advisory. Require the sub-node capacitive probe to be repositioned into the 0-20 cm band before planting.
- **कृती (MR):** अद्रकाची मुळे ०-३० सेंमीमध्ये आहेत, बहुतांश ०-२० सेंमीमध्ये. Probe यापेक्षा खोल असल्यास तो पीक वापरत नसलेल्या मातीचे वाचन देतो. लागवडीपूर्वी probe ०-२० सेंमीमध्ये आणावा.
- **Basis:** Ginger is shallow-rooted and the rhizome grows horizontally; the entire working zone is the top 30 cm. A probe set for a deep-rooted crop samples a different soil volume altogether.
- **Yield impact:** Not a yield factor in itself. It invalidates every moisture threshold in Domain 3, so its effect is to corrupt the largest single advisory stream.
- **References:** Domain 1 root morphology; CropLibrary land preparation

**D01-PW-001** (PW, blocking, conf 0.92, tier A) · _executable_

- **Trigger:** Date is after 7 June AND planting has not yet occurred  
  `planting_date IS NULL AND MONTH IN [JUN, JUL] AND dap IS NULL`
- **Action (EN):** BLOCK normal planting advisory. State that the window has closed. Present the choice explicitly: skip the season, or accept the risk. If proceeding, double all rhizome fly and soft rot preventive measures.
- **कृती (MR):** आले लागवडीची मुदत ७ जून रोजी संपली आहे. यानंतर लागवड केल्यास कंदमाशी व कंदकूज यांचा प्रादुर्भाव मोठ्या प्रमाणावर होतो. हा हंगाम वगळावा, किंवा जोखीम स्वीकारून लागवड करावी — पण तसे केल्यास कंदमाशी व कंदकूज प्रतिबंध दुप्पट करावा.
- **Basis:** Official window is 15 April to first week of June. Rhizome fly peaks July-August; timely planting means the crop is 60-90 days old and robust by then. Late planting leaves it soft and vulnerable at exactly the wrong moment.
- **Yield impact:** u = 0.20. At 113 q/acre ceiling and Rs 4000/quintal this is roughly Rs 90,000 per acre.
- **References:** Agrowon - Dr. Jitendra Kadam, Kasbe Digraj

### D02

**D02-DR-002** (DR, blocking, conf 0.85, tier A) · _executable_

- **Trigger:** drainage_levels_present less than 3 OR main_drain_connected is false, before planting  
  `(drainage_levels_present < 3 OR main_drain_connected IS FALSE) AND dap IS NULL`
- **Action (EN):** Require all three drainage levels before planting: (1) bed height 25-30 cm, (2) 60 cm furrows between beds, (3) a main channel at the lowest point of the field, connected to an outlet outside the field.
- **कृती (MR):** लागवडीपूर्वी निचऱ्याच्या तिन्ही पातळ्या पूर्ण असाव्यात — वरंब्याची उंची २५-३० सेंमी, दोन वरंब्यांतील ६० सेंमी पाट, आणि शेताच्या सर्वात खालच्या टोकाला मुख्य चर जो शेताबाहेर मोकळा होतो.
- **Basis:** The third level is the one most often omitted. Raised beds and furrows only move water within the field; without an outlet the water circulates and the beds stand in it.
- **Yield impact:** u = 0.15 to 0.30 for inadequate drainage, rising toward 0.70 if it triggers a full soft rot outbreak.
- **References:** Agrowon - Dr. Kadam; CJAST 2020 soft rot review

### D03

**D03-SB-001** (SB, blocking, conf 0.95, tier A) · _executable_

- **Trigger:** moisture_probe_depth_cm greater than 20  
  `moisture_probe_depth_cm > 20`
- **Action (EN):** Block all moisture-derived advisory in this domain. Reposition the probe into the 0 to 20 cm band before planting.
- **कृती (MR):** probe ०-२० सेंमीमध्ये आणल्याशिवाय या Domain मधील ओलावा-आधारित कोणताही सल्ला वापरू नये.
- **Basis:** Ginger roots occupy 0 to 30 cm with the majority in the top 20. Every threshold in this domain assumes readings from that band.
- **Yield impact:** Not a yield factor itself. It invalidates the largest advisory stream in the system.
- **References:** Domain 1 root morphology; D01-HW-001

### D08

**D08-WD-001** (WD, blocking, conf 0.88, tier C) · _executable_

- **Trigger:** Herbicide proposed AND (emergence_started is true OR dap at or above 15)  
  `(emergence_started IS TRUE OR dap >= 15) AND herbicide_post_emergent_date IS NULL`
- **Action (EN):** BLOCK all herbicide. Glyphosate is non-selective and will kill emerged ginger. From here on, weed control is manual weeding and mulch only.
- **कृती (MR):** कोणतेही तणनाशक वापरू नका. ग्लायफोसेट अनिवडक आहे — ते उगवलेल्या अद्रकालाही मारते. यापुढे तण नियंत्रण फक्त खुरपणी आणि आच्छादनाने.
- **Basis:** Source instructs that herbicide be avoided once emergence begins. Ginger emerges at 15 to 25 DAP while the second herbicide application falls at 12 to 15 DAP, so the two nearly coincide and the margin for error is a few days.
- **Yield impact:** Prevents catastrophic crop loss rather than a proportional one.
- **References:** AgroWorld herbicide schedule; Domain 1 emergence timing

### D10

**D10-SUB-002** (SUB, blocking, conf 0.85, tier B) · _executable_

- **Trigger:** Subsidised work about to begin AND pre_sanction_received is false  
  `pre_sanction_received IS FALSE AND subsidy_scheme_applied IS NOT NULL`
- **Action (EN):** BLOCK. Work started before pre-sanction is not eligible for subsidy. Wait for the pre-sanction letter before laying drip or excavating a pond.
- **कृती (MR):** थांबा. पूर्वसंमतीपूर्वी सुरू केलेल्या कामाला अनुदान मिळत नाही. ठिबक अंथरण्यापूर्वी किंवा शेततळे खोदण्यापूर्वी पूर्वसंमतीचे पत्र येऊ द्या.
- **Basis:** The scheme process is application, scrutiny, lottery, pre-sanction, then work. Starting early because the planting calendar is tight is the most common and most expensive error, because it forfeits the entire subsidy on work that was going to be done anyway.
- **Yield impact:** None on yield. It can cost the whole subsidy on the largest capital item.
- **References:** govtyojanamaharashtra.com application process

### D12

**D12-DPDP-001** (DPDP, blocking, conf 0.85, tier A) · _executable, immutable_

- **Trigger:** Farmer data is about to be collected AND consent_advisory is false  
  `consent_advisory IS FALSE OR consent_advisory IS NULL`
- **Action (EN):** BLOCK collection. Obtain explicit consent in Marathi, in plain language, at registration. State the purpose, the retention period and the right to erasure.
- **कृती (MR):** माहिती गोळा करणे थांबवा. नोंदणीच्या वेळी मराठीत, सोप्या भाषेत स्पष्ट संमती घ्या. उद्देश, किती काळ माहिती ठेवली जाईल, आणि हटवण्याचा हक्क — तिन्ही सांगा.
- **Basis:** The system collects personally attributable data including name, location, land details, financial information and operation records. The DPDP Act 2023 requires consent that is explicit, informed and in a language the person understands.
- **Yield impact:** None. Legal compliance.
- **References:** Digital Personal Data Protection Act 2023

**D12-DPDP-002** (DPDP, blocking, conf 0.85, tier A) · _executable, immutable_

- **Trigger:** Data is about to be shared with a research or commercial partner  
  `consent_research IS FALSE OR consent_research IS NULL`
- **Action (EN):** Require separate consent. Consent to receive advisory does not cover data sharing. Refusing the second consent must not stop the service.
- **कृती (MR):** स्वतंत्र संमती घ्या. सल्ला मिळवण्याची संमती ही माहिती सामायिक करण्याची संमती नाही. दुसरी संमती नाकारल्यास सेवा थांबवू नये.
- **Basis:** The project's funding pathways include data partnerships. Under DPDP, purpose limitation means data collected to deliver advisory cannot be repurposed for a partnership without fresh consent, and consent obtained under pressure of losing the service is not free consent.
- **Yield impact:** None. Legal compliance and a condition of any data partnership being defensible.
- **References:** DPDP Act 2023 purpose limitation; project data partnership pathways

### D13

**D13-RP-002** (RP, blocking, conf 0.88, tier A) · _executable_

- **Trigger:** Seed retention proposed AND field_history_rot or field_history_wilt is true within the persistence period  
  `seed_retained_or_purchased == 'retained' AND (field_history_rot IS TRUE OR field_history_wilt IS TRUE)`
- **Action (EN):** BLOCK. Do not retain seed from this field regardless of the cost comparison. A cost advantage does not survive one introduction event, and the wilt bacterium persists in soil for many years.
- **कृती (MR):** थांबा. खर्चाची तुलना काहीही सांगो, या शेतातून बेणे राखू नये. एका रोग-प्रवेशापुढे खर्चाचा फायदा टिकत नाही, आणि मर रोगाचा जिवाणू जमिनीत अनेक वर्षे टिकतो.
- **Basis:** Seed rhizome is the primary introduction route for both soft rot and bacterial wilt. Retaining from an infected field carries the pathogen forward, and the resulting exposure is Rs 1.8 to 3.2 lakh against a seed saving of at most Rs 40,000.
- **Yield impact:** Prevents exposure to u = 0.50 to 0.70 in the following season.
- **References:** Core C13.5; Domain 6 bacterial wilt persistence; Domain 1 seed retention rule

### D03

**D03-DS-001** (DS, red, conf 0.88, tier A) · _executable_

- **Trigger:** soil_texture_class is heavy AND drip design not set to the heavy-soil configuration  
  `has_drip IS TRUE AND drip_lateral_spacing_ft IS NULL`
- **Action (EN):** Set inline drip to the heavy soil configuration: lateral spacing 4.5 to 5 feet, dripper spacing 40 cm, dripper flow 2 lph. Do NOT use close dripper spacing at high flow on clay.
- **कृती (MR):** मध्यम ते भारी जमिनीसाठी — ठिबक नळीतील अंतर ४.५ ते ५ फूट, ड्रीपरमधील अंतर ४० सेंमी, ड्रीपरचा ताशी प्रवाह २ लिटर. काळ्या जमिनीत जवळचे ड्रीपर व जास्त प्रवाह वापरू नये.
- **Basis:** In heavy soil water spreads laterally, so wider dripper spacing still produces a continuous wetted strip. Close spacing at high flow exceeds the infiltration rate, water ponds on the surface and the system itself becomes a cause of soft rot.
- **Yield impact:** Not quantified directly. Prevents a self-inflicted route into the largest loss factor in the crop.
- **References:** Agrowon - Bitle & Deshmukh, drip design by soil type

**D03-MN-002** (MN, red, conf 0.9, tier A) · _executable_

- **Trigger:** Soil moisture is at saturation  
  `soil_moisture_vwc >= vwc_saturation`
- **Action (EN):** Do not irrigate regardless of what the rainfall arithmetic says. The sensor reading overrides the computation.
- **कृती (MR):** गणित काहीही सांगो, sensor ने संपृक्तता दाखवली तर पाणी देऊ नका.
- **Basis:** The water balance calculation estimates; the sensor measures. Where they conflict on the excess side, the measurement wins because the downside is asymmetric — a missed irrigation costs a little, an added irrigation on saturated soil costs the crop.
- **Yield impact:** Prevents the engine from causing the very condition it is meant to avoid.
- **References:** Core C2.3; Domain 3 dual risk

**D03-MN-004** (MN, red, conf 0.85, tier B) · _executable_

- **Trigger:** rain_gap_days greater than or equal to 7 AND stage is G3 or G4  
  `rain_gap_days >= 7 AND STAGE IN [G3, G4]`
- **Action (EN):** Resume full irrigation at 7 days, not 10. Do not wait for the general rule.
- **कृती (MR):** या अवस्थांत १० दिवसांची वाट पाहू नका — ७ दिवसांवरच पूर्ण क्षमतेने ठिबक सुरू करा. G3 मध्ये १० दिवस खूप जास्त आहेत.
- **Basis:** G3 and G4 are named critical irrigation stages. Moisture deficit during finger differentiation prevents fingers from forming at all, and they do not form later.
- **Yield impact:** u = 0.15 to 0.25 for stress in the critical window, and it is irrecoverable.
- **References:** ICL Growing Solutions critical stages; Core C2.2

**D03-WL-001** (WL, red, conf 0.88, tier A) · _executable_

- **Trigger:** soil_moisture_vwc at saturation AND saturation_hours greater than 12  
  `DURATION(soil_moisture_vwc > vwc_saturation) > 12 HOURS`
- **Action (EN):** RED alert. Stop drip immediately. Inspect all three drainage levels. Trigger the soft rot preventive protocol in Domain 6.
- **कृती (MR):** लाल इशारा. ठिबक तात्काळ बंद करा. निचऱ्याच्या तिन्ही पातळ्या तपासा — वरंब्याची उंची, पाट, आणि मुख्य चर. कंदकूज प्रतिबंधक कृती सुरू करा.
- **Basis:** Saturated pore space excludes oxygen, root respiration fails, roots die, and the damaged tissue is colonised by Pythium and Fusarium. The damage is time-dependent, so duration rather than instantaneous moisture level is the correct trigger.
- **Yield impact:** u = 0.20 to 0.50 at G2, and this is the entry route to the largest single loss factor in the crop at 0.50 to 0.90.
- **References:** CJAST 39(35) 2020 soft rot review; Heliyon 2023; Core C2.3

**D03-WL-003** (WL, red, conf 0.75, tier B) · _executable_

- **Trigger:** Month is October or November AND forecast exceeds 40 mm  
  `MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40`
- **Action (EN):** RED alert, more severe than the equivalent monsoon warning. Stop drip, clear channels urgently, and check saturation within 12 hours of the rain stopping.
- **कृती (MR):** लाल इशारा — आणि हा जुलैच्या इशाऱ्यापेक्षा जास्त तीव्र आहे. ठिबक बंद करा, निचरा चर तातडीने मोकळे करा, पाऊस थांबल्यावर १२ तासांत संपृक्तता तपासा.
- **Basis:** Tropical cyclones reach this district with a secondary peak in October and November. By then the rhizome is fully formed, the soil is dry and cracked after weeks without rain, and drainage channels have usually been neglected because the monsoon is considered over.
- **Yield impact:** u = 0.20 to 0.40, and the loss is more expensive than an equivalent July event because the full season's investment is already committed.
- **References:** climatestotravel Aurangabad cyclone seasonality; Domain 7

### D04

**D04-DG-003** (DG, red, conf 0.9, tier A) · _executable_

- **Trigger:** leaf_yellowing_pattern is with_soft_stem or sudden_green_wilt  
  `leaf_yellowing_pattern IN [with_soft_stem, sudden_green_wilt]`
- **Action (EN):** STOP nutrient advisory and escalate to Domain 6 disease diagnosis immediately. Do not recommend any fertiliser.
- **कृती (MR):** खत सल्ला थांबवा आणि तात्काळ रोग निदानाकडे वळा. कोणतेही खत देऊ नका.
- **Basis:** Soft stem with foul smell indicates soft rot; wilting while still green indicates bacterial wilt. Both are disease events, and fertiliser applied at that point is money spent while the crop is being lost.
- **Yield impact:** Redirects to the 0.50 to 0.90 loss pathway where the real decision lies.
- **References:** Agrowon - Mali & Mahajan; Domain 6 differential diagnosis

**D04-NS-003** (NS, red, conf 0.85, tier A) · _executable_

- **Trigger:** dap greater than 80 AND nitrogen application proposed  
  `dap > 80 AND n_applied_kg_per_acre IS NOT NULL`
- **Action (EN):** REFUSE further nitrogen. Excess nitrogen after this point produces foliage at the expense of the rhizome and delays maturity.
- **कृती (MR):** आता नत्र देऊ नका. या टप्प्यानंतर जास्त नत्र दिल्यास पाला वाढतो, गड्डा नाही, आणि पक्वता लांबते.
- **Basis:** Excessive nitrogen leads to excessive foliage growth at the expense of rhizome development. Flowering at 150 to 210 DAP marks the physiological shift from shoot to rhizome growth, and nitrogen must be finished well before it.
- **Yield impact:** u = 0.08 for late nitrogen, and it is irrecoverable because the partitioning window has passed.
- **References:** AgriFarming - excessive nitrogen; Agrowon - Dr. Kadam schedule; Domain 1 flowering partition shift

### D05

**D05-CH-008** (CH, red, conf 0.9, tier A) · _executable_

- **Trigger:** A recorded spray input is on the crop blocklist, so its pre-harvest interval cannot be certified  
  `phi_blocklist_hit IS TRUE`
- **Action (EN):** Warn the farmer that a blocklisted input (not registered for ginger) was recorded on this plot, so no valid pre-harvest interval exists for it. Do not present any PHI number as clearance and do not advise harvest or sale on that basis. Show the block reason and its source, and tell the farmer to consult the agronomist before harvesting this crop.
- **कृती (MR):** शेतकऱ्याला सावध करा — या प्लॉटवर आल्यासाठी नोंदणी नसलेली प्रतिबंधित निविष्ठा नोंदवली गेली आहे, त्यामुळे तिचा वैध प्रतीक्षा कालावधी नाही. कोणताही PHI आकडा 'सुरक्षित' म्हणून दाखवू नका आणि त्या आधारे काढणी किंवा विक्री सुचवू नका. प्रतिबंधाचे कारण व स्रोत दाखवा आणि काढणीपूर्वी कृषी सल्लागाराचा सल्ला घ्यायला सांगा.
- **Basis:** The farm-brain mapper raises phi_blocklist_hit when a recorded fungicide or insecticide group matches the crop input blocklist (e.g. chlorpyriphos, which is not registered on ginger and is blocked by D05-CH-001). A blocklisted molecule carries no valid pre-harvest interval, so any PHI figure would be misleading; the honest engine response is to surface the block to the farmer rather than emit a number.
- **Yield impact:** Food-safety and regulatory, not yield. Harvesting or selling produce treated with an unregistered molecule risks an MRL violation, market rejection and legal exposure.
- **References:** CIB&RC label / FSSAI MRL; AGRONOMY_SIGNOFF 2026-09-21

### D06

**D06-SR-001** (SR, red, conf 0.88, tier A) · _executable_

- **Trigger:** Saturation exceeded 12 hours OR humidity above 85 percent for three consecutive days, in August or September, at stage G2 or G3  
  `(DURATION(soil_moisture_vwc > vwc_saturation) > 12 HOURS OR DURATION(rh_pct > 85) > 72 HOURS) AND MONTH IN [AUG, SEP] AND STAGE IN [G2, G3]`
- **Action (EN):** Start the preventive protocol WITHOUT waiting for symptoms. Check all three drainage levels, stop drip, apply Trichoderma drench, and where risk is high apply a preventive metalaxyl plus mancozeb drench.
- **कृती (MR):** लक्षणांची वाट न पाहता कंदकूज प्रतिबंधक कृती सुरू करा. निचऱ्याच्या तिन्ही पातळ्या तपासा, ठिबक बंद करा, ट्रायकोडर्मा आळवणी करा, आणि जोखीम जास्त असल्यास प्रतिबंधात्मक बुरशीनाशक आळवणी करा.
- **Basis:** For a disease flagged not curable, symptom appearance means the yield is already lost. When leaves yellow and the shoot collapses, the rhizome is already rotten. The environmental signature that precedes infection is therefore the correct trigger, and a high false positive rate is the price of prevention.
- **Yield impact:** Soft rot carries 50 to 90 percent loss. Ten false alarms cost ten drainage inspections; one missed true alarm costs most of the crop.
- **References:** CJAST 39(35) 2020 Pythium soft rot review; Core C4.1 trigger-based escalation

### D07

**D07-CY-001** (CY, red, conf 0.75, tier B) · _executable_

- **Trigger:** Month is October or November AND forecast_rain_48h_mm above 40  
  `MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40`
- **Action (EN):** Raise a red drainage alert, more severe than the equivalent monsoon warning. Stop drip, clear channels urgently, and check saturation within 12 hours of the rain stopping.
- **कृती (MR):** लाल इशारा — आणि हा जुलैच्या इशाऱ्यापेक्षा जास्त तीव्र. ठिबक बंद करा, निचरा चर तातडीने मोकळे करा, पाऊस थांबल्यावर बारा तासांत संपृक्तता तपासा.
- **Basis:** The district lies in the path of tropical cyclones with a post-monsoon intensity peak in October and November. It is not struck at full intensity but can receive heavy rainfall. By then the rhizome is fully formed, the soil has been dry and cracked for weeks, and drainage channels have usually been neglected because the monsoon is considered over.
- **Yield impact:** u = 0.20 to 0.40, and more expensive than an equivalent July event because the entire season investment is already committed.
- **References:** climatestotravel Aurangabad cyclone seasonality

**D07-MO-002** (MO, red, conf 0.85, tier A) · _executable_

- **Trigger:** dry_spell_days at or above 7 AND stage is G3 or G4  
  `dry_spell_days >= 7 AND STAGE IN [G3, G4]`
- **Action (EN):** Resume full irrigation at 7 days rather than waiting for the general 10 to 12 day rule. In G3 and G4 a ten day gap is already too long.
- **कृती (MR):** या अवस्थांत १० ते १२ दिवसांची वाट पाहू नका — सात दिवसांवरच पूर्ण क्षमतेने ठिबक सुरू करा. G3 मध्ये दहा दिवस खूप जास्त आहेत.
- **Basis:** Dry spells of 20 to 45 days have been recorded across Maharashtra with Marathwada worse than average, and pulse yields in Latur fell 40 to 60 percent in one such event. The general 10 to 12 day intervention rule is a floor for average conditions, not a description of this belt.
- **Yield impact:** u = 0.20 for stress in the critical window, and it is irrecoverable because fingers that fail to differentiate do not form later.
- **References:** The Wire Science dry spell record; SIMA; Domain 3 critical stages

**D07-RF-001** (RF, red, conf 0.88, tier A) · _executable_

- **Trigger:** Pre-season area planning is initiated  
  `season_water_plan_basis IS NULL OR season_water_plan_basis != 'poor_year'`
- **Action (EN):** Size the area against a POOR year water assumption, not an average one. State plainly that 55 percent of years here fall below the long-term average. Half the area fully watered beats the full area half watered.
- **कृती (MR):** क्षेत्र वाईट वर्षाच्या गृहीतकावर ठरवा, सरासरीवर नाही. इथे निम्म्याहून जास्त वर्षे सरासरीपेक्षा कमी पाऊस पडतो. अर्धे क्षेत्र पूर्ण पाण्यासह हे पूर्ण क्षेत्र अर्ध्या पाण्यासह यापेक्षा चांगले.
- **Basis:** Against the Marathwada long-term average of 776 mm, 55 percent of years recorded less. The average is therefore better than the median, and planning on it fails in more than half of years. In ginger the largest cost is seed rhizome, spent before the season starts, so running short of water mid-season produces a near-total loss rather than a proportional one.
- **Yield impact:** Water exhaustion in G4 carries u = 0.20 to 0.40, and because the seed cost is already sunk the financial loss is close to total.
- **References:** Arabian Journal of Geosciences, Springer 2022

### D08

**D08-EU-002** (EU, red, conf 0.85, tier A) · _executable_

- **Trigger:** flowering_observed is true AND earthing_up_date is empty  
  `flowering_observed IS TRUE AND earthing_up_date IS NULL`
- **Action (EN):** Record that the earthing up window has closed and register a 12.5 percent yield penalty for Domain 11 gap attribution. Do not attempt earthing up now — disturbing roots during bulking causes further loss.
- **कृती (MR):** उटाळणीची मुदत संपली आहे. उत्पादनात सुमारे १२.५% घट गृहीत धरा. आता उटाळणी करू नका — गड्डा भरत असताना मुळे हलवल्यास अधिक नुकसान होईल.
- **Basis:** After the flowering spike opens, leaf growth stops and rhizome growth begins. Earthing up works by breaking roots so new fibrous roots form, which needs time. Doing it after bulking has started damages the root system without the compensating regrowth.
- **Yield impact:** u = 0.125, irrecoverable.
- **References:** Agrowon - Dr. Kadam flowering and rhizome growth; Domain 1 partition shift

**D08-LY-001** (LY, red, conf 0.9, tier A) · _executable_

- **Trigger:** soil_type is vertisol AND has_drip is true AND planting_layout is not broad_ridge  
  `soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout != 'broad_ridge'`
- **Action (EN):** Require broad ridge layout. It is the recommended method specifically for black soils and for fields using drip or sprinkler, and it yields 15 to 20 percent more than the alternatives while using 33 to 44 percent fewer plants.
- **कृती (MR):** रुंद वरंबा पद्धत वापरा. काळ्या जमिनी आणि ठिबक-तुषार वापरल्या जाणाऱ्या ठिकाणी हीच पद्धत शिफारसीत आहे. ती १५ ते २०% जास्त उत्पादन देते आणि त्याच वेळी ३३ ते ४४% कमी रोपे लागतात — म्हणजे खर्च कमी आणि उत्पादन जास्त.
- **Basis:** Both qualifying conditions hold at Kannad — the soil is black and drip is a precondition. The method lifts the root zone above standing water and suits single-line drip. Computed plant population falls from about 198,000 per hectare on flat beds to about 111,000 on the Kadam geometry, because wider spacing lets each rhizome expand laterally rather than competing.
- **Yield impact:** u = 0.167 for not using it, derived from the recorded 20 percent gain. Separately it cuts the largest cost line by roughly 44 percent.
- **References:** Agrowon - Dr. Jitendra Kadam; AgroWorld layout comparison; computed plant population

### D09

**D09-MT-002** (MT, red, conf 0.88, tier A) · _executable_

- **Trigger:** Leaf yellowing reported AND dap below 200  
  `leaf_yellowing_pattern IS NOT NULL AND dap < 200`
- **Action (EN):** BLOCK the maturity conclusion. Yellowing before 200 DAP has at least six other causes in this belt. Run the diagnosis sequence before any harvest planning.
- **कृती (MR):** पाने पिवळी पडली म्हणजे पक्वता नव्हे. या भागात दोनशे दिवसांच्या आत पिवळेपणाची किमान सहा वेगळी कारणे आहेत. काढणीचे नियोजन करण्यापूर्वी निदान करा.
- **Basis:** Yellowing in this belt can be nitrogen deficiency, iron or zinc lock-up from free lime, waterlogging, soft rot, bacterial wilt or heat scorch. Reading it as maturity would mean harvesting early and, worse, missing a rot diagnosis.
- **Yield impact:** Prevents both premature harvest and a missed disease diagnosis worth up to 0.70.
- **References:** Domain 4 yellowing diagnosis; Domain 6 differential diagnosis

**D09-PR-002** (PR, red, conf 0.85, tier C) · _executable, immutable_

- **Trigger:** The Malabar lime and sulphur method is being considered  
  `drying_method == 'malabar_lime_sulphur'`
- **Action (EN):** Warn on two counts before describing the method. Sulphur fumigation leaves SO2 residues that face strict limits in export markets, with some buyers rejecting treated produce outright. And burning sulphur in a closed room is a serious respiratory hazard. Do not present this as first choice until FSSAI and export limits have been verified.
- **कृती (MR):** पद्धत सांगण्यापूर्वी दोन इशारे. गंधकाच्या धुरीने सल्फर डायऑक्साइडचे अवशेष राहतात, आणि निर्यात बाजारात त्यावर कठोर मर्यादा आहेत — काही खरेदीदार गंधक-प्रक्रिया केलेला माल स्वीकारतच नाहीत. तसेच बंद खोलीत गंधक जाळणे श्वसनास गंभीर धोकादायक आहे. FSSAI व निर्यात मर्यादा तपासल्याशिवाय ही पद्धत पहिला पर्याय म्हणून देऊ नये.
- **Basis:** The method uses 6 to 10 g of sulphur per kg of rhizome across three 12-hour fumigation cycles in a closed room. That is both a residue source and an operator hazard, and the residue limit has not been checked.
- **Yield impact:** None. Food safety and market access.
- **References:** AgroWorld Malabar method; SO2 residue limits in export markets

### D14

**D14-DP-001** (DP, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** A satellite chip or image would show a plot other than the current viewer's own plot without aggregation  
  `sat_public_display_context IN ['third_party', 'cluster_aggregate'] AND third_party_share_consent_given IS FALSE`
- **Action (EN):** Block the display. Aggregate to cluster mean if legitimate cluster context is needed. Log the block event with viewer identity, plot identity, and requested purpose.
- **कृती (MR):** प्रदर्शन थांबवा. कायदेशीर cluster context आवश्यक असल्यास cluster mean वर aggregate करा. block घटना viewer, plot, हेतू यांच्यासह log करा.
- **Basis:** DPDP Act 2023 personal data definition. See RAW MASTER §13.6.
- **Yield impact:** Regulatory and reputation protection.
- **References:** DPDP Act 2023; RAW MASTER §13.6; Domain 12 DPDP rules

**D14-NV-004** (NV, red, conf 0.75, tier B) · _executable_

- **Trigger:** Plot NDVI has dropped by 0.15 or more over the last 10 days AND scene is trusted  
  `ndvi_delta_10d <= -0.15 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Send an URGENT scout request to the farmer today. Message: canopy has declined sharply on satellite view; check for waterlogging, disease, pest, hail damage, or herbicide drift, and report back with a photo. Simultaneously, pull last 7 days of sub-node soil moisture, EC, and rainfall for automatic cross-check and stage this for the D06 differential branch.
- **कृती (MR):** शेतकऱ्याला आजच URGENT scout विनंती पाठवा. संदेश: उपग्रह दृश्यात पिकाचा हिरवेपणा झपाट्याने कमी झाला आहे; पाणी साचणे, रोग, कीड, गारपीट, तणनाशक drift पैकी काय झाले ते फोटोसह कळवा. एकाच वेळी सब-नोडचे मागील ७ दिवसांचे मृदा-ओलावा, EC व पाऊस स्वयंचलितपणे ओढून D06 differential शाखेसाठी तयारी करा.
- **Basis:** A 15-point NDVI drop in 10 days is well outside the normal senescence trajectory in G2-G4 and reflects a real change. The signal itself is trustworthy; the CAUSE requires the ground check and D06 differential.
- **Yield impact:** Counted under investigation_dispatched; the yield-impact number is assigned by the confirmed downstream domain (D06 disease, D03 water, etc.), not by this rule.
- **References:** RAW MASTER §8.3, §9.2; Domain 6 differential-diagnosis rules; Zhu & Woodcock 2014

**D14-POS-001** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'the satellite detects ginger rhizome rot'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_001'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. The underground rhizome is invisible to every current satellite; canopy signal is late and shared with several other causes. See RAW MASTER §5.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. भूमिगत गड्डा कोणत्याही उपग्रहाला दिसत नाही; पर्णसमूह-सिग्नल उशीरचा व अनेक कारणांचा common आहे. RAW MASTER §5 पहा.
- **Basis:** The underground rhizome is invisible to every current satellite; canopy signal is late and shared with several other causes. See RAW MASTER §5.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §5; Domain 6 rhizome-canopy decoupling architecture note

**D14-POS-002** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'NDVI tells you when to harvest'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_002'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Canopy senescence signals a stage window, not maturity precision. Harvest timing is a D09 rule with sub-node + DAP inputs.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. पर्णसमूह senescence अवस्थेची खिडकी सांगते, माग्युरिटीची अचूक वेळ नाही. काढणीचा निर्णय D09 चा सब-नोड + DAP आधारित नियम.
- **Basis:** Canopy senescence signals a stage window, not maturity precision. Harvest timing is a D09 rule with sub-node + DAP inputs.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §16.1; Domain 9 harvest rules

**D14-POS-003** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'we predict your yield from space'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_003'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Domain 12 already prohibits yield prediction as a customer claim; satellite-derived estimates carry the same prohibition.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. Domain 12 आधीच उत्पन्न-भविष्यवाणी ग्राहक-दाव्यासाठी प्रतिबंधित करते; उपग्रह-आधारित अंदाजांना तीच बंदी.
- **Basis:** Domain 12 already prohibits yield prediction as a customer claim; satellite-derived estimates carry the same prohibition.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §16.1; Domain 12 prohibited claims

**D14-POS-004** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'our AI counts your ginger plants from orbit'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_004'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Plant count from 10 m Sentinel-2 pixels is not physically possible. Sub-metre commercial imagery is prohibitively expensive per farmer.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. १० मी Sentinel-2 पिक्सेल्सवरून झाडांची गणना भौतिकदृष्ट्या शक्य नाही. Sub-metre व्यावसायिक imagery प्रति शेतकरी अत्यंत महाग.
- **Basis:** Plant count from 10 m Sentinel-2 pixels is not physically possible. Sub-metre commercial imagery is prohibitively expensive per farmer.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §16.1; ESA Sentinel-2 resolution specification

**D14-POS-005** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'cloud is not a problem for us'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_005'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Cloud is a real problem; SAR reduces but does not eliminate the gap; be honest.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. ढग खरे अडथळे आहेत; SAR ते कमी करते पण संपवत नाही; प्रामाणिक रहा.
- **Basis:** Cloud is a real problem; SAR reduces but does not eliminate the gap; be honest.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §3, §16.1

**D14-POS-006** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'we replace your soil sensor with satellite'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_006'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Sub-node soil moisture and EC are the authorities in their domains; satellite provides context, never replaces them.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. सब-नोड मृदा-ओलावा व EC त्यांच्या डोमेनवर अधिकारी आहेत; उपग्रह संदर्भ देतो, त्यांची जागा घेत नाही.
- **Basis:** Sub-node soil moisture and EC are the authorities in their domains; satellite provides context, never replaces them.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §1.4, §16.1

**D14-POS-007** (POS, red, conf 0.95, tier A) · _executable, immutable_

- **Trigger:** An outgoing customer message or marketing artefact contains a claim that 'our satellite view is always up-to-date'  
  `outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_007'`
- **Action (EN):** Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Revisit is 5-20 days depending on cloud. Freshness varies and must be shown, not hidden.
- **कृती (MR):** बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. पुनरागमन ढगांवर अवलंबून ५-२० दिवस. ताजेपणा बदलतो — तो दाखवायचा, लपवायचा नाही.
- **Basis:** Revisit is 5-20 days depending on cloud. Freshness varies and must be shown, not hidden.
- **Yield impact:** Reputation and truthfulness protection.
- **References:** RAW MASTER §3, §16.1

**D14-SR-002** (SR, red, conf 0.78, tier A) · _executable_

- **Trigger:** SAR VV has dropped by more than 4 dB against the previous same-orbit acquisition AND rainfall event exists in the last 48 hours  
  `sar_vv_delta_db < -4.0 AND rainfall_last_48h_mm > 20 AND sar_gap_days <= 12`
- **Action (EN):** Send an URGENT alert to the farmer: satellite radar shows probable standing water on the plot after the recent rain. Inspect drainage channels and remove blockages today. Ginger cannot tolerate more than 24 hours of waterlogging without rhizome damage. If sub-node is available, it will confirm; if it is not (monsoon LoRa fade common), do not wait for confirmation to act.
- **कृती (MR):** शेतकऱ्याला URGENT इशारा पाठवा: नुकत्याच झालेल्या पावसानंतर उपग्रह रडार दाखवत आहे प्लॉटवर पाणी साचले आहे. आजच निचरा नाल्यांची तपासणी करा व अडथळे काढा. आले २४ तासांपेक्षा जास्त पाण्यात राहू शकत नाही — गड्ड्याला इजा होते. सब-नोड उपलब्ध असल्यास पुष्टी देईल; नसल्यास (मान्सूनमध्ये LoRa fade सामान्य) पुष्टीची वाट पाहू नका.
- **Basis:** Water is specular at C-band, causing near-total backscatter loss. A 4 dB drop is well outside speckle noise. See RAW MASTER §6.6 caveats.
- **Yield impact:** Waterlogging in G2-G4 for 48+ hours cuts yield 10-25% depending on stage; D06 has the drainage-failure branch.
- **References:** Torres et al. 2012 Sentinel-1 mission; Small 2011; ICAR-CRIDA drainage studies; RAW MASTER §6.3, §6.6

## P2 — executable, lower severity — 167 rules

### D01

**D01-HV-004** (HV, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** target_product is seed_rhizome AND harvest is being considered before full maturity  
  `harvest_route == 'seed_rhizome' AND dap < 235`
- **Action (EN):** REFUSE early harvest for seed crop. Full maturity is mandatory. Immature rhizome does not survive storage and does not sprout the following season.
- **कृती (MR):** बेण्यासाठीचे पीक कधीही लवकर काढू नये. अपक्व गड्डा साठवणीत टिकत नाही आणि पुढच्या हंगामात उगवत नाही.
- **Basis:** Skin corking and dry matter accumulation complete only at full maturity, and both determine storage survival over the four to five month gap to next planting.
- **Yield impact:** Affects next season. Failure here compounds into establishment loss and wasted seed cost, the largest input line.
- **References:** Agrowon - Dr. Kadam; AgroWorld seed storage

**D01-PH-006** (PH, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** dap equals 120 AND sample_dig_120_done is false  
  `dap BETWEEN 118 AND 124 AND sample_dig_120_done IS FALSE`
- **Action (EN):** Request destructive sample of one plant. Checklist: finger count (3-5 expected), firmness, colour, smell, root condition. A sour or rotten smell is an immediate escalation to Domain 6.
- **कृती (MR):** एक नमुना रोप उकरून पहा. ३-५ स्पष्ट बोटे असावीत, भरीव व टणक, रंग फिकट पिवळसर, वास ताजा. कुजका वास आल्यास तात्काळ कळवा.
- **Basis:** The yield organ is invisible. Partially infected plants stay green above ground while the rhizome is already compromised, so surface appearance is unreliable.
- **Yield impact:** Enables early detection of the largest single factor (soft rot, u up to 0.70) while neighbouring plants can still be protected.
- **References:** Agrowon; ScienceDirect Heliyon soft rot review

**D01-PW-002** (PW, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Month is May or early June AND planting not yet done  
  `MONTH IN [MAY, JUN] AND days_to_planting BETWEEN 1 AND 20`
- **Action (EN):** Warn that ginger timing is opposite to other kharif crops. Cotton and soybean are sown after the monsoon establishes; ginger must be planted before it.
- **कृती (MR):** अद्रक हे इतर खरीप पिकांसारखे नाही. कापूस-सोयाबीन पाऊस आल्यावर पेरतात; अद्रक पाऊस येण्यापूर्वी लावावे लागते. ७ जून ही शेवटची मुदत आहे — पावसाची वाट पाहू नका.
- **Basis:** Monsoon normally covers most of Maharashtra by 10 June, but the ginger deadline is 7 June. A farmer habituated to cotton and soybean timing will wait for rain and miss the window.
- **Yield impact:** Prevents the u = 0.20 loss in D01-PW-001 by acting before the deadline rather than reporting it after.
- **References:** Agrowon - Dr. Kadam; ICAR-CRIDA monsoon onset

**D01-VR-001** (VR, yellow, conf 0.9, tier A) · _executable_

- **Trigger:** variety is not set AND planning phase  
  `variety IS NULL AND days_to_planting > 30`
- **Action (EN):** Recommend Mahima for the main area. Alternate Varada. If dry ginger is the strategic route, consider Rejatha. Fallback to Mahim only if the first three are unavailable locally.
- **कृती (MR):** मुख्य क्षेत्रासाठी महिमा. ती सूत्रकृमी प्रतिकारक असल्याने अप्रत्यक्षपणे कंदकूज व मर रोगापासूनही संरक्षण देते — आणि तो फायदा फुकट आहे, फक्त योग्य बेणे निवडून. न मिळाल्यास वरदा; सुंठ हाच मार्ग असल्यास रीजाथा.
- **Basis:** Mahima leads on yield (94 q/acre), tiller count (12-13) and lowest fibre (3.26 pct), and is nematode resistant. Nematode wounds are a documented entry route for both soft rot fungi and Ralstonia wilt, so resistance here is indirect disease control at zero cost.
- **Yield impact:** u = 0.138 against Mahim, the weakest of the four. Roughly Rs 62,400 per acre.
- **References:** Agrowon - Dr. Kadam variety comparison; IntechOpen - Samuel & Mathew 1986 nematode-wilt link

**D01-VR-002** (VR, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** dap equals 180  
  `dap BETWEEN 178 AND 184 AND sample_dig_180_done IS FALSE`
- **Action (EN):** Remind the farmer to mark healthy vigorous plants for next season's seed NOW, while the crop is still green. This selection cannot be made at harvest. BLOCK this advice entirely if field_history_rot or field_history_wilt is true.
- **कृती (MR):** पुढील हंगामाचे बेणे आत्ताच निवडा. पीक हिरवे असतानाच निरोगी, जोमदार रोपे खुणावून ठेवावी लागतात — काढणीच्या वेळी ही निवड करता येत नाही.
- **Basis:** Seed selection is a mid-season observation task disguised as a post-harvest one. Vigour and disease-freedom are only visible on the standing crop.
- **Yield impact:** Affects next season, not this one. Poor seed carries u = 0.20 to 0.50 into the following crop.
- **References:** Agrowon - Dr. Kadam; Core C13.5

### D02

**D02-CL-001** (CL, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Pre-season planning initiated  
  `days_to_planting BETWEEN 55 AND 95 AND deep_ploughing_done IS FALSE`
- **Action (EN):** Issue the land preparation calendar: March soil sample and deep ploughing, late March stone and weed removal, April solarization, early May kulav passes, May FYM and basal P and K, May bed forming, May drip laid and tested, May main drainage channel, late May seed grading and treatment, planting by 7 June, mulch immediately after planting.
- **कृती (MR):** पूर्वमशागतीचे वेळापत्रक — मार्च: माती नमुना व खोल नांगरट. मार्च अखेर: दगड व तणकंद वेचणी. एप्रिल: सौरीकरण. मे सुरुवात: कुळवाच्या पाळ्या. मे: शेणखत, स्फुरद व पालाश, रुंद वरंबे, ठिबक, निचरा चर. मे अखेर: बेणे प्रतवारी व प्रक्रिया. ७ जूनपर्यंत लागवड. लागवडीनंतर लगेच आच्छादन.
- **Basis:** Every step has a predecessor and the whole chain terminates at a hard deadline. The narrow vertisol working window and the fixed 7 June planting cut-off leave no slack.
- **Yield impact:** Protects the 0.20 u-value attached to late planting and the 0.167 attached to bed layout.
- **References:** Agrowon - Dr. Kadam; Domain 2 land preparation sequence

**D02-DR-003** (DR, yellow, conf 0.8, tier A) · _executable_

- **Trigger:** Forecast exceeds 50 mm rain in 48 hours AND stage is G2 or G3  
  `forecast_rain_48h_mm > 50 AND STAGE IN [G2, G3]`
- **Action (EN):** Pre-warn: check that all three drainage levels are clear of silt, and stop drip. After the rain, check for saturation within 12 hours.
- **कृती (MR):** निचरा चर मोकळे आहेत का तपासा, ठिबक बंद करा. पाऊस थांबल्यावर १२ तासांत पाणी साचले आहे का पहा.
- **Basis:** Channels silt up during the season and are usually only noticed when they fail. A forecast-triggered check converts a reactive failure into a scheduled inspection.
- **Yield impact:** Reduces the probability of the saturation event that drives soft rot.
- **References:** Agrowon - Dr. Kadam; Core C2.3

### D03

**D03-MN-003** (MN, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** rain_gap_days greater than or equal to 10 AND stage is not G3 or G4  
  `rain_gap_days >= 10 AND STAGE IN [G1, G2]`
- **Action (EN):** Resume full irrigation per the table.
- **कृती (MR):** पावसात १० ते १२ दिवसांचा खंड पडल्यास पिकास पाणी द्यावे — तक्त्यानुसार पूर्ण क्षमतेने.
- **Basis:** Published guidance for Maharashtra ginger sets the intervention point at a 10 to 12 day break in rainfall.
- **Yield impact:** Prevents drought stress during less sensitive stages.
- **References:** Agrowon - Dr. Kadam

**D03-MU-001** (MU, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** Planting completed AND mulch_stage_1_done is false  
  `dap BETWEEN 0 AND 4 AND mulch_stage_1_done IS FALSE`
- **Action (EN):** Apply mulch immediately. This is not an optional improvement in this belt; it is a precondition for emergence.
- **कृती (MR):** लागवडीनंतर लगेच आच्छादन घाला. इथे ते ऐच्छिक सुधारणा नाही — उगवणीची अट आहे. उघड्या काळ्या जमिनीचे तापमान हवेपेक्षा बरेच जास्त असते आणि बेणे भाजू शकते.
- **Basis:** Optimal soil temperature for sprouting is 25 to 26 C. Recorded maxima in this district reach 45.9 C and bare black soil runs hotter than air. Mulch is the only practical way to bring the surface temperature down.
- **Yield impact:** u = 0.12 estimated for absent stage-one mulch under heat stress, and it also carries the largest single documented disease benefit at stage level.
- **References:** Domain 1 sprouting optimum; Organic Mandya mulch programme; District Profile temperature

**D03-SB-002** (SB, yellow, conf 0.85, tier B) · _executable_

- **Trigger:** calibration_done is false or calibration_date is older than the validity period  
  `calibration_done IS FALSE`
- **Action (EN):** Mark all moisture-derived advisory LOW CONFIDENCE and disable automated irrigation triggers. Fall back to the month-wise table plus rain deduction. Tell the user this is happening and why.
- **कृती (MR):** calibration झालेले नसल्यास ओलावा-आधारित सल्ला कमी विश्वासार्ह म्हणून दाखवा आणि स्वयंचलित ठिबक बंद ठेवा. तक्ता आणि पाऊस वजावट यावर चालवा — आणि हे वापरकर्त्याला सांगा.
- **Basis:** Capacitive sensors respond to bulk dielectric permittivity, which varies strongly with clay content, so factory calibration is invalid on vertisol. Two-point calibration using plot soil is required.
- **Yield impact:** None if the fallback is used. Significant if uncalibrated readings drive irrigation.
- **References:** Core C10.3; sensor physics

**D03-SC-002** (SC, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** soil_texture_class is heavy AND drip_runtime_min greater than 60  
  `drip_runtime_min > 60 AND soil_texture_class == 'heavy'`
- **Action (EN):** Split the run into two shifts rather than one long run. Applies particularly from September to November.
- **कृती (MR):** एका वेळी ९० मिनिटे न देता ४५ अधिक ४५ अशा दोन पाळ्यांत द्या. काळ्या जमिनीत झिरपण्याचा वेग कमी असल्याने एकाच वेळी जास्त पाणी दिल्यास ते पृष्ठभागावर साचते आणि वाहून जाते — म्हणजे मोजून दिलेले पाणी मुळांपर्यंत पोहोचतच नाही.
- **Basis:** Application rate must not exceed soil infiltration rate. On vertisol a long single run produces surface ponding and runoff, so the measured volume does not reach the root zone.
- **Yield impact:** Prevents a silent deficit in which the schedule appears correct but delivery is not.
- **References:** Domain 3 infiltration reasoning; Domain 2 percolation test

**D03-SC-003** (SC, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** current_stage is G1  
  `STAGE IN [G1] AND air_temp_max_c > 33`
- **Action (EN):** Run two shifts, morning and evening, of 30 to 45 minutes each. Keep the soil moist, not soaked.
- **कृती (MR):** सकाळ आणि संध्याकाळ अशा दोन पाळ्यांत, प्रत्येकी ३० ते ४५ मिनिटे. जमीन ओलसर ठेवा — भिजवू नका. या अवस्थेत जास्त पाणी हा ताणापेक्षा मोठा धोका आहे, कारण बेणे हा मुळे नसलेला मांसल तुकडा आहे.
- **Basis:** Freshly planted seed rhizome has no root system and rots readily in saturated soil. Small frequent doses also moderate the surface temperature of bare black soil, which in May runs well above the 25-26 C optimum for sprouting.
- **Yield impact:** Protects establishment, which is a hard ceiling for the season.
- **References:** Agrowon - Dr. Kadam runtime; Domain 1 sprouting optimum

**D03-WL-004** (WL, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** Forecast exceeds 50 mm within 48 hours AND stage is G2 or G3  
  `DURATION(soil_moisture_vwc > vwc_saturation) > 6 HOURS AND STAGE IN [G1]`
- **Action (EN):** Pre-warn. Stop drip now rather than after the rain. Verify channels are clear before the event.
- **कृती (MR):** पूर्वसूचना — पाऊस पडल्यावर नव्हे, आत्ताच ठिबक बंद करा आणि चर मोकळे आहेत का तपासा.
- **Basis:** Acting on the forecast rather than the sensor converts a reactive response into a preventive one, and channel clearing takes time that is not available once the rain has started.
- **Yield impact:** Reduces the probability of the saturation event rather than responding to it.
- **References:** Core C3.3 forecast-conditioned suppression

**D03-WW-001** (WW, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** Estimated 60 days to harvest  
  `days_to_harvest BETWEEN 55 AND 62 AND water_withdrawal_start_date IS NULL`
- **Action (EN):** Begin gradual water withdrawal. Reduce to about 80 percent at 45 days, 60 percent at 30 days, 30 percent at 15 days, and stop completely 7 days before harvest.
- **कृती (MR):** काढणीच्या एक ते दोन महिने आधी पाणी हळूहळू कमी करायला सुरुवात करा, आणि काढणीच्या एक ते दोन आठवडे आधी पूर्ण बंद करा. हे प्रत सुधारण्यासाठी आहे.
- **Basis:** Continued irrigation prevents skin corking. An uncured rhizome weighs more but stores badly and gives lower dry recovery. Abrupt cessation cracks vertisol and makes harvest injurious, so the taper must be gradual.
- **Yield impact:** Does not change weight materially but strongly affects grade, and the observed market spread between grades is about 2.7 times.
- **References:** CropLibrary; Agrowon - Bitle & Deshmukh descending table; Domain 9 grading

**D03-WW-002** (WW, yellow, conf 0.7, tier B) · _executable_

- **Trigger:** soil_texture_class is heavy AND water withdrawal in progress  
  `water_withdrawal_start_date IS NOT NULL AND soil_texture_class == 'heavy'`
- **Action (EN):** Make the taper slower than the standard schedule. Abrupt drying cracks black soil, which makes lifting difficult and injures rhizomes.
- **कृती (MR):** काळ्या जमिनीत उतरण अधिक हळू ठेवा. एकदम पाणी बंद केल्यास जमीन फुटते, काढणी कठीण होते आणि गड्ड्याला इजा होते — आणि तीच इजा साठवणीत कूज बनते.
- **Basis:** Vertisol shrinks and cracks on drying. Harvest injury is the entry route for storage rot, and by harvest the entire season's cost is already committed.
- **Yield impact:** Acts on post-harvest loss rather than field yield.
- **References:** Domain 2 vertisol behaviour; Domain 9 harvest injury

### D04

**D04-DG-004** (DG, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** leaf_yellowing_pattern is margin_scorch AND air_temp_max_c below 35 in the last three days  
  `leaf_yellowing_pattern == 'margin_scorch' AND air_temp_max_c > 35`
- **Action (EN):** Diagnose as potassium deficiency rather than heat scorch, and check whether the late potassium splits were applied.
- **कृती (MR):** हे उष्णतेचे नव्हे तर पालाशाच्या कमतरतेचे लक्षण असू शकते. उशिराचे पालाश हप्ते दिले होते का ते तपासा.
- **Basis:** Both potassium deficiency and heat stress scorch leaf margins. The weather record separates them, which is a discriminator available only where temperature is logged.
- **Yield impact:** Directs attention to the 0.12 late potassium value.
- **References:** Domain 4 diagnosis table; Domain 1 heat threshold

**D04-FG-001** (FG, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** Fertigation scheduled  
  `has_drip IS TRUE AND fertigation_active IS FALSE AND dap BETWEEN 30 AND 150`
- **Action (EN):** Flush with plain water for 15 to 20 minutes before and after fertigation. Do not fertigate into saturated soil.
- **कृती (MR):** फर्टिगेशनपूर्वी १५-२० मिनिटे साधे पाणी सोडा आणि नंतरही १५-२० मिनिटे — म्हणजे नळ्यांत खत राहणार नाही. संपृक्त जमिनीत फर्टिगेशन करू नये, खत वाहून जाते.
- **Basis:** Pre-flush fills the lines so distribution is even; post-flush prevents salt and algal build-up in emitters. Fertigating saturated soil leaches the nutrient below the shallow root zone.
- **Yield impact:** Protects delivery efficiency rather than adding yield.
- **References:** standard fertigation practice; Domain 3 saturation override

**D04-MC-001** (MC, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** dap between 45 and 60 AND micronutrient_spray_1_done is false  
  `dap BETWEEN 45 AND 60 AND micronutrient_spray_1_done IS FALSE`
- **Action (EN):** Apply the first foliar micronutrient spray: zinc sulphate 3 g, ferrous sulphate 2 g and boron 2 g per litre. Spray early morning or evening, with a spreader.
- **कृती (MR):** सूक्ष्म अन्नद्रव्यांची पहिली फवारणी करा — प्रति लिटर झिंक सल्फेट ३ ग्रॅम, फेरस सल्फेट २ ग्रॅम, बोरॉन २ ग्रॅम. सकाळी लवकर किंवा संध्याकाळी, चिकटद्रव्यासह फवारा.
- **Basis:** The combination of zinc 0.3 percent, iron 0.2 percent and boron 0.2 percent sprayed twice gave the highest yield in a documented trial. Foliar delivery bypasses soil chemistry, which matters where free lime locks up zinc and iron.
- **Yield impact:** u = 0.11, derived from the trial in which foliar zinc gave 16.2 kg per 3 square metre bed against 14.4 for soil application.
- **References:** Roy et al 1992; IISR 2002; Vikaspedia timing

**D04-MC-002** (MC, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** dap between 75 and 90 AND micronutrient_spray_2_done is false  
  `dap BETWEEN 75 AND 90 AND micronutrient_spray_2_done IS FALSE`
- **Action (EN):** Apply the second foliar micronutrient spray with the same mixture.
- **कृती (MR):** सूक्ष्म अन्नद्रव्यांची दुसरी फवारणी त्याच मिश्रणाने करा.
- **Basis:** Both source pairs specify two sprays. The second falls just before rhizome initiation, when demand rises and the canopy is large enough to absorb well.
- **Yield impact:** Completes the 0.11 micronutrient value.
- **References:** Roy et al 1992; Vikaspedia

**D04-NS-001** (NS, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** dap approximately 60 AND n_split_1_date is empty  
  `dap BETWEEN 57 AND 64 AND n_split_1_date IS NULL`
- **Action (EN):** Apply the first nitrogen split, about 24 kg N per acre — half the season total.
- **कृती (MR):** नत्राचा पहिला हप्ता द्या — एकरी सुमारे २४ किलो नत्र, म्हणजे हंगामाच्या निम्मा.
- **Basis:** First split falls about one month after emergence completes, when tillering is active and the crop can use nitrogen for shoot growth.
- **Yield impact:** u = 0.10 estimated for a missed nitrogen split, partially recoverable if caught early.
- **References:** Agrowon - Dr. Kadam

**D04-NS-002** (NS, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** Earthing up scheduled at about 80 DAP  
  `dap BETWEEN 78 AND 88 AND n_split_2_date IS NULL`
- **Action (EN):** Apply the second and FINAL nitrogen split, about 24 kg N per acre, together with 600 to 800 kg per acre of neem or karanj cake. Bundle with earthing up and mulch stage two so all are done in one field visit.
- **कृती (MR):** नत्राचा दुसरा आणि शेवटचा हप्ता द्या — एकरी सुमारे २४ किलो नत्र, सोबत करंज किंवा निंबोळी पेंड ६०० ते ८०० किलो. उटाळणी आणि आच्छादनाचा दुसरा टप्पा याच फेरीत करा.
- **Basis:** This is the last nitrogen of the season. Combining it with earthing up incorporates it into the soil at the same time as the operation that stimulates new root formation, and neem cake applied with urea produced the highest available nitrogen in a documented trial.
- **Yield impact:** Carries both the nitrogen split value and, through bundling, protects the 0.125 earthing up value.
- **References:** Agrowon - Dr. Kadam; IISR Annual Report 2002 neem cake plus urea

**D04-PK-001** (PK, yellow, conf 0.8, tier A) · _executable_

- **Trigger:** dap approximately 110 AND k_late_split_1_date is empty AND has_drip is false  
  `dap BETWEEN 108 AND 115 AND k_late_split_1_date IS NULL`
- **Action (EN):** Apply about 15 kg K per acre. Explain clearly why: the crop looks healthy now, but the rhizome is filling right now and it fills on potassium.
- **कृती (MR):** पालाशाचा हप्ता द्या — एकरी सुमारे १५ किलो. पीक चांगले दिसत असले तरी गड्डा नेमका आत्ता भरतो आहे, आणि तो पालाशावर भरतो. हा हप्ता वगळू नये.
- **Basis:** The Maharashtra schedule adds two potassium splits after nitrogen has finished, bringing the season total to about 60 kg per acre which closely matches the measured uptake of about 59 kg. Without these splits the schedule under-supplies the nutrient the crop removes most.
- **Yield impact:** u = 0.12 estimated for skipping the late potassium splits.
- **References:** Agrowon - Dr. Kadam; SciELO uptake study

**D04-PK-002** (PK, yellow, conf 0.8, tier A) · _executable_

- **Trigger:** dap approximately 140 AND k_late_split_2_date is empty AND has_drip is false  
  `dap BETWEEN 138 AND 145 AND k_late_split_2_date IS NULL`
- **Action (EN):** Apply the second late potassium split, about 15 kg K per acre.
- **कृती (MR):** पालाशाचा दुसरा वाढीव हप्ता द्या — एकरी सुमारे १५ किलो.
- **Basis:** Rhizome bulking continues to harvest. Source notes that the rhizome keeps developing even after foliage growth has slowed, so nutrition cannot stop when the leaves do.
- **Yield impact:** Part of the 0.12 late potassium value.
- **References:** Agrowon - Dr. Kadam; IntechOpen growth phases

**D04-SB-002** (SB, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** Fertigation completed AND no EC rise detected within 2 to 4 hours  
  `fertigation_active IS TRUE AND fertigation_last_ec_response IS NULL`
- **Action (EN):** Alert that the fertiliser may not have reached the root zone. Check emitters, venturi and tank.
- **कृती (MR):** खत मुळांपर्यंत पोहोचले का तपासा — तोट्या तुंबल्या असतील, venturi बंद असेल, किंवा टाकी रिकामी असेल.
- **Basis:** EC responds immediately to a salt pulse regardless of which nutrient it is. That makes it a reliable delivery check even though it is an unreliable NPK estimate.
- **Yield impact:** A fertigation failure otherwise goes unnoticed for weeks while the crop slowly falls behind and the cause is never identified.
- **References:** Domain 4 probe valid uses

**D04-SB-003** (SB, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** ec_trend_pct rising steadily across the season AND rainfall low  
  `ec_trend_pct > 20 AND rainfall_mm < 2`
- **Action (EN):** Warn of salt accumulation. Consider a leaching irrigation and switching late potassium from MOP to SOP.
- **कृती (MR):** क्षार साचत आहेत. लीचिंग सिंचनाचा विचार करा आणि उशिराचे पालाश MOP ऐवजी SOP मधून द्या.
- **Basis:** Drip concentrates salts at the wetting front perimeter. In low rainfall conditions there is no leaching event to reset it, so EC climbs across the season and across years.
- **Yield impact:** Long-term soil degradation rather than single-season yield.
- **References:** Core C1.4; Domain 4 probe valid uses

### D05

**D05-CH-007** (CH, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Seed treatment being planned  
  `days_to_planting BETWEEN 1 AND 8 AND hot_water_treatment_done IS FALSE`
- **Action (EN):** Include an insecticide with the fungicide in the seed dip: quinalphos 25 EC 20 ml or dimethoate 30 EC 10 ml per 10 litres, dip 15 to 20 minutes. Then shade dry before any biological treatment.
- **कृती (MR):** बेणे प्रक्रियेत बुरशीनाशकासोबत कीडनाशकही घ्या — प्रति १० लिटर पाण्यात क्विनॉलफॉस २५% प्रवाही २० मिलि किंवा डायमेथोएट ३०% प्रवाही १० मिलि, १५ ते २० मिनिटे बुडवा. नंतर सावलीत सुकवूनच जैविक प्रक्रिया करा.
- **Basis:** Seed rhizome is the entry vector for both pests and pathogens. Treating once at planting covers both, and it is the only point at which carried infestation can be addressed.
- **Yield impact:** Contributes to the 0.135 seed treatment value recorded in Domain 1.
- **References:** Agrowon - Dr. Kadam seed treatment

**D05-LR-001** (LR, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** rolled_leaves observed AND month between late August and November  
  `STAGE IN [G3] AND MONTH IN [SEP, OCT, NOV]`
- **Action (EN):** Pluck the rolled leaves with the larva inside and destroy them. This removes larva and pupa together because both are in the same roll.
- **कृती (MR):** गुंडाळलेली पाने अळीसह खुडून नष्ट करा. अळी आणि कोष दोन्ही त्याच गुंडाळीत असतात, त्यामुळे एकाच कृतीत दोन्ही अवस्था नष्ट होतात.
- **Basis:** Source notes that the pest pupates inside the leaf roll. So mechanical removal is unusually efficient for this species.
- **Yield impact:** u = 0.03. Damage is to foliage only, not to the rhizome.
- **References:** Agrowon - Mali & Mahajan

**D05-NE-001** (NE, yellow, conf 0.78, tier A) · _executable_

- **Trigger:** dap at 60 or 90 AND tillers_per_plant below 70 percent of variety expectation AND nitrogen split applied  
  `dap IN [60, 90] AND tillers_per_plant < 9`
- **Action (EN):** Suspect nematodes rather than nitrogen deficiency. Dig roots and look for galls. If confirmed, raise neem cake at earthing up toward 8 quintal per acre.
- **कृती (MR):** हे नत्राच्या कमतरतेचे नव्हे तर सूत्रकृमींचे लक्षण असू शकते. मुळे उकरून गाठी आहेत का पहा. पुष्टी झाल्यास उटाळणीच्या वेळी निंबोळी पेंडीची मात्रा एकरी ८ क्विंटलपर्यंत वाढवा.
- **Basis:** Nematodes suck root sap, so growth is stunted and tiller number falls. Mahima is expected to produce 12 to 13 tillers per plant, so a shortfall against the variety norm is measurable. The symptom set overlaps with nitrogen deficiency, which is why the nitrogen record is part of the trigger.
- **Yield impact:** u = 0.15, and it also opens the wound route for rot.
- **References:** Agrowon - Mali & Mahajan; Agrowon variety tiller counts

**D05-PC-002** (PC, yellow, conf 0.9, tier A) · _executable_

- **Trigger:** Planting date being decided  
  `planting_date IS NOT NULL AND dap < 0`
- **Action (EN):** Reinforce the 7 June deadline as a pest control measure. Rhizome fly peaks in July and August; timely planting means the crop is 60 to 90 days old and robust by then.
- **कृती (MR):** ७ जूनची मुदत ही कीड नियंत्रणाचीही पहिली आणि सर्वात स्वस्त उपाययोजना आहे. कंदमाशीचा हंगाम जुलै-ऑगस्ट आहे; वेळेवर लागवड केल्यास तेव्हा पीक ६० ते ९० दिवसांचे व मजबूत असते.
- **Basis:** Source states directly that planting after the first week of June causes large scale rhizome fly and soft rot incidence. Late planting leaves the crop tender at exactly the moment the pest peaks.
- **Yield impact:** Shares the 0.20 u-value with the Domain 1 planting deadline rule.
- **References:** Agrowon - Dr. Kadam

**D05-PC-004** (PC, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** Weeding or earthing up in progress  
  `previous_crops_3yr IS NOT NULL AND days_to_planting > 30`
- **Action (EN):** Instruct that the rhizome must not be injured. Mechanical injury opens the same wound route as any pest and requires no insect at all.
- **कृती (MR):** खुरपणी व उटाळणी करताना गड्ड्याला इजा होणार नाही याची काळजी घ्या. यांत्रिक इजा हीसुद्धा किडीसारखीच जखम आहे, आणि तिच्यातूनही बुरशी आत शिरते.
- **Basis:** Source states that injury to the rhizome during earthing up or weeding allows Pythium and Fusarium to enter. This is a pest-free route into the same disease.
- **Yield impact:** Prevents entry into the 0.50 to 0.90 rot pathway.
- **References:** Agrowon - Mali & Mahajan; Domain 2 weeding chain

**D05-RF-001** (RF, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Date is around 20 June, or dap is about 30, AND castor_bait_prepared_date is empty  
  `dap BETWEEN 28 AND 33 AND castor_bait_prepared_date IS NULL`
- **Action (EN):** Start the castor seed bait TODAY. Crush 200 g castor seed into 1.5 litres of water in plastic containers. Explain that it takes 8 to 10 days to develop the smell and the pest arrives in July.
- **कृती (MR):** एरंडी आमिष आजच भिजत घाला. प्लॅस्टिकच्या भांड्यात भरडलेले एरंडीचे बी २०० ग्रॅम आणि १.५ लिटर पाणी. ८ ते १० दिवसांनी विशिष्ट वास येऊन कंदमाशा आकर्षित होऊन मरतात — आणि कंदमाशी जुलैत येते, म्हणून आत्ताच सुरुवात करावी लागते.
- **Basis:** The bait requires 8 to 10 days to develop the attractant odour. Rhizome fly peaks in July and August. Starting when the pest is seen is already too late.
- **Yield impact:** Primary control for the pest carrying u = 0.175, with no regulatory constraint and negligible cost.
- **References:** Agrowon - Mali & Mahajan; described as extremely simple, effective and low cost

**D05-SH-001** (SH, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** dap between 45 and 60 AND light_trap_installed is false  
  `dap BETWEEN 45 AND 60 AND light_trap_installed IS FALSE`
- **Action (EN):** Install one light trap per acre, at field centre slightly above crop height. Switch on at dusk and off before dawn. Begin recording the nightly catch by hand.
- **कृती (MR):** एकरी एक प्रकाश सापळा लावा — शेताच्या मध्यभागी, पिकाच्या उंचीच्या थोडे वर. संध्याकाळी चालू, पहाटे बंद. रात्रभर चालू ठेवू नये, कारण मित्रकीटकही पडतात. रोजची संख्या हाताने नोंदवायला सुरुवात करा.
- **Basis:** Light trap at one per acre is the recommended mechanical control for shoot borer, which is active July to October.
- **Yield impact:** u = 0.075 for shoot borer.
- **References:** Agrowon - Mali & Mahajan

**D05-SW-001** (SW, yellow, conf 0.75, tier A) · _executable_

- **Trigger:** rh_pct above 80 for three consecutive days AND cloudy AND month between July and October  
  `DURATION(rh_pct > 80) > 72 HOURS AND MONTH IN [JUL, AUG, SEP, OCT]`
- **Action (EN):** Issue a pest pressure alert and double the scouting frequency. Check biological preventives are in place. Do not spray on this signal alone.
- **कृती (MR):** कीड-दाबाचा इशारा द्या आणि निरीक्षणाची वारंवारता दुप्पट करा. जैविक प्रतिबंधक उपाय जागेवर आहेत का तपासा. फक्त या संकेतावर फवारणी करू नये.
- **Basis:** Source names high humidity, cloudy weather and lower temperature as the conditions under which pests and diseases appear during the monsoon. All three are measurable at the cluster station.
- **Yield impact:** Enables action before symptoms, when control is cheaper and more effective.
- **References:** Agrowon - Mali & Mahajan weather statement

**D05-WG-002** (WG, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** plant_pulls_easily is true  
  `plant_pulls_easily IS TRUE`
- **Action (EN):** Diagnose white grub. Roots have been gnawed. Begin evening beetle collection and consider Metarhizium.
- **कृती (MR):** ही हुमणीची खूण आहे — मुळेच कुरतडलेली असल्याने रोप सहज उपटते. संध्याकाळी भुंगेरे गोळा करून रॉकेलमिश्रित पाण्यात नष्ट करा.
- **Basis:** Source names easy uplift of affected plants as the diagnostic sign. It takes two seconds and needs no equipment.
- **Yield impact:** u = 0.10.
- **References:** Agrowon - Mali & Mahajan

### D06

**D06-DX-005** (DX, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Leaf spots reported AND air_temp_max_c above 35 in the preceding three days  
  `leaf_spot_rings_visible IS NOT NULL AND air_temp_max_c > 35`
- **Action (EN):** Before treating as disease, hold a leaf up to the sun and look for concentric rings inside the spots. Rings mean leaf spot. No rings, with scorched tips and margins on exposed leaves, means heat damage — treat with mulch, shade and irrigation timing, not fungicide.
- **कृती (MR):** उपचारापूर्वी पान सूर्याकडे धरून पहा. ठिपक्यांमध्ये अनेक वर्तुळे दिसली तर तो करपा रोग. वर्तुळे नाहीत आणि उघड्या पानांच्या टोकांना व कडांना करपा असेल तर ती उष्णतेची इजा — त्यावर आच्छादन, सावली आणि पाण्याची वेळ, बुरशीनाशक नाही.
- **Basis:** The source gives the sun-held ring test as the diagnostic sign for leaf spot. In this district recorded maxima reach 45.9 C and leaves scorch above 35 C, so heat damage to foliage is routine rather than exceptional and will otherwise be misread as disease.
- **Yield impact:** Prevents unnecessary fungicide use. Leaf spot itself carries roughly 0.08.
- **References:** Agrowon - Mali & Mahajan sun-held ring test; District Profile Chhatrapati Sambhajinagar

**D06-LS-001** (LS, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** fog_days_consecutive is high OR estimated leaf_wetness_hours above 8 for two consecutive days, AND crop age below seven months  
  `DURATION(leaf_wetness_hours > 8) > 48 HOURS AND dap < 210`
- **Action (EN):** Start a 15-day interval spray schedule, rotating fungicide GROUPS, and continue until the crop is seven months old.
- **कृती (MR):** पंधरा दिवसांच्या अंतराने बुरशीनाशकांची आलटून-पालटून फवारणी सुरू करा आणि पीक सात महिन्यांचे होईपर्यंत चालू ठेवा. एकच बुरशीनाशक सतत वापरू नये.
- **Basis:** The source states that if fog persists for many days, alternating fungicides should be sprayed at 15-day intervals until the crop is seven months old, and that the same fungicide must not be used repeatedly.
- **Yield impact:** Leaf spot carries roughly 0.08. Foliar disease reduces photosynthetic area during bulking.
- **References:** Agrowon - Mali & Mahajan fog rule

**D06-SR-003** (SR, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** Any field operation involving soil disturbance near the rhizome is scheduled  
  `earthing_up_date IS NULL AND dap BETWEEN 70 AND 95`
- **Action (EN):** Instruct that the rhizome must not be injured during weeding, earthing up or harvest. Mechanical injury opens the same entry route as any pest, with no pest involved.
- **कृती (MR):** खुरपणी, उटाळणी किंवा काढणी करताना गड्ड्याला इजा होणार नाही याची काळजी घ्या. यांत्रिक इजा हीसुद्धा किडीसारखीच जखम आहे, आणि तिच्यातूनही पिथियम व फ्युजेरियम आत शिरतात.
- **Basis:** The source states that injury to the rhizome during earthing up or weeding allows Pythium and Fusarium to enter. This is a pathogen entry route that requires no insect at all, and it originates in the operations the farmer performs deliberately.
- **Yield impact:** Prevents entry into the 0.50 to 0.90 pathway at zero input cost.
- **References:** Agrowon - Mali & Mahajan injury as entry route; Domain 2 weeding chain

**D06-SW-002** (SW, yellow, conf 0.7, tier B) · _executable_

- **Trigger:** Estimated leaf wetness exceeds 8 hours for two consecutive days and the crop is under seven months  
  `soil_temp_c BETWEEN 25 AND 32 AND DURATION(soil_moisture_vwc > vwc_field_capacity) > 24 HOURS`
- **Action (EN):** Trigger the foliar disease spray schedule. Estimate leaf wetness from humidity above 90 percent, the temperature to dew point gap, and rainfall, since no dedicated sensor is fitted.
- **कृती (MR):** पानांवरील रोगाचे फवारणी वेळापत्रक सुरू करा. समर्पित sensor नसल्याने आर्द्रता, तापमान व दव-बिंदू यांवरून ओलाव्याचा कालावधी अंदाजावा.
- **Basis:** Leaf spot and blotch depend on the duration of surface wetness. The fog rule in the source is a qualitative version of the same relationship, and the underlying variable can be estimated from measurements already being taken.
- **Yield impact:** Leaf spot carries roughly 0.08.
- **References:** Core C3.2 derived agro-meteorological variables

**D06-SW-003** (SW, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** Month is October or November and forecast rainfall exceeds 40 mm  
  `MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40`
- **Action (EN):** Raise a red drainage alert, more severe than the equivalent monsoon warning. Stop drip, clear channels urgently, and check saturation within 12 hours of the rain stopping.
- **कृती (MR):** लाल इशारा — आणि हा जुलैच्या इशाऱ्यापेक्षा जास्त तीव्र. ठिबक बंद करा, निचरा चर तातडीने मोकळे करा, पाऊस थांबल्यावर बारा तासांत संपृक्तता तपासा.
- **Basis:** Tropical cyclones reach this district with a secondary peak in October and November. By then the rhizome is fully formed, the soil is dry and cracked after weeks without rain, and drainage channels have usually been neglected because the monsoon is considered finished.
- **Yield impact:** A saturation event at this stage is more expensive than an equivalent July event because the full season investment is already committed.
- **References:** climatestotravel Aurangabad cyclone seasonality; Domain 7

### D07

**D07-CC-001** (CC, yellow, conf 0.82, tier A) · _executable_

- **Trigger:** Planting plan relies on pre-monsoon showers to moisten the soil  
  `days_to_planting BETWEEN 20 AND 40 AND has_drip IS FALSE`
- **Action (EN):** Warn that pre-monsoon rainfall in this region has declined by about 31 percent. Plan to supply the planting moisture through drip rather than relying on showers.
- **कृती (MR):** इथे मान्सूनपूर्व पाऊस सुमारे ३१ टक्क्यांनी घटला आहे. लागवडीच्या वेळचे पाणी ठिबकातून द्यायचे नियोजन करा — सरींवर अवलंबून राहू नका.
- **Basis:** Pre-monsoon rainfall shows a statistically significant decline of 30.81 percent for Marathwada. The traditional recommendation to plant with pre-monsoon showers was written when that rainfall was more reliable, so the practice is now less dependable than the recommendation implies.
- **Yield impact:** Protects establishment, which is a hard ceiling for the season.
- **References:** Arabian Journal of Geosciences, Springer 2022

**D07-CY-002** (CY, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** Month is October or November AND stage is G3 end or G4  
  `MONTH IN [OCT, NOV] AND STAGE IN [G3, G4]`
- **Action (EN):** Issue a monthly reminder to inspect and clear all three drainage levels, even though the monsoon is over. Give the reason: cyclonic rain reaches this district in these months.
- **कृती (MR):** मासिक आठवण द्या — निचऱ्याच्या तिन्ही पातळ्या तपासा, पावसाळा संपला असला तरी. कारण सांगा: चक्रीवादळाचा पाऊस या महिन्यांत येऊ शकतो.
- **Basis:** Channels silt up during the monsoon and are then ignored once the rain stops. A scheduled inspection converts a reactive failure into a routine check at the point of highest crop value.
- **Yield impact:** Reduces the probability of the saturation event in D07-CY-001.
- **References:** climatestotravel cyclone seasonality; Domain 2 drainage levels

**D07-CY-WX-001** (CY, yellow, conf 0.7, tier C) · _executable_

- **Trigger:** Forecast 24h rainfall at or above 75 mm OR wind gust at or above 40 km/h  
  `rainfall_24h_mm >= 75 OR wind_gust_kmph >= 40`
- **Action (EN):** Raise a severe-weather advisory (weather_stress_risk = HIGH): stop drip, clear drainage channels, secure staking and shade, and delay any spray. Check saturation within 12 hours of the rain stopping. This is an operational risk trigger, not an official IMD warning.
- **कृती (MR):** तीव्र-हवामान सूचना द्या (हवामान-ताण = उच्च): ठिबक बंद करा, निचरा चर मोकळे करा, आधार व सावली मजबूत करा, फवारणी पुढे ढकला. पाऊस थांबल्यावर बारा तासांत संपृक्तता तपासा. हा कार्यान्वयनात्मक धोका-इशारा आहे, IMD चा अधिकृत इशारा नाही.
- **Basis:** A custom operational trigger for severe weather. 75 mm sits in the lower part of the IMD Heavy Rainfall band (64.5-115.5 mm) and 40 km/h is below the IMD severe-thunderstorm gust band (62-87 km/h); neither is an IMD crop-loss threshold, so this is an Agro-Guardian operational risk flag for lodging, canopy damage, drainage stress and spray timing, not a claim of an official warning.
- **Yield impact:** Framing/operational; the yield cost of the underlying saturation or lodging is carried by the Domain 3 and Domain 6 rules it feeds.
- **References:** AGRONOMY_SIGNOFF 2026-09-21 sections 7-8; IMD rainfall and thunderstorm classification

**D07-HU-001** (HU, yellow, conf 0.82, tier A) · _executable_

- **Trigger:** rh_pct above 85 for three consecutive days AND month is August or September  
  `DURATION(rh_pct > 85) > 72 HOURS AND MONTH IN [AUG, SEP]`
- **Action (EN):** Trigger the soil-borne disease protocol. August is the highest humidity month here and it coincides with the soft rot peak.
- **कृती (MR):** कंदकूज प्रतिबंधक कृती सुरू करा. इथे ऑगस्टमध्ये सर्वाधिक आर्द्रता असते आणि तोच कंदकुजीचा शिखर काळ आहे.
- **Basis:** August records the highest relative humidity in this district and soft rot peaks in August and September. The coincidence is causal rather than accidental — high humidity is one of the conditions the pathogen requires.
- **Yield impact:** Feeds the 0.70 soft rot pathway.
- **References:** climate-data.org humidity; Agrowon - Mali and Mahajan disease timing

**D07-HU-002** (HU, yellow, conf 0.7, tier B) · _executable_

- **Trigger:** Estimated leaf_wetness_hours above 8 for two consecutive days AND month between December and February  
  `leaf_wetness_hours > 8 AND MONTH IN [DEC, JAN, FEB]`
- **Action (EN):** Trigger the foliar disease schedule. This is the second disease season, driven by winter fog rather than by soil saturation.
- **कृती (MR):** पानांवरील रोगाचे वेळापत्रक सुरू करा. हा दुसरा रोग-हंगाम आहे — जमिनीतील ओलाव्यामुळे नव्हे, हिवाळी धुक्यामुळे.
- **Basis:** Leaf spot and blotch depend on the duration of surface wetness, and the source's fog rule is a qualitative version of the same relationship. Leaf wetness must be estimated from humidity, temperature and dew point because no dedicated sensor is fitted.
- **Yield impact:** Leaf spot carries roughly 0.08.
- **References:** Agrowon - Mali and Mahajan fog rule; Core C3.2 derived variables

**D07-HU-003** (HU, yellow, conf 0.75, tier A) · _executable_

- **Trigger:** rh_pct above 80 for three consecutive days AND cloudy AND month between July and October  
  `DURATION(rh_pct > 80) > 72 HOURS AND MONTH IN [JUL, AUG, SEP, OCT]`
- **Action (EN):** Issue a pest pressure alert and double the scouting frequency. Do not spray on this signal alone.
- **कृती (MR):** कीड-दाबाचा इशारा द्या आणि निरीक्षणाची वारंवारता दुप्पट करा. फक्त या संकेतावर फवारणी करू नये.
- **Basis:** The source names high humidity, cloudy weather and lower temperature as the combination under which pests and diseases appear during the monsoon. All three are measurable at the cluster station, so the pressure can be anticipated rather than discovered.
- **Yield impact:** Enables action before symptoms, when control is cheapest and most effective.
- **References:** Agrowon - Mali and Mahajan weather statement

**D07-MO-001** (MO, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Month is May or early June AND planting has not occurred  
  `MONTH IN [MAY, JUN] AND days_to_planting BETWEEN 1 AND 20`
- **Action (EN):** Warn that ginger timing is the opposite of other kharif crops. Cotton, soybean and tur are sown after the monsoon establishes, typically in early July. Ginger must be planted before it arrives, and 7 June is the deadline.
- **कृती (MR):** अद्रक इतर खरीप पिकांसारखे नाही. कापूस, सोयाबीन, तूर पाऊस स्थिरावल्यावर पेरतात — साधारण जुलैच्या पहिल्या पंधरवड्यात. अद्रक पाऊस येण्यापूर्वी लावावे लागते, आणि ७ जून ही शेवटची मुदत आहे. पावसाची वाट पाहू नका.
- **Basis:** The monsoon normally covers most of Maharashtra by 10 June, three days after the ginger deadline. A farmer whose habit is to wait for rain will therefore miss the window every time, and late planting causes severe rhizome fly and soft rot.
- **Yield impact:** Prevents the 0.20 late planting loss by acting before the deadline rather than reporting it afterwards.
- **References:** ICAR-CRIDA monsoon coverage; Agrowon - Dr. Kadam planting window

**D07-RF-003** (RF, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Seasonal water plan is being computed  
  `rainfall_mm > 60`
- **Action (EN):** Show the distribution, not only the total. Rainfall peaks in July at 195 to 217 mm while crop demand peaks in September and October. The two do not coincide, so October to February must come almost entirely from stored or pumped water.
- **कृती (MR):** फक्त एकूण आकडा नव्हे, वाटप दाखवा. पावसाचे शिखर जुलैत, पण पिकाच्या गरजेचे शिखर सप्टेंबर-ऑक्टोबरमध्ये. दोन्ही जुळत नाहीत — ऑक्टोबर ते फेब्रुवारी हे पाणी जवळपास पूर्णपणे विहिरीतून किंवा साठवणीतून द्यावे लागेल.
- **Basis:** Peak rainfall and peak demand are separated by two to three months. July rain is therefore mainly a drainage risk for ginger rather than a supply opportunity, while the late-season demand falls entirely on irrigation.
- **Yield impact:** Frames the water source assessment that carries u = 0.30.
- **References:** Government gazetteer monthly distribution; Domain 3 monthly water table

**D07-RF-004** (RF, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** rainfall_ytd_mm falls more than 25 percent below the expected accumulation for this date  
  `rainfall_deviation_pct < -25 AND rainfall_ytd_mm IS NOT NULL`
- **Action (EN):** Warn early that this is trending toward a poor year. Recommend reviewing water storage and, if the crop is not yet planted, reconsidering area.
- **कृती (MR):** हे वर्ष कमी पावसाचे ठरण्याकडे कल आहे. पाण्याचा साठा तपासा, आणि लागवड झालेली नसेल तर क्षेत्राचा पुनर्विचार करा.
- **Basis:** A shortfall detected in July or August still leaves time to act on storage or area. The same shortfall discovered in November leaves no options, because the crop is committed and the demand peak has arrived.
- **Yield impact:** Enables action while choices remain.
- **References:** Domain 7 variability tiers; Domain 3 water budget

**D07-WS-004** (WS, yellow, conf 0.78, tier B) · _executable_

- **Trigger:** Station readings missing or implausible for more than 24 hours  
  `station_data_age_hours > 24`
- **Action (EN):** Fall back to the public forecast and the Domain 3 monthly table, mark all weather-dependent advisory as reduced confidence, and raise a maintenance alert.
- **कृती (MR):** सार्वजनिक अंदाज आणि महिनानिहाय तक्ता यावर परत जा, हवामान-आधारित सल्ल्याची विश्वासार्हता कमी दाखवा, आणि देखभालीचा इशारा द्या.
- **Basis:** One station serves five to ten farms, so a station failure degrades the whole cluster rather than one plot. The fallback must be automatic and visible rather than silent.
- **Yield impact:** Prevents advisory being issued on stale or faulty data.
- **References:** Core C10.4 plausibility gating; Domain 3 monthly table as fallback

### D08

**D08-BN-002** (BN, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** dap equals 75  
  `dap BETWEEN 73 AND 77 AND earthing_up_date IS NULL`
- **Action (EN):** Issue the bundle three preparation checklist a week ahead: labour confirmed, nitrogen ready, neem cake ready, mulch material on hand, long-handled khurpa available. Then plan reduced drip for three to five days afterwards.
- **कृती (MR):** एका आठवड्याआधी तयारीची यादी द्या — मजूर ठरले आहेत का, नत्र तयार आहे का, निंबोळी पेंड आहे का, आच्छादनाचे साहित्य जागेवर आहे का, लांब दांड्याचा खुरपा आहे का. आणि नंतर तीन ते पाच दिवस ठिबक कमी करण्याचे नियोजन.
- **Basis:** Six operations in one day fail if any input is missing on the day. Preparation lead time converts a hard-deadline operation into a routine one.
- **Yield impact:** Protects u-values of 0.125 earthing up, 0.175 rhizome fly and 0.200 mulch simultaneously.
- **References:** Domain 8 bundle definition; Core C7.1

**D08-CA-001** (CA, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Pre-season planning initiated  
  `days_to_planting BETWEEN 85 AND 95`
- **Action (EN):** Issue the operations calendar from day minus 90 to harvest, with priorities. The chain is tight and terminates at a hard deadline, so losing March compresses everything downstream.
- **कृती (MR):** वजा ९० दिवसांपासून काढणीपर्यंतची कृती कालदर्शिका प्राधान्यक्रमासह द्या. साखळी घट्ट आहे आणि ती कठोर मुदतीवर संपते — मार्च गमावला तर पुढील सर्व कामे दाटीवाटीने करावी लागतात.
- **Basis:** Every step has a predecessor. March deep ploughing, April solarization, May bed forming and drip, planting by 7 June. The narrow vertisol working window and the fixed planting cut-off leave no slack.
- **Yield impact:** Protects the 0.20 late planting value and the 0.167 layout value.
- **References:** Agrowon - Dr. Kadam sequence; Domain 2 land preparation calendar

**D08-EU-001** (EU, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** dap between 75 and 90 AND earthing_up_date is empty  
  `dap BETWEEN 75 AND 90 AND earthing_up_date IS NULL AND flowering_observed IS FALSE`
- **Action (EN):** Carry out earthing up now with a long-handled khurpa. Bundle with weeding, covering exposed rhizomes, the final nitrogen split, neem cake and mulch stage two. Skipping earthing up costs 10 to 15 percent yield.
- **कृती (MR):** आत्ता लांब दांड्याच्या खुरप्याने उटाळणी करा. सोबतच खुरपणी, उघडे गड्डे झाकणे, नत्राचा शेवटचा हप्ता, निंबोळी पेंड आणि आच्छादनाचा दुसरा टप्पा — सर्व एकाच फेरीत. उटाळणी न केल्यास उत्पादनात १० ते १५% घट.
- **Basis:** Moving the soil breaks old roots and new fibrous roots emerge in their place, and the soil becomes friable so the rhizome has room to expand laterally. It must precede the flowering spike, after which assimilate shifts from foliage to rhizome and there is no time to build new roots.
- **Yield impact:** u = 0.125. Two institutional-grade sources agree on 10 to 15 percent; a third gives 15 to 20 percent and is not used.
- **References:** Agrowon - Dr. Kadam; AgroWorld earthing up description

**D08-EU-003** (EU, yellow, conf 0.8, tier A) · _executable_

- **Trigger:** earthing_up_date recorded AND water_stress_after_earthing_done is false  
  `earthing_up_date IS NOT NULL AND water_stress_after_earthing_done IS FALSE`
- **Action (EN):** Reduce drip to about 60 percent for three to five days. A light water stress after earthing up produces stronger tillering.
- **कृती (MR):** उटाळणीनंतर तीन ते पाच दिवस ठिबक सुमारे ६० टक्क्यांपर्यंत कमी करा. हलका पाण्याचा ताण दिल्यास फुटवे चांगले फुटतात.
- **Basis:** Both Maharashtra sources give this instruction. It is easily overlooked because it is an instruction to do less rather than more, and because it belongs to the water domain while the operation belongs to this one.
- **Yield impact:** Affects tiller number, which sets rhizome count.
- **References:** Agrowon - Dr. Kadam; AgroWorld

**D08-EU-004** (EU, yellow, conf 0.82, tier A) · _executable_

- **Trigger:** dap between 115 and 130 AND earthing_up_2_date is empty  
  `dap BETWEEN 115 AND 130 AND earthing_up_2_date IS NULL AND earthing_up_date IS NOT NULL`
- **Action (EN):** Carry out the second earthing up, about 40 days after the first. Bundle with the potassium split and mulch stage three. Minimum two earthing operations per season.
- **कृती (MR):** पहिल्या उटाळणीनंतर सुमारे ४० दिवसांनी दुसरी उटाळणी करा. सोबत पालाशाचा हप्ता आणि आच्छादनाचा तिसरा टप्पा. हंगामात कमीत कमी दोन भर आवश्यक.
- **Basis:** Source specifies a minimum of two earthing operations with the second about 40 days after the first. Rhizome expansion continues, so the soil covering has to be renewed and exposed rhizomes covered again.
- **Yield impact:** Part of the 0.125 earthing up value and protects against rhizome fly re-exposure.
- **References:** Agrowon - Dr. Kadam second earthing

**D08-EU-005** (EU, yellow, conf 0.88, tier A) · _executable_

- **Trigger:** Month is between July and September AND exposed_rhizomes_observed is true  
  `MONTH IN [JUL, AUG, SEP] AND exposed_rhizomes_observed IS TRUE`
- **Action (EN):** Cover exposed rhizomes with soil immediately, without waiting for the scheduled earthing up. Rhizome fly larvae enter through exposed rhizomes.
- **कृती (MR):** उघडे पडलेले गड्डे तात्काळ मातीने झाकून घ्या — ठरलेल्या उटाळणीची वाट पाहू नका. कंदमाशीच्या अळ्या उघड्या गड्ड्यांमधून आत शिरतात.
- **Basis:** The source gives the explicit instruction to cover exposed rhizomes during July to September, which is the rhizome fly peak. Rhizome expansion and rainfall both push soil away from the crown, so exposure recurs between earthing operations.
- **Yield impact:** Blocks the entry event for a pest carrying 0.175 that also opens the rot pathway.
- **References:** Agrowon - Mali and Mahajan

**D08-GF-001** (GF, yellow, conf 0.65, tier B) · _executable_

- **Trigger:** dap between 30 and 40 AND establishment_pct below 85  
  `dap BETWEEN 33 AND 40 AND establishment_pct < 85`
- **Action (EN):** Assess before acting. Above 85 percent, do not gap fill. Between 70 and 85 percent, gap filling up to 35 DAP is an economic decision. Below 70 percent, find the cause FIRST — if it is rot, gap filling wastes a second lot of the most expensive input.
- **कृती (MR):** आधी कारण शोधा, मग निर्णय. उगवण ८५% वर असल्यास नांगी भरणी नको. ७० ते ८५% असल्यास ३५ दिवसांपर्यंत भरता येईल — तो आर्थिक निर्णय. ७०% पेक्षा कमी असल्यास कारण शोधा — कूज असेल तर नांगी भरणे म्हणजे सर्वात महागडी निविष्ठा दुसऱ्यांदा वाया घालवणे.
- **Basis:** No source gives a gap filling recommendation for ginger. Reasoning from the crop: emergence completes by 30 to 45 days, so plants set later never catch up, and establishment is a hard ceiling with no ratoon. If the cause is soft rot the replacement seed enters the same infested soil.
- **Yield impact:** Prevents a second seed loss on top of the first.
- **References:** absence of source; Domain 1 establishment ceiling; Domain 6 rot pathway

**D08-LB-001** (LB, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** dap equals 60 AND labour_arranged_date is empty  
  `dap BETWEEN 58 AND 64 AND labour_arranged_date IS NULL`
- **Action (EN):** Arrange labour for earthing up now. August is also cotton, soybean and tur intercultivation season, so labour becomes scarce exactly when earthing up has a hard deadline.
- **कृती (MR):** उटाळणीसाठी मजूर आत्ताच ठरवा. ऑगस्टमध्ये कापूस, सोयाबीन आणि तूर यांच्या आंतरमशागतीमुळे सर्वत्र मजुरांना मागणी असते — आणि उटाळणीला कठोर मुदत आहे.
- **Basis:** Earthing up falls at 75 to 90 DAP which is around August for a June planting. That coincides with intercultivation in the dominant local crops. Labour scarcity is the most likely reason the operation slips past the flowering deadline.
- **Yield impact:** Protects the 0.125 earthing up value through a logistics reminder rather than an agronomic one.
- **References:** Core C7.3 labour feasibility; Domain 8 labour competition

**D08-MU-001** (MU, yellow, conf 0.85, tier B) · _executable_

- **Trigger:** Planting completed AND mulch_stage_1_done is false  
  `dap BETWEEN 0 AND 4 AND mulch_stage_1_done IS FALSE`
- **Action (EN):** Apply mulch immediately, the same day. This is a precondition for emergence in this belt, not a moisture-saving improvement.
- **कृती (MR):** लागवडीच्या दिवशीच आच्छादन घाला. इथे ते ओलावा टिकवण्याची सुधारणा नाही — उगवणीची अट आहे.
- **Basis:** Germination needs a soil temperature of 25 to 26 C while May maxima here reach 45.9 C and bare black soil runs hotter than air. Mulch is the only practical way to bring the surface temperature into range. It also carries the largest documented disease benefit of any single operation.
- **Yield impact:** u = 0.20 across the full three-stage programme, with the disease effect being the largest component.
- **References:** Organic Mandya field records; Spices Board / TNAU; Domain 7 May temperatures

**D08-MU-002** (MU, yellow, conf 0.78, tier B) · _executable_

- **Trigger:** dap in the 40 to 60 or 90 to 120 band AND the corresponding mulch stage not done  
  `((dap BETWEEN 40 AND 60 AND mulch_stage_2_done IS FALSE) OR (dap BETWEEN 90 AND 120 AND mulch_stage_3_done IS FALSE))`
- **Action (EN):** Apply the next mulch stage. Bundle stage two with earthing up so both happen in one field visit.
- **कृती (MR):** आच्छादनाचा पुढील टप्पा घाला. दुसरा टप्पा उटाळणीसोबत करा — एकाच फेरीत दोन्ही कामे.
- **Basis:** Two sources give different quantities but both specify three applications rather than one. Cumulative cover is what sustains the effect through the season, and stage two coincides naturally with earthing up.
- **Yield impact:** Completes the 0.20 mulch programme.
- **References:** Organic Mandya three-stage programme; Spices Board / TNAU

**D08-WD-002** (WD, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** dap equals 11 AND herbicide_post_emergent_date is empty  
  `dap BETWEEN 10 AND 13 AND herbicide_post_emergent_date IS NULL AND emergence_started IS FALSE`
- **Action (EN):** Warn that the glyphosate window closes in three to four days, after which ginger begins to emerge and no herbicide can be used. Offer mulch as the alternative if the window is missed.
- **कृती (MR):** ग्लायफोसेट फवारणीची शेवटची संधी पुढील तीन-चार दिवसांत. त्यानंतर अद्रक उगवू लागेल आणि तणनाशक वापरता येणार नाही. संधी गेल्यास आच्छादन हा पर्याय.
- **Basis:** The window is defined at one end by planting and at the other by emergence, and the second application sits close to the closing edge. A three to four day warning is the practical lead time for arranging labour and spray.
- **Yield impact:** Prevents a weed pressure problem that would otherwise force more weeding, and weeding injures the rhizome.
- **References:** AgroWorld schedule; Domain 8 window reasoning

**D08-WD-003** (WD, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Manual weeding scheduled  
  `dap BETWEEN 25 AND 60 AND weeding_count < 2`
- **Action (EN):** Instruct that the rhizome must not be injured. Keep the field weed free for the first four to six weeks; three to four weedings across the season depending on pressure.
- **कृती (MR):** खुरपणी करताना गड्ड्याला इजा होणार नाही याची काळजी घ्या. पहिले चार ते सहा आठवडे शेत तणविरहित ठेवा; हंगामभर तणाच्या तीव्रतेनुसार तीन ते चार खुरपण्या.
- **Basis:** Injury during weeding allows Pythium and Fusarium to enter. Because heavy FYM raises weed pressure, ginger needs more weeding than most crops, which raises the injury exposure proportionally.
- **Yield impact:** Prevents entry into the 0.50 to 0.90 rot pathway at zero cost.
- **References:** Agrowon - Mali and Mahajan injury route; Vikaspedia weeding schedule

### D09

**D09-DR-004** (DR, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** dap approximately 200  
  `dap BETWEEN 195 AND 205 AND drying_space_ready IS FALSE`
- **Action (EN):** Ask whether drying space and tarpaulin are ready. If the price crashes at harvest, drying is the fallback — and there will be no time to arrange it then.
- **कृती (MR):** वाळवणीची जागा आणि ताडपत्री तयार आहे का ते विचारा. काढणीच्या वेळी भाव कोसळल्यास सुंठ हा पर्याय लागेल, आणि तेव्हा तयारीला वेळ नसेल.
- **Basis:** Dry ginger is insurance against a price crash rather than a default route. Insurance has to be in place before the event. Arranging tarpaulin and space after prices fall means either selling at the crashed price or delaying while the produce deteriorates.
- **Yield impact:** Preserves the option rather than the crop.
- **References:** Domain 9 value addition framing; Domain 7 poor-year planning logic

**D09-GD-001** (GD, yellow, conf 0.82, tier B) · _executable_

- **Trigger:** Harvest preparation begins, about 30 days before expected harvest  
  `days_to_harvest BETWEEN 25 AND 35`
- **Action (EN):** State the grading spread plainly. A 2.7 times price difference was recorded within one market on one day, purely on quality. Washing and grading before sale is worth more than any yield improvement available this season.
- **कृती (MR):** प्रतवारीचा फरक स्पष्ट सांगा. एकाच बाजारात, एकाच दिवशी, केवळ प्रतीमुळे २.७ पट भाव फरक नोंदवला गेला आहे. धुऊन आणि प्रतवारी करून विकल्यास हा फरक मिळतो — आणि तो या हंगामातील कोणत्याही उत्पादन-वाढीपेक्षा मोठा आहे.
- **Basis:** Akola market recorded Rs 6,000 to Rs 16,000 per quintal on a 180 quintal arrival on a single day. Two of the seven grading determinants — skin condition and cleanliness with uniformity — sit entirely in this domain, and both are labour-only.
- **Yield impact:** Not a yield factor. On 90 quintal at the two ends of that band the difference is roughly Rs 9 lakh, which exceeds every yield factor in the knowledge base combined.
- **References:** News18 Marathi APMC daily report 2026

**D09-GD-002** (GD, yellow, conf 0.8, tier B) · _executable_

- **Trigger:** Produce is being prepared for sale AND graded_separately is false  
  `graded_separately IS FALSE AND WITHIN(harvest_date, 7 DAYS)`
- **Action (EN):** Sort into grades and sell each grade separately. Sold together, the lower grade drags the whole consignment down to an average price.
- **कृती (MR):** प्रतवारी करून प्रत्येक श्रेणी वेगळी विका. सर्व एकत्र विकल्यास खालच्या प्रतीचा माल वरच्या प्रतीचा भावही खाली खेचतो आणि सरासरी भाव मिळतो.
- **Basis:** The observed spread exists because buyers price on quality. A mixed lot is priced on its weakest visible fraction rather than on its average, so separation captures value that already exists in the crop.
- **Yield impact:** Pure price effect. The cost is sorting labour.
- **References:** News18 Marathi APMC spread observation

**D09-HV-001** (HV, yellow, conf 0.8, tier C) · _executable_

- **Trigger:** Harvest day  
  `days_to_harvest BETWEEN 0 AND 3 AND skin_scrape_result == 'firmly_attached'`
- **Action (EN):** Issue the harvest sequence: cut foliage, lift without injury digging from the side of the bed rather than from above, separate mother rhizome from fingers, wash clean, drain in shade in a thin layer, then grade.
- **कृती (MR):** काढणीचा क्रम — पाला कापा, वाफ्याच्या बाजूने खोदून इजा न करता गड्डे काढा, मातृ गड्डा व बोटे वेगळी करा, स्वच्छ धुवा, सावलीत पातळ थरात निथळू द्या, मग प्रतवारी करा.
- **Basis:** Each step protects the next. Injury during lifting becomes storage rot; unwashed produce loses grade and has soil deducted from weight; wet produce heaped rather than drained generates heat and moisture at the centre and begins to rot.
- **Yield impact:** Protects realised value rather than weight.
- **References:** AgroWorld harvest sequence

**D09-MT-003** (MT, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** harvest_route is seed_rhizome AND early harvest is being considered  
  `harvest_route == 'seed_rhizome' AND skin_scrape_result == 'peels_easily'`
- **Action (EN):** REFUSE early harvest for the seed crop. Full maturity is mandatory. Immature rhizome does not survive storage and does not sprout the following season.
- **कृती (MR):** बेण्यासाठीचे पीक कधीही लवकर काढू नये. पूर्ण पक्वता अनिवार्य आहे. अपक्व गड्डा साठवणीत टिकत नाही आणि पुढच्या हंगामात उगवत नाही.
- **Basis:** Skin corking and dry matter accumulation complete only at full maturity, and both determine survival across the four to five month gap to next planting. Seed rhizome already loses 28 to 40 percent of its weight in storage; starting that clock with an immature rhizome worsens both the loss and the germination.
- **Yield impact:** Affects next season, compounding into establishment loss and wasted seed cost.
- **References:** Agrowon - Dr. Kadam; Domain 8 seed storage

**D09-PH-001** (PH, yellow, conf 0.8, tier C) · _executable_

- **Trigger:** Harvest complete AND produce_washed is false  
  `harvest_date IS NOT NULL AND produce_washed IS FALSE`
- **Action (EN):** Wash the rhizomes clean and free of soil before sale. Soil-covered produce looks like a lower grade and the trader deducts the soil from the weight, so the loss falls twice.
- **कृती (MR):** विक्रीपूर्वी गड्डे स्वच्छ धुवून मातीपासून वेगळे करा. मातीने माखलेला माल खालच्या प्रतीचा दिसतो आणि व्यापारी वजनातून मातीही वजा करतो — नुकसान दोनदा होते.
- **Basis:** The source instructs washing before dispatch. Cleanliness is one of the three grading determinants that remain in the farmer's hands at this point, and unwashed produce is penalised on both appearance and weight.
- **Yield impact:** Directly affects realised price through the 2.7 times grading spread.
- **References:** AgroWorld post-harvest handling

**D09-ST-003** (ST, yellow, conf 0.82, tier C) · _executable_

- **Trigger:** Dry ginger stored AND moisture_pct_final above 10  
  `drying_method IS NOT NULL AND moisture_pct_final > 10`
- **Action (EN):** Do not store until moisture is down to 8 to 10 percent. Above that, mould develops and the whole lot is at risk.
- **कृती (MR):** पाण्याचा अंश ८ ते १०% येईपर्यंत साठवू नका. त्यापेक्षा जास्त असल्यास बुरशी लागते आणि संपूर्ण लॉट धोक्यात येतो.
- **Basis:** Both drying methods specify 8 to 10 percent final moisture. Above that the product supports mould growth during storage, and a stored lot fails as a whole rather than partially.
- **Yield impact:** Protects the entire processed output.
- **References:** AgroWorld drying endpoint

**D09-WW-001** (WW, yellow, conf 0.78, tier B) · _executable_

- **Trigger:** About 60 days to expected harvest AND water_withdrawal_start_date is empty  
  `days_to_harvest BETWEEN 55 AND 62 AND water_withdrawal_start_date IS NULL`
- **Action (EN):** Begin gradual water withdrawal. Reduce to about 80 percent at 45 days, 60 percent at 30 days, 30 percent at 15 days, and stop completely 7 days before harvest. This determines skin condition, which is a grading determinant.
- **कृती (MR):** पाणी हळूहळू कमी करायला सुरुवात करा — ४५ दिवसांवर सुमारे ८०%, ३० दिवसांवर ६०%, १५ दिवसांवर ३०%, आणि काढणीच्या सात दिवस आधी पूर्ण बंद. यावरून सालीची स्थिती ठरते, आणि तीच प्रतवारीचा निकष आहे.
- **Basis:** Continued irrigation to harvest keeps the rhizome heavier but leaves the skin uncured, which lowers storability, lowers dry recovery and lowers grade. Withdrawal is what hardens the skin. The temptation to keep watering is strong because the crop looks heavier.
- **Yield impact:** Does not change weight materially but strongly affects grade, and the observed grade spread is 2.7 times.
- **References:** CropLibrary; Agrowon descending water table; Domain 9 grading determinants

**D09-WW-002** (WW, yellow, conf 0.72, tier B) · _executable_

- **Trigger:** soil_texture_class is heavy AND water withdrawal in progress  
  `water_withdrawal_start_date IS NOT NULL AND soil_texture_class == 'heavy'`
- **Action (EN):** Make the taper slower than the standard schedule. Abrupt drying cracks black soil, which makes lifting difficult and injures the rhizomes — and harvest injury becomes storage rot.
- **कृती (MR):** काळ्या जमिनीत उतरण अधिक हळू ठेवा. एकदम पाणी बंद केल्यास जमीन फुटते, काढणी कठीण होते आणि गड्ड्याला इजा होते — आणि तीच इजा साठवणीत कूज बनते.
- **Basis:** Vertisol shrinks and cracks on drying. Harvest injury is the documented entry route for storage rot, and by harvest the entire season's cost is committed, so a loss at this point is the most expensive kind.
- **Yield impact:** Acts on post-harvest loss rather than field yield.
- **References:** Domain 2 vertisol behaviour; Domain 6 handling and storage rot

**D09-YD-001** (YD, yellow, conf 0.85, tier A) · _executable_

- **Trigger:** Harvest complete  
  `harvest_date IS NOT NULL AND yield_quintal_per_acre_actual IS NULL`
- **Action (EN):** Record actual yield in quintal per acre, the grade split, and the rot and wilt incidence. These are the inputs that let Domain 11 correct its estimated u-values against reality.
- **कृती (MR):** प्रत्यक्ष उत्पादन क्विंटल प्रति एकर, श्रेणीनिहाय विभागणी, आणि कूज व मर रोगाचे प्रमाण नोंदवा. याच नोंदींवरून अंदाजित u मूल्ये प्रत्यक्ष आकड्यांनी दुरुस्त होतात.
- **Basis:** Twenty-two of the thirty u-values in Domain 11 are estimates. They can only become measurements through recorded harvest outcomes matched against the season's operation record.
- **Yield impact:** None this season. Foundational for every following season.
- **References:** Domain 11 gap attribution; Domain 12 minimum record set

### D10

**D10-INS-001** (INS, yellow, conf 0.7, tier B) · _executable_

- **Trigger:** Pre-season planning AND pmfby_notified_for_ginger is unverified  
  `days_to_planting BETWEEN 40 AND 60 AND pmfby_notified_for_ginger == 'unverified'`
- **Action (EN):** Check with the District Superintending Agriculture Officer whether ginger is a notified crop under PMFBY for this district, and if not whether the restructured weather-based horticulture insurance applies. The kharif deadline of around 31 July fits a 7 June planting.
- **कृती (MR):** जिल्हा अधीक्षक कृषी अधिकाऱ्याकडे तपासा — या जिल्ह्यासाठी अद्रक PMFBY मध्ये अधिसूचित पीक आहे का, आणि नसल्यास पुनर्रचित हवामान आधारित फळपीक विमा लागू होतो का. खरीपची साधारण ३१ जुलैची मुदत ७ जूनच्या लागवडीशी जुळते.
- **Basis:** Investment is about Rs 1.45 lakh per acre over eight months and the main risks — water exhaustion, soft rot and price collapse — are all capable of taking most of the crop. For an exposure this size the insurance question is decisive rather than incidental.
- **Yield impact:** None on yield. Changes the risk profile of the whole enterprise.
- **References:** Domain 13 investment figure; PMFBY notification framework

### D14

**D14-LT-002** (LT, yellow, conf 0.72, tier B) · _executable_

- **Trigger:** CWSI is above 0.60 AND sub-node moisture reads adequate AND advisory confidence is at least 0.5  
  `cwsi > 0.60 AND sub_node_moisture_status == 'adequate' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Open non-water investigation, same branch as NM-002. If NM-002 has already opened one for this plot in the last 5 days, do NOT open a second — link the CWSI evidence to the existing task.
- **कृती (MR):** NM-002 प्रमाणेच पाणी-नसलेली तपासणी उघडा. मागील ५ दिवसांत NM-002 ने आधीच task उघडलेला असल्यास नवीन उघडू नका — CWSI पुरावा त्या विद्यमान task ला जोडा.
- **Basis:** CWSI > 0.6 with wet soil is thermodynamically strong evidence of non-water stress. Section 10 case A confirmed thermally.
- **Yield impact:** Under NM-002 investigation grouping.
- **References:** Idso et al. 1981; RAW MASTER §7.3, §7.5, §10.2 case A

**D14-NM-002** (NM, yellow, conf 0.72, tier B) · _executable_

- **Trigger:** NDMI has dropped 0.10 or more over 10 days AND sub-node moisture reads adequate AND advisory confidence is at least 0.5  
  `ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == 'adequate' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Open a plot-specific investigation. Likely non-water causes: (1) drip line partly blocked or emitter uneven — check flow at 3 points; (2) pest — check root and stem base; (3) root damage from tillage. Do NOT increase irrigation on this signal alone.
- **कृती (MR):** प्लॉट-विशिष्ट तपासणी उघडा. संभाव्य पाणी-नसलेली कारणे: (१) ठिबक अंशतः बंद किंवा emitter असमान — ३ ठिकाणी flow तपासा; (२) कीड — मूळ व खोड-आधार तपासा; (३) मशागतीमुळे मूळ इजा. फक्त या सिग्नलवर सिंचन वाढवू नका.
- **Basis:** NDMI drop with adequate root-zone moisture is definitionally not a water shortage. The signal is real but the cause is something else — Section 10 case A.
- **Yield impact:** Investigation_dispatched.
- **References:** RAW MASTER §7.5, §10.2 case A

**D14-NR-002** (NR, yellow, conf 0.7, tier B) · _executable_

- **Trigger:** NDVI is rising in early G2 but NDRE slope is near-flat AND advisory confidence is at least 0.5  
  `current_stage == 'G2' AND dap BETWEEN 40 AND 80 AND ndvi_delta_10d > 0.05 AND ndre_slope_5d < 0.005 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Route to D04 nitrogen check. Do NOT prescribe a nitrogen top-dressing on satellite signal alone; D04 must confirm from soil-test-derived N budget and leaf tissue proxy. If confirmed, D04's own top-dressing rule fires.
- **कृती (MR):** D04 नत्र तपासणीकडे पाठवा. फक्त उपग्रह सिग्नलवर वरखत शिफारस करू नका; D04 ने माती-परीक्षणावर आधारित N अर्थसंकल्प व पर्ण-ऊतक प्रतिनिधीने पुष्टी करावी. पुष्टी झाल्यास D04 चा स्वतःचा top-dressing नियम कार्यरत होतो.
- **Basis:** Ginger's canopy expansion in early G2 can outrun N supply, giving a large but thin canopy. NDVI/NDRE divergence is the recognised satellite signature.
- **Yield impact:** Under D04 nitrogen u-value grouping.
- **References:** ICAR-IISS Bhopal red-edge nitrogen studies; RAW MASTER §4.4, §8.3

**D14-NR-003** (NR, yellow, conf 0.68, tier B) · _executable_

- **Trigger:** NDRE is 0.10 or more below the regional baseline in closed-canopy stage AND advisory confidence is at least 0.5  
  `current_stage IN [G3, G4] AND plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Route to D04 nitrogen check with 'closed-canopy NDRE gap' as the reason code. Same D04-authoritative discipline as NR-002.
- **कृती (MR):** D04 नत्र तपासणीकडे 'closed-canopy NDRE gap' कारणासह पाठवा. NR-002 प्रमाणेच D04 प्राधिकरण.
- **Basis:** Once LAI passes ~3.5 the NDVI saturation floor makes NDRE the only satellite channel with meaningful nitrogen sensitivity.
- **Yield impact:** Under D04 nitrogen u-value grouping.
- **References:** Fitzgerald et al. 2010; ICAR-IISS Bhopal red-edge studies

**D14-NV-003** (NV, yellow, conf 0.55, tier B) · _executable_

- **Trigger:** Plot NDVI is more than 0.10 below the regional baseline for the current stage AND scene is trusted AND advisory confidence is at least 0.5  
  `plot_ndvi_gap_regional < -0.10 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Open an investigation task for this plot: check sub-node moisture and EC over the last 7 days, and schedule a farmer scout report. Do NOT recommend any chemical intervention on this signal alone. If the sub-node shows a matching anomaly, escalate through the appropriate domain (D03 water, D04 nutrient, or D06 disease). If sub-node shows nothing, request the scout and hold.
- **कृती (MR):** या प्लॉटसाठी तपासणी task उघडा — सर्व सब-नोड मृदा-ओलावा व EC मागील ७ दिवसांची तपासा आणि शेतकऱ्याला scout अहवाल पाठवण्याची विनंती करा. फक्त या सिग्नलवर कोणतीही रासायनिक शिफारस करू नका. सब-नोडवर तीच अनियमितता आढळल्यास योग्य डोमेनमार्फत (D03/D04/D06) escalate करा; काहीच नसल्यास scout अहवालाची वाट पहा.
- **Basis:** Regional-baseline deviation is a coarse signal; the underlying model is Phase-1 author-estimated. Requires cross-check by §8.4 double-signal principle.
- **Yield impact:** Grouped under investigation_dispatched — not counted separately from downstream domain-specific u-values.
- **References:** RAW MASTER §8, §9; Domain 6 double-signal principle

**D14-NV-005** (NV, yellow, conf 0.72, tier B) · _executable_

- **Trigger:** Plot NDVI is more than 0.10 below the peer cluster mean at the same DAP AND at least 3 peer plots contribute AND DAP is at least 60  
  `plot_ndvi_gap_peer < -0.10 AND dap >= 60 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Open a plot-specific investigation. This plot is developing slower than its cluster peers. Likely causes in order of frequency: nitrogen shortfall (D04), waterlogging on this plot (D03), variety difference (D01), planting-date mismatch (D01). Cross-check the last farmer-reported input dates.
- **कृती (MR):** प्लॉट-विशिष्ट तपासणी उघडा. हा प्लॉट cluster peers पेक्षा हळू विकसित होत आहे. वारंवारतेने: नत्र कमतरता (D04), पाणी साचणे (D03), वाणातील फरक (D01), लागवडीच्या तारखेतील फरक (D01). शेतकऱ्याने नोंदवलेल्या शेवटच्या तारखांची तपासणी करा.
- **Basis:** Peer-cluster comparison neutralises weather, soil zone, and market-level variety effects. It isolates plot-specific management differences.
- **Yield impact:** Investigation_dispatched grouping.
- **References:** RAW MASTER §9.1 baseline construction; Precision agriculture peer-benchmarking studies

**D14-NV-007** (NV, yellow, conf 0.75, tier B) · _executable_

- **Trigger:** Plot NBR has dropped by 0.20 or more over the last 10 days AND scene is trusted  
  `nbr_delta_10d <= -0.20 AND scene_valid_pixel_pct >= 60`
- **Action (EN):** Log a residue-burning-candidate event on the plot. Notify the operations team for verification. Do not display any punitive message to the farmer; this is compliance intelligence, not an accusation. False positives include intentional black plastic mulching, which needs a farmer confirmation reply.
- **कृती (MR):** प्लॉटवर residue-burning-candidate घटना नोंदवा. संचालन टीमला पडताळणीसाठी कळवा. शेतकऱ्याला दंडात्मक संदेश दाखवू नका — ही अनुपालन-गुप्तवार्ता आहे, आरोप नाही. काळी पॉलिथिन आच्छादन असल्यास खोटा इशारा असू शकतो — शेतकऱ्याच्या पुष्टीने बंद करा.
- **Basis:** Burnt residue reflects strongly in SWIR (B12) and weakly in NIR (B8), collapsing NBR. The signal is unambiguous for a real burn.
- **Yield impact:** Compliance-only. No direct yield mapping.
- **References:** Key & Benson 2006 NBR; RAW MASTER §4.1

**D14-PH-003** (PH, yellow, conf 0.72, tier B) · _executable_

- **Trigger:** Peak NDVI in G3 is below 0.60 AND scenes are trusted AND advisory confidence is at least 0.5  
  `current_stage == 'G3' AND ndvi_mean < 0.60 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Dispatch a differential investigation: (a) D04 nitrogen check, (b) D02 salinity check, (c) sub-node saturation-hours history for hidden waterlogging, (d) farmer report on early emergence issues that might indicate seed vigour. This is one of the few satellite signals worth firing across four domains in parallel.
- **कृती (MR):** differential तपासणी सुरू करा: (अ) D04 नत्र तपासणी, (आ) D02 क्षारता तपासणी, (इ) लपलेल्या पाणी साचण्यासाठी सब-नोड saturation-hours इतिहास, (ई) बियाणे शक्तीचे संकेत लवकर उगवणीच्या नोंदींतून. हा उपग्रह सिग्नल चार डोमेनवर एकाच वेळी चालवण्यायोग्य आहे.
- **Basis:** Peak canopy that undershoots a full stage window carries a strong integrated signal.
- **Yield impact:** Investigation branch — yield mapping through confirmed downstream domain.
- **References:** RAW MASTER §8.3; Domain 6 differential-diagnosis architecture

**D14-PH-004** (PH, yellow, conf 0.68, tier B) · _executable_

- **Trigger:** NDVI shows accelerating decline before DAP 180 AND stage is G3 or G4 AND advisory confidence is at least 0.5  
  `current_stage IN [G3, G4] AND dap < 180 AND ndvi_delta_10d <= -0.12 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Dispatch to D06 wilt differential and D03 water branch. If a farmer has started lifting early, close the investigation with the lifting confirmation.
- **कृती (MR):** D06 wilt differential व D03 पाणी शाखेकडे पाठवा. शेतकऱ्याने लवकर काढणी सुरू केली असल्यास त्यांच्या पुष्टीने तपासणी बंद करा.
- **Basis:** The senescence curve shape is stage-informative; an early decline is diagnostic across three families of causes.
- **Yield impact:** Under D06/D03 confirmed diagnosis.
- **References:** RAW MASTER §8.1, §8.3

### D01

**D01-HV-001** (HV, info, conf 0.85, tier B) · _executable_

- **Trigger:** dap greater than or equal to 200  
  `dap BETWEEN 205 AND 240 AND harvest_date IS NULL`
- **Action (EN):** Advise the skin scrape test as the primary maturity indicator. Secondary signs are leaf yellowing and pseudostem lodging. Day count is the least reliable of the three.
- **कृती (MR):** गड्डा उकरून अंगठ्याने साल घासा. साल सहज निघते म्हणजे अपक्व; साल घट्ट बसलेली म्हणजे पक्व. ही चाचणी दिवस मोजण्यापेक्षा जास्त विश्वासार्ह आहे आणि तिला कोणतेही उपकरण लागत नाही.
- **Basis:** Maturity varies with variety, season and planting date, so day count drifts. Skin corking is a direct physiological indicator.
- **Yield impact:** Premature harvest carries u = 0.10 to 0.15 and much larger storage losses.
- **References:** Tractorkarvan; CropLibrary; ICAR-AICRP

**D01-PH-001** (PH, info, conf 0.75, tier A) · _executable_

- **Trigger:** planting_date and variety are known  
  `dap BETWEEN 0 AND 35 AND STAGE IN [G1]`
- **Action (EN):** Compute current_stage from DAP using the variety duration profile. Set stage_source to calendar and confidence to medium.
- **कृती (MR):** लागवडीच्या तारखेवरून व जातीच्या कालावधीवरून सध्याची अवस्था काढा.
- **Basis:** Stage boundaries scale with variety duration; a 200-day variety reaches rhizome initiation earlier than a 240-day one.
- **Yield impact:** Indirect. Every time-bound rule in every domain depends on the stage being right.
- **References:** Agrowon variety durations; Domain 1 duration profiles

**D01-PH-002** (PH, info, conf 0.88, tier A) · _executable_

- **Trigger:** A farmer-observable marker has been recorded  
  `dap BETWEEN 33 AND 40 AND establishment_pct IS NULL`
- **Action (EN):** Re-anchor the stage clock to the marker. Marker overrides calendar. Set stage_source to marker and raise confidence.
- **कृती (MR):** निरीक्षणाची खूण दिसल्यास तिच्यावरून अवस्था ठरवा — दिवस मोजणीपेक्षा ती जास्त विश्वासार्ह आहे.
- **Basis:** Calendar days drift with season and variety. Observable markers do not drift. A mis-entered planting date otherwise mistimes every downstream event for the whole season.
- **Yield impact:** Indirect but broad. Protects the timing of earthing-up, fertiliser splits and harvest.
- **References:** Core C6.1; Domain 1 stage markers

**D01-PH-003** (PH, info, conf 0.9, tier B) · _executable_

- **Trigger:** Engine attempts GDD-based staging  
  `dap BETWEEN 90 AND 150 AND STAGE IN [G3]`
- **Action (EN):** REFUSE. The GDD arm is disabled for ginger. Fall back to calendar plus marker and state the reason if asked.
- **कृती (MR):** अद्रकासाठी GDD पद्धत बंद आहे. दिवस मोजणी व निरीक्षण यावरच अवस्था ठरवा.
- **Basis:** No reliable published GDD series for ginger in Indian conditions was located. Sugarcane has a validated base temperature and thermal-time model; ginger does not.
- **Yield impact:** None directly. Prevents false precision, which is worse than declared uncertainty.
- **References:** absence of source across ICAR-IISR, KAU, TNAU

**D01-TM-002** (TM, info, conf 0.82, tier A) · _executable_

- **Trigger:** Stage is G4 AND month is between November and January  
  `MONTH IN [NOV, DEC, JAN] AND STAGE IN [G4]`
- **Action (EN):** Inform that conditions are now favourable and that the priority shifts from protection to supply — consistent moisture and potassium.
- **कृती (MR):** आता तापमान गड्डा भरण्यासाठी अनुकूल आहे. या काळात पीक वाचवण्यापेक्षा भरू देणे महत्वाचे — ओलाव्यात सातत्य आणि पालाश.
- **Basis:** Optimal temperature for rhizome growth is 18-20 C. December average here is 20.8 C. This is a genuine local advantage not available in Kerala or Konkan, where winters remain warm.
- **Yield impact:** Not a loss factor. It identifies the window in which the largest share of yield is actually laid down.
- **References:** Agrowon - Bitle & Deshmukh; climatestotravel Aurangabad

### D02

**D02-SN-001** (SN, info, conf 0.75, tier A) · _executable_

- **Trigger:** Month is April or early May AND field is empty AND solarization_done is false  
  `MONTH IN [APR, MAY] AND days_to_planting > 30 AND solarization_done IS FALSE`
- **Action (EN):** Recommend soil solarization for four to six weeks. Moisten the soil, lay TRANSPARENT (not black) polythene, seal the edges with soil, and remove before planting.
- **कृती (MR):** जमीन ओलसर करून पारदर्शक प्लास्टिक अंथरा, कडा मातीने बंद करा, चार ते सहा आठवडे ठेवा आणि लागवडीपूर्वी काढा. काळे नव्हे — पारदर्शक प्लास्टिक वापरावे, कारण काळे स्वतः तापते पण उष्णता जमिनीत जाऊ देत नाही.
- **Basis:** Solarization raises topsoil temperature enough to kill soil-borne pathogens, nematodes and weed seed. It is a recognised cultural measure in soft rot management.
- **Yield impact:** u = 0.05 estimated for omitting it.
- **References:** CJAST 39(35) 2020 soft rot review

**D02-TL-003** (TL, info, conf 0.7, tier B) · _executable_

- **Trigger:** Soil moisture enters the workable band after rain AND land preparation is incomplete  
  `vafsa_state == 'workable' AND deep_ploughing_done IS FALSE`
- **Action (EN):** Notify that the field is workable for approximately the next three to four days.
- **कृती (MR):** पुढील तीन-चार दिवस मशागतीस योग्य आहेत. वाफसा गेल्यावर काळ्या जमिनीत काम करता येणार नाही.
- **Basis:** Vafsa is the intermediate moisture state between sticky and hard. In black soil it lasts only a few days and judging it by eye is unreliable.
- **Yield impact:** Indirect. Protects soil structure and prevents lost operating days.
- **References:** Domain 2 vertisol behaviour; Core C3

### D03

**D03-DS-002** (DS, info, conf 0.85, tier A) · _executable_

- **Trigger:** Drip configuration set  
  `has_drip IS TRUE AND drip_system_flow_lph IS NULL`
- **Action (EN):** Compute and store system hydraulics: about 7,380 drippers per acre giving about 14,760 litres per hour. All runtime advisory derives from this figure.
- **कृती (MR):** प्रति एकर सुमारे ७,३८० ड्रीपर, ताशी सुमारे १४,७६० लिटर. ठिबक किती वेळ चालवायचे हे सर्व गणित याच आकड्यावरून येते.
- **Basis:** Runtime cannot be advised without knowing system flow. Deriving it once at installation removes a recurring source of error.
- **Yield impact:** Indirect. Determines whether the intended volume actually reaches the crop.
- **References:** computed from Agrowon drip design; cross-validated against Agrowon runtime recommendation

**D03-MN-001** (MN, info, conf 0.85, tier A) · _executable_

- **Trigger:** Rainfall recorded  
  `rainfall_mm > 2 AND dap BETWEEN 0 AND 225`
- **Action (EN):** Deduct effective rainfall from the day's requirement. Net requirement equals table or formula value minus effective rainfall in mm times 4000. If the result is zero or less, skip irrigation.
- **कृती (MR):** आजची निव्वळ गरज = तक्त्यातील गरज − (प्रभावी पाऊस मिमी × ४०००). शून्य किंवा कमी आले तर आज ठिबक नको.
- **Basis:** Rain and irrigation are substitutes, but only partially. Ten millimetres of rain supplies 40,000 litres per acre, which against a September demand of 22,000 litres per day is about two days of water, not a week.
- **Yield impact:** Prevents both wasteful irrigation after rain and, more commonly, an unrecognised deficit when a small rain event is treated as sufficient.
- **References:** Agrowon - Dr. Kadam monsoon gap rule; Domain 3 water budget

**D03-SC-001** (SC, info, conf 0.88, tier A) · _executable_

- **Trigger:** Daily irrigation scheduled  
  `has_drip IS TRUE AND drip_system_flow_lph IS NOT NULL AND dap BETWEEN 0 AND 225`
- **Action (EN):** Convert the day's volume to runtime using system flow. Range is about 34 minutes in May to about 89 minutes at the September and October peak.
- **कृती (MR):** आजची पाण्याची गरज ÷ संचाचा ताशी प्रवाह = ठिबक किती वेळ चालवायचा. मे मध्ये सुमारे ३४ मिनिटे, सप्टेंबर-ऑक्टोबरमध्ये सुमारे ८९ मिनिटे.
- **Basis:** Computed runtimes match the independently published recommendation of 30-45 minutes early rising to 60-90 minutes later. Two Maharashtra sources agree, which raises confidence in both.
- **Yield impact:** Indirect but continuous. Wrong runtime means either chronic deficit or chronic saturation.
- **References:** Agrowon - Dr. Kadam runtime; computed from Agrowon - Bitle & Deshmukh volumes

**D03-SC-004** (SC, info, conf 0.7, tier B) · _executable_

- **Trigger:** Irrigation timing being set  
  `STAGE IN [G5] AND days_to_harvest BETWEEN 0 AND 20`
- **Action (EN):** Prefer early morning. Avoid midday because evaporation is high. Avoid night because prolonged surface wetness favours fungal infection.
- **कृती (MR):** पहाटे किंवा सकाळी लवकर सर्वोत्तम. दुपारी बाष्पीभवन जास्त, पाणी वाया. रात्री जमीन व पाने रात्रभर ओली राहिल्यास बुरशीला अनुकूल.
- **Basis:** Morning irrigation minimises evaporative loss and allows surfaces to dry during the day, shortening the wetness duration that fungal pathogens require.
- **Yield impact:** Small but continuous water saving plus reduced disease pressure.
- **References:** general irrigation practice; Domain 6 leaf wetness reasoning

**D03-SC-005** (SC, info, conf 0.75, tier A) · _executable_

- **Trigger:** Planting completed  
  `dap BETWEEN 2 AND 5`
- **Action (EN):** Plant into vafsa condition after a pre-irrigation, then give the first light irrigation on the third or fourth day.
- **कृती (MR):** पूर्वपाणी देऊन वाफसा स्थितीत लागवड करा, नंतर तिसऱ्या-चौथ्या दिवशी आंबवणीचे हलके पाणी द्या.
- **Basis:** Sources differ — one recommends water immediately after planting, another on the third or fourth day. The latter comes with the precondition of planting into vafsa, so soil moisture is already present. Heavy irrigation immediately after planting compacts vertisol and impedes shoot emergence.
- **Yield impact:** Affects emergence uniformity.
- **References:** Agrowon - Dr. Kadam ambavani; Vikaspedia

**D03-SC-006** (SC, info, conf 0.8, tier A) · _executable_

- **Trigger:** Month is October to January AND has_drip is true  
  `dap BETWEEN 150 AND 210 AND has_drip IS TRUE`
- **Action (EN):** Continue daily small doses. Do NOT switch to the 12 to 15 day flood interval. Consistency matters more than level during bulking.
- **कृती (MR):** रोज थोडे पाणी देत रहा. १२ ते १५ दिवसांचे अंतर हे पाटपाण्याचे नियम आहेत, ठिबकाचे नाहीत. गड्डा भरताना ओलाव्यातील सातत्य हे पातळीपेक्षा जास्त महत्वाचे — चढउतार झाल्यास गड्डा वेडावाकडा होतो.
- **Basis:** Fluctuating moisture during bulking produces misshapen rhizomes even when the mean level is correct, and shape affects grade and therefore price. Drip's advantage is precisely the ability to hold a steady state.
- **Yield impact:** Affects quality and grade more than weight, and the grading price spread is larger than most yield factors.
- **References:** Agrowon - Bitle & Deshmukh permanent vafsa; Domain 9 grading spread

**D03-WR-001** (WR, info, conf 0.85, tier A) · _executable_

- **Trigger:** Daily irrigation planning AND station evaporation data unavailable  
  `has_drip IS TRUE AND pan_evaporation_mm_day IS NULL AND dap BETWEEN 0 AND 225`
- **Action (EN):** Use the month-wise table as the base requirement. Range is 8,400 litres per acre per day in May to 22,000 in September and October. Flag confidence as medium and state that the figure is a regional average.
- **कृती (MR):** महिनानिहाय तक्त्यानुसार पाणी द्या — मे मध्ये ८,४०० लिटर प्रति एकर प्रति दिवस, सप्टेंबर-ऑक्टोबरमध्ये शिखर २२,००० लिटर. हा विभागीय सरासरीचा आकडा आहे.
- **Basis:** The table is published for Maharashtra ginger under drip and internally consistent — litres equal mm times 4000 for every month.
- **Yield impact:** Provides a complete working irrigation schedule with no sensor dependency, so the system functions from day one.
- **References:** Agrowon - Bitle & Deshmukh month-wise table

**D03-WR-002** (WR, info, conf 0.85, tier A) · _executable_

- **Trigger:** Daily irrigation planning AND pan_evaporation_mm_day is available from the cluster station  
  `pan_evaporation_mm_day IS NOT NULL AND dap BETWEEN 0 AND 225`
- **Action (EN):** Compute requirement as evaporation times crop coefficient times pan coefficient times 4000, and use it in preference to the table. Raise confidence to high.
- **कृती (MR):** पाण्याची गरज = बाष्पीभवन × पीक गुणांक × बाष्प पात्र गुणांक × ४०००. तक्त्याऐवजी हा रोजचा आकडा वापरा.
- **Basis:** The only locally variable term in the equation is evaporation. Kannad is hotter and drier than the belt the table averages over, so the regional figure is systematically wrong here in one direction.
- **Yield impact:** Improves dosing accuracy across the whole season and eliminates both chronic over- and under-watering.
- **References:** Agrowon - Bitle & Deshmukh formula and worked example

**D03-WR-003** (WR, info, conf 0.6, tier B) · _executable_

- **Trigger:** Engine requires a stage-wise crop coefficient  
  `STAGE IN [G3, G4] AND soil_moisture_vwc < vwc_stress_threshold`
- **Action (EN):** Use the back-calculated indicative values and mark them DERIVED. Do not present them as published. Record actual Kc from station data as a first-season deliverable.
- **कृती (MR):** अद्रकासाठी प्रकाशित Kc मालिका उपलब्ध नाही. तक्त्यावरून उलट गणित करून काढलेली अंदाजित मूल्ये वापरा, पण ती प्रकाशित म्हणून दाखवू नका. पहिल्या हंगामात station च्या डेटावरून खरी मालिका काढता येईल.
- **Basis:** The source worked example uses Kc of 0.5 without stating the stage. No complete stage-wise series for ginger in Indian conditions was located across ICAR-IISR, KAU or TNAU.
- **Yield impact:** None directly. Prevents false precision and identifies a valuable data gap.
- **References:** absence of source; Domain 3 back-calculation

**D03-WR-004** (WR, info, conf 0.88, tier B) · _executable_

- **Trigger:** Stage is G1, G3 or G4  
  `STAGE IN [G3, G4] AND dry_spell_days >= 5`
- **Action (EN):** Flag critical irrigation window. Tighten the moisture tolerance band, raise sampling to hourly, escalate advisory severity by one level, and apply the 7 day rain gap rule instead of 10.
- **कृती (MR):** ही निर्णायक सिंचन अवस्था आहे. ओलाव्याची सहन-मर्यादा घट्ट करा, sensor वाचन तासाला करा, इशाऱ्याची तीव्रता एक पातळी वर न्या.
- **Basis:** Published irrigation guidance names germination, rhizome initiation and rhizome development as critical, which matches the criticality ranking derived independently from crop physiology in Domain 1.
- **Yield impact:** u = 0.15 to 0.25 for stress inside these windows, and it is irrecoverable.
- **References:** ICL Growing Solutions; Domain 1 stage criticality

### D04

**D04-MC-004** (MC, info, conf 0.75, tier B) · _executable_

- **Trigger:** Micronutrient spray scheduled AND air_temp_max_c above 35 OR rain forecast within 6 hours  
  `air_temp_max_c > 35 OR forecast_rain_48h_mm > 5`
- **Action (EN):** Postpone the spray. Spray early morning or evening only, and not before rain.
- **कृती (MR):** फवारणी पुढे ढकला. दुपारच्या उन्हात फवारल्यास पाने करपतात, आणि पावसापूर्वी फवारल्यास औषध वाहून जाते.
- **Basis:** Ginger leaves scorch above 35 C and this district records maxima up to 45.9 C. Rain within a few hours washes off foliar application before absorption.
- **Yield impact:** Protects the 0.11 micronutrient value from being wasted at execution.
- **References:** Domain 1 heat threshold; Core C3.3 forecast-conditioned suppression

**D04-NU-002** (NU, info, conf 0.78, tier A) · _executable_

- **Trigger:** dap greater than 180  
  `dap > 180 AND k_late_split_2_date IS NOT NULL`
- **Action (EN):** Do not stop potassium and micronutrient support simply because foliage growth has slowed. The rhizome continues to develop until harvest.
- **कृती (MR):** पानांची वाढ मंदावली म्हणून खत थांबवू नका. गड्डा काढणीपर्यंत वाढतच राहतो.
- **Basis:** Documented growth phases are active growth 90 to 120 DAP, sluggish vegetative growth 120 to 180, and senescence after 180 during which the rhizome continues to develop until harvest.
- **Yield impact:** Protects the final bulking period, which contributes the largest share of weight.
- **References:** IntechOpen INM chapter growth phases

**D04-PK-003** (PK, info, conf 0.7, tier B) · _executable_

- **Trigger:** Late potassium application AND (soil_ec elevated OR target_product is dry_ginger)  
  `dap > 150 AND k_late_split_2_date IS NULL`
- **Action (EN):** Consider sulphate of potash instead of muriate for the late splits. It is chloride free and supplies sulphur.
- **कृती (MR):** उशिराचे पालाश हप्ते MOP ऐवजी SOP मधून देण्याचा विचार करा. SOP क्लोराईडमुक्त आहे आणि गंधकही देते.
- **Basis:** Drip concentrates salts at the wetting front and there is no leaching rain in this period, so chloride from MOP accumulates. SOP avoids that and supplies sulphur, which is commonly deficient in black soil. The published fertigation schedule itself switches to SOP for the earthing-up application, which suggests the distinction is deliberate.
- **Yield impact:** Affects quality and soil condition rather than yield weight.
- **References:** Agrowon fertigation schedule SOP at earthing; Core C1.4 salt accumulation

**D04-SN-002** (SN, info, conf 0.7, tier B) · _executable_

- **Trigger:** dap greater than 130 AND fertigation_active AND soil_free_lime_pct elevated  
  `soil_free_lime_pct > 10 AND micronutrient_spray_1_done IS FALSE`
- **Action (EN):** Review whether weekly calcium nitrate is needed. Calcareous soil already supplies abundant calcium, and calcium nitrate also adds nitrogen, which is unwanted this late.
- **कृती (MR):** चुनखडीयुक्त जमिनीत कॅल्शिअम आधीच भरपूर आहे. कॅल्शिअम नायट्रेटमधून नत्रही जाते, जे या टप्प्यावर नको. माती परीक्षणानुसार गरज तपासा.
- **Basis:** The published fertigation schedule adds calcium nitrate weekly from 130 DAP for skin hardening and storage quality. On calcareous soil the calcium is not limiting, and the nitrate fraction conflicts with the no-nitrogen-after-80-DAP rule.
- **Yield impact:** Avoids an unnecessary input and an unwanted late nitrogen source.
- **References:** Agrowon fertigation schedule; Domain 4 late nitrogen rule

### D05

**D05-CH-005** (CH, info, conf 0.85, tier A) · _executable_

- **Trigger:** Soil drench scheduled  
  `last_insecticide_group IS NOT NULL AND insecticide_group_repeated IS TRUE`
- **Action (EN):** Drench only when the soil is at vafsa condition, and give a slight water stress afterwards rather than irrigating immediately.
- **कृती (MR):** आळवणी करताना जमिनीस वाफसा असावा. आळवणीनंतर पिकास थोडासा पाण्याचा ताण द्यावा — लगेच पाणी दिल्यास औषध वाहून जाते.
- **Basis:** Source gives both instructions explicitly. Drenching saturated soil dilutes and displaces the chemical; irrigating immediately after leaches it below the shallow root zone.
- **Yield impact:** Protects the effectiveness of the application rather than adding yield.
- **References:** Agrowon - Mali & Mahajan application rules

**D05-CH-006** (CH, info, conf 0.8, tier A) · _executable_

- **Trigger:** Foliar spray scheduled  
  `air_temp_max_c > 35 OR forecast_rain_48h_mm > 5`
- **Action (EN):** Add a sticker at 1 ml per litre. Spray early morning or evening, not in the midday heat, and postpone if rain is forecast within a few hours.
- **कृती (MR):** फवारणीत चिकट पदार्थ १ मिलि प्रति लिटर मिसळा. सकाळी लवकर किंवा संध्याकाळी फवारा — दुपारच्या उन्हात पाने करपतात. काही तासांत पावसाचा अंदाज असल्यास फवारणी पुढे ढकला.
- **Basis:** Source specifies the sticker. Ginger leaves are smooth so retention is poor without one. Leaves scorch above 35 C and this district reaches 45.9 C.
- **Yield impact:** Protects application efficacy and avoids leaf damage.
- **References:** Agrowon - Mali & Mahajan; Domain 1 heat threshold; Core C3.3

**D05-PC-003** (PC, info, conf 0.75, tier B) · _executable_

- **Trigger:** dap approximately 60  
  `dap BETWEEN 58 AND 64 AND labour_arranged_date IS NULL`
- **Action (EN):** Remind the farmer to arrange labour for earthing up now. August is also cotton and soybean intercultivation season and labour becomes scarce.
- **कृती (MR):** उटाळणीसाठी मजूर आत्ताच ठरवा. ऑगस्टमध्ये कापूस-सोयाबीनच्या आंतरमशागतीमुळे सर्वत्र मजुरांना मागणी असते, आणि उटाळणीला कठोर मुदत आहे.
- **Basis:** Earthing up must be completed before flowering and it is simultaneously a rhizome fly control measure. Labour scarcity is the most likely reason it is delayed.
- **Yield impact:** Protects the 0.125 earthing up value and part of the 0.175 rhizome fly value.
- **References:** Core C7.3 labour feasibility; Domain 8 operations calendar

**D05-SC-001** (SC, info, conf 0.7, tier B) · _executable_

- **Trigger:** Weekly or fortnightly scouting due  
  `dap BETWEEN 40 AND 200 AND pest_scouting_date IS NULL`
- **Action (EN):** Issue the scouting checklist for the current stage and month, with sample sizes. Record percentages, not impressions.
- **कृती (MR):** सध्याच्या अवस्थेनुसार निरीक्षण यादी द्या — पाच ठिकाणी, प्रत्येकी पाच किंवा दहा रोपे. टक्केवारी नोंदवा, अंदाज नाही.
- **Basis:** Sources say to act as needed but do not define need. Recorded percentages are what will eventually turn those qualitative instructions into local thresholds.
- **Yield impact:** Indirect this season; foundational for future seasons.
- **References:** Domain 5 scouting protocol

### D06

**D06-CH-004** (CH, info, conf 0.85, tier A) · _executable_

- **Trigger:** A soil drench is scheduled  
  `last_fungicide_group IS NOT NULL AND fungicide_group_repeated IS TRUE`
- **Action (EN):** Drench only at vafsa condition and give a light water stress afterwards rather than irrigating immediately. Add a sticker at 1 ml per litre for foliar sprays.
- **कृती (MR):** आळवणी करताना जमिनीस वाफसा असावा, आणि नंतर लगेच पाणी न देता थोडासा ताण द्यावा. फवारणीत चिकट पदार्थ एक मिलि प्रति लिटर मिसळा.
- **Basis:** The source gives both instructions explicitly. Drenching saturated soil dilutes and displaces the chemical, and irrigating immediately afterwards leaches it below the shallow root zone where ginger roots sit.
- **Yield impact:** Protects the effectiveness of the application.
- **References:** Agrowon - Mali & Mahajan application rules

**D06-SW-001** (SW, info, conf 0.8, tier A) · _executable_

- **Trigger:** Disease risk scoring is being computed  
  `DURATION(rh_pct > 85) > 48 HOURS AND MONTH IN [JUL, AUG, SEP]`
- **Action (EN):** Compute the soft rot risk score from saturation duration, soil temperature, humidity, rainfall forecast, crop stage and field history. Saturation duration carries the greatest weight.
- **कृती (MR):** कंदकूज जोखीम गुण संपृक्ततेचा कालावधी, मातीचे तापमान, आर्द्रता, पावसाचा अंदाज, पिकाची अवस्था आणि शेताचा इतिहास यांवरून काढा. संपृक्ततेच्या कालावधीला सर्वाधिक वजन.
- **Basis:** Soft rot thrives in warm humid conditions and poor drainage, and Pythium is favoured by 25 to 30 C soil temperature. Every one of these inputs is measurable on the deployed hardware, which makes this the domain where the sensor investment returns most directly.
- **Yield impact:** Enables preventive action on the largest loss factor in the crop.
- **References:** ScienceDirect Heliyon 2023 warm humid conditions and poor drainage

### D07

**D07-BC-001** (BC, info, conf 0.8, tier B) · _executable_

- **Trigger:** A public forecast is received for this location  
  `bias_observation_count >= 30`
- **Action (EN):** Store the forecast alongside the later observed value. Compute the rolling bias and apply it to subsequent forecasts. Report confidence as a function of how many observations exist.
- **कृती (MR):** अंदाज आणि नंतरचे प्रत्यक्ष मापन दोन्ही साठवा. दोघांतील फरकाची सरासरी काढून पुढील अंदाज दुरुस्त करा. किती निरीक्षणे जमली आहेत त्यावरून विश्वासार्हता सांगा.
- **Basis:** Public forecast grids carry systematic local bias. A station measures actual conditions, and the running difference is a correction function that improves with every observation. It cannot be reproduced without physical hardware in the same locality.
- **Yield impact:** Improves every forecast-conditioned rule across Domains 3, 5 and 6.
- **References:** Core C3.1 bias-correction flywheel

**D07-BC-002** (BC, info, conf 0.85, tier B) · _executable_

- **Trigger:** The product's forecasting capability is being described to a farmer or partner  
  `forecast_bias_correction_mm IS NOT NULL`
- **Action (EN):** State the position accurately. We do not produce forecasts. We measure actual local conditions, correct the public forecast for this village, and translate the result into a crop decision. Do not claim forecasting ability.
- **कृती (MR):** स्थिती अचूक सांगा. आपण हवामान अंदाज तयार करत नाही. आपण प्रत्यक्ष स्थानिक स्थिती मोजतो, सार्वजनिक अंदाज या गावासाठी दुरुस्त करतो, आणि त्यावरून पिकाचा निर्णय देतो. अंदाज वर्तवण्याचा दावा करू नये.
- **Basis:** Long range monsoon forecasting is IMD's work and has real limits. Overstating capability fails at the first dry spell that was not predicted. The genuine contribution is the third element — IMD reports weather but does not say what the crop should do.
- **Yield impact:** None. Protects credibility, which is a precondition for the advice being followed at all.
- **References:** Domain 7 honest limit section; Domain 12 honest positioning

**D07-BC-003** (BC, info, conf 0.7, tier B) · _executable_

- **Trigger:** bias_observation_count below 30  
  `bias_observation_count < 30 AND bias_observation_count > 0`
- **Action (EN):** Apply the raw public forecast without correction and mark forecast-conditioned advisory as medium confidence. State that local correction improves with each season.
- **कृती (MR):** अजून पुरेशी निरीक्षणे नाहीत, म्हणून दुरुस्तीशिवाय सार्वजनिक अंदाज वापरा आणि विश्वासार्हता मध्यम दाखवा. दर हंगामागणिक स्थानिक दुरुस्ती सुधारत जाईल.
- **Basis:** A bias estimate computed from too few observations is noise. Applying it would make the forecast worse rather than better. The threshold is a judgement rather than a derived figure.
- **Yield impact:** None. Prevents a premature correction from degrading forecast-driven rules.
- **References:** Core C3.1 confidence as a function of observation count

**D07-CC-003** (CC, info, conf 0.8, tier A) · _executable_

- **Trigger:** Any historical rainfall average is being cited in advisory  
  `rainfall_ytd_mm IS NOT NULL AND season_water_plan_basis IS NULL`
- **Action (EN):** Note that all rainfall figures in this knowledge base are historical averages measured against a declining trend, so future years are more likely to fall below them than above.
- **कृती (MR):** या knowledge base मधील सर्व पावसाचे आकडे ऐतिहासिक सरासरी आहेत, आणि कल ऋण आहे — म्हणजे भविष्यातील वर्षे या आकड्यांपेक्षा कोरडी असण्याची शक्यता जास्त आहे, कमी नाही.
- **Basis:** Sen's slope is negative for monsoon rainfall across Marathwada districts, and winter and pre-monsoon rainfall show statistically significant declines. Historical normals therefore describe a wetter past than the likely future.
- **Yield impact:** Framing that justifies the safety margin in every water calculation.
- **References:** Arabian Journal of Geosciences 2022; ResearchGate 2021

**D07-CL-002** (CL, info, conf 0.65, tier A) · _executable_

- **Trigger:** agro_climatic_zone is unknown  
  `agro_climatic_zone IS NULL`
- **Action (EN):** Assume Marathwada western zone provisionally — 600 to 750 mm and mean temperature below 26 C — and flag it as inferred rather than confirmed. Confirm with VNMKV Parbhani or the district agriculture office.
- **कृती (MR):** तात्पुरता पश्चिम विभाग गृहीत धरा — ६०० ते ७५० मिमी, सरासरी तापमान २६ अंशांखाली — पण हे अनुमान आहे, पुष्टी नाही. VNMKV परभणी किंवा जिल्हा कृषी कार्यालयाकडून तालुका-स्तरीय वर्गीकरण घ्यावे.
- **Basis:** Three agro-climatic zones are identified within Marathwada. Kannad sits in the western part of the district near the Ajanta range and above 600 m, which places it in the western zone on the available criteria. The study does not assign talukas individually.
- **Yield impact:** Affects which regional recommendations apply. Not a direct yield factor.
- **References:** Agro-Climatic Zonation of Marathwada, IMD plus Hydrological Project Nashik 1980-2016

**D07-HS-002** (HS, info, conf 0.8, tier A) · _executable_

- **Trigger:** Leaf tip and margin scorch reported AND air_temp_max_c above 35 in the preceding three days  
  `heat_stress_days_count >= 3 AND STAGE IN [G1, G2, G3]`
- **Action (EN):** Classify as heat stress, not disease. Recommend mulch, shade and irrigation timing. Do not recommend a fungicide on this signal.
- **कृती (MR):** ही उष्णतेची इजा आहे, रोग नाही. आच्छादन, सावली आणि पाण्याची वेळ हे उपाय. बुरशीनाशक सुचवू नका.
- **Basis:** Leaves scorch above 35 C, and in this district maxima reach 45.9 C, so foliage scorch is routine rather than exceptional. Without the weather record it is indistinguishable from leaf spot, and the source's sun-held ring test is the confirming check.
- **Yield impact:** Prevents repeated unnecessary fungicide application through the hot months.
- **References:** Agrowon stage temperature limits; Domain 6 sun-held ring test

**D07-HS-003** (HS, info, conf 0.75, tier A) · _executable_

- **Trigger:** Month is October AND stage is G3 or G4  
  `MONTH IN [OCT] AND heat_stress_days_count >= 3`
- **Action (EN):** Raise vigilance. October carries three pressures at once — a secondary temperature maximum, peak water demand at 22,000 litres per acre per day, and the cyclone window.
- **कृती (MR):** ऑक्टोबरमध्ये दक्षता वाढवा. या महिन्यात तीन गोष्टी एकत्र येतात — दिवसाच्या तापमानाचा दुय्यम शिखर, पाण्याची सर्वाधिक मागणी, आणि चक्रीवादळाची शक्यता.
- **Basis:** The gazetteer records that day temperature rises again after monsoon withdrawal, giving a secondary October maximum. The Domain 3 water table peaks in September and October. The cyclone season has a post-monsoon peak in October and November.
- **Yield impact:** Not a separate factor. It concentrates existing risks into one month at the highest criticality stage.
- **References:** Government gazetteer October secondary maximum; Domain 3 monthly water table; climatestotravel cyclone seasonality

**D07-HS-004** (HS, info, conf 0.78, tier B) · _executable_

- **Trigger:** A foliar spray of any kind is scheduled  
  `air_temp_max_c > 35 OR forecast_rain_48h_mm > 5`
- **Action (EN):** Restrict spraying to early morning or evening. Postpone if the maximum is above 35 C at the intended time or if rain is forecast within a few hours.
- **कृती (MR):** फवारणी फक्त सकाळी लवकर किंवा संध्याकाळी करा. त्या वेळी तापमान ३५ अंशांवर असेल किंवा काही तासांत पावसाचा अंदाज असेल तर पुढे ढकला.
- **Basis:** Leaves scorch above 35 C, and midday maxima here regularly exceed that through the hot months. Rain within a few hours removes foliar application before absorption.
- **Yield impact:** Protects the effectiveness of every spray in Domains 4, 5 and 6.
- **References:** Domain 1 heat threshold; Core C3.3 forecast-conditioned suppression

**D07-HU-004** (HU, info, conf 0.8, tier A) · _executable_

- **Trigger:** Two disease seasons need to be distinguished in advisory  
  `(fog_observed IS TRUE AND MONTH IN [DEC, JAN, FEB]) OR (saturation_hours > 12 AND MONTH IN [JUL, AUG, SEP])`
- **Action (EN):** Treat July to September as the soil-borne season driven by saturation, and December to February as the foliar season driven by fog. Different triggers, different responses, different times of year.
- **कृती (MR):** जुलै ते सप्टेंबर हा जमिनीखालील रोगांचा हंगाम — कारण संपृक्तता. डिसेंबर ते फेब्रुवारी हा पानांवरील रोगांचा हंगाम — कारण धुके. वेगळे संकेत, वेगळे उपाय, वेगळा काळ.
- **Basis:** Soft rot peaks in August and September with high humidity and saturation, while leaf spot and blotch follow prolonged fog in winter. Conflating them would apply the wrong trigger at the wrong time of year.
- **Yield impact:** Ensures the correct protocol fires in each season.
- **References:** Agrowon - Mali and Mahajan disease timing and fog rule; climate-data.org humidity

**D07-MO-003** (MO, info, conf 0.75, tier B) · _executable_

- **Trigger:** Seasonal outlook available before planting  
  `MONTH IN [SEP, OCT] AND dry_spell_days >= 10`
- **Action (EN):** Present the seasonal outlook as context, not as a decision. State the forecast, state that distribution matters more than quantity, and do not adjust the planting date on a seasonal forecast — the deadline is fixed by pest and disease risk, not by rainfall.
- **कृती (MR):** हंगामी अंदाज संदर्भ म्हणून द्या, निर्णय म्हणून नाही. पावसाचे वाटप हे प्रमाणापेक्षा महत्वाचे. आणि हंगामी अंदाजावरून लागवडीची तारीख बदलू नका — ती मुदत पावसाने नव्हे, कीड व रोगाच्या जोखमीने ठरलेली आहे.
- **Basis:** Seasonal forecasts have limited skill at taluka level. The ginger planting deadline is set by rhizome fly and soft rot timing, which do not move with the rainfall outlook. Adjusting the planting date on a seasonal forecast trades a certain risk for an uncertain one.
- **Yield impact:** Protects the planting deadline rule from being overridden by weaker information.
- **References:** IMD statement on distribution versus quantity; Domain 2 planting deadline

**D07-MO-004** (MO, info, conf 0.82, tier A) · _executable_

- **Trigger:** Continuous rainfall recorded during the monsoon  
  `rainfall_mm > 20 AND STAGE IN [G2, G3] AND drainage_levels_present < 3`
- **Action (EN):** Stop drip entirely and switch attention to drainage. July rainfall in this belt is a drainage problem for ginger, not a water supply opportunity.
- **कृती (MR):** ठिबक पूर्ण बंद करा आणि लक्ष निचऱ्याकडे वळवा. इथला जुलैचा पाऊस अद्रकासाठी मुख्यतः धोका आहे, संधी नाही.
- **Basis:** July delivers 195 to 217 mm over about ten rainy days, which is the wettest month, while crop demand at that stage is moderate. The excess must leave the root zone rather than be conserved.
- **Yield impact:** Feeds the saturation and soft rot pathway.
- **References:** climate-data.org monthly rainfall; Domain 3 monthly water table

**D07-RF-002** (RF, info, conf 0.85, tier A) · _executable_

- **Trigger:** Rainfall figures are being used for planning  
  `rainfall_ytd_mm IS NOT NULL AND rainfall_deviation_pct < -25`
- **Action (EN):** Use 725 to 775 mm as the planning range. Prefer the conservative figure. Note that published sources vary from 725.8 to 859 mm depending on station and period.
- **कृती (MR):** नियोजनासाठी ७२५ ते ७७५ मिमी ही श्रेणी वापरा, आणि कमी आकडा गृहीत धरा. स्रोतांत ७२६ ते ८५९ मिमी असा फरक आहे — station आणि कालावधी वेगळे असल्याने.
- **Basis:** The government gazetteer gives 725.8 mm over 70 years and is both the lowest and the best documented figure. Newer normals from shorter periods run higher. In planning, the conservative figure is the correct one, particularly against a declining trend.
- **Yield impact:** Sets the denominator for the whole water budget.
- **References:** Government gazetteer 70 year series; District Profile; climate-data.org

**D07-RF-005** (RF, info, conf 0.65, tier B) · _executable_

- **Trigger:** Rainfall is being converted into an irrigation credit  
  `rainfall_mm > 2 AND percolation_class IS NOT NULL`
- **Action (EN):** Use effective rainfall rather than gross. Roughly 65 percent is a working assumption on this soil pending measurement, because concentrated rain on heavy soil runs off.
- **कृती (MR):** एकूण पाऊस नव्हे, प्रभावी पाऊस वापरा. काळ्या जमिनीत केंद्रित पाऊस वाहून जातो, म्हणून सुमारे ६५ टक्के हे तात्पुरते गृहीतक — प्रत्यक्ष मोजणी होईपर्यंत.
- **Basis:** Not all rainfall enters the root zone. On heavy soil with concentrated rainfall, runoff and deep percolation losses are significant, and July delivers about 195 mm over roughly ten days.
- **Yield impact:** Prevents systematic under-irrigation from over-crediting rainfall.
- **References:** Domain 3 effective rainfall fraction; Domain 2 percolation behaviour

**D07-TM-001** (TM, info, conf 0.82, tier A) · _executable_

- **Trigger:** Stage transition or monthly planning  
  `air_temp_max_c > 35 AND STAGE IN [G0, G1]`
- **Action (EN):** Compare current temperature against the stage requirement: germination 30 to 35, tillering 25 to 30, rhizome formation 20 to 25, rhizome growth 18 to 20. Flag only genuine mismatches.
- **कृती (MR):** सध्याचे तापमान अवस्थेच्या गरजेशी तपासा — उगवण ३०-३५, फुटवा २५-३०, कंद तयार होणे २०-२५, कंद वाढ १८-२०. खरी तफावत असेल तरच इशारा द्या.
- **Basis:** Stage-wise optima are published for Maharashtra ginger under drip. Ten of the twelve crop months in this belt fall within or close to the requirement, so a blanket temperature warning would produce noise.
- **Yield impact:** Framing for the heat rules rather than a factor in itself.
- **References:** Agrowon - Bitle and Deshmukh, Netafim

**D07-TM-002** (TM, info, conf 0.82, tier A) · _executable_

- **Trigger:** Month is between November and January AND stage is G4  
  `air_temp_min_c < 12 AND STAGE IN [G4]`
- **Action (EN):** Inform that conditions are now favourable and the priority shifts from protection to supply — consistent moisture and potassium. This is when yield is actually made.
- **कृती (MR):** आता तापमान गड्डा भरण्यासाठी अनुकूल आहे. आता पीक वाचवण्यापेक्षा भरू देणे महत्वाचे — ओलाव्यात सातत्य आणि पालाश. उत्पादन याच काळात ठरते.
- **Basis:** Rhizome growth optimum is 18 to 20 C and the December mean here is 20.8 C. Kerala and Konkan do not have this because their winters stay warm. The dryness and the cold winter come from the same geography.
- **Yield impact:** Identifies the window in which the largest share of yield accumulates.
- **References:** Agrowon stage-wise temperature optima; climatestotravel December mean

**D07-TM-003** (TM, info, conf 0.85, tier B) · _executable_

- **Trigger:** GDD-based staging is requested  
  `soil_temp_c > 32 AND STAGE IN [G1, G2]`
- **Action (EN):** Refuse. No reliable published GDD series exists for ginger in Indian conditions. Log daily temperature so that a local series can be derived after one season, but do not invent a base temperature in the meantime.
- **कृती (MR):** अद्रकासाठी भारतीय परिस्थितीत विश्वासार्ह GDD मालिका उपलब्ध नाही. रोजचे तापमान नोंदवत रहा म्हणजे एका हंगामानंतर स्थानिक मालिका काढता येईल — पण तोपर्यंत आधार तापमान अंदाजाने ठरवू नका.
- **Basis:** Sugarcane has a validated base temperature and thermal time model; ginger does not. A plausible-looking invented number would give false precision and would silently mistime every downstream event.
- **Yield impact:** None directly. Prevents false precision and identifies a first-season data opportunity.
- **References:** absence of source across ICAR-IISR, KAU and TNAU; Domain 1 GDD disabled

**D07-VP-001** (VP, info, conf 0.85, tier A) · _executable_

- **Trigger:** A daily station reading is received AND both air_temp_max_c and rh_pct are present  
  `air_temp_max_c IS NOT NULL AND rh_pct IS NOT NULL`
- **Action (EN):** Compute vpd_kpa = 0.6108 * exp(17.27 * air_temp_max_c / (air_temp_max_c + 237.3)) * (1 - rh_pct/100) and store it on the daily record. Also update vpd_night_mean_kpa from the nighttime hourly readings where available. Emit nothing to the farmer.
- **कृती (MR):** vpd_kpa या नोंदीची गणना करा — Tetens समीकरणाने. रात्रीच्या तासांतील सरासरी vpd_night_mean_kpa सुद्धा नोंदवा. शेतकऱ्याला कोणतीही सूचना पाठवू नका — ही केवळ आतील गणना आहे.
- **Basis:** Relative humidity conflates two very different agronomic situations at different temperatures. VPD is the temperature-corrected form and is what plants and spray droplets actually respond to. Storing it once per day lets every downstream rule read the same value and lets the count-once check succeed.
- **Yield impact:** None directly. Enables D07-VP-002 (spray safety) and D07-VP-003 (leaf wetness confidence).
- **References:** FAO-56 chapter 3, Penman–Monteith reference evapotranspiration; Tetens 1930, saturation vapour pressure equation

**D07-VP-002** (VP, info, conf 0.78, tier B) · _executable_

- **Trigger:** A foliar spray is scheduled AND vpd_kpa is either below 0.4 or above 2.0  
  `spray_scheduled_today IS TRUE AND (vpd_kpa < 0.4 OR vpd_kpa > 2.0)`
- **Action (EN):** Delay the spray to the next window inside VPD 0.8 to 1.5 kPa, typically 2 to 4 hours later or the following morning. Below 0.4 kPa the droplets do not dry and disease pressure is amplified rather than reduced. Above 2.0 kPa evaporation is faster than uptake and effective dose collapses. If D07-HS-004 also fires, present one combined message: temperature or rain plus VPD, one recommended new window.
- **कृती (MR):** फवारणी VPD ०.८ ते १.५ kPa च्या पट्ट्यात होईल अशा वेळेवर पुढे ढकला — बहुतेक वेळा २–४ तासांनी किंवा दुसऱ्या दिवशी सकाळी. VPD ०.४ पेक्षा कमी असेल तर थेंब वाळत नाहीत आणि रोगदाब कमी होण्याऐवजी वाढतो. VPD २.० च्या वर असेल तर पानांवर बसण्यापूर्वीच बाष्पीभवन होते आणि प्रभावी मात्रा खूप कमी होते. D07-HS-004 देखील लागू होत असल्यास एकच एकत्रित संदेश द्या — तापमान/पाऊस आणि VPD, एकच पुढील वेळ.
- **Basis:** Spray efficacy is a function of droplet residence on the leaf, which in turn tracks VPD, not temperature or rainfall alone. D07-HS-004 catches high temperature and imminent rain but is blind to the two humidity extremes. This rule adds only that missing discrimination, without changing D07-HS-004's behaviour.
- **Yield impact:** Grouped under the existing spray-timing duplication group. Not counted separately; see v_u_values_deduplicated.
- **References:** Foliar spray drift and efficacy studies, ICAR-CPCRI 2019; FAO-56 chapter 3; Ministry of Agriculture, Government of India — spray timing guidelines

**D07-VP-003** (VP, info, conf 0.75, tier B) · _executable_

- **Trigger:** vpd_night_mean_kpa is below 0.3 AND fog is not observed AND month is December, January or February  
  `vpd_night_mean_kpa < 0.3 AND fog_observed IS FALSE AND MONTH IN [DEC, JAN, FEB]`
- **Action (EN):** Tag tonight's estimated leaf_wetness_hours with a high dew-probability confidence flag and log the reason (very low nighttime VPD with clear sky). Do not raise a new disease alert. If D07-HU-002 fires overnight or the next morning, the confidence flag travels with it. This is the interim substitute for the missing leaf wetness sensor logged as D07-OI-05.
- **कृती (MR):** आजच्या रात्रीच्या अंदाजित leaf_wetness_hours नोंदीवर उच्च-दव-संभाव्यता ध्वज लावा आणि कारण नोंदवा (रात्रीचा VPD अत्यंत कमी, आकाश निरभ्र). नवीन रोग सूचना देऊ नका. रात्रभर किंवा सकाळी D07-HU-002 सुरू झाल्यास हा ध्वज त्याच्यासोबत जातो. हा पानावरील ओलावा सेन्सर बसेपर्यंतचा (D07-OI-05) तात्पुरता पर्याय आहे.
- **Basis:** Dew formation on ginger leaves requires the leaf surface to reach the dew point of the surrounding air. Low nighttime VPD means the air is already close to saturation and radiative cooling of the leaf will cross that threshold. Fog observations catch part of this signal; low VPD catches the other part, especially on cold clear nights when fog does not form but dew still soaks the canopy.
- **Yield impact:** None directly. Improves the reliability of D07-HU-002 and future disease-forecast rules that depend on it.
- **References:** Grantz 1990, Plant, Cell & Environment; IMD Marathwada winter humidity records; Domain 6 leaf wetness estimation notes

**D07-WS-001** (WS, info, conf 0.85, tier A) · _executable_

- **Trigger:** Weather station commissioning or measurement priorities being set  
  `wind_speed_ms > 8`
- **Action (EN):** Prioritise evaporation above everything else. It is the only locally variable term in the water requirement formula, and every other measurement supports either it or a disease trigger.
- **कृती (MR):** बाष्पीभवनाला सर्वोच्च प्राधान्य द्या. पाण्याच्या गरजेच्या सूत्रातील एकमेव स्थानिक बदलणारा घटक तोच आहे — बाकी सर्व मापने त्याला किंवा रोग-संकेतांना आधार देतात.
- **Basis:** The water requirement formula is evaporation times crop coefficient times pan coefficient. The two coefficients are crop and instrument constants; only evaporation varies with location. Kannad is hotter and drier than the belt the published table averages over, so the regional figure is systematically wrong here in one direction.
- **Yield impact:** Improves dosing accuracy across the entire season and removes both chronic over and under watering.
- **References:** Agrowon - Bitle and Deshmukh formula; Domain 3 monthly table caveat

**D07-WS-002** (WS, info, conf 0.7, tier B) · _executable_

- **Trigger:** Hardware roadmap review  
  `wind_speed_ms > 5 AND air_temp_max_c > 33`
- **Action (EN):** Record the leaf wetness sensor as the highest value missing measurement, followed by solar radiation if not already fitted. Both are cheap.
- **कृती (MR):** पानांवरील ओलावा मोजणारा sensor हा सर्वात मूल्यवान गहाळ मापन आहे; त्यानंतर सौर विकिरण. दोन्ही स्वस्त आहेत.
- **Basis:** Leaf wetness duration drives foliar disease and is currently estimated rather than measured. Solar radiation improves the evaporation computation where no pan is fitted.
- **Yield impact:** Improves accuracy of the 0.08 foliar disease trigger and of the whole irrigation schedule.
- **References:** Core C10.5 capability gap register; Domain 6 leaf wetness estimation

**D07-WS-003** (WS, info, conf 0.8, tier B) · _executable_

- **Trigger:** Daily station readings received  
  `wind_speed_ms > 4 AND forecast_rain_48h_mm < 2`
- **Action (EN):** Compute and store the derived variables: evaporation, dew point, estimated leaf wetness hours, and accumulated rainfall against the seasonal expectation.
- **कृती (MR):** रोजच्या वाचनांवरून काढलेली मूल्ये साठवा — बाष्पीभवन, दव-बिंदू, अंदाजित पानांवरील ओलावा, आणि हंगामी अपेक्षेविरुद्ध जमा पाऊस.
- **Basis:** Raw readings are converted into the variables biology actually responds to. Storing the derived values rather than recomputing them keeps the advisory reproducible and lets the bias correction accumulate.
- **Yield impact:** Foundational rather than direct.
- **References:** Core C3.2 derived agro-meteorological variables

### D08

**D08-BN-001** (BN, info, conf 0.8, tier B) · _executable_

- **Trigger:** Multiple operations fall due within a few days of each other  
  `dap IN [0, 82, 120]`
- **Action (EN):** Bundle them into one field visit and issue a single combined instruction list. Do not send separate notifications for each.
- **कृती (MR):** ती सर्व कामे एकाच फेरीत बांधा आणि एकच एकत्रित सूचना यादी द्या. प्रत्येक कामासाठी वेगळी सूचना पाठवू नका.
- **Basis:** The farmer visits the field once. Three separate instructions on three days produce three ignored instructions. The natural bundles are pre-planting, the herbicide window, earthing up, and the second earthing.
- **Yield impact:** Indirect but broad. Adherence is what converts a correct recommendation into a yield effect.
- **References:** Core C7.1 operation bundling

**D08-GR-001** (GR, info, conf 0.6, tier C) · _executable_

- **Trigger:** dap at 60 or 75 AND all basic operations are complete  
  `dap BETWEEN 58 AND 78 AND earthing_up_date IS NOT NULL AND mulch_stage_2_done IS TRUE`
- **Action (EN):** Offer the optional growth regulator: 2 percent urea plus 400 ppm NAA, reported to raise yield and reduce fibre. Emit active ingredients only, never a brand. Do not surface this until earthing up, mulching and drainage are complete.
- **कृती (MR):** ऐच्छिक सुधारणा — २% युरिया अधिक ४०० ppm NAA, उत्पादन वाढ आणि तंतू कमी करण्यासाठी. घटकांची नावे सांगा, ब्रँड नाही. उटाळणी, आच्छादन आणि निचरा पूर्ण झाल्याशिवाय हा पर्याय दाखवू नका.
- **Basis:** Source reports NAA with urea at 60 and 75 days for yield increase and fibre reduction. Fibre is a quality determinant and variety fibre ranges from 3.26 to 4.5 percent, so a treatment that reduces fibre can move quality by about as much as variety choice does.
- **Yield impact:** Not quantified in the source. Presented as optional because the cost-benefit is unverified and the source is commercial.
- **References:** AgroWorld growth regulator section

**D08-IC-003** (IC, info, conf 0.65, tier C) · _executable_

- **Trigger:** Shade decision being made AND target_product is dry_ginger  
  `target_product == 'dry_ginger' AND shade_pct IS NULL`
- **Action (EN):** Note that excessive direct sunlight reduces ginger aroma. Where dry ginger is the route, shade carries a quality argument as well as a heat argument. Consider a tall intercrop such as tur, or temporary netting during the hot months.
- **कृती (MR):** जास्त सूर्यप्रकाशाने आल्याचा सुवास कमी होतो. सुंठ हा मार्ग असल्यास सावलीचा युक्तिवाद दुहेरी होतो — उष्णतेपासून बचाव आणि प्रत टिकवणे. तूरसारखे उंच आंतरपीक किंवा उन्हाळ्यात तात्पुरती जाळी विचारात घ्या.
- **Basis:** Source states that trials found aroma declines with excessive direct sunlight, and separately that the crop grows well in 25 percent shade. Kannad is an open-field high-radiation belt with no multi-storey plantation, so the aroma risk is greater here than in the shaded gardens of Kerala. Aroma is the main quality determinant for dry ginger and oil.
- **Yield impact:** Affects quality and therefore price rather than weight. Given the grading spread observed in the market, that can exceed a yield effect.
- **References:** AgroWorld shade and aroma finding; Domain 9 grading spread

**D08-TL-002** (TL, info, conf 0.7, tier B) · _executable_

- **Trigger:** Soil moisture enters the workable band after rain AND land preparation is incomplete  
  `vafsa_state == 'workable' AND kulav_passes < 3`
- **Action (EN):** Notify that the field is workable for approximately the next three to four days.
- **कृती (MR):** पुढील तीन-चार दिवस मशागतीस योग्य आहेत. वाफसा गेल्यावर काळ्या जमिनीत काम करता येणार नाही.
- **Basis:** Vertisol is unworkable when wet because it forms clods and the structure is damaged, and resists implements when bone dry. The usable window is a few days and judging it by hand is coarse.
- **Yield impact:** Indirect. Protects soil structure and prevents lost operating days in a tight pre-season calendar.
- **References:** Domain 2 vertisol behaviour; Core C3

### D09

**D09-HV-004** (HV, info, conf 0.6, tier B) · _executable_

- **Trigger:** Harvest scheduling  
  `days_to_harvest BETWEEN 0 AND 2 AND air_temp_max_c > 33`
- **Action (EN):** Prefer early morning harvest. Rhizomes are cooler, dehydration is lower and the crew works in less heat.
- **कृती (MR):** सकाळी लवकर काढणी करा. गड्डे थंड राहतात, पाणी कमी उडते, आणि मजुरांना उन्हाचा त्रास कमी होतो.
- **Basis:** Not stated in any source. Reasoned from field temperature and dehydration behaviour, and from labour productivity in a belt recording maxima near 46 C.
- **Yield impact:** Marginal, but free.
- **References:** reasoned; no source

**D09-MT-001** (MT, info, conf 0.82, tier B) · _executable_

- **Trigger:** dap at or above 200  
  `dap > 200 AND skin_scrape_result IS NULL`
- **Action (EN):** Use the skin scrape test as the primary maturity indicator. Dig a rhizome and rub the skin with the thumb. Peels easily means immature; firmly attached means mature. This is more reliable than counting days.
- **कृती (MR):** गड्डा उकरून अंगठ्याने साल घासा. साल सहज निघते म्हणजे अपक्व; साल घट्ट बसलेली म्हणजे पक्व. ही चाचणी दिवस मोजण्यापेक्षा जास्त विश्वासार्ह आहे आणि तिला कोणतेही उपकरण लागत नाही.
- **Basis:** Maturity varies with variety, season and planting date, so day count drifts. Skin corking is a direct physiological indicator of the process that determines storability and dry recovery.
- **Yield impact:** Premature harvest carries u = 0.10 to 0.15 plus much larger storage losses.
- **References:** Tractorkarvan; CropLibrary; ICAR-AICRP

### D13

**D13-RP-003** (RP, info, conf 0.78, tier A) · _executable_

- **Trigger:** First season AND no own seed exists  
  `dap BETWEEN 178 AND 184 AND seed_retained_or_purchased IS NULL`
- **Action (EN):** Purchase is unavoidable, and it is also the opportunity to obtain the recommended variety. From the second season, mark healthy plants at 180 DAP while the crop is still green and run the comparison then.
- **कृती (MR):** पहिल्या हंगामात खरेदी अपरिहार्य आहे — आणि तीच शिफारसीत जात मिळवण्याची संधी आहे. दुसऱ्या हंगामापासून १८० दिवसांना पीक हिरवे असतानाच निरोगी रोपे खुणावून ठेवा, आणि मग तुलना करा.
- **Basis:** Seed selection is a mid-season observation task disguised as a post-harvest one — vigour and disease freedom are only visible on the standing crop. So the decision to retain has to be taken at 180 DAP, not at harvest.
- **Yield impact:** Affects the following season's seed quality and cost.
- **References:** Domain 1 seed selection reminder; Domain 9 post-harvest seed separation

**D13-RR-001** (RR, info, conf 0.78, tier B) · _executable_

- **Trigger:** Risk assessment before planting  
  `days_to_planting BETWEEN 85 AND 95`
- **Action (EN):** Present all ten risks with their impact and mitigation, and separate the four that are entirely avoidable — late planting, earthing up missed, produce not graded, and seed ordered late.
- **कृती (MR):** दहाही जोखमी परिणाम व उपायांसह मांडा, आणि पूर्णपणे टाळता येणाऱ्या चार वेगळ्या दाखवा — उशिरा लागवड, उटाळणी चुकणे, प्रतवारी न करणे, आणि बेणे उशिरा मागवणे.
- **Basis:** Six of the ten risks can only be mitigated, not eliminated. Four can be removed entirely, and separating them directs attention to where control actually exists.
- **Yield impact:** The four avoidable risks are worth Rs 50,000 to over a lakh per acre per season.
- **References:** Domain 13 risk register

**D13-RR-002** (RR, info, conf 0.78, tier B) · _executable_

- **Trigger:** The advisory system's value is being quantified  
  `harvest_date IS NOT NULL AND action_compliance_rate IS NOT NULL`
- **Action (EN):** Use the four avoidable risks. All four depend on a timely reminder and their combined value is Rs 50,000 to over a lakh per acre per season. The machine does not make fertiliser, bring rain or kill pathogens — it reminds at the right time.
- **कृती (MR):** चार टाळता येणाऱ्या जोखमी वापरा. चारही वेळेवर आठवणीवर अवलंबून आहेत आणि त्यांचे एकत्रित मूल्य एकरी प्रति हंगाम ५०,००० ते एक लाखाहून जास्त आहे. यंत्र खत बनवत नाही, पाऊस आणत नाही, रोग मारत नाही — ते वेळेवर आठवण देते.
- **Basis:** Late planting carries u = 0.20, earthing up 0.125, grading a 2.7 times price spread, and late seed ordering forfeits the variety choice worth 0.138. Three of the four cost nothing to avoid and the fourth costs about Rs 6,000 in labour.
- **Yield impact:** None directly. It is the clearest defensible statement of what a timing engine is worth.
- **References:** Domain 13 avoidable risks; Domain 11 economic conversion; Domain 12 positioning

### D14

**D14-AN-001** (AN, info, conf 0.85, tier A) · _executable_

- **Trigger:** Regional baseline is available AND peer baseline has fewer than 3 contributing plots  
  `plot_ndvi_baseline_regional IS NOT NULL AND (plot_ndvi_baseline_peer IS NULL OR plot_area_ha >= 0.10)`
- **Action (EN):** Set anomaly-mode = REGIONAL or REGIONAL+PEER. NV-003 always fires when in scope; NV-005 fires only when peer baseline is populated with 3 or more plots.
- **कृती (MR):** anomaly-mode = REGIONAL किंवा REGIONAL+PEER निर्धारित करा. NV-003 नेहमी लागू; NV-005 फक्त peer baseline मध्ये ३+ plots असल्यास.
- **Basis:** Cluster-peer baselines mature in season 1; before that regional is all we have.
- **Yield impact:** Routing rule, no direct yield.
- **References:** RAW MASTER §9.1

**D14-AN-002** (AN, info, conf 0.85, tier A) · _executable_

- **Trigger:** Plot area is below the informational-only threshold OR NDVI standard deviation across plot exceeds 0.15  
  `plot_area_ha < 0.05 OR ndvi_std > 0.15`
- **Action (EN):** Set plot_advisory_class = INFORMATIONAL_ONLY. NV/NR/NM/LT rules can still fire but their delivery downgrades to EVENT with 'informational' severity. Farmer app labels the message with a plot-size note explaining the reduced confidence.
- **कृती (MR):** plot_advisory_class = INFORMATIONAL_ONLY. NV/NR/NM/LT नियम चालू शकतात पण delivery EVENT + 'informational' severity ला उतरते. शेतकऱ्याच्या app मध्ये लहान प्लॉटमुळे कमी विश्वास असल्याची स्पष्ट नोंद दिसते.
- **Basis:** A 4-6 pixel plot has more edge than interior; a mean is dominated by mixed pixels.
- **Yield impact:** Prevents low-quality advisory from driving action.
- **References:** RAW MASTER §11.1

**D14-AN-003** (AN, info, conf 0.8, tier B) · _executable_

- **Trigger:** It is within the first 20 days after monsoon onset AND NDVI has risen sharply  
  `monsoon_days_since_onset BETWEEN 0 AND 20 AND ndvi_delta_10d > 0.15 AND STAGE IN [G0, G1, G2]`
- **Action (EN):** Set an internal flag: recent_ndvi_rise_may_be_weeds = TRUE. Any AN rule that would treat NDVI rise as a positive-anomaly signal checks this flag and stays silent for the flush window.
- **कृती (MR):** अंतर्गत ध्वज नोंदवा — recent_ndvi_rise_may_be_weeds = TRUE. NDVI वाढ चांगली अनियमितता म्हणून हाताळणारे AN नियम हा ध्वज तपासतील आणि weed-flush खिडकीत शांत राहतील.
- **Basis:** Post-monsoon weed emergence in Marathwada is intense in the two weeks after onset. Historically documented.
- **Yield impact:** False-alarm prevention; indirect.
- **References:** RAW MASTER §4.5, §9.3; Marathwada agronomy field notes

**D14-AN-004** (AN, info, conf 0.85, tier A) · _executable_

- **Trigger:** A farmer scout report has arrived on a plot where a satellite anomaly is open  
  `scout_request_pending IS FALSE AND farmer_scout_report_days_ago IS NOT NULL AND farmer_scout_report_days_ago <= 3`
- **Action (EN):** Read the scout report. If it confirms a specific cause, escalate that cause through its home domain (D03/D04/D06). If it clears the plot, close the satellite anomaly. Log the resolution against the anomaly rule that opened it.
- **कृती (MR):** scout अहवाल वाचा. विशिष्ट कारण पुष्टी झाल्यास त्याच्या मूळ डोमेनमार्फत (D03/D04/D06) escalate करा. प्लॉट मोकळा असल्याची पुष्टी झाल्यास उपग्रह अनियमितता बंद करा. निराकरण मूळ नियमाशी जोडून log करा.
- **Basis:** Section 8.4 double-signal principle. Satellite opens an investigation; ground truth closes it.
- **Yield impact:** Closure tracking; indirect.
- **References:** RAW MASTER §8.4; Domain 6 differential architecture

**D14-DP-002** (DP, info, conf 0.9, tier A) · _executable_

- **Trigger:** A satellite product is being displayed to any user AND attribution has not yet been rendered on the current view  
  `sat_source IS NOT NULL AND sat_attribution_shown IS FALSE`
- **Action (EN):** Ensure the UI renders the required attribution before the satellite product is shown. Block if the UI cannot render attribution.
- **कृती (MR):** उपग्रह उत्पादन दाखवण्यापूर्वी UI ने आवश्यक श्रेय रेंडर करावे. UI ते रेंडर करू शकत नसल्यास प्रदर्शन थांबवा.
- **Basis:** Every displayed satellite product carries a licence-compliance attribution requirement (Copernicus, USGS, Bhuvan, Planet). RAW MASTER Section 13.7 specifies the exact wording for each source. Silent guard enforces the UI-side template before the product renders to any user.
- **Yield impact:** None; regulatory.
- **References:** RAW MASTER §13.7; Copernicus attribution requirement

**D14-FU-001** (FU, info, conf 0.68, tier B) · _executable_

- **Trigger:** Sub-node moisture is stale AND satellite indicates canopy stress  
  `sub_node_moisture_status == 'stale' AND (ndmi_delta_10d <= -0.10 OR cwsi > 0.60) AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Send an INVESTIGATIVE advisory: 'Sub-node reading not received recently. Satellite view shows canopy stress. Please visit the plot and check moisture manually.' Priority: high; delivery: ONCE_UNTIL_RESOLVED. Do NOT auto-schedule irrigation.
- **कृती (MR):** तपासणी सल्ला पाठवा: 'सब-नोडची अलीकडची नोंद मिळाली नाही. उपग्रह दृश्यात पर्णसमूह ताण दिसतो. कृपया प्लॉटवर जाऊन हाताने ओलावा तपासा.' प्राधान्य: उच्च; delivery: ONCE_UNTIL_RESOLVED. स्वयंचलित सिंचन ठरवू नका.
- **Basis:** Section 10 case E — one input silent, the other present. The living response is to have a human look, not to guess.
- **Yield impact:** Under D03/D06 confirmed downstream.
- **References:** RAW MASTER §10.2 case E

**D14-FU-002** (FU, info, conf 0.75, tier B) · _executable_

- **Trigger:** Sub-node moisture reads low AND satellite canopy looks healthy AND advisory confidence at least 0.5  
  `sub_node_moisture_status == 'low' AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Tag D03 irrigation rule with 'early_action_window'. Do NOT emit a separate message. D03's own irrigation rule fires with its own message and takes credit for the action; this rule contributes a leading-indicator confidence increment.
- **कृती (MR):** D03 सिंचन नियमाला 'early_action_window' tag जोडा. वेगळा संदेश देऊ नका. D03 चा स्वतःचा सिंचन नियम त्याच्या संदेशासह चालतो; हा नियम फक्त leading-indicator विश्वास वाढवतो.
- **Basis:** Section 10 case B — the sub-node is the authority, and the satellite is a leading confidence indicator.
- **Yield impact:** Under D03.
- **References:** RAW MASTER §10.2 case B

**D14-FU-003** (FU, info, conf 0.72, tier B) · _executable_

- **Trigger:** SAR indicates surface standing water AND sub-node moisture reads adequate  
  `sar_vv_delta_db < -3.0 AND sub_node_moisture_status == 'adequate' AND sar_gap_days <= 12`
- **Action (EN):** Send an ADVISORY (not URGENT): 'Satellite shows standing water on part of your plot. Root-zone moisture is still normal. Check surface drainage — likely a blocked furrow or edge that needs clearing before the next rain.' Delivery: EVENT.
- **कृती (MR):** सल्ला पाठवा (URGENT नाही): 'उपग्रहावर तुमच्या प्लॉटच्या भागावर पाणी साचलेले दिसते. रूट-झोन ओलावा अजून सामान्य आहे. पुढच्या पावसाआधी बंद पडलेला वाफा किंवा कडा साफ करा.' Delivery: EVENT.
- **Basis:** Section 10 case F — sub-node monitors depth, satellite monitors surface. Both true, different problems.
- **Yield impact:** Preventive; averts full waterlogging.
- **References:** RAW MASTER §10.2 case F; ICAR-CRIDA drainage studies

**D14-FU-004** (FU, info, conf 0.65, tier B) · _executable_

- **Trigger:** Sub-node EC reads normal AND satellite NDRE is below expected in closed canopy  
  `sub_node_ec_status == 'normal' AND current_stage IN [G3, G4] AND plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Dispatch D04 leaf-tissue test scheduling. Do not recommend a specific micro-nutrient without the test.
- **कृती (MR):** D04 पर्ण-ऊतक चाचणी नियोजनाकडे पाठवा. चाचणीशिवाय विशिष्ट सूक्ष्म-अन्नद्रव्य शिफारस करू नका.
- **Basis:** Bulk EC misses localised deficiencies of Zn, Fe, Mn — which the leaf-side NDRE picks up.
- **Yield impact:** Under D04.
- **References:** RAW MASTER §10.2 case G; Marathwada Zn deficiency literature

**D14-FU-005** (FU, info, conf 0.82, tier A) · _executable_

- **Trigger:** Sub-node moisture adequate AND EC normal AND all satellite indices in healthy band  
  `sub_node_moisture_status == 'adequate' AND sub_node_ec_status == 'normal' AND ndvi_mean >= 0.45 AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND sat_advisory_confidence >= 0.5`
- **Action (EN):** Log a plot_health_green_flag entry with timestamp and contributing evidence. No farmer message. Used by season-review, buyer attestation, and DPDP consent-limited third-party sharing.
- **कृती (MR):** plot_health_green_flag नोंद वेळेसह व पुराव्यासह log करा. शेतकऱ्याला संदेश नाही. हंगाम-आढावा, खरेदीदार-प्रमाणीकरण व DPDP-अनुमत तृतीय-पक्ष सामायिकीकरणासाठी वापर.
- **Basis:** Section 10 case H. High-confidence positive attestation is a business asset.
- **Yield impact:** Indirect — attestation value.
- **References:** RAW MASTER §10.2 case H

**D14-LT-001** (LT, info, conf 0.75, tier A) · _executable_

- **Trigger:** A Landsat-8 or Landsat-9 Collection-2 Level-2 ST band scene is received AND cluster air temperature is present  
  `sat_source IN ['landsat-8', 'landsat-9'] AND air_temp_max_c IS NOT NULL`
- **Action (EN):** Store lst_c from the ST band. Compute CWSI using Idso formulation with author-estimated wet/dry baselines. Log baseline set version. CWSI values above 1.0 or below 0 are clipped to [0,1].
- **कृती (MR):** ST band वरून lst_c साठवा. Idso सूत्राने CWSI मोजा — Phase-1 च्या तात्पुरत्या baselines सह. baseline सेट आवृत्ती log करा. [०,१] बाहेरील मूल्ये clip करा.
- **Basis:** Landsat is currently the only free thermal at 100 m; MODIS at 1 km is too coarse. The 8-day combined revisit is thin but acceptable as confirmation channel.
- **Yield impact:** Enables LT-002/003.
- **References:** USGS Landsat Collection-2 Level-2 documentation; Idso et al. 1981; RAW MASTER §7

**D14-LT-003** (LT, info, conf 0.78, tier B) · _executable_

- **Trigger:** CWSI is above 0.60 AND sub-node moisture reads low AND advisory confidence is at least 0.5  
  `cwsi > 0.60 AND sub_node_moisture_status == 'low' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Tag active D03 irrigation rule with 'thermal_confirms'. Do not emit separate message.
- **कृती (MR):** सक्रिय D03 सिंचन नियमाला 'thermal_confirms' tag जोडा. वेगळा संदेश देऊ नका.
- **Basis:** Section 10 case C confirmed thermally. Both sub-node moisture and canopy transpiration signal the same water shortage; thermal confirmation raises D03's own irrigation rule from moderate to strong confidence. This is the archetypal high-confidence green flag for a real water stress episode.
- **Yield impact:** Confidence increment.
- **References:** RAW MASTER §10.2 case C

**D14-NM-001** (NM, info, conf 0.85, tier A) · _executable_

- **Trigger:** A cloud-clear Sentinel-2 scene is received AND B11 SWIR is valid  
  `sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15`
- **Action (EN):** Compute ndmi_mean = (B8 - B11) / (B8 + B11). Compute ndmi_delta_10d against value from ten days ago.
- **कृती (MR):** ndmi_mean = (B8 - B11) / (B8 + B11) मोजा. १० दिवसांपूर्वीच्या मूल्याच्या तुलनेत ndmi_delta_10d नोंदवा.
- **Basis:** NDMI is the reflectance-side canopy moisture indicator and is available every cloud-clear Sentinel-2 scene, unlike CWSI which needs Landsat thermal timing.
- **Yield impact:** Enables NM-002/003.
- **References:** Gao 1996; RAW MASTER §4.1, §7.5

**D14-NM-003** (NM, info, conf 0.8, tier B) · _executable_

- **Trigger:** NDMI has dropped 0.10 or more over 10 days AND sub-node moisture reads low AND advisory confidence is at least 0.5  
  `ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == 'low' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]`
- **Action (EN):** Do not emit a separate message. Contribute a confidence-tag ('canopy_moisture_confirms') to whichever D03 irrigation rule is currently active for this plot. This upgrades D03's own alert from moderate to strong confidence. If no D03 rule is currently active, log a tag for the next one that fires.
- **कृती (MR):** स्वतंत्र संदेश देऊ नका. सध्या सक्रिय असलेल्या D03 सिंचन नियमाला 'canopy_moisture_confirms' हा confidence-tag जोडा. D03 चा सल्ला मध्यम पासून प्रबळ विश्वासाला वाढवा. D03 चा कोणताही नियम सध्या सक्रिय नसल्यास पुढच्यासाठी tag नोंदवा.
- **Basis:** Section 10 case C — both signals agree. The canonical high-confidence green flag for the sub-node's water shortage story.
- **Yield impact:** Confidence increment on existing D03 rule; no separate u-value.
- **References:** RAW MASTER §10.2 case C; Domain 3 irrigation rules

**D14-NR-001** (NR, info, conf 0.85, tier A) · _executable_

- **Trigger:** A cloud-clear Sentinel-2 scene is received AND red-edge bands B5, B6, B7 are valid  
  `sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15`
- **Action (EN):** Compute ndre_mean = (B8 - B5) / (B8 + B5) over valid pixels. Compute ndre_slope_5d as the slope of the last 5 days of NDRE values. Store both.
- **कृती (MR):** ndre_mean = (B8 - B5) / (B8 + B5) वैध पिक्सेल्सवर मोजा. मागील ५ दिवसांतील NDRE मूल्यांवरून ndre_slope_5d मोजा.
- **Basis:** Red-edge stays sensitive to canopy chlorophyll well past the saturation point of NDVI (LAI ~ 3.5). Necessary for closed-canopy nitrogen work.
- **Yield impact:** Enables NR-002/003.
- **References:** Gitelson & Merzlyak 1996; RAW MASTER §4

**D14-NV-001** (NV, info, conf 0.9, tier A) · _executable_

- **Trigger:** A cloud-clear Sentinel-2 scene is received for the plot AND scene_valid_pixel_pct is at least 60  
  `sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15`
- **Action (EN):** Compute and store ndvi_mean, ndvi_std, evi_mean, savi_mean using the standard Sentinel-2 L2A band arithmetic (NDVI = (B8-B4)/(B8+B4)). Log scene id and pipeline version. Do not emit anything to the farmer app; this rule is a pipeline hook, not a message.
- **कृती (MR):** ndvi_mean, ndvi_std, evi_mean, savi_mean यांची गणना करून नोंदवा. दृश्याचा id व pipeline version log करा. शेतकऱ्याला कोणतीही सूचना पाठवू नका — हा फक्त pipeline hook आहे.
- **Basis:** Cloud-clear valid-pixel gating is required before any index is trustworthy. Values below 60% valid pixels give a plot mean dominated by mask edges; above 60% is the industry consensus for smallholder analysis. See RAW MASTER §4 and §12.4.
- **Yield impact:** None directly. Enables every downstream NV, AN, and PH rule.
- **References:** ESA Sentinel-2 L2A product specification; Rouse et al. 1974 (NDVI); RAW MASTER Domain 14 §4

**D14-NV-002** (NV, info, conf 0.85, tier A) · _executable_

- **Trigger:** ndvi_freshness_days exceeds the confidence-full threshold — degrade advisory confidence  
  `ndvi_freshness_days > 5 AND ndvi_freshness_days <= 20`
- **Action (EN):** Compute sat_advisory_confidence = max(0, 1 - (ndvi_freshness_days - 5) / 15). Downstream NV/NR/NM/AN rules multiply their base confidence by this scalar before delivery. This is the same pattern as D07 station_data_age_hours degradation.
- **कृती (MR):** sat_advisory_confidence = max(0, 1 - (ndvi_freshness_days - 5) / 15) या सूत्राने गणना करा. NV/NR/NM/AN नियम delivery पूर्वी त्यांचा base confidence याने गुणतील. D07 station_data_age_hours degradation प्रमाणे.
- **Basis:** A plot state that was valid 3 days ago is still probably valid; a state valid 15 days ago is not. Linear degradation is the honest simplification.
- **Yield impact:** None directly. Protects downstream advisory quality.
- **References:** RAW MASTER §3.4 working definitions; D07 station_data_age_hours pattern

**D14-NV-006** (NV, info, conf 0.8, tier B) · _executable_

- **Trigger:** It is 5 to 30 days before planned planting AND plot NDVI exceeds the pre-plant bare-soil threshold  
  `days_to_planting BETWEEN 5 AND 30 AND ndvi_mean > 0.25 AND scene_valid_pixel_pct >= 60`
- **Action (EN):** Send an ADVISORY (not alarm) to the farmer: satellite view shows green vegetation on the plot 15-30 days before your planned planting. Verify — this is likely weed flush or uncleared residue. Land preparation instructions from D02 apply. If it is inter-crop cover (green manure being incorporated), no action is needed — reply to close the advisory.
- **कृती (MR):** शेतकऱ्याला सूचना पाठवा (धोक्याची घंटा नाही): नियोजित लागवडीच्या १५-३० दिवस आधी उपग्रह दृश्यात प्लॉटवर हिरवी वनस्पती दिसते. तपासा — बहुधा तण किंवा मागील पिकाचे कचरे. D02 चे भूमी-तयारीचे सल्ले लागू. हिरवळीचे खत (green manure) मुद्दाम पेरले असेल तर कारवाईची गरज नाही — reply देऊन सूचना बंद करा.
- **Basis:** Bare-soil NDVI in Kannad basaltic soils is 0.10-0.20. Anything above 0.25 in a supposedly bare plot has active vegetation.
- **Yield impact:** Land-preparation quality — grouped under D02 preparation compliance.
- **References:** RAW MASTER §4.2, §4.5; ISRO NRSC bare-soil reference

**D14-PH-001** (PH, info, conf 0.75, tier A) · _executable_

- **Trigger:** The plot has at least 8 NDVI observations across the season AND DAP is at least 60  
  `dap >= 60 AND ndvi_freshness_days <= 20`
- **Action (EN):** Fit double-logistic to NDVI series with 4 parameters (greenup mid, senescence mid, amplitude, background). Store fitted stage-transition dates for cross-check against DAP-driven stage.
- **कृती (MR):** NDVI मालिकेवर ४-पॅरामीटर double-logistic fit करा (greenup mid, senescence mid, amplitude, background). DAP-आधारित अवस्थेच्या तुलनेसाठी fit केलेल्या अवस्था-संक्रमण तारखा साठवा.
- **Basis:** Curve fit gives a phenology view independent of farmer-reported planting date; catches planting-date misreports.
- **Yield impact:** Enables PH-002.
- **References:** Zhang et al. 2003; RAW MASTER §8.2

**D14-PH-002** (PH, info, conf 0.72, tier B) · _executable_

- **Trigger:** Curve-fit-estimated stage differs from DAP-derived stage by at least one step  
  `dap >= 60 AND ndvi_freshness_days <= 20`
- **Action (EN):** Compare fitted stage vs DAP-derived stage. If they differ by one or more steps, dispatch a verification ask to the farmer: 'Please confirm the planting date on record is correct.' D01 records the response and, if planting date changes, rebuilds the stage series.
- **कृती (MR):** fit केलेली अवस्था व DAP-आधारित अवस्थेची तुलना करा. एक किंवा अधिक step ने वेगळ्या असल्यास शेतकऱ्याला पडताळणी विनंती पाठवा: 'नोंदवलेली लागवडीची तारीख बरोबर आहे का याची पुष्टी द्या.' D01 उत्तर नोंदवते आणि गरजेनुसार stage series पुन्हा बांधते.
- **Basis:** Wrong planting date breaks every stage-conditioned rule downstream; catching it early saves an entire season of miscalibrated advisories.
- **Yield impact:** Prevents downstream u_value miscount rather than adding a new one.
- **References:** Sakamoto et al. 2010; RAW MASTER §8.2, §8.4

**D14-PL-001** (PL, info, conf 0.95, tier A) · _executable_

- **Trigger:** Plot polygon geometry is missing or fails validation  
  `plot_polygon_wkt IS NULL OR plot_area_ha IS NULL`
- **Action (EN):** Suspend all D14 rules for this plot. Send a low-priority prompt to the farmer app requesting plot boundary capture. Restore when polygon is provided.
- **कृती (MR):** या प्लॉटवरील सर्व D14 नियम स्थगित करा. शेतकऱ्याच्या app वर कमी-प्राधान्य विनंती पाठवा — प्लॉट सीमा नोंदवा. Polygon दिल्यावर पुन्हा सक्रिय.
- **Basis:** Precondition rule. Every satellite advisory rule in Domain 14 requires a valid plot polygon; without one the pixel extract, all indices, all baselines and all anomaly detections are meaningless. Failing closed with a farmer-side prompt is the honest response.
- **Yield impact:** None; enables all downstream.
- **References:** RAW MASTER §12.4

**D14-PL-002** (PL, info, conf 0.9, tier A) · _executable_

- **Trigger:** Both optical and SAR are stale beyond the maximum advisory freshness AND scout report is also older than 5 days  
  `optical_gap_days > 21 AND sar_gap_days > 12 AND (farmer_scout_report_days_ago IS NULL OR farmer_scout_report_days_ago > 5)`
- **Action (EN):** Set operating mode to BLIND_PLOT. Suspend NV/NR/NM/AN/FU rules. Send a high-priority prompt: 'We have not seen your plot from any source for over 3 weeks. Please visit and send a photo.' Reset when any source comes back.
- **कृती (MR):** operating mode = BLIND_PLOT. NV/NR/NM/AN/FU स्थगित. उच्च-प्राधान्य विनंती पाठवा: '३ आठवड्यांहून अधिक काळ आम्हाला तुमचा प्लॉट कोणत्याही स्रोतातून दिसलेला नाही. कृपया भेट देऊन फोटो पाठवा.' कोणताही स्रोत परत आल्यावर सामान्य मोड.
- **Basis:** Advisory in blindness is worse than no advisory.
- **Yield impact:** Prevents low-confidence action.
- **References:** RAW MASTER §12.4

**D14-PL-003** (PL, info, conf 0.9, tier A) · _executable_

- **Trigger:** Pipeline version has changed since the last stored indices  
  `sat_pipeline_version IS NOT NULL`
- **Action (EN):** Compare sat_pipeline_version to last stored version for the plot. If different, run baseline recomputation of ndvi_delta_10d, ndmi_delta_10d, ndre_slope_5d against the same pipeline version before any AN or PH rule fires. Log the migration event.
- **कृती (MR):** sat_pipeline_version प्लॉटवरील मागील साठवलेल्या आवृत्तीशी तुलना करा. वेगळी असल्यास AN किंवा PH नियम चालण्यापूर्वी त्याच आवृत्तीत ndvi_delta_10d, ndmi_delta_10d, ndre_slope_5d ची पुनर्गणना करा. migration घटना log करा.
- **Basis:** Trend analysis across pipeline versions is a known source of false anomalies in satellite pipelines.
- **Yield impact:** None; protects downstream.
- **References:** RAW MASTER §12.4

**D14-PL-004** (PL, info, conf 0.9, tier A) · _executable_

- **Trigger:** Scene valid pixel percentage is below the minimum trusted threshold  
  `scene_valid_pixel_pct < 60 AND sat_source == 'sentinel-2'`
- **Action (EN):** Skip index computation for the scene. Log 'scene_rejected_low_valid_pixel'. Do not update ndvi_freshness_days from this scene — treat as if the scene did not arrive.
- **कृती (MR):** दृश्यासाठी निर्देशांक गणना वगळा. 'scene_rejected_low_valid_pixel' log करा. या दृश्यावरून ndvi_freshness_days अद्ययावत करू नका — दृश्य आले नाही असे मानून पुढे जा.
- **Basis:** Bad scenes generate false anomalies; fail closed rather than fail loud.
- **Yield impact:** None; false alarm prevention.
- **References:** RAW MASTER §9.3

**D14-SR-001** (SR, info, conf 0.85, tier A) · _executable_

- **Trigger:** A Sentinel-1 GRD scene is received for the plot polygon  
  `sat_source == 'sentinel-1' AND sar_gap_days IS NOT NULL`
- **Action (EN):** Run the standard SNAP or Sentinel-Hub chain (orbit, noise removal, calibration, terrain flattening, speckle filter, terrain correction, multi-look over polygon). Store sigma-nought values, compute RVI, delta_vv, and coherence against the last acquisition from the same relative orbit.
- **कृती (MR):** मानक SNAP किंवा Sentinel-Hub साखळी चालवा. सिग्मा-नॉट मूल्ये साठवा; RVI, delta_vv, आणि coherence त्याच relative orbit च्या मागील acquisition विरुद्ध मोजा.
- **Basis:** SAR is monsoon-primary for Kannad ginger — it is the only satellite signal available with reasonable frequency in Jul-Aug when optical is blinded.
- **Yield impact:** Enables all SR rules and the monsoon SAR-only mode PL-001.
- **References:** ESA Sentinel-1 handbook; RAW MASTER §6

**D14-SR-003** (SR, info, conf 0.68, tier B) · _executable_

- **Trigger:** SAR coherence between the last two same-orbit acquisitions has dropped below 0.4 AND stage is G4 or later AND rainfall in the last 48 hours is under 20 mm  
  `sar_coherence < 0.4 AND STAGE IN [G4, G5] AND rainfall_last_48h_mm < 20 AND sar_gap_days <= 12`
- **Action (EN):** Log a probable-harvest event on the plot. Prompt the farmer (LOW priority, EVENT delivery) to confirm the harvest date and record yield if actually harvested. If not harvesting, ask what mechanical activity happened — the operations team may want to know.
- **कृती (MR):** प्लॉटवर संभाव्य काढणी घटना नोंदवा. शेतकऱ्याला LOW priority ने विचारा — काढणी सुरू आहे का, तारीख व उत्पन्न नोंदवा. काढणी नसेल तर काय यांत्रिक क्रिया झाली विचारा.
- **Basis:** Coherence between two same-orbit acquisitions falls when the scattering surface changes. Harvest of a ginger plot is one such change; so is deep tillage or heavy foot traffic.
- **Yield impact:** Compliance and yield-tracking data collection. No direct treatment.
- **References:** Bamler & Hartl 1998 InSAR coherence; RAW MASTER §6.5

**D14-SR-004** (SR, info, conf 0.75, tier B) · _executable_

- **Trigger:** SAR VV delta exceeds ±2 dB between two consecutive same-orbit acquisitions AND rainfall in the same window is at least 10 mm  
  `(sar_vv_delta_db > 2.0 OR sar_vv_delta_db < -2.0) AND rainfall_last_48h_mm >= 10 AND sar_gap_days <= 12`
- **Action (EN):** Tag rainfall_last_48h_mm with confidence flag 'confirmed_by_sar'. No message. This upgrades D07's forecast bias record with an in-situ confirmation, useful for BC series over time.
- **कृती (MR):** rainfall_last_48h_mm ला 'confirmed_by_sar' विश्वास ध्वज जोडा. संदेश नाही. D07 चा forecast bias रेकॉर्ड यामुळे अधिक अचूक बनतो.
- **Basis:** The cluster weather station covers ~1-2 km reliably; convective monsoon cells can land on one plot and miss the station.
- **Yield impact:** Bias-correction data quality; indirect.
- **References:** RAW MASTER §6.3; Domain 7 BC series

**D14-SR-005** (SR, info, conf 0.85, tier A) · _executable_

- **Trigger:** Optical gap has exceeded 14 days AND a Sentinel-1 acquisition is fresh (sar_gap_days at most 6)  
  `optical_gap_days > 14 AND sar_gap_days <= 6`
- **Action (EN):** Set operating mode to SAR_ONLY for this plot. Suppress NV-003/004/005, NR-002/003, NM-002/003 for the duration. Continue SR-001 through SR-004. Reset when optical_gap_days drops below 10.
- **कृती (MR):** प्लॉटला SAR_ONLY मोडमध्ये ठेवा. NV-003/004/005, NR-002/003, NM-002/003 तात्पुरते बंद करा. SR-001 ते SR-004 चालू ठेवा. optical_gap_days १० पेक्षा कमी झाल्यावर सामान्य मोडवर परत या.
- **Basis:** Kannad Jul-Aug delivers exactly this pattern for weeks at a time; ignoring it produces stale-optical false alarms.
- **Yield impact:** Prevents false-alarm-driven interventions.
- **References:** RAW MASTER §3.2, §12.4

## P3 — advisory / policy / computational (surfaced by context) — 237 rules

### D01

**D01-VR-003** (VR, red, conf 0.92, tier A)

- **When:** Farmer intends to retain own seed AND field_history_rot or field_history_wilt is true
- **Action (EN):** Advise strongly against retaining seed from this plot, regardless of the cost comparison. Ralstonia survives in soil for many years and travels with planting material.
- **कृती (MR):** या प्लॉटवर कंदकूज किंवा मर रोगाची नोंद असल्याने इथून बेणे राखू नये. खर्चाचा फायदा एका रोग-प्रवेशापुढे टिकत नाही.
- **Basis:** Bacterial wilt bacterium is notorious for persisting in soil for many years and has a wide host range. Seed rhizome is the primary introduction vector for both wilt and soft rot.
- **Yield impact:** Prevents u = 0.30 to 0.70 in the following season.
- **References:** Springer - Journal of Plant Pathology 2020, bacterial wilt review; Core C13.5

### D02

**D02-LY-001** (LY, red, conf 0.9, tier A)

- **When:** soil_type is vertisol AND has_drip is true AND planting_layout is not broad_ridge
- **Action (EN):** Require broad ridge layout. The official recommendation names this method specifically for black soils and for fields using drip or sprinkler, and records 15 to 20 percent higher yield than the alternatives.
- **कृती (MR):** रुंद वरंबा किंवा गादी वाफा पद्धत वापरा. काळ्या जमिनी आणि ठिबक-तुषार वापरल्या जाणाऱ्या ठिकाणी हीच पद्धत शिफारसीत आहे, आणि इतर पद्धतींपेक्षा १५ ते २०% जास्त उत्पादन मिळते.
- **Basis:** Both qualifying conditions are met at Kannad — the soil is black and drip is a precondition for the crop here. The method raises the root zone above standing water and suits single-line drip.
- **Yield impact:** u = 0.167 for not using it, derived from the recorded 20 percent gain.
- **References:** Agrowon - Dr. Jitendra Kadam

**D02-OM-002** (OM, red, conf 0.85, tier A)

- **When:** FYM application scheduled AND fym_fully_decomposed is false or unknown
- **Action (EN):** Verify decomposition before applying. Criteria: dark brown to black, no smell, original material no longer recognisable. If half-decomposed, either let it decompose further or mix Metarhizium with it.
- **कृती (MR):** शेणखत पूर्ण कुजले आहे का तपासा — गडद तपकिरी किंवा काळे, वास नाही, मूळ पदार्थ ओळखू येत नाही. अर्धवट कुजलेले असल्यास आणखी कुजू द्या, किंवा मेटॅरायझियम मिसळा.
- **Basis:** White grub larvae feed first on organic matter in half-decomposed FYM and then move to roots. Decomposition heat also kills weed seed. So one condition addresses a pest problem and a weed problem simultaneously.
- **Yield impact:** u = 0.10 estimated for white grub damage traceable to undecomposed FYM.
- **References:** Agrowon - Mali & Mahajan, white grub

**D02-SL-001** (SL, red, conf 0.9, tier A)

- **When:** Soil is acidic, saline or sodic (chopan)
- **Action (EN):** Advise against ginger on this plot. These soil classes are explicitly excluded by the official recommendation.
- **कृती (MR):** आम्लधर्मी, खारवट किंवा चोपण जमिनीत आले घेऊ नये. अधिकृत शिफारस अशा जमिनी स्पष्टपणे वगळते.
- **Basis:** Official Maharashtra recommendation names these three soil classes as unsuitable. Ginger has no salinity tolerance and a shallow root system that cannot escape a bad surface layer.
- **Yield impact:** Not quantified in source. Treated as a plot-selection exclusion rather than a yield factor.
- **References:** Agrowon - Dr. Jitendra Kadam, Kasbe Digraj

**D02-SL-003** (SL, red, conf 0.85, tier A)

- **When:** previous_crops_3yr contains ginger, turmeric, potato, tomato, brinjal or chilli
- **Action (EN):** Warn that rotation requirement is not met. Ginger and turmeric share soil-borne pathogens; the solanaceous crops are hosts for bacterial wilt. Recommend a different plot if one is available.
- **कृती (MR):** फेरपालट पाळलेली नाही. हळद व आले एकाच कुळातील असल्याने त्यांचे soil-borne रोग सामाईक आहेत; बटाटा, टोमॅटो, वांगी, मिरची हे मर रोगाचे यजमान आहेत. शक्य असल्यास दुसरा प्लॉट निवडा.
- **Basis:** Continuous cropping raises infection risk from both Pythium and Ralstonia. Minimum recommended gap is three years, and the wilt bacterium can persist longer than that.
- **Yield impact:** u = 0.15 estimated for rotation failure alone; substantially higher if a wilt outbreak follows.
- **References:** Microbiology Spectrum / NCBI PMC9603371; Agrowon - Dr. Kadam

### D04

**D04-BI-002** (BI, red, conf 0.88, tier A)

- **When:** Biological treatment proposed AND chemical treatment same day or seed not dried
- **Action (EN):** Enforce the sequence: chemical treatment, then shade dry 3 to 6 hours, then biological treatment, then plant. Never simultaneously.
- **कृती (MR):** क्रम पाळा — आधी रासायनिक प्रक्रिया, मग सावलीत ३ ते ६ तास सुकवणे, मग जैविक प्रक्रिया, मग लागवड. एकाच वेळी करू नये.
- **Basis:** Fungicide kills Trichoderma and other biological cultures. Applying them together makes the biological step useless and wastes the input.
- **Yield impact:** Protects the value of both the seed treatment and the Trichoderma application.
- **References:** Agrowon - Dr. Kadam sequence; Domain 2 Trichoderma rule

### D05

**D05-RF-003** (RF, red, conf 0.85, tier A)

- **When:** soft_rhizome_found is true
- **Action (EN):** Act immediately. No threshold applies to this pest because symptoms appear only after the rhizome is already damaged. Escalate to the Domain 6 rot protocol simultaneously.
- **कृती (MR):** तात्काळ कृती करा. या किडीला सहनशीलता पातळी लागू होत नाही — लक्षण दिसेपर्यंत गड्डा आधीच खराब झालेला असतो. सोबतच कंदकूज प्रतिबंधक कृतीही सुरू करा.
- **Basis:** Once larvae have tunnelled, fungi and nematodes follow, the rhizome softens and exudes water, leaves yellow and the plant dries. In severe infestation the rhizome is consumed entirely.
- **Yield impact:** Entry point into the largest loss factor in the crop.
- **References:** Agrowon - Mali & Mahajan symptom sequence

**D05-WG-001** (WG, red, conf 0.85, tier A)

- **When:** FYM application scheduled AND fym_fully_decomposed is false or unknown
- **Action (EN):** Verify decomposition before applying. Half decomposed FYM is white grub larval food. If decomposition is incomplete, either wait or mix Metarhizium anisopliae 2 kg per acre into it.
- **कृती (MR):** शेणखत पूर्ण कुजले आहे का तपासा. अर्धवट कुजलेले शेणखत हे हुमणीच्या अळ्यांचे खाद्य आहे. पूर्ण कुजलेले नसल्यास आणखी कुजू द्या, किंवा मेटॅरायझियम २ किलो प्रति एकर मिसळा.
- **Basis:** Source states that white grub larvae initially feed on organic matter, specifically farmyard manure, and later gnaw roots. It gives the explicit instruction not to use half decomposed FYM.
- **Yield impact:** u = 0.10.
- **References:** Agrowon - Mali & Mahajan

### D06

**D06-BW-001** (BW, red, conf 0.9, tier A)

- **When:** field_history_wilt is true for this plot and the persistence window has not elapsed
- **Action (EN):** Warn clearly before replanting ginger or turmeric here. The bacterium persists in soil for many years. Recommend a different plot if one is available, and treat the standard three-year rotation as insufficient where wilt has actually been recorded.
- **कृती (MR):** या प्लॉटवर मर रोग नोंदवलेला आहे. हा जिवाणू जमिनीत अनेक वर्षे टिकतो. दुसरा प्लॉट उपलब्ध असल्यास तो निवडा. जिथे प्रत्यक्ष मर रोग आढळला आहे तिथे तीन वर्षांची फेरपालट पुरेशी मानू नये.
- **Basis:** Ralstonia is described as notorious for persisting in soil for many years and has a wide host range. Management strategies have met with limited success and it remains an enigma, so there is no reliable curative response once the crop is planted into infested soil.
- **Yield impact:** Prevents exposure to a 0.30 to 0.70 loss with no available treatment.
- **References:** Springer Journal of Plant Pathology 2020 soil persistence

**D06-ST-002** (ST, red, conf 0.88, tier A)

- **When:** Biological seed treatment proposed on the same day as chemical treatment, or without drying in between
- **Action (EN):** Enforce the sequence: chemical treatment, shade dry three to six hours, then biological treatment, then plant. Never simultaneously.
- **कृती (MR):** क्रम पाळा — आधी रासायनिक प्रक्रिया, मग सावलीत तीन ते सहा तास सुकवणे, मग जैविक प्रक्रिया, मग लागवड. एकाच वेळी करू नये.
- **Basis:** Fungicide kills Trichoderma and the other biological cultures. Applying them together makes the biological step useless and wastes the input, while appearing to have been done.
- **Yield impact:** Protects the value of both the seed treatment and the Trichoderma application.
- **References:** Agrowon - Dr. Jitendra Kadam seed treatment sequence

### D09

**D09-HV-002** (HV, red, conf 0.85, tier C)

- **When:** Harvest in progress
- **Action (EN):** Instruct that rhizomes must not be injured while lifting. Affected rhizomes soften and disintegrate during handling and storage, so a small wound now becomes a large loss in store.
- **कृती (MR):** गड्डे बाहेर काढताना इजा होणार नाही याची खबरदारी घ्या. इजा झालेले गड्डे हाताळणी व साठवणीत मऊ होऊन विरघळतात — आत्ताची छोटी जखम साठवणीत मोठे नुकसान बनते.
- **Basis:** Rot-affected rhizomes disintegrate during handling and storage. Mechanical injury at harvest creates exactly the wound that allows that, and by this point the whole season's cost is already spent.
- **Yield impact:** Prevents post-harvest loss on a fully committed investment.
- **References:** AgroWorld injury warning; Domain 6 storage rot

### D11

**D11-DC-001** (DC, red, conf 0.88, tier A)

- **When:** Two or more rules from different domains reference the same underlying factor
- **Action (EN):** Apply the u-value ONCE. Rules are written per domain but the yield computation is global. Twelve shared factors are named explicitly in the schema; check membership before applying any u-value.
- **कृती (MR):** u मूल्य एकदाच लागू करा. नियम Domain निहाय लिहिलेले आहेत पण उत्पादनाचे गणित एकत्रित आहे. बारा सामाईक घटक schema मध्ये स्पष्ट नावानिशी दिलेले आहेत — कोणतेही u मूल्य लागू करण्यापूर्वी ते तपासा.
- **Basis:** Cross-file audits found twelve factors appearing in more than one domain. Post-monsoon cyclonic saturation appears in three, the mulch programme in three, late planting in three, and the pre-harvest interval block in three. Each was written separately because each domain needed it, but the loss occurs once.
- **Yield impact:** Prevents systematic overstatement of avoidable loss, which would make every prediction pessimistic and every economic case overstated.
- **References:** Domain 11 double counting policy; cross-file audit findings

**D11-DC-002** (DC, red, conf 0.85, tier A)

- **When:** Factors that share a causal chain are being multiplied together
- **Action (EN):** Group them and apply the terminal u-value once. Do not multiply each link. Pest wound leading to rot, or FYM leading to weeds leading to weeding injury leading to rot, is one loss with several steps.
- **कृती (MR):** त्यांना एकत्र गटात घ्या आणि शेवटच्या टप्प्याचे u मूल्य एकदाच लावा — प्रत्येक दुवा वेगळा गुणू नका. किडीची जखम ते कूज, किंवा शेणखत ते तण ते खुरपणीतील इजा ते कूज — ही अनेक टप्प्यांची एकच घट आहे.
- **Basis:** The sub-additive formula assumes independence and in ginger the factors are not independent. Every major pest is a gateway to rot, and mechanical injury reaches the same endpoint without any pest. Multiplying each link counts the same rhizome loss several times.
- **Yield impact:** Prevents the largest source of overstatement, because the rot pathway is both the biggest u-value and the most connected.
- **References:** Domain 5 pest to rot chain; Domain 11 interdependence caveat

### D12

**D12-VOC-001** (VOC, red, conf 0.82, tier A)

- **When:** A language model or ASR system is being used with ginger terminology
- **Action (EN):** Supply the controlled vocabulary first. Ginger's Marathi technical terms are absent from general corpora, which are built from news and general text. A model that does not know utalni cannot record the operation.
- **कृती (MR):** आधी नियंत्रित शब्दकोश द्या. अद्रकाच्या मराठी तांत्रिक संज्ञा सामान्य corpora मध्ये नाहीत — ते वृत्तपत्रे आणि सामान्य मजकुरातून बनलेले आहेत. ज्या मॉडेलला 'उटाळणी' माहीत नाही ते ती नोंदच करू शकत नाही.
- **Basis:** Sangraha holds 251 billion tokens across 22 languages including Marathi, but from general sources. Utalni, hurde band, vafsa, ambavani and mokya are either absent or present in a different sense. The utalni case is concrete: unrecognised means unrecorded, unanswerable, and possibly misinterpreted — on a factor worth about Rs 56,500 per acre.
- **Yield impact:** Protects the recording of operations carrying u-values of 0.125 and above.
- **References:** AI4Bharat Sangraha; Domain 12 vocabulary gap

### D13

**D13-SRC-002** (SRC, red, conf 0.88, tier A)

- **When:** A variety yield figure is quoted in tonnes per acre from a non-institutional source
- **Action (EN):** Check the unit. The same source reports Varada at 15 to 18 tonnes per ACRE where institutional sources give 22.3 tonnes per HECTARE — a 2.47 times error that would be roughly double any recorded figure. Use institutional values.
- **कृती (MR):** एकक तपासा. त्याच स्रोतात वरदा जात १५ ते १८ टन प्रति एकर दिली आहे, तर संस्थात्मक स्रोतांत २२.३ टन प्रति हेक्टर — २.४७ पट फरक, आणि तो कोणत्याही नोंदवलेल्या आकड्याच्या जवळपास दुप्पट होईल. संस्थात्मक आकडे वापरा.
- **Basis:** Varada at 15 to 18 t/acre converts to 37 to 44 t/ha, roughly double the institutional record. Durations also disagree — 240 to 270 days in the blog against 200 to 210 institutionally. This is the same error made in Domain 1 version 2.0 and corrected in 2.1, found independently in a second source.
- **Yield impact:** Prevents a doubled yield expectation, which would propagate into fertiliser doses, water planning and the whole economic model.
- **References:** Agrowon institutional variety figures; Shetkari Marg variety table; Domain 1 version 2.1 correction

### D01

**D01-PH-004** (PH, yellow, conf 0.9, tier A)

- **When:** flowering_observed is true (हुरडे बांड)
- **Action (EN):** Re-anchor stage. Then CHECK earthing_up_date. If earthing-up has not been recorded, the window has closed — record a 12.5 percent yield penalty for Domain 11 gap attribution and inform the farmer plainly.
- **कृती (MR):** हुरडे बांड आले आहे. आता पानांची वाढ थांबून गड्ड्याची वाढ सुरू होते. उटाळणी झाली नसल्यास तिची मुदत संपली आहे आणि उत्पादनात १०-१५% घट गृहीत धरावी लागेल.
- **Basis:** Source states that after the flowering spike opens, leaf growth stops and rhizome growth begins. Earthing-up must precede this because it triggers new fibrous root formation, which needs time before bulking starts.
- **Yield impact:** u = 0.125. Skipping earthing-up costs 10-15 percent yield, roughly Rs 56,500 per acre at 113 q ceiling and Rs 4000/quintal.
- **References:** Agrowon - Dr. Kadam; AgroWorld

**D01-PH-005** (PH, yellow, conf 0.88, tier A)

- **When:** dap equals 35
- **Action (EN):** Request establishment count per running metre and record establishment_pct. This number sets the ceiling for the whole season.
- **कृती (MR):** उगवण मोजा — प्रति चालू मीटर किती रोपे उगवली. हा आकडा पुढील संपूर्ण उत्पादनाची कमाल मर्यादा ठरवतो. ८५% पेक्षा जास्त उत्तम; ७०% पेक्षा कमी असल्यास कारण शोधावे.
- **Basis:** Ginger has no ratoon and gap filling produces plants that never catch up. Establishment is therefore a hard ceiling, not a starting point.
- **Yield impact:** Directly proportional. A 70 percent establishment caps the season at 70 percent of potential regardless of later management.
- **References:** Springer seed treatment study germination figures; Domain 1 sprouting stage

**D01-PH-007** (PH, yellow, conf 0.8, tier B)

- **When:** dap equals 180
- **Action (EN):** Request destructive sample and weight, compared against the 120 DAP sample. Also trigger D01-VR-002 seed selection reminder. Set yield_prediction_interval_pct to 8 if done, 12 if skipped.
- **कृती (MR):** नमुना रोप उकरून वजन करा आणि मागील तपासणीशी तुलना करा. वजन जेमतेम वाढले असल्यास पालाश व ओलावा तपासा.
- **Basis:** Bulking rate between 120 and 180 DAP is the best available predictor of final yield, and there is no non-destructive substitute.
- **Yield impact:** Improves prediction accuracy by roughly one third. Does not change yield itself, but changes every decision that depends on the forecast.
- **References:** Domain 1 stage markers; Core C9.2

### D02

**D02-BF-001** (BF, yellow, conf 0.9, tier A)

- **When:** Land preparation reaching final stage
- **Action (EN):** Apply the full phosphorus and basal potassium dose now — 30 kg P and 30 kg K per acre. Nitrogen is NOT basal.
- **कृती (MR):** स्फुरद व पायाभूत पालाश यांची संपूर्ण मात्रा आत्ताच द्या — एकरी ३० किलो स्फुरद आणि ३० किलो पालाश. नत्र पायाभूत देऊ नये.
- **Basis:** Phosphorus is immobile and must be placed in the root zone before planting. All state recommendations agree on full basal P. Basal potassium is the first of three potassium applications; the remaining two follow in Domain 4.
- **Yield impact:** Part of the overall nutrition schedule; not separately quantified here.
- **References:** Agrowon - Dr. Kadam, 75:75 kg/ha P and K basal

**D02-BF-002** (BF, yellow, conf 0.8, tier B)

- **When:** Basal phosphorus scheduled AND soil_free_lime_pct is elevated
- **Action (EN):** Band the phosphorus rather than broadcasting it, and place it with organic matter. Do NOT increase the dose to compensate for fixation — the extra also gets fixed.
- **कृती (MR):** स्फुरद पसरून न देता पट्ट्यात द्या, आणि सेंद्रिय पदार्थासोबत द्या. चुनखडीमुळे स्फुरद स्थिर होतो म्हणून मात्रा वाढवू नये — वाढवलेलाही तेवढ्याच प्रमाणात स्थिर होतो. उत्तर मात्रा नाही, पद्धत आहे.
- **Basis:** In calcareous soil applied phosphorus binds with calcium into unavailable calcium phosphate. Banding reduces soil contact and therefore fixation; organic acids from decomposing matter keep more of it available; phosphate-solubilising bacteria release some of the fixed pool.
- **Yield impact:** Prevents wasted input rather than adding yield. Also explains why the Mahima-specific trial recommends lower phosphorus and higher potassium than the general schedule.
- **References:** Domain 2 fixation mechanism; Int. J. Adv. Biochem. Res. 2025, IISR Mahima NPK trial

**D02-CA-001** (CA, yellow, conf 0.85, tier A)

- **When:** soil_free_lime_pct is elevated OR soil_ph greater than 7.5
- **Action (EN):** Warn of expected persistent yellowing and yield decline. Schedule two foliar micronutrient sprays (45-60 and 75-90 DAP) as a SCHEDULED operation, not an optional suggestion. Increase FYM toward the upper end of the range.
- **कृती (MR):** चुनखडीयुक्त जमिनीत पीक येते पण पिवळसर छटा कायम राहते आणि उत्पादनात घट येते. सूक्ष्म अन्नद्रव्यांच्या दोन फवारण्या अनुसूचित कराव्यात — त्या ऐच्छिक नाहीत. शेणखताची मात्रा वरच्या टोकाला ठेवावी.
- **Basis:** High pH and free lime fix iron and zinc into unavailable forms. The nutrients are present in the soil but not available to the crop, so a soil test can read adequate while the plant is deficient. The same effect is documented for turmeric, which is in the same family.
- **Yield impact:** Source states yield declines but does not quantify. Related Domain 4 figure for missing the foliar spray is u = 0.11.
- **References:** Agrowon - Dr. Kadam; Krishi Jagran - turmeric calcareous soil

**D02-DR-004** (DR, yellow, conf 0.75, tier B)

- **When:** percolation_class is poor AND planting_layout is broad_ridge
- **Action (EN):** Increase bed height to the upper end of the range (30 cm) and widen furrows beyond 60 cm. Confirm the main drain has adequate fall to an outlet.
- **कृती (MR):** वाफ्याची उंची ३० सेंमीपर्यंत वाढवा आणि पाट ६० सेंमीपेक्षा रुंद करा. मुख्य चराला पुरेसा उतार असून तो शेताबाहेर मोकळा होतो याची खात्री करा.
- **Basis:** Bed height is the primary control on root-zone saturation. Where infiltration is slow, the standard height is not sufficient and the error is one-sided — excess height costs slightly more irrigation, insufficient height costs the crop.
- **Yield impact:** Modifies the drainage u-value of 0.15 to 0.30 downward.
- **References:** Agrowon - Bitle & Deshmukh 30 cm bed; Domain 2 percolation classes

**D02-LY-002** (LY, yellow, conf 0.88, tier A)

- **When:** planting_layout is broad_ridge AND bed geometry not yet set
- **Action (EN):** Set geometry: 120 cm cycle, 60 cm ridge width, 60 cm furrow width, height 25 to 30 cm, planting 22.5 x 22.5 cm, depth 4 to 5 cm, one drip line per bed with 2 lph drippers. Lay beds along the slope so water runs off.
- **कृती (MR):** १२० सेंमी अंतरावर सरी पाडा — मधील वरंबा ६० सेंमी रुंद, दोन वरंब्यांतील पाट ६० सेंमी, उंची २५ ते ३० सेंमी. लागवड २२.५ × २२.५ सेंमी अंतरावर, खोली ४ ते ५ सेंमी. एका वाफ्यावर एक ठिबक नळी, २ लिटर प्रति तास तोट्या. वाफे उताराला अनुसरून करा.
- **Basis:** Official height is 20 to 25 cm; a second Maharashtra source using drip specifies 30 cm. Both point the same way, and the error is one-sided — excess height costs a little more water, insufficient height costs the crop.
- **Yield impact:** Realises the 0.167 u-value captured by D02-LY-001.
- **References:** Agrowon - Dr. Kadam; Agrowon - Bitle & Deshmukh, Netafim

**D02-OM-001** (OM, yellow, conf 0.85, tier A)

- **When:** FYM application scheduled
- **Action (EN):** Apply 14 to 16 tonnes per acre of fully decomposed FYM before the final kulav pass. Do not reduce this figure for Kannad — here FYM is a soil amendment, not merely a nutrient source.
- **कृती (MR):** शेवटच्या कुळवाच्या पाळीअगोदर एकरी १४ ते १६ टन चांगले कुजलेले शेणखत मिसळा. Kannad मध्ये ही मात्रा कमी करू नये — इथे शेणखत अन्नद्रव्यांपेक्षा जमीन दुरुस्तीचे काम करते.
- **Basis:** In this belt FYM does three jobs at once: it improves friability of heavy clay so drainage improves, it helps keep zinc and iron available against lime lock-up, and it raises organic carbon from a low base of 0.3 to 0.5 percent toward the 1 percent target.
- **Yield impact:** Not separately quantified. Acts indirectly through drainage, micronutrient availability and soil structure.
- **References:** Agrowon - Dr. Kadam (35-40 t/ha); Domain 4 organic carbon target

**D02-OM-003** (OM, yellow, conf 0.8, tier A)

- **When:** FYM application scheduled
- **Action (EN):** Mix Trichoderma at 2 kg per acre into the FYM at the time of application. Do not broadcast it separately onto bare soil.
- **कृती (MR):** शेणखतात ट्रायकोडर्मा २ किलो प्रति एकर मिसळून द्या. नुसते जमिनीवर टाकू नये.
- **Basis:** Trichoderma is a living organism and needs an organic substrate to colonise. Applied to bare soil it does not establish; applied through FYM it survives and works through the season.
- **Yield impact:** u = 0.08 estimated for omitting it, acting through soft rot and nematode suppression.
- **References:** Agrowon - Mali & Mahajan; CJAST 2020 soft rot review

**D02-SL-002** (SL, yellow, conf 0.88, tier A)

- **When:** soil_depth_cm less than 30
- **Action (EN):** Warn that minimum soil depth is not met. Ginger rhizome grows horizontally and needs a loose working layer; a shallow soil caps rhizome size regardless of other inputs.
- **कृती (MR):** आल्यासाठी किमान ३० सेंमी खोली आवश्यक आहे. गड्डा आडवा वाढतो, त्याला बाजूला मोकळी मऊ माती लागते.
- **Basis:** Official minimum is 30 cm. Because the rhizome expands laterally in the top layer, depth below 30 cm cannot be substituted by fertiliser or irrigation.
- **Yield impact:** Not quantified. Acts as a physical ceiling on rhizome size.
- **References:** Agrowon - Dr. Kadam

**D02-ST-001** (ST, yellow, conf 0.85, tier A)

- **When:** Pre-season planning initiated AND soil_test_available is false
- **Action (EN):** Request a soil test at least four months before planting. Specify that free lime, zinc and iron must be requested separately — they are normally absent from a standard report and they are the three parameters that matter most in this belt.
- **कृती (MR):** लागवडीच्या किमान चार महिने आधी माती परीक्षण करा. मुक्त चुनखडी, जस्त आणि लोह हे तीन घटक वेगळे मागावे लागतात — नेहमीच्या अहवालात ते नसतात, आणि इथे तेच सर्वात जास्त सांगणारे आहेत.
- **Basis:** The routine soil health card panel covers pH, EC, organic carbon and NPK. Free lime, zinc and iron determine whether the calcareous yellowing problem will occur, and they are the basis for the Domain 4 micronutrient schedule.
- **Yield impact:** Enables correct dosing across Domain 4. Without it the engine falls back to generic doses at medium confidence.
- **References:** Domain 2 soil test panel; Vikaspedia micronutrient guidance

**D02-ST-002** (ST, yellow, conf 0.8, tier B)

- **When:** Pre-season planning AND percolation_time_hours is unknown
- **Action (EN):** Request the field percolation pit test. 30 cm deep and wide, fill and drain fully, refill and time the second drain. Record percolation_class.
- **कृती (MR):** ३० सेंमी खोल व रुंद खड्डा खणा, पाण्याने भरून पूर्ण मुरू द्या, पुन्हा भरा आणि वेळ मोजा. दोन तासांत मुरले तर उत्तम; बारा तासांहून जास्त लागल्यास या शेतात अद्रक टाळावे.
- **Basis:** For ginger the governing soil risk is physical drainage, not chemical fertility. No laboratory report measures infiltration rate on the actual plot.
- **Yield impact:** Determines bed height and channel design, and in the worst case the go or no-go decision.
- **References:** Domain 2 percolation method; standard field infiltration practice

**D02-TL-001** (TL, yellow, conf 0.88, tier A)

- **When:** Land preparation phase, deep_ploughing_done is false
- **Action (EN):** Require deep ploughing to about one foot, both lengthwise and crosswise, followed by kulav passes until the tilth is friable and clod-free.
- **कृती (MR):** एक फुटापर्यंत उभी व आडवी खोल नांगरट करा, नंतर कुळवाच्या पाळ्या देऊन जमीन भुसभुशीत करा. काळ्या जमिनीत ढेकळे मोठी होतात, त्यामुळे तीन ते चार पाळ्या लागू शकतात.
- **Basis:** The crop stays in the soil for eight months and the rhizome expands horizontally. It needs a loose lateral working layer; compacted soil produces small and misshapen rhizomes.
- **Yield impact:** Not separately quantified. Acts through rhizome size rather than plant count.
- **References:** Agrowon - Dr. Kadam; CropLibrary

**D02-TL-002** (TL, yellow, conf 0.8, tier A)

- **When:** Month is March AND deep_ploughing_done is false
- **Action (EN):** Start deep ploughing now. In black soil the workable window is narrow and closes once the pre-monsoon showers begin. Starting in May is already too late.
- **कृती (MR):** खोल नांगरट आत्ता सुरू करा. काळी जमीन मार्चमध्ये कोरडी व कडक असते — तीच नांगरटीची योग्य वेळ. मे मध्ये सुरू केल्यास उशीर होतो आणि पाऊस सुरू झाल्यावर मशागत अशक्य होते.
- **Basis:** Vertisol is unworkable when wet (clods and structural damage) and resists implements when bone dry. The usable window is short and falls in March for this belt.
- **Yield impact:** Missing the window compresses all subsequent operations and risks planting after the 7 June deadline.
- **References:** Agrowon - Dr. Kadam; Domain 2 vertisol behaviour

**D02-WD-001** (WD, yellow, conf 0.85, tier A)

- **When:** Land preparation phase
- **Action (EN):** Physically remove perennial weed tubers and rhizomes — nutsedge, bermuda grass and similar — along with stones. Do not rely on later weeding to control them.
- **कृती (MR):** लव्हाळा, हराळी, कुंदा यांसारख्या बहुवार्षिक तणांचे कंद व काश्या वेचून काढा, तसेच मोठे दगड-गोटे. नंतरच्या खुरपणीवर विसंबून राहू नये.
- **Basis:** Ginger emerges slowly and cannot outcompete established perennial weeds. More importantly, heavy later weeding injures the rhizome, and Pythium and Fusarium enter through those wounds.
- **Yield impact:** Acts through the disease pathway rather than through competition alone.
- **References:** Agrowon - Dr. Kadam; Agrowon - Mali & Mahajan on wound entry

### D03

**D03-MU-002** (MU, yellow, conf 0.75, tier B)

- **When:** dap in the 40-60 or 90-120 band AND the corresponding mulch stage not done
- **Action (EN):** Apply the next mulch stage. Bundle stage two with earthing up so both are done in one field visit.
- **कृती (MR):** आच्छादनाचा पुढील टप्पा घाला. दुसरा टप्पा उटाळणीसोबत करा — एकाच फेरीत दोन्ही कामे.
- **Basis:** Sources differ on quantity but agree the programme is three applications rather than one. Cumulative cover is what maintains the effect through the season.
- **Yield impact:** Contributes to the documented reduction in soft rot incidence from 20-30 percent to below 5 percent.
- **References:** Organic Mandya; Spices Board / TNAU

**D03-WS-002** (WS, yellow, conf 0.75, tier B)

- **When:** Water supply assessed as marginal
- **Action (EN):** Recommend a lined farm pond to capture monsoon runoff for the October to February period. This stores the water that the drainage channels are already carrying away.
- **कृती (MR):** शेततळे विचारात घ्या. मान्सूनमध्ये जे पाणी निचरा चरातून वाहून जाते तेच साठवून ऑक्टोबरनंतर वापरता येईल — म्हणजे एकाच रचनेतून दोन्ही समस्या सुटतात.
- **Basis:** Monsoon water must be removed from the root zone to prevent soft rot, and the same water is short four months later. Storage converts a disposal problem into a supply solution.
- **Yield impact:** Reduces exposure to both the waterlogging pathway and the late-season exhaustion pathway.
- **References:** Domain 3 water budget; Domain 10 farm pond subsidy

### D04

**D04-BI-001** (BI, yellow, conf 0.8, tier A)

- **When:** Seed treatment being planned
- **Action (EN):** After the chemical treatment and shade drying, dip seed in Azospirillum 25 g plus PSB 25 g per litre for 10 to 15 minutes. Ten litres treats 100 to 120 kg of seed.
- **कृती (MR):** रासायनिक प्रक्रियेनंतर सावलीत सुकवून, ॲझोस्पिरिलम २५ ग्रॅम अधिक PSB २५ ग्रॅम प्रति लिटर या द्रावणात बेणे १० ते १५ मिनिटे बुडवा. १० लिटर द्रावणात १०० ते १२० किलो बेण्यास प्रक्रिया होते.
- **Basis:** Azospirillum fixes nitrogen and PSB releases fixed phosphorus. PSB is directly relevant on calcareous soil where applied phosphorus binds with calcium.
- **Yield impact:** Not separately quantified. Supports the phosphorus availability problem identified in Domain 2.
- **References:** Agrowon - Dr. Kadam seed treatment sequence

**D04-DG-002** (DG, yellow, conf 0.88, tier A)

- **When:** leaf_yellowing_pattern is interveinal_new
- **Action (EN):** Diagnose as iron or zinc lock-up, not nitrogen deficiency. Recommend foliar micronutrient spray. Do NOT apply urea.
- **कृती (MR):** हे लोह किंवा जस्ताच्या अनुपलब्धतेचे लक्षण आहे, नत्राच्या कमतरतेचे नाही. सूक्ष्म अन्नद्रव्यांची फवारणी करा. युरिया देऊ नका — त्याने काहीही होणार नाही, फक्त खर्च वाढेल आणि पाला माजेल.
- **Basis:** Iron and zinc are immobile in the plant, so deficiency appears in new growth first. Nitrogen is mobile and is withdrawn from old leaves first, so nitrogen deficiency appears in old growth. Leaf age is therefore a reliable discriminator.
- **Yield impact:** Directs the 0.11 micronutrient correction to the right cause and prevents an ineffective nitrogen application.
- **References:** Domain 4 diagnosis table; Krishi Jagran calcareous yellowing in turmeric

**D04-FG-003** (FG, yellow, conf 0.75, tier A)

- **When:** Published fertigation schedule about to be applied as printed
- **Action (EN):** Scale it down in proportion to the actual yield target. Total MOP in the printed schedule is about 207 kg per acre, roughly double the Maharashtra official potassium figure.
- **कृती (MR):** हे वेळापत्रक जसेच्या तसे वापरू नका. त्यातील एकूण MOP एकरी सुमारे २०७ किलो आहे — म्हणजे अधिकृत शिफारशीच्या जवळपास दुप्पट. आपल्या उत्पादन लक्ष्याच्या प्रमाणात कमी करा.
- **Basis:** Fertigation splits nutrients into small frequent doses which raises efficiency, but the printed totals target a higher yield than the validated ceiling for this belt. Nutrient requirement scales with expected yield.
- **Yield impact:** Prevents systematic over-application and unnecessary cost.
- **References:** Agrowon fertigation schedule; Domain 1 yield ceiling; Agrowon - Dr. Kadam official dose

**D04-NP-001** (NP, yellow, conf 0.78, tier A)

- **When:** Dose setting AND soil_test_available is false
- **Action (EN):** Use the safe starting range: 40 to 48 kg N, 20 to 30 kg P, 40 to 60 kg K per acre. Keep nitrogen at the lower end and potassium at the upper end. Mark confidence MEDIUM and tell the user a soil test would sharpen this.
- **कृती (MR):** सुरक्षित प्रारंभ श्रेणी वापरा — एकरी नत्र ४० ते ४८ किलो, स्फुरद २० ते ३० किलो, पालाश ४० ते ६० किलो. नत्र खालच्या टोकाला, पालाश वरच्या टोकाला ठेवा. माती परीक्षण केल्यास मात्रा अचूक करता येईल.
- **Basis:** State recommendations range from 28 to 51 kg N per acre. The highest uptake in semi-arid conditions was recorded at a lower nitrogen dose, and Kannad is semi-arid. The Mahima-specific trial also points to less phosphorus and more potassium, which suits calcareous soil where phosphorus is fixed.
- **Yield impact:** Both extremes are documented as harmful — deficiency limits yield, and indiscriminate use degrades soil physical, chemical and biological condition and reduces yield significantly.
- **References:** IntechOpen INM chapter; Int. J. Adv. Biochem. Res. 2025 Mahima trial; Agrowon - Dr. Kadam

**D04-OR-001** (OR, yellow, conf 0.85, tier A)

- **When:** Basal application being planned
- **Action (EN):** Include neem cake 300 to 400 kg per acre at basal, with a second 300 to 400 kg at earthing up. Rank it high in the recommendation list.
- **कृती (MR):** पायाभूत मात्रेत निंबोळी पेंड एकरी ३०० ते ४०० किलो, आणि उटाळणीच्या वेळी आणखी ३०० ते ४०० किलो द्या.
- **Basis:** Neem cake at 2 tonnes per hectare with NPK increased yield AND reduced rhizome rot incidence in Kerala trials. Separately it produced the highest available nitrogen when combined with half the urea dose. It also suppresses nematodes, which are a documented entry route for both soft rot and bacterial wilt.
- **Yield impact:** Acts across three domains simultaneously. Not separately quantified but supports several u-values.
- **References:** Sarma et al 2001; IISR Annual Report 2002; extension nematode guidance

**D04-PP-001** (PP, yellow, conf 0.9, tier A)

- **When:** Phosphorus application scheduled
- **Action (EN):** Apply the full phosphorus dose as basal at land preparation. Phosphorus is immobile and is needed early for root development.
- **कृती (MR):** स्फुरदाची संपूर्ण मात्रा जमीन तयार करतानाच द्या. स्फुरद जमिनीत हलत नाही आणि तो सुरुवातीच्या मूळ विकासासाठी लागतो.
- **Basis:** All state recommendations agree on full basal phosphorus. It does not move in soil, so top-dressing later does not reach the root zone.
- **Yield impact:** Part of the overall nutrition schedule; not separately quantified.
- **References:** Agrowon - Dr. Kadam; Kerala and Karnataka packages

**D04-PP-002** (PP, yellow, conf 0.8, tier B)

- **When:** soil_free_lime_pct elevated OR soil_ph greater than 7.5
- **Action (EN):** Band the phosphorus with organic matter rather than broadcasting. Use PSB in the seed treatment. Do NOT increase the phosphorus dose to compensate for fixation.
- **कृती (MR):** स्फुरद पसरून न देता पट्ट्यात, सेंद्रिय पदार्थासोबत द्या. बीजप्रक्रियेत PSB वापरा. चुनखडीमुळे स्फुरद स्थिर होतो म्हणून मात्रा वाढवू नये — वाढवलेलाही तेवढ्याच प्रमाणात स्थिर होतो. उत्तर मात्रा नाही, पद्धत आहे.
- **Basis:** In calcareous soil applied phosphorus binds with calcium into unavailable calcium phosphate. Banding reduces soil contact and so reduces fixation; organic acids from decomposing matter keep more of it available; phosphate solubilising bacteria release part of the fixed pool.
- **Yield impact:** Prevents wasted input rather than adding yield. Also explains why the Mahima-specific trial uses lower phosphorus than the general schedule.
- **References:** Domain 2 fixation mechanism; Int. J. Adv. Biochem. Res. 2025; Agrowon fertigation phosphoric acid

### D05

**D05-CH-002** (CH, yellow, conf 0.85, tier A)

- **When:** A chemical option is about to be presented
- **Action (EN):** Emit the molecule name, group and source-reported dose, and append that CIB&RC label claim for ginger must be verified and label dose and pre-harvest interval followed. Always show biological and cultural options above it.
- **कृती (MR):** रसायनाचे नाव, गट आणि स्रोतातील मात्रा दाखवा, आणि सोबत अनिवार्य शेरा — लेबलवर अद्रकासाठी नोंदणी असल्याची खात्री करा, मात्रा व प्रतीक्षा कालावधी लेबलनुसार. जैविक व सांस्कृतिक पर्याय नेहमी वर दाखवा.
- **Basis:** Ginger is a minor crop, so many insecticides lack a specific ginger label claim. Being recommended in extension literature and being registered on the label are different things.
- **Yield impact:** Regulatory compliance rather than yield.
- **References:** Agrowon - Mali & Mahajan doses; CIB&RC minor crop position

**D05-CH-004** (CH, yellow, conf 0.8, tier A)

- **When:** Chemical spray scheduled AND the same group was used in the previous application
- **Action (EN):** Alternate the mode of action group, not merely the product name. Track the group of the last two applications and select a different one.
- **कृती (MR):** एकच रसायन सतत वापरू नये. फक्त नाव नव्हे, क्रियापद्धतीचा गट बदला. मागील दोन फवारण्यांचे गट तपासून वेगळा गट निवडा.
- **Basis:** Source instructs alternating chemicals. Two products with different trade names but the same mode of action do not break resistance selection, so the group is what must change.
- **Yield impact:** Preserves the useful life of the available molecules.
- **References:** Agrowon - Mali & Mahajan; Domain 6 fungicide rotation rule

**D05-LC-001** (LC, yellow, conf 0.85, tier A)

- **When:** straight_line_holes_in_whorl is true
- **Action (EN):** Identify as leaf eating caterpillar. Collect and destroy larvae and pupae. Chemical control only if damage is widespread.
- **कृती (MR):** ही पाने खाणाऱ्या अळीची खूण आहे. अळ्या व कोष वेचून नष्ट करा. प्रादुर्भाव मोठा असेल तरच रासायनिक उपाय.
- **Basis:** The caterpillar bores through the rolled whorl at one point, so when the leaf unfurls the single hole appears as a row of holes in a straight line. This is highly specific and unambiguous.
- **Yield impact:** u = 0.05, foliage damage only.
- **References:** Agrowon - Mali & Mahajan

**D05-NE-002** (NE, yellow, conf 0.8, tier A)

- **When:** FYM application scheduled
- **Action (EN):** Mix Trichoderma 2 kg per acre into about 250 kg of FYM at planting. This serves nematodes and soft rot together.
- **कृती (MR):** लागवडीच्या वेळी सुमारे २५० किलो शेणखतात ट्रायकोडर्मा २ किलो प्रति एकर मिसळा. हे सूत्रकृमी आणि कंदकूज दोन्हीवर काम करते.
- **Basis:** Trichoderma is recommended for nematode suppression and independently for soft rot control. It needs an organic carrier to colonise, so mixing into FYM is not incidental.
- **Yield impact:** u = 0.08 for omission, acting across both pest and disease pathways.
- **References:** Agrowon - Mali & Mahajan; Krishi app blog rates; CJAST 2020 soft rot review

**D05-RF-002** (RF, yellow, conf 0.88, tier A)

- **When:** Month is July, August or September AND exposed_rhizomes_observed is true
- **Action (EN):** Cover exposed rhizomes with soil immediately. Rhizome fly larvae enter through exposed rhizomes.
- **कृती (MR):** शेतात उघडे पडलेले गड्डे मातीत तात्काळ झाकून घ्या. कंदमाशीच्या अळ्या उघड्या गड्ड्यांमध्ये शिरून त्यावर उपजीविका करतात.
- **Basis:** Source states the entry route is exposed rhizomes and gives the explicit instruction to cover them during July to September.
- **Yield impact:** Direct prevention of the entry event that starts the rot chain.
- **References:** Agrowon - Mali & Mahajan

**D05-SH-002** (SH, yellow, conf 0.85, tier A)

- **When:** stem_hole_with_webbing is true
- **Action (EN):** Confirm shoot borer with a live larva inside. Remove and destroy the affected shoot. If incidence exceeds about 5 percent, check the light trap; above about 10 percent consider chemical control.
- **कृती (MR):** खोडावरील छिद्र म्हणजे आत अळी जिवंत आहे. प्रादुर्भावित खोड काढून नष्ट करा. प्रादुर्भाव ५ टक्क्यांहून जास्त असल्यास प्रकाश सापळा तपासा; १० टक्क्यांहून जास्त असल्यास रासायनिक उपायाचा विचार करा.
- **Basis:** Source states that a hole in the stem means the larva is alive inside, and that webbing is visible over the hole. This makes the pest verifiable by the farmer, so it can be handled on scouting rather than on calendar.
- **Yield impact:** u = 0.05 to 0.10.
- **References:** Agrowon - Mali & Mahajan diagnostic signs

**D05-WG-003** (WG, yellow, conf 0.8, tier A)

- **When:** white_grub_suspected is true on any plot in the cluster
- **Action (EN):** Issue a cluster-wide alert. Ask all farms in the cluster to collect beetles on the same three evenings. Individual action does not work because the beetles fly.
- **कृती (MR):** cluster मधील सर्व शेतकऱ्यांना एकाच वेळी इशारा द्या — पुढील तीन संध्याकाळी सर्वांनी भुंगेरे गोळा करावेत. भुंगेरे उडतात, त्यामुळे एकट्याने केलेले नियंत्रण टिकत नाही.
- **Basis:** Source states that integrated pest management carried out collectively is beneficial for this pest. Beetles are mobile, so a single treated field is recolonised from neighbouring untreated ones.
- **Yield impact:** Raises the effectiveness of the 0.10 white grub control from partial to substantial.
- **References:** Agrowon - Mali & Mahajan

### D06

**D06-BW-002** (BW, yellow, conf 0.8, tier A)

- **When:** nematode_suspected is true
- **Action (EN):** Raise the bacterial wilt risk score as well as the soft rot risk score. Root-knot nematode has a documented role in inducing bacterial wilt, so nematode control is indirect wilt prevention.
- **कृती (MR):** सूत्रकृमींचा प्रादुर्भाव असल्यास मर रोगाचीही जोखीम वाढवा. मूळगाठ सूत्रकृमींची जिवाणूजन्य मर निर्माण होण्यात भूमिका नोंदवलेली आहे — म्हणजे सूत्रकृमी नियंत्रण हे अप्रत्यक्षपणे मर रोग प्रतिबंध आहे.
- **Basis:** Samuel and Mathew documented the role of Meloidogyne incognita in inducing bacterial wilt in ginger. The nematode wounds provide entry, so the two problems are causally linked rather than merely co-occurring.
- **Yield impact:** Strengthens the case for the nematode-resistant variety, which is a free preventive against a disease that has no cure.
- **References:** IntechOpen Diseases of Ginger 2019, Samuel & Mathew 1986

**D06-CH-002** (CH, yellow, conf 0.85, tier A)

- **When:** A fungicide option is about to be presented to the farmer
- **Action (EN):** Emit molecule, group and source-reported dose, and append that CIB&RC label claim for ginger must be verified and label dose and pre-harvest interval followed. Show biological and cultural options above it.
- **कृती (MR):** रसायनाचे नाव, गट आणि स्रोतातील मात्रा दाखवा, आणि सोबत अनिवार्य शेरा — लेबलवर अद्रकासाठी नोंदणी असल्याची खात्री करा, मात्रा व प्रतीक्षा कालावधी लेबलनुसार. जैविक व सांस्कृतिक पर्याय नेहमी वर दाखवा.
- **Basis:** Ginger is a minor crop, so many fungicides lack a specific ginger label claim. Appearing in state extension literature and being registered on the label are different things, and only the second is a legal basis for use.
- **Yield impact:** Regulatory compliance rather than yield.
- **References:** CIB&RC minor crop position; Agrowon - Mali & Mahajan doses

**D06-FH-001** (FH, yellow, conf 0.85, tier A)

- **When:** Harvest is complete
- **Action (EN):** Record actual rot and wilt incidence as percentages against this plot, permanently. This is a first-class input to next season planning and to Domain 11 gap attribution.
- **कृती (MR):** काढणीनंतर कंदकूज व मर रोगाचे प्रत्यक्ष प्रमाण टक्केवारीत या प्लॉटविरुद्ध कायमस्वरूपी नोंदवा. ही नोंद पुढील हंगामाच्या नियोजनाचा आणि उत्पादन-दरी विश्लेषणाचा प्राथमिक आधार आहे.
- **Basis:** Field history is a first-class input because inoculum persists across seasons and the wilt bacterium persists for many years. Without a recorded incidence figure, next season starts blind and the u-values cannot be corrected against reality.
- **Yield impact:** Foundational for the u-value validation loop rather than for this season's yield.
- **References:** Core C4.3 inoculum carry-over; Core C11.2 field history as persistent state

**D06-FH-002** (FH, yellow, conf 0.75, tier B)

- **When:** Soft rot confirmed on any plot within the cluster
- **Action (EN):** Issue an anonymised cluster-level advisory raising the disease pressure score for neighbouring plots. Do not name the affected farm.
- **कृती (MR):** cluster मधील शेजारच्या शेतांना अनामीकृत इशारा द्या — या भागात कंदकुजीचा दाब वाढला आहे. बाधित शेताचे नाव सांगू नये.
- **Basis:** Because symptom appearance means the yield is already lost for the affected plant, a neighbouring plot warned before symptoms appear has a genuine preventive window that it would not otherwise have.
- **Yield impact:** Extends the preventive window to plots that have not yet been infected.
- **References:** Core C11.2 field history; Domain 12 DPDP constraints

**D06-LS-002** (LS, yellow, conf 0.8, tier A)

- **When:** A fungicide spray is scheduled AND last_fungicide_group equals the proposed group
- **Action (EN):** Change the mode of action GROUP, not merely the product name. Check the last two applications and select a different group. When groups are exhausted, return to a multi-site such as copper or Bordeaux.
- **कृती (MR):** क्रियापद्धतीचा गट बदला, फक्त नाव नव्हे. मागील दोन फवारण्यांचे गट तपासून वेगळा गट निवडा. गट संपल्यास तांबे किंवा बोर्डो मिश्रणाकडे परत या.
- **Basis:** Two products with different trade names but the same mode of action do not break resistance selection. The source instructs alternation; the group is what must actually change for that instruction to have effect.
- **Yield impact:** Preserves the useful life of the few molecules available for a minor crop.
- **References:** Agrowon - Mali & Mahajan do not use the same fungicide repeatedly

**D06-MU-001** (MU, yellow, conf 0.85, tier A)

- **When:** Mulch stage is due and not yet done, at planting or at 40 to 60 or 90 to 120 DAP
- **Action (EN):** Apply the due mulch stage. Treat the three-stage programme as disease control, not as moisture conservation. Bundle stage two with earthing up.
- **कृती (MR):** आच्छादनाचा टप्पा घाला. तीन-टप्पी आच्छादन हे ओलावा टिकवण्याचे साधन नाही — ते रोग-प्रतिबंधाचे मुख्य साधन आहे. दुसरा टप्पा उटाळणीसोबत करा.
- **Basis:** Records from Kodagu and Shivamogga show soft rot below 5 percent among farmers following a three-stage mulching programme against a district average of 20 to 30 percent. Mulch lowers soil temperature, stops rain impact compaction, prevents splash carrying soil onto leaves, and keeps moisture steady so the plant is less stressed.
- **Yield impact:** u = 0.20, derived from 25 percent average incidence reduced to 5 percent. This is the best quantified preventive measure in the knowledge base.
- **References:** Organic Mandya Kodagu and Shivamogga field records; Spices Board / TNAU mulch programme

**D06-PV-002** (PV, yellow, conf 0.85, tier A)

- **When:** previous_crops_3yr contains ginger, turmeric, potato, tomato, brinjal or chilli
- **Action (EN):** Warn that rotation is not satisfied. Ginger and turmeric share soil-borne pathogens; the solanaceous crops are bacterial wilt hosts. Recommend a different plot where available.
- **कृती (MR):** फेरपालट पाळलेली नाही. हळद व आले एकाच कुळातील असल्याने त्यांचे soil-borne रोग सामाईक आहेत; बटाटा, टोमॅटो, वांगी, मिरची हे मर रोगाचे यजमान आहेत.
- **Basis:** Continuous cropping raises the risk of infection by both Pythium myriotylum and Ralstonia solanacearum. The minimum recommended gap is three years, and the wilt bacterium can persist longer than that.
- **Yield impact:** u = 0.15 for rotation failure alone, substantially higher if a wilt outbreak follows.
- **References:** Microbiology Spectrum NCBI PMC9603371 continuous cropping risk; Agrowon - Dr. Kadam

**D06-SR-002** (SR, yellow, conf 0.85, tier A)

- **When:** Soft rot confirmed on any plant
- **Action (EN):** Remove affected plants with roots and burn them. Do not leave them in the field or on the bund. Drench the affected and adjacent beds. Drench only when the soil is at vafsa condition and give a light water stress afterwards.
- **कृती (MR):** बाधित रोपे मुळासकट काढून जाळून नष्ट करा — शेतात किंवा बांधावर टाकू नका. बाधित व शेजारच्या वाफ्यांत आळवणी करा. आळवणी करताना जमिनीस वाफसा असावा, आणि नंतर पिकास थोडासा पाण्याचा ताण द्यावा.
- **Basis:** Affected rhizomes left in the field become inoculum for the rest of the season and for subsequent seasons. Drenching saturated soil dilutes and displaces the chemical, and irrigating immediately afterwards leaches it below the shallow root zone.
- **Yield impact:** Limits spread within the season and reduces carry-over inoculum.
- **References:** Agrowon - Mali & Mahajan drench and disposal instructions

**D06-ST-001** (ST, yellow, conf 0.85, tier A)

- **When:** Seed treatment is being planned
- **Action (EN):** Treat seed rhizome twice — once before storage and again before planting. Hot water at 51 C for 10 minutes followed by Trichoderma harzianum at 15 g per kg gave the best result among biological treatments. Then shade dry before any further biological step.
- **कृती (MR):** बेणे प्रक्रिया दोन वेळा करा — साठवणीपूर्वी आणि लागवडीपूर्वी. ५१ अंश सेल्सिअस पाण्यात दहा मिनिटे, नंतर ट्रायकोडर्मा हार्जियानम प्रति किलो पंधरा ग्रॅम. मग सावलीत सुकवूनच पुढील जैविक प्रक्रिया करा.
- **Basis:** Seed rhizome is the primary entry route for both soft rot and bacterial wilt, and once the pathogen is in the soil it cannot be removed. Recorded germination was 80 to 83 percent untreated against 93 to 98 percent treated. Treating only before planting does not address infection already established inside the rhizome during storage.
- **Yield impact:** u = 0.135 on establishment alone. On roughly 800 kg of seed a 15 percent germination difference is worth about 120 to 150 kg of seed. The disease prevention value is separate and larger.
- **References:** Springer hot water plus Trichoderma harzianum trial; CJAST 39(35) 2020 treat before storage and before planting

### D08

**D08-LY-002** (LY, yellow, conf 0.88, tier A)

- **When:** planting_layout is broad_ridge AND bed geometry not yet fixed
- **Action (EN):** Set 120 cm cycle, 60 cm ridge, 60 cm furrow, height 25 to 30 cm, planting 22.5 x 22.5 cm, depth 4 to 5 cm, one drip line per bed. Lay beds along the slope.
- **कृती (MR):** १२० सेंमी अंतरावर सरी — वरंबा ६० सेंमी, पाट ६० सेंमी, उंची २५ ते ३० सेंमी, लागवड २२.५ × २२.५ सेंमी, खोली ४ ते ५ सेंमी, एका वाफ्यावर एक ठिबक नळी. वाफे उताराला अनुसरून.
- **Basis:** Three published geometries exist. The 90 cm ridge with a 45 cm furrow gives more plants but less drainage capacity, which is the wrong trade where July delivers 195 mm and cyclonic rain can arrive in October. The wide furrow and greater height are chosen deliberately over plant population.
- **Yield impact:** Realises the 0.167 captured by D08-LY-001.
- **References:** Agrowon - Dr. Kadam 120/60/60; Agrowon - Bitle and Deshmukh 30 cm height; AgroWorld 135/90/45

**D08-LY-003** (LY, yellow, conf 0.7, tier B)

- **When:** Seed quantity is being estimated
- **Action (EN):** Compute seed requirement from area, spacing and piece weight rather than using a rule of thumb. Show the calculation. A wrong assumption here moves the largest cost line in the crop.
- **कृती (MR):** बेण्याचे प्रमाण गृहीत धरून सांगू नका — क्षेत्र, अंतर आणि तुकड्याचे वजन यावरून गणित करून दाखवा. इथली चूक सर्वात मोठ्या खर्च रेषेवर परिणाम करते.
- **Basis:** Reported seed rates and computed plant populations do not reconcile. At 850 kg per acre and 35 g per piece the count is about 24,300 per acre, roughly 60,000 per hectare, against a computed broad ridge population of about 111,000 per hectare. Either the rate is higher than reported, the spacing is wider in practice, or the pieces are lighter.
- **Yield impact:** Seed is 28 to 35 percent of total cost. A factor-of-two error in the estimate is the single largest budgeting error available.
- **References:** Domain 8 plant population computation; Domain 13 seed cost line

**D08-PL-001** (PL, yellow, conf 0.72, tier C)

- **When:** Planting day AND bud_orientation_instructed is false
- **Action (EN):** Instruct the planting team that the bud must face UP and OUTWARD. A bud facing down and inward produces a small weak shoot.
- **कृती (MR):** मजुरांना स्पष्ट सूचना द्या — कंदावरील डोळा वरती आणि बाहेरच्या बाजूला असावा. डोळा खाली आणि आतल्या बाजूला राहिल्यास कोंब लहान आणि कमकुवत राहतो.
- **Basis:** Source states that when the bud faces up and outward the emerging shoot is strong and grows well, and that the reverse orientation gives a small weak shoot. A weak shoot means fewer tillers, and tiller count sets rhizome number.
- **Yield impact:** u = 0.05. Small individually but entirely free, and it compounds across every plant in the field.
- **References:** AgroWorld bud orientation

**D08-PL-002** (PL, yellow, conf 0.75, tier C)

- **When:** Planting in progress
- **Action (EN):** Plant at 4 to 5 cm depth and confirm the rhizome is fully covered. Too shallow exposes it to heat and to rhizome fly; too deep delays emergence.
- **कृती (MR):** ४ ते ५ सेंमी खोलीवर लावा आणि गड्डा पूर्ण झाकला जाईल याची खात्री करा. उथळ लावल्यास उष्णता आणि कंदमाशीचा धोका; खोल लावल्यास उगवण लांबते.
- **Basis:** Source specifies 4 to 5 cm with the instruction to ensure full covering. Exposed rhizomes are the documented entry route for rhizome fly, which is the primary pest here.
- **Yield impact:** u = 0.05 estimated. Also feeds the rhizome fly pathway.
- **References:** AgroWorld planting depth; Agrowon - Mali and Mahajan exposed rhizome entry

**D08-PL-003** (PL, yellow, conf 0.75, tier C)

- **When:** Seed grading in progress
- **Action (EN):** Grade to 30 to 40 g pieces with 2 to 3 swollen buds, 2.5 to 5 cm long. Reject rotten or partly decayed pieces. Separate pieces from the mother rhizome.
- **कृती (MR):** ३० ते ४० ग्रॅम वजनाचे, २ ते ३ फुगलेले डोळे असलेले, २.५ ते ५ सेंमी लांबीचे तुकडे करा. कुजलेले किंवा अर्धवट सडलेले तुकडे वापरू नका. मातृकंदापासून तुकडे वेगळे करा.
- **Basis:** Sources give 25 to 55 g, 30 to 45 g and 20 to 30 g. The overlapping practical range is 30 to 40 g. Bud count matters more than weight because each bud is a potential shoot, and rejecting decayed pieces removes carried inoculum at the cheapest possible point.
- **Yield impact:** Feeds the establishment ceiling and the seed cost line simultaneously.
- **References:** AgroWorld seed specification; Agrowon - Dr. Kadam; Vikaspedia

**D08-SS-001** (SS, yellow, conf 0.78, tier C)

- **When:** Seed rhizome is being put into storage
- **Action (EN):** Warn that 28 to 40 percent of the weight will be lost by planting time. To have a given quantity at planting, store roughly 1.4 times that amount. Record both weights.
- **कृती (MR):** साठवणीत बेण्याचे वजन २८ ते ४०% घटते. लागवडीच्या वेळी जेवढे हवे आहे त्याच्या सुमारे १.४ पट आत्ता साठवावे लागेल. साठवणीचे आणि लागवडीच्या वेळचे — दोन्ही वजन नोंदवा.
- **Basis:** Source states that 25 quintal per hectare is required at planting but by then the stored weight has fallen to 15 to 18 quintal. A separate statement in the same source gives 25 to 30 percent loss for simple shade storage, so the range is internally consistent.
- **Yield impact:** Not a yield factor. It is a cost of roughly half the seed line again, paid in kind rather than in cash, and therefore invisible in every cost sheet.
- **References:** AgroWorld seed storage section

**D08-SS-002** (SS, yellow, conf 0.75, tier C)

- **When:** Seed storage method being decided
- **Action (EN):** Use the pit method rather than a shade heap. Pit 60 cm deep, walls and floor plastered with cow dung and mud, dried 10 to 15 days, 2 cm sand base, then alternating 10 cm seed and sand layers to 45 to 50 cm, leaving 10 cm headspace under a wooden plank with an air hole and a grass thatch above. Confirm the water table is more than a metre below the pit floor.
- **कृती (MR):** सावलीत रचून ठेवण्यापेक्षा खड्डा पद्धत वापरा. ६० सेंमी खोल खड्डा, भिंती व तळ शेण-मातीने सारवा, १०-१५ दिवस वाळू द्या, तळाला २ सेंमी कोरडी वाळू, नंतर १० सेंमी बेणे व वाळू आलटून-पालटून ४५-५० सेंमीपर्यंत, वर १० सेंमी मोकळी जागा, हवेसाठी भोक असलेली लाकडी फळी, आणि वर वाळलेल्या गवताचे छप्पर. खड्ड्याखाली पाण्याची पातळी एक मीटरहून खोल असल्याची खात्री करा.
- **Basis:** Simple shade storage loses 25 to 30 percent. The pit method controls temperature and humidity, and the plaster, sand layering and air hole together manage moisture and respiration. Closed rooms of tin, cement or tile are explicitly to be avoided.
- **Yield impact:** Reducing loss from 30 to 20 percent saves roughly 150 kg of seed on an 850 kg requirement, at negligible cost.
- **References:** AgroWorld pit storage detail

**D08-SS-003** (SS, yellow, conf 0.75, tier C)

- **When:** Seed is being taken out of storage AND seed_sprouts_visible is false
- **Action (EN):** Treat as a quality warning. At two and a half to three months in storage the buds should have swollen and fine sprouts should be visible. Seed showing no sprouts is suspect and germination should be tested before committing the whole lot.
- **कृती (MR):** अडीच ते तीन महिन्यांत डोळे फुगून बारीक कोंब यायला हवेत. कोंब न आलेले बेणे संशयास्पद आहे — संपूर्ण लॉट लावण्यापूर्वी उगवण तपासा.
- **Basis:** Source states that at two and a half to three months the buds swell and fine sprouts appear, and that seed showing such sprouts should be used. Absence of sprouts after that period indicates the seed is either dead or still fully dormant.
- **Yield impact:** Protects establishment, which is a hard ceiling for the season.
- **References:** AgroWorld readiness sign

**D08-TL-001** (TL, yellow, conf 0.85, tier A)

- **When:** Land preparation phase AND deep_ploughing_done is false
- **Action (EN):** Deep plough to about one foot, lengthwise and crosswise, then kulav until the tilth is friable and clod free. Expect three to four passes on black soil rather than the one or two the source states.
- **कृती (MR):** एक फुटापर्यंत उभी व आडवी खोल नांगरट करा, नंतर जमीन भुसभुशीत होईपर्यंत कुळवाच्या पाळ्या द्या. काळ्या जमिनीत ढेकळे मोठी होतात, त्यामुळे स्रोतातील एक-दोन पाळ्यांऐवजी तीन-चार लागू शकतात.
- **Basis:** The crop stays in the soil for eight months and needs friable soil. The rhizome grows horizontally, so it needs loose lateral soil to expand into — compacted soil gives small misshapen rhizomes regardless of nutrition. Black soil forms larger clods so more passes are needed.
- **Yield impact:** Acts through rhizome size rather than plant count, so it does not appear in establishment figures.
- **References:** Agrowon - Dr. Kadam; AgroWorld tillage sequence

**D08-TL-003** (TL, yellow, conf 0.85, tier A)

- **When:** FYM application scheduled
- **Action (EN):** Apply 14 to 16 tonnes per acre of FULLY DECOMPOSED FYM before the final kulav pass. Decomposition matters for three separate reasons — weed seed, white grub, and rot.
- **कृती (MR):** शेवटच्या कुळवाच्या पाळीअगोदर एकरी १४ ते १६ टन पूर्ण कुजलेले शेणखत मिसळा. पूर्ण कुजलेले असणे तीन वेगळ्या कारणांसाठी महत्वाचे — तणाचे बी, हुमणी, आणि कूज.
- **Basis:** Decomposition heat kills weed seed, which reduces the weeding that injures rhizomes. Undecomposed organic matter is white grub larval food. And the FYM rate here is high, so both exposures scale with it.
- **Yield impact:** u = 0.10 for white grub traceable to undecomposed FYM, plus an indirect effect through the weeding and injury chain.
- **References:** Agrowon - Dr. Kadam FYM timing; Agrowon - Mali and Mahajan white grub; AgroWorld weed seed statement

**D08-WD-004** (WD, yellow, conf 0.85, tier A)

- **When:** Land preparation phase AND perennial_weeds_removed is false
- **Action (EN):** Physically remove perennial weed tubers and rhizomes — nutsedge, bermuda grass and kunda — along with stones. Do not rely on later weeding.
- **कृती (MR):** लव्हाळा, हराळी, कुंदा यांचे कंद व काश्या वेचून काढा, तसेच दगड. नंतरच्या खुरपणीवर विसंबून राहू नये.
- **Basis:** Ginger emerges slowly and cannot outcompete established perennial weeds. More importantly, controlling them later means heavy weeding around a developing rhizome, which is the injury route into rot.
- **Yield impact:** Acts through the disease pathway rather than through competition alone.
- **References:** AgroWorld weed species; Agrowon - Dr. Kadam land preparation

**D08-WD-005** (WD, yellow, conf 0.8, tier B)

- **When:** A herbicide option is about to be presented
- **Action (EN):** Show mulch above the chemical option. Name the molecule and the timing but defer the dose to the label, and append that CIB&RC label claim for ginger must be verified.
- **कृती (MR):** रासायनिक पर्यायाच्या वर आच्छादन दाखवा. रसायनाचे नाव व वेळ सांगा पण मात्रा लेबलनुसार म्हणा, आणि लेबलवर अद्रकासाठी नोंदणी तपासण्याचा शेरा जोडा.
- **Basis:** Ginger is a minor crop, so atrazine and glyphosate may not carry a ginger label claim even though extension material lists them. Mulch achieves weed suppression and is already required for disease, water and temperature reasons.
- **Yield impact:** Regulatory compliance. Also directs the farmer toward an input that does four jobs instead of one.
- **References:** AgroWorld doses recorded for reference; CIB&RC minor crop position

### D09

**D09-DR-002** (DR, yellow, conf 0.75, tier C)

- **When:** Skin removal in progress for drying
- **Action (EN):** Scrape the skin, do not peel it deeply, and use a sharpened bamboo edge rather than a metal knife. The oil and aroma compounds sit immediately below the skin.
- **कृती (MR):** साल फक्त खरडून काढा, खोल काढू नका, आणि धातूच्या सुरीऐवजी बांबूची टोकदार कड वापरा. तेल आणि सुगंधी घटक सालीच्या अगदी खाली असतात — खोल साल काढल्यास वजन आणि प्रत दोन्ही जाते.
- **Basis:** The source specifies bamboo rather than metal. Bamboo is softer and does not cut deep, which preserves the sub-surface oil layer that carries the aroma. Aroma is the main quality determinant for dry ginger and oil.
- **Yield impact:** Protects both recovery weight and quality grade.
- **References:** AgroWorld bamboo scraping

**D09-DR-003** (DR, yellow, conf 0.78, tier C)

- **When:** Ginger is spread out for sun drying and evening approaches
- **Action (EN):** Cover with tarpaulin in the evening WITHOUT gathering the produce into a heap. Cooking smoke darkens the produce and darkened ginger drops a grade.
- **कृती (MR):** सायंकाळी पसरलेले आले गोळा न करता ताडपत्रीने झाकून घ्या. गावात संध्याकाळी चुली पेटतात आणि धुराने माल काळपट पडतो — आणि काळपट पडलेली सुंठ खालच्या प्रतीत जाते.
- **Basis:** The source gives this instruction explicitly with the reason. Rural evenings mean cooking smoke, and it discolours drying produce. Gathering the produce would also trap moisture and slow drying.
- **Yield impact:** Pure grade protection at zero cost.
- **References:** AgroWorld evening covering instruction

**D09-HV-003** (HV, yellow, conf 0.75, tier B)

- **When:** Produce has been washed
- **Action (EN):** Drain in shade in a thin layer before bagging. Do not heap wet produce or put it straight into sacks — heat and moisture build at the centre and rot begins.
- **कृती (MR):** ओले गड्डे थेट पोत्यात किंवा ढिगात भरू नका. सावलीत पातळ थरात निथळू द्या, मगच भरा — ढिगाच्या आतल्या भागात उष्णता व ओलावा साचून कूज सुरू होते.
- **Basis:** Soft rot is favoured by warm humid conditions. A heap of freshly washed rhizomes reproduces exactly those conditions at its centre, so the washing that improves grade can itself start a rot if the draining step is skipped.
- **Yield impact:** Prevents a post-harvest loss created by a post-harvest improvement.
- **References:** Domain 6 soft rot conditions; AgroWorld handling

**D09-MK-001** (MK, yellow, conf 0.8, tier B)

- **When:** Pre-season planning AND current market prices are high
- **Action (EN):** Warn that ginger is strongly cyclical and current prices are bullish. Run the profit calculation at a crashed price as well as at the current one. Ask directly whether the costs are covered at around Rs 6,000 per quintal.
- **कृती (MR):** अद्रक हे तीव्र चक्रीय पीक आहे आणि सध्याचे भाव तेजीत आहेत. नफ्याचे गणित कोसळलेल्या भावावरही तपासा — सुमारे ६,००० रुपये प्रति क्विंटल भावात खर्च निघतो का, हा प्रश्न स्पष्ट विचारा.
- **Basis:** High price leads to more planting, higher arrivals and a crash. In ginger the cycle is severe because it is an eight month crop so the response is slow, the seed cost is large so the decision is made once, and the market is thin so a modest arrival increase moves the price a long way.
- **Yield impact:** None on yield. Prevents an area decision based on a price that will not hold.
- **References:** News18 Marathi price reports describing a bullish market; Domain 9 cyclicality mechanism

**D09-ST-001** (ST, yellow, conf 0.65, tier B)

- **When:** Green ginger is being held before sale
- **Action (EN):** Store cool, shaded and with air circulating. Do not pack wet. Separate out injured rhizomes first, because one rotting rhizome infects its neighbours. Avoid closed tin, cement or tile rooms.
- **कृती (MR):** थंड, सावलीत, हवा खेळती अशा जागी ठेवा. ओले पॅक करू नका. इजा झालेले गड्डे आधीच वेगळे काढा — एक कुजका गड्डा शेजारच्यांना संक्रमित करतो. बंद पत्र्याच्या, सिमेंटच्या किंवा कौलारू खोलीत ठेवू नका.
- **Basis:** No source gives specific short-term green storage guidance, so the principles are derived from the soft rot conditions in Domain 6 and from the seed storage guidance which explicitly warns against closed rooms of tin, cement or tile.
- **Yield impact:** Protects realised value on a fully committed crop.
- **References:** Domain 6 soft rot conditions; AgroWorld seed storage warnings

**D09-ST-002** (ST, yellow, conf 0.8, tier B)

- **When:** Dry ginger is being stored AND storage_loss_monthly_pct is unknown
- **Action (EN):** Weigh a sample each month and record the loss. Without this figure the hold-or-sell decision cannot be computed at all — net return equals expected price times one minus cumulative loss, minus storage cost.
- **कृती (MR):** दर महिन्याला नमुना वजन करून घट नोंदवा. हा आकडा नसेल तर विकावे की थांबावे हा निर्णय मोजताच येत नाही — निव्वळ परतावा म्हणजे अपेक्षित भाव गुणिले (एक वजा संचित घट) उणे साठवण खर्च.
- **Basis:** The storage decision model requires the loss rate as an input and no source supplies it for dry ginger. Two weighings a month apart begin to answer it, and a season of them answers it properly.
- **Yield impact:** None directly. Unblocks the most valuable economic decision in the domain.
- **References:** Core C8.3 storage decision formula; Domain 9 critical gap

### D10

**D10-ACT-001** (ACT, yellow, conf 0.8, tier A)

- **When:** Pre-season planning begins
- **Action (EN):** Issue the contact and action register in priority order, flagging the two time-sensitive items — the Taluka Agriculture Officer for the subsidy window and local seed traders for variety availability. Everything else can wait; those two cannot.
- **कृती (MR):** संपर्क व कृती यादी प्राधान्यक्रमाने द्या, आणि दोन वेळ-संवेदनशील मुद्दे ठळक करा — अनुदानाच्या मुदतीसाठी तालुका कृषी अधिकारी, आणि जातीच्या उपलब्धतेसाठी स्थानिक बेणे विक्रेते. बाकीचे थांबू शकते; ही दोन नाहीत.
- **Basis:** Ten institutional actions are identified. Two of them gate downstream decisions with fixed deadlines — the subsidy chain takes six or more months and includes a lottery, and the seed market is small enough that late ordering forfeits the variety choice.
- **Yield impact:** Protects the 0.138 variety value and the capital structure of the whole enterprise.
- **References:** Domain 10 action register

**D10-APP-001** (APP, yellow, conf 0.82, tier B)

- **When:** Subsidy application about to be filed AND subsidy_documents_ready is false
- **Action (EN):** Assemble the documents first: Aadhaar, 7/12 extract, 8-A extract, passport photograph, Aadhaar-linked bank passbook, and caste certificate where applicable. Apply on mahadbt.maharashtra.gov.in.
- **कृती (MR):** आधी कागदपत्रे जमवा — आधार कार्ड, ७/१२ उतारा, ८-अ उतारा, पासपोर्ट फोटो, आधार-लिंक बँक पासबुक, आणि लागू असल्यास जात प्रमाणपत्र. अर्ज mahadbt.maharashtra.gov.in वर.
- **Basis:** The application cannot proceed without the full document set, and assembling 7/12 and 8-A extracts takes time at the talathi office. Starting the assembly late compresses an already long chain.
- **Yield impact:** None. Protects the application timeline.
- **References:** govtyojanamaharashtra.com document list

**D10-APP-003** (APP, yellow, conf 0.8, tier B)

- **When:** Subsidised work complete AND geo_tagging_done is false
- **Action (EN):** Arrange geo-tagging verification. Payment is released by RTGS only after it, so an unverified completed installation earns nothing.
- **कृती (MR):** जिओ टॅगिंग तपासणी करून घ्या. ती झाल्यानंतरच RTGS ने अनुदान खात्यात जमा होते — तपासणीशिवाय पूर्ण झालेल्या कामाचे पैसे मिळत नाहीत.
- **Basis:** Geo-tagging is step seven of eight in the process. Skipping or delaying it leaves the farmer having spent the capital and completed the work with no reimbursement.
- **Yield impact:** None. Completes the subsidy chain.
- **References:** govtyojanamaharashtra.com process steps

**D10-FRESH-001** (FRESH, yellow, conf 0.85, tier B)

- **When:** Any advisory draws on Domain 10 data AND the domain review_by date has passed
- **Action (EN):** Append a verification note rather than presenting the figure as current. Subsidy rates, scheme eligibility and contacts change annually by government resolution.
- **कृती (MR):** आकडा चालू म्हणून दाखवण्याऐवजी तपासणीचा शेरा जोडा. अनुदानाचे दर, योजनांची पात्रता आणि संपर्क दरवर्षी शासन निर्णयाने बदलतात.
- **Basis:** This is the only domain whose content expires. Agronomy in Domains 1 to 9 holds for years; roughly half of this file is stale within twelve months. The engine has to know that about itself rather than treating all stored facts as equally durable.
- **Yield impact:** None. Prevents advice based on a lapsed scheme rate.
- **References:** Domain 10 data freshness policy

**D10-GEO-001** (GEO, yellow, conf 0.75, tier B)

- **When:** drought_prone_listed is unverified AND subsidy planning in progress
- **Action (EN):** Confirm with the Taluka Agriculture Officer whether Kannad appears on the 149 drought-prone taluka list. It is worth about 5 percentage points of subsidy and it is a single phone call.
- **कृती (MR):** कन्नड तालुका १४९ अवर्षणप्रवण तालुक्यांच्या यादीत आहे का, हे तालुका कृषी अधिकाऱ्याकडून निश्चित करा. त्यावर सुमारे ५ टक्के अनुदान अवलंबून आहे, आणि हे एका फोनवर कळेल.
- **Basis:** Marathwada is named a priority region, but the scheme operates on a specific list of 149 talukas. Priority region status and list membership are not the same thing.
- **Yield impact:** None. Affects the subsidy percentage on the largest capital item.
- **References:** govtyojanamaharashtra.com coverage

**D10-LAB-001** (LAB, yellow, conf 0.85, tier A)

- **When:** Soil test being arranged
- **Action (EN):** Request free lime, zinc and iron SEPARATELY. They are absent from the standard soil health card and they are precisely the parameters that drive the calcareous yellowing problem and the whole micronutrient schedule.
- **कृती (MR):** मुक्त चुनखडी, जस्त आणि लोह हे तीन घटक वेगळे मागा. नेहमीच्या मृदा आरोग्य पत्रिकेत ते नसतात — आणि तेच चुनखडीमुळे होणारा पिवळेपणा आणि संपूर्ण सूक्ष्म अन्नद्रव्य वेळापत्रक ठरवतात.
- **Basis:** The routine panel covers pH, EC, organic carbon and NPK. Free lime predicts whether the yellowing problem will occur; zinc and iron are the nutrients it locks up. Without them the Domain 4 micronutrient rules run on assumption.
- **Yield impact:** Enables correct micronutrient dosing, worth u = 0.11.
- **References:** Domain 2 soil test panel; Domain 4 micronutrient schedule

**D10-REG-001** (REG, yellow, conf 0.85, tier A)

- **When:** Any chemical recommendation is about to be emitted AND cibrc_list_checked_date is empty or stale
- **Action (EN):** Apply the standing behaviour: biological and cultural options first, name the molecule and group, state the source dose as reference only, defer the actual dose to the label, and append that CIB&RC label claim for ginger must be verified. Where the pre-harvest interval is unknown, block spraying within 30 days of harvest.
- **कृती (MR):** ठरलेले वर्तन पाळा — जैविक व सांस्कृतिक पर्याय प्रथम, रसायनाचे नाव व गट सांगा, स्रोतातील मात्रा फक्त संदर्भ म्हणून द्या, प्रत्यक्ष मात्रा लेबलनुसार, आणि अद्रकासाठी CIB&RC नोंदणी तपासण्याचा शेरा जोडा. प्रतीक्षा कालावधी माहीत नसल्यास काढणीपूर्वी ३० दिवस फवारणी अडवा.
- **Basis:** Ginger is a minor crop and many chemicals recommended in state extension literature lack a ginger-specific label claim. This is the largest remaining gap in the knowledge base and it affects four domains, but it is not blocking because biological and cultural options cover the main pests and diseases.
- **Yield impact:** Regulatory compliance rather than yield. Protects the platform and the farmer.
- **References:** CIB&RC minor crop position; Domains 1, 5, 6 and 8 chemical rules

**D10-REG-002** (REG, yellow, conf 0.72, tier B)

- **When:** New borewell or well deepening being considered AND cgwb_block_category is unverified
- **Action (EN):** Check the CGWB block classification for Kannad before planning new extraction. If the block is over-exploited, permission may be restricted and the farm pond becomes the only expansion route.
- **कृती (MR):** नवीन उपसा नियोजित करण्यापूर्वी कन्नड ब्लॉकचे भूजल वर्गीकरण तपासा. ब्लॉक अति-शोषित असल्यास परवानगी मिळणे अवघड होते आणि शेततळे हाच एकमेव विस्तार-पर्याय उरतो.
- **Basis:** October to February requires about 27 lakh litres per acre entirely from stored or pumped water. If the block classification restricts new extraction, the water plan must be built around storage instead, and that changes both the capital plan and the viable area.
- **Yield impact:** None directly. Determines whether the water plan is achievable at all.
- **References:** Domain 3 water budget; CGWB block classification framework

**D10-REG-003** (REG, yellow, conf 0.8, tier B)

- **When:** Malabar sulphur fumigation method being considered
- **Action (EN):** Verify the FSSAI and export SO2 residue limits for ginger before proceeding. Until they are confirmed, present simple sun drying as the route.
- **कृती (MR):** पुढे जाण्यापूर्वी अद्रकातील SO2 अवशेषांच्या FSSAI व निर्यात मर्यादा तपासा. त्या निश्चित होईपर्यंत साधी वाळवणी पद्धतच सुचवा.
- **Basis:** The method uses 6 to 10 g of sulphur per kg across three 12-hour fumigation cycles. Export markets impose strict SO2 limits and some buyers reject treated produce outright, so an unverified limit is a market access risk rather than a technical one.
- **Yield impact:** None. Protects market access on the dry ginger route.
- **References:** Domain 9 Malabar method; FSSAI residue framework

**D10-SUB-001** (SUB, yellow, conf 0.75, tier B)

- **When:** Pre-season planning AND has_drip is false AND subsidy_lottery_result is not_applied
- **Action (EN):** Start the drip subsidy application now. Combined central and state schemes give up to 80 percent for small and marginal farmers and 75 percent for others in this region. Apply at least six months before planting.
- **कृती (MR):** ठिबक अनुदानाचा अर्ज आत्ताच सुरू करा. केंद्र आणि राज्य योजना मिळून अल्प व अत्यल्प भूधारकांना ८०% पर्यंत आणि इतर शेतकऱ्यांना ७५% पर्यंत अनुदान मिळते. लागवडीच्या किमान सहा महिने आधी अर्ज करा.
- **Basis:** Domains 3 and 7 make drip a precondition rather than an option — the belt receives 725 to 775 mm against a crop requirement of 1320 to 1520 mm, and 55 percent of years fall below the average. The scheme covers 149 drought-prone talukas with priority to Marathwada, so the largest capital cost of the crop has an institutional answer available.
- **Yield impact:** Not a yield factor. It changes whether the crop is economically viable, by a factor of about five on the largest capital line.
- **References:** govtyojanamaharashtra.com Mukhyamantri Shashwat Krushi Sinchan Yojana; marathisheti.in PMKSY

**D10-SUB-003** (SUB, yellow, conf 0.85, tier B)

- **When:** Subsidy discussion in progress
- **Action (EN):** State clearly that selection is by lottery and never promise the subsidy. Present both the with-subsidy and without-subsidy cost cases. If not selected, the fallback is to reduce area rather than to skip drip.
- **कृती (MR):** निवड लॉटरी पद्धतीने होते हे स्पष्ट सांगा — अनुदान मिळेल असे आश्वासन कधीही देऊ नका. अनुदानासह आणि अनुदानाशिवाय अशी दोन्ही गणिते दाखवा. निवड झाली नाही तर ठिबक वगळण्याऐवजी क्षेत्र कमी करावे.
- **Basis:** Beneficiary selection is explicitly by lottery. A farmer who plans on receiving it and does not is left either without drip, which makes the crop unviable here, or with an unplanned capital cost.
- **Yield impact:** None directly. Prevents a plan built on an uncertain input.
- **References:** govtyojanamaharashtra.com lottery selection

**D10-SUB-004** (SUB, yellow, conf 0.75, tier B)

- **When:** Water availability assessed as marginal for October to February
- **Action (EN):** Recommend a lined farm pond, subsidised at 50 percent up to Rs 75,000. It stores the monsoon water that the drainage channels are already carrying away and supplies it back after October.
- **कृती (MR):** अस्तरीकरण केलेले शेततळे विचारात घ्या — ५०% किंवा ₹७५,००० पर्यंत अनुदान. मान्सूनमध्ये जे पाणी निचरा चरातून वाहून जाते तेच साठवून ऑक्टोबरनंतर वापरता येते.
- **Basis:** Two problems solve each other. Monsoon water must leave the root zone to prevent soft rot, and about 27 lakh litres per acre are needed from October to February when rainfall has ended. Storage converts the disposal problem into the supply.
- **Yield impact:** Reduces exposure to both the waterlogging pathway and the late-season exhaustion pathway.
- **References:** govtyojanamaharashtra.com farm pond lining; Domain 3 water budget; Domain 6 drainage requirement

### D11

**D11-AP-002** (AP, yellow, conf 0.8, tier B)

- **When:** Several advisories are due within the same few days
- **Action (EN):** Bundle them into one instruction list ordered by priority score. Do not issue separate notifications. The 75 to 90 DAP bundle alone protects u-values of 0.125, 0.175 and 0.200 in a single field visit.
- **कृती (MR):** त्या सर्व एका सूचना यादीत, प्राधान्य गुणानुसार क्रमाने द्या — वेगवेगळ्या सूचना पाठवू नका. ७५ ते ९० दिवसांचा गुच्छ एकाच फेरीत ०.१२५, ०.१७५ आणि ०.२०० ही तीन u मूल्ये संरक्षित करतो.
- **Basis:** The farmer visits the field once. Three separate notifications on three days produce three ignored notifications, and the accumulated u-value at stake in the earthing-up window is about half the season's controllable loss.
- **Yield impact:** Adherence is what converts a correct recommendation into a yield effect.
- **References:** Domain 8 operation bundling; Core C7.1

**D11-CL-001** (CL, yellow, conf 0.7, tier A)

- **When:** Ceiling is being set for a yield computation AND ceiling_basis is unverified
- **Action (EN):** Use the range 94 to 113 quintal per acre and mark it as unresolved. The published variety trial yields do not state which planting layout was used, so whether the broad ridge multiplier applies on top is unknown.
- **कृती (MR):** ९४ ते ११३ क्विंटल प्रति एकर ही श्रेणी वापरा आणि ती अनिश्चित असल्याचे नोंदवा. जातींचे प्रकाशित उत्पादन आकडे कोणत्या लागवड पद्धतीत घेतले होते हे स्रोतात नाही, म्हणून रुंद वरंब्याचा गुणक त्यावर लागू होतो का हे माहीत नाही.
- **Basis:** Mahima is rated at 23.2 tonnes per hectare, about 94 quintal per acre. Broad ridge is reported to give 15 to 20 percent more. If the trials already used broad ridge the multiplier is already included and the ceiling is 94; if not, it is 113.
- **Yield impact:** Every u-value computation and every economic scenario scales with this number.
- **References:** Agrowon variety yields; Agrowon broad ridge gain

**D11-EC-003** (EC, yellow, conf 0.8, tier B)

- **When:** An economic model is being built from yield factors alone
- **Action (EN):** Add the grading factor. A 2.7 times price spread on 90 quintal is about Rs 9 lakh, which exceeds every yield factor in the register including a full soft rot outbreak. A model built on yield alone misses the largest lever.
- **कृती (MR):** प्रतवारीचा घटक जोडा. ९० क्विंटलवर २.७ पट भाव फरक म्हणजे सुमारे ९ लाख रुपये — आणि तो या नोंदवहीतील प्रत्येक उत्पादन घटकापेक्षा मोठा आहे, कंदकुजीच्या पूर्ण प्रादुर्भावापेक्षाही. फक्त उत्पादनावर आधारित गणित सर्वात मोठा लीव्हर चुकवते.
- **Basis:** Soft rot at 0.70 costs about Rs 3.16 lakh at 113 quintal and Rs 4,000. The grading spread on a healthy 90 quintal crop is about Rs 9 lakh. Grade and yield are separate dimensions and both belong in the model.
- **Yield impact:** None on yield. Corrects the economic framing of the whole knowledge base.
- **References:** News18 Marathi grading spread; Domain 9 grading determinants

**D11-FM-002** (FM, yellow, conf 0.88, tier A)

- **When:** A source reports a percentage GAIN from a practice and it is being entered as a u-value
- **Action (EN):** Convert before entering. A gain of g corresponds to a loss of g divided by one plus g. A reported 20 percent gain is a u-value of 0.167, not 0.20.
- **कृती (MR):** नोंदवण्यापूर्वी रूपांतर करा. g टक्के फायदा म्हणजे g ÷ (१ + g) एवढी घट. २०% फायदा म्हणजे u = ०.१६७, ०.२० नाही.
- **Basis:** Sources usually report the benefit of doing something rather than the cost of not doing it. The two are not the same number, because the denominators differ.
- **Yield impact:** The error is small per factor and compounds across six or more, systematically overstating avoidable loss.
- **References:** Domain 11 conversion table

**D11-GA-001** (GA, yellow, conf 0.8, tier A)

- **When:** Harvest complete AND actual yield recorded
- **Action (EN):** Run the gap attribution. Start from the ceiling, apply the u-value of every recorded omission or event with grouping applied, compute the expected loss, compare against actual, and record the unexplained residual.
- **कृती (MR):** दरी-विश्लेषण चालवा. कमाल मर्यादेपासून सुरुवात करा, नोंदवलेल्या प्रत्येक चुकीचे किंवा घटनेचे u मूल्य गटबद्ध करून लावा, अपेक्षित घट काढा, प्रत्यक्ष उत्पादनाशी तुलना करा, आणि न समजलेला उर्वरित भाग नोंदवा.
- **Basis:** The residual is the informative part. A large unexplained gap means either a factor is missing from the register or a u-value is wrong, and both are findings worth having.
- **Yield impact:** None this season. It is the mechanism that turns estimates into measurements.
- **References:** Core C9.3; Domain 11 gap attribution method

**D11-GA-002** (GA, yellow, conf 0.82, tier A)

- **When:** Season beginning AND season_record_complete is false
- **Action (EN):** Set up the twelve required records at the start. Without them the gap attribution at harvest cannot run, and the whole season produces advice but no learning.
- **कृती (MR):** हंगामाच्या सुरुवातीलाच बारा आवश्यक नोंदी ठरवून घ्या. त्यांशिवाय काढणीच्या वेळी दरी-विश्लेषण चालवता येत नाही, आणि संपूर्ण हंगाम सल्ला देतो पण शिकवत काहीच नाही.
- **Basis:** Each required record maps to specific factors in the register. Missing records mean those factors cannot be attributed, and the residual absorbs them, which makes the residual uninformative.
- **Yield impact:** None directly. It is the precondition for the register ever improving.
- **References:** Domain 11 required records; Domain 12 minimum record set

**D11-PR-002** (PR, yellow, conf 0.78, tier B)

- **When:** Pre-harvest prediction requested AND sample_dig_180_done is false
- **Action (EN):** Use the wider interval of plus or minus 12 percent and say why. Explain that digging one plant would narrow it to about plus or minus 8 — a one third improvement in accuracy for the cost of one plant.
- **कृती (MR):** रुंद अंतराल ±१२% वापरा आणि कारण सांगा. एक रोप उकरून तपासल्यास ते ±८% पर्यंत घट्ट होते — एका रोपाच्या खर्चात अचूकता सुमारे एक तृतीयांश सुधारते.
- **Basis:** The yield organ is below ground and there is no non-destructive substitute. A partially infected crop stays green above ground while the rhizome is compromised, so surface appearance is systematically unreliable near harvest.
- **Yield impact:** None on yield. Changes forecast accuracy, which affects every marketing and storage decision built on it.
- **References:** Domain 1 destructive sampling rule; Domain 6 partial infection note

**D11-PR-003** (PR, yellow, conf 0.85, tier A)

- **When:** dap between 35 and 45 AND establishment_pct recorded
- **Action (EN):** Reset the ceiling to the establishment percentage. Ginger has no ratoon and gap filling produces plants that never catch up, so establishment is a hard ceiling for the season rather than a starting point.
- **कृती (MR):** कमाल मर्यादा उगवण टक्केवारीवर पुन्हा ठरवा. अद्रकात खोडवा नाही आणि नांगी भरलेली रोपे कधीच बरोबरीला येत नाहीत — म्हणून उगवण ही हंगामाची कमाल मर्यादा आहे, सुरुवात नाही.
- **Basis:** Establishment count is the first real measurement of the season and it caps everything downstream. A crop at 70 percent establishment cannot exceed 70 percent of its potential no matter how well it is managed afterwards.
- **Yield impact:** Directly proportional. It is the multiplier on every subsequent factor.
- **References:** Domain 1 establishment ceiling; Domain 8 gap filling assessment

**D11-RC-001** (RC, yellow, conf 0.85, tier A)

- **When:** dap equals 35 AND establishment_pct not recorded
- **Action (EN):** Request the establishment count now. It is the first real measurement of the season, it resets the ceiling, and it cannot be reconstructed later.
- **कृती (MR):** उगवणीची मोजणी आत्ताच करा. हंगामातील हे पहिले खरे मोजमाप आहे, ते कमाल मर्यादा पुन्हा ठरवते, आणि नंतर ते पुन्हा मोजता येत नाही.
- **Basis:** By 45 days emergence is complete and by 60 days the gaps have closed visually, so the count has a narrow window. It is also the input that converts a pre-season estimate into a grounded prediction.
- **Yield impact:** None directly. It is the multiplier on every other factor for the rest of the season.
- **References:** Domain 1 establishment ceiling; Domain 11 prediction staging

**D11-RC-002** (RC, yellow, conf 0.85, tier A)

- **When:** A saturation event or moisture stress period occurs
- **Action (EN):** Record it in hours or days with the stage it occurred in. These events carry the largest u-values in the register and they leave no trace afterwards unless recorded at the time.
- **कृती (MR):** ती घटना तासांत किंवा दिवसांत, कोणत्या अवस्थेत घडली यासह नोंदवा. या घटनांची u मूल्ये नोंदवहीतील सर्वात मोठी आहेत, आणि त्या वेळी नोंदवल्या नाहीत तर नंतर त्यांचा मागमूसही उरत नाही.
- **Basis:** Saturation at G2 or G3 carries 0.35, water exhaustion in G4 carries 0.30, and critical window stress carries 0.20. All three are sensor-detectable at the time and invisible afterwards, which makes them the events most likely to be lost from the attribution.
- **Yield impact:** None directly. Without these records the gap attribution attributes their loss to the residual.
- **References:** Domain 3 saturation rules; Domain 11 required records

**D11-SC-002** (SC, yellow, conf 0.78, tier A)

- **When:** Recorded omissions during the season are being turned into a revised expectation
- **Action (EN):** Recompute the expectation from the ceiling and the recorded factors, applying the grouping rules. Show which factors caused which part of the reduction.
- **कृती (MR):** कमाल मर्यादेपासून सुरुवात करून नोंदवलेल्या घटकांवरून अपेक्षा पुन्हा मोजा, गटबद्ध करण्याचे नियम पाळून. कोणत्या घटकामुळे किती घट झाली ते दाखवा.
- **Basis:** A revised expectation that shows its working is actionable in a way that a bare number is not. If earthing up was late and that accounts for 12.5 percent, the farmer learns something for next season even though this season cannot be recovered.
- **Yield impact:** None directly. Converts a recorded omission into transferable knowledge.
- **References:** Domain 11 gap attribution method

**D11-SC-003** (SC, yellow, conf 0.8, tier A)

- **When:** A disease event is recorded during the season
- **Action (EN):** Recompute immediately and show the economic consequence. Scenario D shows that a 60 percent rot event on otherwise good management leaves about 34 quintal, at which the net return is approximately zero.
- **कृती (MR):** लगेच पुन्हा गणित करा आणि आर्थिक परिणाम दाखवा. परिस्थिती D नुसार चांगल्या व्यवस्थापनावर ६०% कूज आल्यास सुमारे ३४ क्विंटल उरतात, आणि त्यावर निव्वळ परतावा जवळपास शून्य होतो.
- **Basis:** Soft rot has by far the largest u-value in the register and it can occur on a well-managed crop. Showing the arithmetic makes the case for the prevention stack concrete rather than theoretical.
- **Yield impact:** None directly. It informs the remaining decisions for the season, particularly harvest route and market strategy.
- **References:** Domain 11 scenario D; Domain 13 break-even

**D11-VL-002** (VL, yellow, conf 0.85, tier B)

- **When:** The validation result is being presented
- **Action (EN):** State the limitation alongside it. This is one validation point and it could be coincidence. Twenty-two of thirty-five u-values are estimates. Real validation comes from first-season gap attribution, not from this arithmetic.
- **कृती (MR):** सोबत मर्यादाही सांगा. ही एकच पडताळणी आहे आणि ती योगायोगही असू शकते. पस्तीसपैकी बावीस u मूल्ये अंदाजित आहेत. खरी पडताळणी पहिल्या हंगामाच्या दरी-विश्लेषणातून येईल, या गणितातून नाही.
- **Basis:** A single agreement between a computation and an observation is suggestive rather than conclusive. Overstating it would be the same error the knowledge base has avoided elsewhere — presenting an estimate as a measurement.
- **Yield impact:** None. Protects credibility at the point where it is most tempting to overclaim.
- **References:** Domain 11 register summary; Domain 11 validation caveat

### D12

**D12-AL-001** (AL, yellow, conf 0.82, tier B)

- **When:** A recommended action is not recorded within 3 days of its deadline
- **Action (EN):** Ask one question with fixed options — was it done, and if not what got in the way? Labour, time, cost, did not seem necessary, other.
- **कृती (MR):** एकच प्रश्न, ठराविक पर्यायांसह — काम झाले का, आणि नसेल तर काय अडचण आली? मजूर, वेळ, खर्च, गरज वाटली नाही, इतर.
- **Basis:** If the engine recommended something and it was not done, either the message failed or the recommendation was wrong for local conditions. Both are learnable. And implementation barriers are invisible to every sensor — a moisture probe cannot detect that labour was unavailable.
- **Yield impact:** None this season. It is the most valuable data the product collects.
- **References:** Core C12.3; Domain 8 overdue operation query

**D12-CLU-001** (CLU, yellow, conf 0.82, tier B)

- **When:** A cluster-level advisory is being issued
- **Action (EN):** Aggregate it. Say this area has raised disease pressure, never your neighbour's field has rot. Naming an affected farm breaches the consent basis.
- **कृती (MR):** अनामीकृत करा. 'या भागात रोगाचा दाब वाढला आहे' असे म्हणा, 'शेजारच्या शेतात कूज आहे' असे कधीही नाही. बाधित शेताचे नाव सांगणे संमतीच्या आधाराचे उल्लंघन आहे.
- **Basis:** Cluster learning is genuinely valuable — a neighbour warned before symptoms appear has a preventive window that would not otherwise exist. But that value has to be delivered without identifying the source farm.
- **Yield impact:** Extends the preventive window across the cluster while staying within the consent basis.
- **References:** Domain 6 cluster advisory; DPDP Act 2023

**D12-COLD-002** (COLD, yellow, conf 0.85, tier A)

- **When:** Any advisory is being displayed
- **Action (EN):** Show the confidence level. Where it is low, explain why in one line. Never hide low confidence and never present an estimated value as a measured one.
- **कृती (MR):** विश्वासार्हता पातळी दाखवा. कमी असल्यास एका ओळीत कारण सांगा. कमी विश्वासार्हता लपवू नका, आणि अंदाजित मूल्य मोजलेले म्हणून दाखवू नका.
- **Basis:** Twenty-two of thirty-five u-values are estimates and several key inputs are unmeasured. Presenting everything with equal confidence would misrepresent the basis of the advice and would fail the first time a confident recommendation turned out wrong.
- **Yield impact:** None. Determines whether the advisory is trusted after the first mistake.
- **References:** Domain 11 source class policy; Domain 12 confidence display

**D12-COLD-003** (COLD, yellow, conf 0.82, tier A)

- **When:** A VERIFY-class rule is used in production advisory
- **Action (EN):** Flag it in the advisory and queue it for verification. VERIFY class means the value must be confirmed with a named institution before it is relied on, and using it without saying so misrepresents its basis.
- **कृती (MR):** सल्ल्यात ते स्पष्ट करा आणि तपासणीसाठी रांगेत ठेवा. VERIFY वर्ग म्हणजे संबंधित संस्थेकडून पुष्टी झाल्याशिवाय त्यावर अवलंबून राहू नये — आणि तसे न सांगता वापरणे त्याचा आधार चुकीचा दाखवते.
- **Basis:** VERIFY-class items include the CIB&RC label claims, the SO2 residue limits, the drought-prone taluka listing and the yield ceiling question. Each is used in advisory but none is confirmed, and the distinction between an unconfirmed value and a confirmed one matters most where a chemical or a subsidy is involved.
- **Yield impact:** None. Keeps the stated basis of the advice accurate.
- **References:** Domain 1 source class definitions; Domain 10 VERIFY items

**D12-DPDP-004** (DPDP, yellow, conf 0.8, tier A)

- **When:** A farmer requests deletion of their data
- **Action (EN):** Delete on request, including from any downstream copies. Note that this removes the plot's field history, which is a first-class input to disease rules — tell the farmer that consequence before deleting.
- **कृती (MR):** विनंतीनुसार माहिती हटवा, पुढील प्रतींसह. यामुळे त्या प्लॉटचा रोग-इतिहास नष्ट होतो, आणि तो रोग नियमांचा प्राथमिक आधार आहे — हटवण्यापूर्वी हा परिणाम शेतकऱ्याला सांगा.
- **Basis:** The right to erasure is a legal requirement. But the field disease history is the input that the bacterial wilt rule depends on, and the bacterium persists in soil for many years, so the farmer should understand what is being lost.
- **Yield impact:** Removes an input that Domain 6 rules rely on in later seasons.
- **References:** DPDP Act 2023 right to erasure; Domain 6 field history rule

**D12-IMG-001** (IMG, yellow, conf 0.8, tier B)

- **When:** Season 1 or 2 AND a farmer submits a photograph
- **Action (EN):** Store it and have an expert label it. Do not attempt automatic classification. Photographs cannot be collected retrospectively, so collection must begin before any model exists.
- **कृती (MR):** फोटो साठवा आणि तज्ज्ञाकडून लेबल लावून घ्या. आपोआप वर्गीकरणाचा प्रयत्न करू नका. फोटो मागे जाऊन जमवता येत नाहीत — म्हणून मॉडेल नसतानाही जमवायला आत्ताच सुरुवात करावी लागते.
- **Basis:** No public labelled image set exists for any of the eight candidate markers. Each class needs hundreds of images and they only appear when the condition actually occurs, so collection is opportunistic and slow.
- **Yield impact:** None this season. It is the precondition for image recognition ever working.
- **References:** Domain 12 image data reality

**D12-LANG-002** (LANG, yellow, conf 0.8, tier B)

- **When:** A farmer-facing message is being composed
- **Action (EN):** Use the four-part structure: what to do in one sentence starting with a verb, when with an exact date or deadline, why in one sentence, and what happens if not — with a number wherever one exists.
- **कृती (MR):** चार भागांची रचना वापरा — काय करायचे (क्रियापदाने सुरू, एक वाक्य), कधी (नेमकी तारीख किंवा मुदत), का (एक वाक्य), आणि न केल्यास काय (आकडा उपलब्ध असेल तिथे आकड्यासह).
- **Basis:** The fourth part is what creates urgency. Do earthing up is ignorable; do earthing up or lose 10 to 15 percent of the crop is not. Twenty of the thirty-five register factors have a number available.
- **Yield impact:** Affects compliance, which is the metric that converts correct advice into yield.
- **References:** Domain 12 message structure

**D12-LOG-002** (LOG, yellow, conf 0.82, tier A)

- **When:** A durable fact is learned during a conversation or a field visit
- **Action (EN):** Record it against the plot at the time. Class B action records and class C observation records are manual and are the ones most often lost, and together they cover most of the register.
- **कृती (MR):** ती त्याच वेळी प्लॉटविरुद्ध नोंदवा. कृती-नोंदी आणि निरीक्षण-नोंदी या हाताने कराव्या लागतात आणि त्याच सर्वात जास्त वेळा हरवतात — आणि त्या दोन मिळून नोंदवहीचा बहुतांश भाग व्यापतात.
- **Basis:** Machine records log themselves. Action and observation records depend on someone entering them, and they cover the operations that carry u-values of 0.125 to 0.20 each.
- **Yield impact:** None directly. It is the majority of the gap attribution input.
- **References:** Domain 12 logging classes; Domain 11 record detectability

**D12-LOG-004** (LOG, yellow, conf 0.75, tier B)

- **When:** A light trap is installed AND nightly counts are not being recorded
- **Action (EN):** Record the nightly catch by hand from season one. The count is a direct measure of pest pressure and is currently discarded. Aggregated across a cluster it would produce a local pest pressure map, and it cannot be collected retrospectively.
- **कृती (MR):** पहिल्या हंगामापासून रोजची संख्या हाताने नोंदवा. ती संख्या कीड-दाबाचे थेट माप आहे आणि सध्या ती फेकून दिली जाते. cluster मध्ये एकत्र केल्यास स्थानिक कीड-दाब नकाशा तयार होईल — आणि ही माहिती मागे जाऊन जमवता येत नाही.
- **Basis:** The light trap is already a recommended practice for shoot borer, so the farmer will accept it. Adding a counter to the sub-node later would automate it, but the manual record is what makes the first two seasons of data exist at all.
- **Yield impact:** None directly. Builds a local dataset that exists nowhere else.
- **References:** Domain 5 light trap product opportunity; Core C10.5 capability gap register

**D12-VOC-002** (VOC, yellow, conf 0.7, tier B)

- **When:** Local terminology differs from standard Marathi
- **Action (EN):** Record the local variant alongside the standard term. The farmer uses the local word, so that is what must be recognised. Whether bharani and utalni are the same operation still needs confirming.
- **कृती (MR):** प्रमाण संज्ञेसोबत स्थानिक शब्दही नोंदवा. शेतकरी स्थानिक शब्द वापरतो, म्हणून तोच ओळखता आला पाहिजे. 'भरणी' आणि 'उटाळणी' एकच काम आहे का, हे अजून निश्चित करायचे आहे.
- **Basis:** Standard Marathi and Kannad usage may differ, and the system has to match what is actually said rather than what is written in a bulletin. The bharani and utalni question is a live ambiguity in the sources.
- **Yield impact:** Affects recording accuracy on the largest manual-record factors.
- **References:** Domain 12 controlled vocabulary structure

### D13

**D13-AD-003** (AD, yellow, conf 0.82, tier B)

- **When:** Harvest complete
- **Action (EN):** Record actual cost line by line — seed, land preparation, mulch, fertiliser, plant protection, labour, harvest and transport. Several figures in this model are estimates and only recorded actuals correct them.
- **कृती (MR):** प्रत्यक्ष खर्च बाबनिहाय नोंदवा — बेणे, पूर्वमशागत, आच्छादन, खते, कीड-रोग नियंत्रण, मजुरी, काढणी आणि वाहतूक. या गणितातील अनेक आकडे अंदाजित आहेत आणि फक्त प्रत्यक्ष नोंदीच ते दुरुस्त करतात.
- **Basis:** The Kannad adjusted figure of about Rs 1,45,000 adds three lines to a published sheet and raises three others, all on reasoning rather than measurement. Transport cost and labour days in particular are unmeasured.
- **Yield impact:** None. Corrects the economic model for subsequent seasons.
- **References:** Domain 9 cost recording rule; Domain 12 minimum records

**D13-BE-002** (BE, yellow, conf 0.82, tier B)

- **When:** Break-even figures are being presented
- **Action (EN):** State what is excluded — land rent or opportunity cost, own labour valued, interest on capital, and the drip capital share where unsubsidised. Including these raises the break-even. The figure is a floor, not a full economic cost.
- **कृती (MR):** काय वगळले आहे ते सांगा — जमिनीचे भाडे किंवा संधी-खर्च, स्वतःच्या मजुरीचे मूल्य, भांडवलावरील व्याज, आणि अनुदान न मिळाल्यास ठिबकाचा भांडवली हिस्सा. हे धरल्यास समतोल बिंदू वर सरकतो. हा आकडा तळ आहे, पूर्ण आर्थिक खर्च नाही.
- **Basis:** A break-even that omits land, labour and capital is a cash break-even rather than an economic one. Presenting it without the caveat overstates the safety margin.
- **Yield impact:** None. Keeps the stated margin honest.
- **References:** Domain 13 excluded items

**D13-CF-001** (CF, yellow, conf 0.8, tier B)

- **When:** Pre-season planning AND cash flow has not been discussed
- **Action (EN):** Show the timeline. About Rs 1.45 lakh goes out over eight months with no income until the end, and about half of it is spent before the crop emerges. This is ginger's largest practical challenge here, and it is financial rather than agronomic.
- **कृती (MR):** कालरेषा दाखवा. सुमारे १.४५ लाख रुपये आठ महिन्यांत बाहेर जातात आणि शेवटपर्यंत उत्पन्न शून्य — आणि त्यातील सुमारे निम्मा खर्च पीक उगवण्यापूर्वीच होतो. Kannad मध्ये अद्रकाचे हे सर्वात मोठे व्यावहारिक आव्हान आहे, आणि ते कृषिशास्त्रीय नाही, आर्थिक आहे.
- **Basis:** Rs 73,000 of Rs 1,45,000 is spent by day zero and 44 percent falls in the week around planting, driven by the seed purchase. Revenue arrives at about day 235.
- **Yield impact:** None. Determines whether the farmer can complete the season without distress selling or borrowing badly.
- **References:** Domain 13 cash flow timeline

**D13-CP-001** (CP, yellow, conf 0.8, tier B)

- **When:** Economic model being run AND drip_capital_cost is unknown
- **Action (EN):** Obtain a supplier quotation before completing the model. Drip capital cost is the largest missing figure in this domain and neither the with-subsidy nor the without-subsidy case can be closed without it.
- **कृती (MR):** गणित पूर्ण करण्यापूर्वी पुरवठादाराकडून कोटेशन घ्या. ठिबकाचा भांडवली खर्च हा या Domain मधील सर्वात मोठा गहाळ आकडा आहे — तो नसेल तर अनुदानासह किंवा अनुदानाशिवाय कोणतेही गणित पूर्ण होत नाही.
- **Basis:** Drip is a precondition, so the cost is incurred regardless. Subsidy at 75 to 80 percent changes who bears it, and because selection is by lottery both cases must be modelled. Without the base figure neither can be.
- **Yield impact:** None. Determines whether the enterprise is viable and at what area.
- **References:** Domain 3 drip precondition; Domain 10 subsidy rates

**D13-CS-001** (CS, yellow, conf 0.75, tier C)

- **When:** A cost estimate is being prepared for a Kannad plot
- **Action (EN):** Use about Rs 1,45,000 per acre, not the published Rs 1,15,000. The standard sheet omits mulch, drainage channels and micronutrient sprays, which together are about Rs 22,500 and are all required here.
- **कृती (MR):** एकरी सुमारे १,४५,००० रुपये धरा, प्रकाशित १,१५,००० नव्हे. प्रमाणित ताळेबंदात आच्छादन, निचरा चर आणि सूक्ष्म अन्नद्रव्य फवारणी या तीन बाबी नाहीत — त्या मिळून सुमारे २२,५०० रुपये आहेत आणि इथे तिन्ही आवश्यक आहेत.
- **Basis:** Mulch is required by Domains 3, 6 and 7 and carries the best-quantified preventive value in the knowledge base. Drainage channels are a precondition on vertisol. Micronutrient sprays are needed because free lime locks up zinc and iron. None appears in the published sheet.
- **Yield impact:** None directly. An understated budget leads to items being dropped mid-season, and the dropped items are usually the ones that were not budgeted.
- **References:** Shetkari Marg cost breakdown; Domains 2, 3, 4, 6 and 7 requirements

**D13-MI-002** (MI, yellow, conf 0.75, tier B)

- **When:** Budget being finalised AND drainage or micronutrient provision is absent
- **Action (EN):** Add about Rs 4,000 for drainage channels and Rs 3,500 for two micronutrient sprays. Both are preconditions here rather than enhancements.
- **कृती (MR):** निचरा चरांसाठी सुमारे ४,००० आणि सूक्ष्म अन्नद्रव्यांच्या दोन फवारण्यांसाठी ३,५०० रुपयांची तरतूद करा. इथे या दोन्ही सुधारणा नाहीत, पूर्वअटी आहेत.
- **Basis:** Three drainage levels are required before planting on vertisol, and the third — the outlet channel — is the one most often omitted. Micronutrient sprays are needed because free lime locks up zinc and iron, and foliar delivery beat soil application by 12.5 percent in trial.
- **Yield impact:** Drainage carries u = 0.22 and micronutrients u = 0.11.
- **References:** Domain 2 drainage levels; Domain 4 micronutrient schedule

**D13-RV-002** (RV, yellow, conf 0.8, tier B)

- **When:** Area decision being made AND current prices are high
- **Action (EN):** Run the calculation at a crashed price before committing area. Ginger is strongly cyclical — high price, everyone plants, arrivals rise, price collapses. Ask directly whether the costs are covered at about Rs 6,000 per quintal.
- **कृती (MR):** क्षेत्र निश्चित करण्यापूर्वी कोसळलेल्या भावावर गणित चालवा. अद्रक तीव्र चक्रीय पीक आहे — भाव चांगला, सगळे लावतात, आवक वाढते, भाव कोसळतो. सुमारे ६,००० रुपये प्रति क्विंटल भावात खर्च निघतो का, हा प्रश्न स्पष्ट विचारा.
- **Basis:** The cycle is severe in ginger because it is an eight month crop so the response is slow, the seed cost is large so the decision is made once, and the market is thin at about one percent of onion arrivals so a modest increase moves the price a long way.
- **Yield impact:** None. Prevents over-planting on a price that will not survive the season.
- **References:** Domain 9 price cyclicality; News18 Marathi bullish market description

**D13-RV-003** (RV, yellow, conf 0.8, tier B)

- **When:** Revenue is being estimated from yield alone
- **Action (EN):** Include the grade dimension. A 2.7 times price spread was recorded within one market on one day. On 90 quintal that is about Rs 9 lakh, which exceeds every yield factor in the knowledge base.
- **कृती (MR):** प्रतवारीचा घटक जोडा. एकाच बाजारात, एकाच दिवशी २.७ पट भाव फरक नोंदवला गेला आहे. ९० क्विंटलवर तो सुमारे ९ लाख रुपये होतो — आणि तो या knowledge base मधील प्रत्येक उत्पादन घटकापेक्षा मोठा आहे.
- **Basis:** Grade and yield are separate dimensions. The two grading determinants that remain controllable at harvest — skin condition from water withdrawal, and cleanliness and uniformity from washing and sorting — are both labour-only.
- **Yield impact:** None on yield. It is the largest single economic lever in the crop.
- **References:** News18 Marathi grading spread; Domain 9 grading determinants; Domain 11 economic conversion

**D13-SD-004** (SD, yellow, conf 0.78, tier B)

- **When:** Market price is high in the season before planting
- **Action (EN):** Warn that seed cost will rise with it. Seed is selected from marketable rhizome and is priced off the produce market, so a high-price year is followed by a high-cost season.
- **कृती (MR):** बेण्याचा खर्चही तेवढाच वाढेल हे लक्षात घ्या. बेणे बाजारातील विक्रीयोग्य आल्यातूनच निवडले जाते आणि त्याचा भाव उत्पादनाच्या भावावरून ठरतो — म्हणून चांगल्या भावाच्या वर्षानंतरचा हंगाम महाग असतो.
- **Basis:** The derived seed price of about Rs 47 per kg is close to the produce price, which is expected because the same rhizome can go to either use. So the largest cost line tracks the market the grower is hoping to sell into.
- **Yield impact:** None. Explains part of the mechanism behind the price cycle.
- **References:** Domain 13 seed price relationship; Core C13.4

**D13-SL-001** (SL, yellow, conf 0.78, tier C)

- **When:** Seed is being retained and stored
- **Action (EN):** Warn that 28 to 40 percent of the weight will be lost by planting. To have 850 kg at planting, store about 1,308 kg. That extra 458 kg is worth about Rs 21,500 — over half the seed cost again, paid in kind rather than cash.
- **कृती (MR):** साठवणीत वजन २८ ते ४०% घटते. लागवडीच्या वेळी ८५० किलो हवे असल्यास आत्ता सुमारे १,३०८ किलो साठवावे लागेल. ते अतिरिक्त ४५८ किलो म्हणजे सुमारे २१,५०० रुपये — बेण्याच्या खर्चाच्या निम्म्याहून जास्त, आणि तो रोखीत नव्हे तर मालाच्या रूपात जातो.
- **Basis:** The source states 25 quintal per hectare is needed at planting but the stored weight falls to 15 to 18 quintal. A separate statement gives 25 to 30 percent for simple shade storage, so the range is internally consistent.
- **Yield impact:** None on yield. It is a cost of about half the seed line again that appears in no cost sheet.
- **References:** AgroWorld seed storage; Domain 8 storage rule

**D13-SL-003** (SL, yellow, conf 0.85, tier B)

- **When:** Seed is put into storage
- **Action (EN):** Weigh it now and weigh it again at planting. Two numbers settle the storage loss for this plot, and the figure feeds directly into the retain-versus-purchase decision every season after.
- **कृती (MR):** आत्ता वजन करा आणि लागवडीच्या वेळी पुन्हा करा. दोनच आकडे या शेतासाठी साठवण घट निश्चित करतात, आणि तो आकडा पुढील प्रत्येक हंगामात 'राखावे की विकत घ्यावे' या निर्णयात थेट वापरला जातो.
- **Basis:** The published range of 28 to 40 percent is wide, and the difference between the two ends is about Rs 10,000 per acre. Only measurement narrows it, and it costs a set of scales and two entries.
- **Yield impact:** None. Converts a wide assumption into a measured figure.
- **References:** Domain 13 storage loss measurement; Domain 12 minimum records

### D01

**D01-HV-003** (HV, info, conf 0.8, tier B)

- **When:** dap greater than or equal to 180
- **Action (EN):** Present the four harvest routes with their trade-offs. Do NOT recommend one. This is an economic decision and belongs to Domains 9 and 13.
- **कृती (MR):** चार पर्याय मांडा — लवकर हिरवे (१८० दिवस), पूर्ण पक्व हिरवे (२३० दिवस), सुंठ करून लगेच विक्री, किंवा सुंठ करून साठवणे. हा आर्थिक निर्णय आहे, कृषिशास्त्रीय नाही.
- **Basis:** Green ginger can be harvested from about six months; full maturity for processing needs eight. A crop that is 75 percent mature is still marketable.
- **Yield impact:** Route choice affects weight, dry recovery, storability and realised price, not yield potential.
- **References:** AgroWorld; Agrowon; Tractorkarvan

**D01-PH-008** (PH, info, conf 0.9, tier A)

- **When:** current_stage is G1, G3 or G4
- **Action (EN):** Flag critical irrigation window to Domain 3. Tighten moisture tolerance band, raise sensor sampling frequency, and escalate advisory severity by one level.
- **कृती (MR):** ही निर्णायक सिंचन अवस्था आहे. ओलाव्याची सहन-मर्यादा घट्ट करा, sensor वाचन वाढवा, आणि इशाऱ्याची तीव्रता एक पातळी वर न्या.
- **Basis:** Published irrigation guidance names germination, rhizome initiation and rhizome development as the critical stages. This matches the criticality ranking derived independently from crop physiology.
- **Yield impact:** Moisture stress in G3 prevents finger differentiation and is irrecoverable. u = 0.15 to 0.25.
- **References:** ICL Growing Solutions ginger crop nutrition; Agrowon drip article

**D01-YD-001** (YD, info, conf 0.8, tier A)

- **When:** Pre-season planning initiated
- **Action (EN):** Present the yield target as a RANGE with three levels: minimum viable 60, target 90, stretch 110 quintal per acre. Never present a single number.
- **कृती (MR):** उत्पादन लक्ष्य श्रेणीत मांडा — किमान ६०, लक्ष्य ९०, ताणून ११० क्विंटल प्रति एकर. मराठवाड्याच्या काळ्या जमिनीत ११० क्विंटल मिळवणे हे राज्य सरासरीच्या (५३) दुपटीहून जास्त आहे.
- **Basis:** Genetic capacity of the best variety is 94 q/acre; broad ridge adds up to 20 percent. The stated range spans realistic to excellent under Kannad conditions.
- **Yield impact:** Sets the denominator for every dose calculation in Domains 3 and 4.
- **References:** Agrowon variety data; Directorate of Agriculture Maharashtra state average

### D02

**D02-LY-003** (LY, info, conf 0.7, tier A)

- **When:** Bed forming scheduled AND area_acre greater than 1
- **Action (EN):** Arrange a tractor-drawn bed former before land preparation reaches the bed stage. Hand-forming beds is not practical beyond a small area and the machine setting for 60/60 geometry must be arranged with the operator in advance.
- **कृती (MR):** मोठ्या क्षेत्रावर हाताने वाफे बांधणे व्यवहार्य नाही. ट्रॅक्टरचे सरी यंत्र आधीच ठरवा, आणि ६०/६० रचनेसाठी यंत्राची मांडणी चालकाशी बोलून निश्चित करा.
- **Basis:** Bed geometry determines drainage, plant population and drip layout. If the machine cannot be set correctly the whole layout decision fails at execution.
- **Yield impact:** Indirect. Protects the 0.167 u-value from being lost at implementation.
- **References:** Agrowon - onion bed forming machinery method

**D02-OM-004** (OM, info, conf 0.75, tier B)

- **When:** soil_oc_pct less than 0.75
- **Action (EN):** Inform that organic carbon is below target and that raising it is a three to four season programme, not a single-season fix. FYM, neem cake and mulch all contribute.
- **कृती (MR):** सेंद्रिय कर्ब लक्ष्यापेक्षा कमी आहे. तो एका हंगामात वाढत नाही — शेणखत, निंबोळी पेंड आणि आच्छादन यांतून तीन-चार हंगामांत वाढतो. ही तूट भरून काढणे हे दीर्घकालीन काम आहे.
- **Basis:** Target is above 1 percent; Marathwada black soil typically runs 0.3 to 0.5 percent. Organic carbon governs water holding, microbial activity and micronutrient availability, all of which matter more in calcareous heavy soil.
- **Yield impact:** Not directly quantified. Acts through drainage, nutrient availability and disease suppression.
- **References:** Agrowon - Bitle & Deshmukh 1 percent OC target; Domain 4

### D03

**D03-SB-003** (SB, info, conf 0.75, tier B)

- **When:** Stage changes
- **Action (EN):** Adjust sampling frequency: hourly in G1, G3 and G4, four-hourly in G2 and G5, daily in G0, and hourly at all stages during a rain alert.
- **कृती (MR):** अवस्थेनुसार sensor वाचनाची वारंवारता बदला — G1, G3, G4 मध्ये तासाला एकदा; G2 आणि G5 मध्ये चार तासांनी; पावसाच्या इशाऱ्यादरम्यान सर्व अवस्थांत तासाला.
- **Basis:** Sampling frequency should scale with stage criticality and with the rate at which the risk can develop. Saturation damage accrues over hours, so hourly sampling is needed when the crop is sensitive.
- **Yield impact:** Indirect. Affects how early a saturation event is detected.
- **References:** Core C6.2; Domain 3 sensor binding

**D03-SB-004** (SB, info, conf 0.7, tier B)

- **When:** Hardware upgrade under consideration
- **Action (EN):** Record the three-depth measurement requirement in the capability gap register: 10 cm for the rhizome zone, 20 cm for root base stress, 30 cm for drainage. One point at 10 cm is adequate for season one.
- **कृती (MR):** तीन खोलींवर मोजमाप हवे — १० सेंमी गड्डा क्षेत्र, २० सेंमी मुळांचा तळ, ३० सेंमी निचरा. पहिल्या हंगामासाठी १० सेंमीचा एक बिंदू पुरेसा.
- **Basis:** A reading at 30 cm showing saturation while 10 cm does not indicates water rising from below, meaning drainage is blocked. That is detectable before anything is visible at the surface.
- **Yield impact:** Would improve early detection of the largest loss pathway.
- **References:** Core C10.5 capability gap register

### D04

**D04-MC-003** (MC, info, conf 0.8, tier A)

- **When:** soil_zn_ppm below sufficiency
- **Action (EN):** Apply basal zinc sulphate at about 12 kg per acre in addition to, not instead of, the foliar sprays.
- **कृती (MR):** जमिनीतून झिंक सल्फेट एकरी सुमारे १२ किलो द्या — पण हे फवारणीच्या ऐवजी नव्हे, त्याच्या जोडीला.
- **Basis:** Basal zinc at 6 kg Zn per hectare gives good response where soil is deficient, but on calcareous soil a substantial fraction is fixed. Soil application builds the base; foliar delivers the crop's requirement.
- **Yield impact:** Supports the foliar programme rather than replacing it.
- **References:** Nutrition of Zingiberaceae Crops - basal zinc; PubMed PMC8381012 combined NPK plus micro formula

**D04-NP-003** (NP, info, conf 0.72, tier A)

- **When:** variety is mahima AND dose being set
- **Action (EN):** Consider the variety-specific trial figure of about 51 kg N, 20 kg P and 40 kg K per acre, which was found most effective for this cultivar.
- **कृती (MR):** महिमा जातीसाठी प्रयोगात एकरी सुमारे ५१ किलो नत्र, २० किलो स्फुरद आणि ४० किलो पालाश ही मात्रा सर्वाधिक प्रभावी आढळली — म्हणजे स्फुरद कमी, पालाश जास्त.
- **Basis:** A 2025 trial on cv. IISR Mahima found 125:50:100 kg per hectare most effective for both vegetative growth and yield. The direction — less phosphorus, more potassium — also suits calcareous soil where phosphorus is fixed.
- **Yield impact:** Directionally supported by a variety-matched trial, which is rare.
- **References:** International Journal of Advanced Biochemistry Research 2025

**D04-NU-001** (NU, info, conf 0.85, tier A)

- **When:** Nutrient planning initiated
- **Action (EN):** Set potassium, not nitrogen, as the governing nutrient. Measured uptake is about 59 kg K per acre against 49 kg N and 17 kg P.
- **कृती (MR):** पालाश हेच अद्रकाचे प्रमुख अन्नद्रव्य आहे, नत्र नाही. प्रत्यक्ष उचल एकरी सुमारे ५९ किलो पालाश, ४९ किलो नत्र आणि १७ किलो स्फुरद अशी मोजली गेली आहे.
- **Basis:** Potassium uptake exceeds nitrogen uptake in measured data, and potassium leaves the field inside the harvested rhizome while most nitrogen remains in foliage that returns to the soil. So potassium is both the largest uptake and the largest net export.
- **Yield impact:** Sets the priority order for the whole domain. Under-replacement of potassium is the most common and most correctable nutritional error in this crop.
- **References:** SciELO Inceptisol uptake study; IntechOpen INM chapter

**D04-OR-002** (OR, info, conf 0.65, tier A)

- **When:** Nutrient planning AND organic sources available
- **Action (EN):** Consider partial substitution of inorganic nitrogen with organic sources. A combination of neem cake, poultry manure and groundnut cake with inorganic nitrogen produced yields up to about 117 quintal per acre in trials.
- **कृती (MR):** अकार्बनिक नत्राचा काही भाग सेंद्रिय स्रोतांतून बदलण्याचा विचार करा — निंबोळी पेंड, कोंबडीखत आणि भुईमूग पेंड यांच्या संयोजनात प्रयोगात जास्त उत्पादन नोंदवले गेले आहे.
- **Basis:** Integrated nutrient management combining organic and inorganic sources outperformed inorganic alone, reaching about 29 tonnes per hectare, which exceeds the best variety's rated genetic capacity of 23.2 tonnes per hectare.
- **Yield impact:** Directionally positive. The trial was in a different climate, so the magnitude should not be transferred.
- **References:** Nutrition of Zingiberaceae Crops - INM combinations

**D04-OR-003** (OR, info, conf 0.75, tier A)

- **When:** soil_oc_pct below 1.0
- **Action (EN):** Set the expectation that raising organic carbon is a three to four season programme. FYM, neem cake and mulch all contribute, and none of them will show the target in one season.
- **कृती (MR):** सेंद्रिय कर्ब एका हंगामात वाढत नाही. शेणखत, निंबोळी पेंड आणि आच्छादन यांतून तो तीन-चार हंगामांत वाढतो. ही तूट भरून काढणे दीर्घकालीन काम आहे.
- **Basis:** Target is above 1 percent; black soil in this region typically runs 0.3 to 0.5 percent. Organic carbon governs water holding, microbial activity and micronutrient availability, all of which matter more in calcareous heavy soil.
- **Yield impact:** Indirect and cumulative.
- **References:** Agrowon - Bitle & Deshmukh soil targets; Domain 2

**D04-SN-001** (SN, info, conf 0.75, tier A)

- **When:** Basal application being planned
- **Action (EN):** Include magnesium sulphate about 25 kg per acre at basal, and continue about 2.4 kg per acre weekly through fertigation where drip is used.
- **कृती (MR):** पायाभूत मात्रेत मॅग्नेशिअम सल्फेट एकरी सुमारे २५ किलो द्या, आणि ठिबक असल्यास आठवड्याला सुमारे २.४ किलो चालू ठेवा.
- **Basis:** Calcium, magnesium and sulphur are all taken up in larger quantities than phosphorus, yet receive far less attention. SSP already supplies sulphur and calcium as a side benefit.
- **Yield impact:** Not separately quantified.
- **References:** Agrowon fertigation basal; SciELO uptake order

### D05

**D05-IP-001** (IP, info, conf 0.85, tier A)

- **When:** Any pest control recommendation about to be issued
- **Action (EN):** Present options in order: cultural, mechanical, biological, chemical. Do not surface a chemical option without recording why the preceding tiers are insufficient.
- **कृती (MR):** उपाय याच क्रमाने द्या — सांस्कृतिक, यांत्रिक, जैविक, मग रासायनिक. आधीचे टप्पे का अपुरे आहेत हे नोंदवल्याशिवाय रासायनिक पर्याय दाखवू नये.
- **Basis:** This ordering is what makes the output defensible as integrated pest management rather than a spray calendar. It also preserves natural enemies, whose loss makes later outbreaks worse.
- **Yield impact:** Indirect. Reduces input cost and resistance development.
- **References:** Core C5.2; Agrowon - Mali & Mahajan control ordering

**D05-IP-002** (IP, info, conf 0.85, tier A)

- **When:** Pre-season planning
- **Action (EN):** Issue the free-measure checklist: plant by 7 June, choose Mahima, use fully decomposed FYM, maintain three year rotation, do summer deep ploughing and solarization, and avoid rhizome injury during operations.
- **कृती (MR):** मोफत उपायांची यादी — ७ जूनपर्यंत लागवड, महिमा जात, पूर्ण कुजलेले शेणखत, तीन वर्षांची फेरपालट, उन्हाळी खोल नांगरट व सौरीकरण, आणि मशागतीत गड्ड्याला इजा टाळणे.
- **Basis:** All six are decisions rather than purchases, and all are taken before or at planting.
- **Yield impact:** Collectively these address the majority of pest exposure in the crop at effectively zero input cost.
- **References:** Domain 5 IPM ladder; Agrowon - Dr. Kadam; Agrowon - Mali & Mahajan

**D05-NE-003** (NE, info, conf 0.78, tier B)

- **When:** Earthing up scheduled AND nematode_suspected is true
- **Action (EN):** Raise neem cake at earthing up toward 8 quintal per acre instead of the routine 300 to 400 kg. The dose is condition dependent and must not be held fixed.
- **कृती (MR):** सूत्रकृमींचा प्रादुर्भाव असल्यास उटाळणीच्या वेळी निंबोळी पेंडीची मात्रा एकरी ८ क्विंटलपर्यंत वाढवा. एरवी ३०० ते ४०० किलो पुरेसे.
- **Basis:** Neem cake at 8 quintal per acre at earthing up is the recommended nematode measure, while 300 to 400 kg per acre is the general nutrition rate. Same input, different dose, different purpose.
- **Yield impact:** Reduces the 0.15 nematode value.
- **References:** Krishi app blog; Domain 4 neem cake programme

**D05-NE-004** (NE, info, conf 0.85, tier A)

- **When:** Variety being selected
- **Action (EN):** Prefer Mahima on nematode resistance grounds alone, independent of its yield advantage.
- **कृती (MR):** महिमा जात सूत्रकृमी प्रतिकारक आहे — आणि हा फायदा फुकट आहे, फक्त योग्य बेणे निवडून.
- **Basis:** Nematode wounds are a documented entry route for rot fungi and for bacterial wilt. Resistance therefore delivers indirect disease control at no cost.
- **Yield impact:** Reduces exposure to the 0.15 nematode value and indirectly to the 0.50 to 0.90 rot value.
- **References:** Agrowon variety register; Agrowon - Mali & Mahajan wound pathway

**D05-PC-001** (PC, info, conf 0.88, tier A)

- **When:** Pest management planning initiated
- **Action (EN):** Frame pest control as wound prevention rather than insect killing. Measure success by rot incidence at harvest, not by pest counts.
- **कृती (MR):** अद्रकात कीड नियंत्रण म्हणजे गड्ड्याला जखम होऊ न देणे. यश किडीच्या संख्येने नव्हे, काढणीच्या वेळी कंदकुजीच्या प्रमाणाने मोजावे.
- **Basis:** Rhizome fly larvae entering the rhizome are followed by pathogenic fungi and nematodes. Nematode wounds are a documented entry route for rot fungi. Shoot borer and white grub both create wounds. The same wounds are created without any pest by careless weeding.
- **Yield impact:** Links the pest u-values to the soft rot u-value of 0.50 to 0.90 rather than treating them as independent.
- **References:** Agrowon - Mali & Mahajan, rhizome fly and nematode descriptions

**D05-SC-002** (SC, info, conf 0.85, tier B)

- **When:** Provisional threshold exceeded
- **Action (EN):** Present the threshold as provisional and estimated, not as an established economic threshold level. State that no published ETL exists for ginger pests.
- **कृती (MR):** ही सहनशीलता पातळी तात्पुरती व अंदाजित आहे. अद्रकाच्या किडींसाठी प्रकाशित आर्थिक नुकसान पातळी उपलब्ध नाही.
- **Basis:** No published economic threshold levels for ginger pests were located across the sources consulted. Presenting an estimate as an established threshold would be a false precision claim.
- **Yield impact:** None. Protects credibility and sets correct expectations.
- **References:** absence of source across consulted material

**D05-SW-002** (SW, info, conf 0.85, tier B)

- **When:** Sensor-based pest detection expected
- **Action (EN):** State plainly that sensors cannot detect the two most important pests, because rhizome fly larvae and nematodes are below ground. Value here comes from timely reminders, weather-based forecasting and correct diagnostic sequencing.
- **कृती (MR):** मुख्य दोन किडी — कंदमाशी आणि सूत्रकृमी — जमिनीखाली आहेत आणि कोणताही sensor त्यांना पाहू शकत नाही. इथे advisory चे मूल्य वेळेवर आठवण, हवामान-आधारित पूर्वानुमान, आणि निदानाचा योग्य क्रम यातून येते.
- **Basis:** The primary damage occurs below ground and is invisible until the crop is already compromised. Overstating sensor capability here would fail at the first field test.
- **Yield impact:** None. Sets correct expectations and directs effort to what actually works.
- **References:** Domain 5 sensor limitation section

**D05-TC-001** (TC, info, conf 0.75, tier B)

- **When:** Planting layout being planned
- **Action (EN):** Plant marigold as a trap crop, starting at bed ends and field bunds where competition with ginger is least.
- **कृती (MR):** झेंडू सापळा पीक म्हणून लावा — वाफ्यांच्या टोकाला व बांधावर, जिथे अद्रकाशी स्पर्धा कमी होईल.
- **Basis:** Marigold is recommended as a nematode trap crop and is separately listed as a compatible intercrop. Nematodes are attracted to it but cannot reproduce on it.
- **Yield impact:** Reduces the 0.15 nematode value and provides early cash flow at 2 to 3 months against ginger's 8 month cycle.
- **References:** Krishi app blog; Agrowon intercrop list

### D06

**D06-BW-003** (BW, info, conf 0.6, tier B)

- **When:** Pre-season planning AND aromatic crop residue is locally available
- **Action (EN):** Offer biofumigation as a trial option: incorporate residue of lemongrass, palmarosa, mint or similar into the soil before planting. Present it as a trial strip, not as an established recommendation.
- **कृती (MR):** जैव-धुरीकरण चाचणी पट्ट्यात करून पहा — गवती चहा, पामारोसा, पुदिना यांचा अवशेष लागवडीपूर्वी जमिनीत मिसळणे. ही प्रस्थापित शिफारस नाही, प्रयोग आहे.
- **Basis:** Different biofumigation soil amendments were tested against bacterial wilt in Ethiopia using citronella, palmarosa, mint, lemongrass and Chinese chive incorporated before planting. Three of these are grown commercially in parts of Maharashtra, and the distillation residue is otherwise waste.
- **Yield impact:** Unquantified. Offered because bacterial wilt has no reliable control, so a cheap trial with a plausible mechanism is worth running.
- **References:** Pesticidi i Fitomedicina 37(1) 2022, Tepi Ethiopia

**D06-LS-003** (LS, info, conf 0.75, tier A)

- **When:** Leaf blotch identified, beginning on the lowest leaves
- **Action (EN):** Note that mulch reduces this disease as well, by stopping rain splash from carrying soil onto the leaves.
- **कृती (MR):** आच्छादन याही रोगावर मदत करते — पावसाच्या थेंबांनी माती उडून पानांवर पडणे थांबते.
- **Basis:** The source records that leaf blotch begins on the leaves closest to the ground and spreads upward, which indicates soil or splash-borne inoculum rather than airborne infection.
- **Yield impact:** Adds a further benefit to an operation already justified on soft rot and water grounds.
- **References:** Agrowon - Mali & Mahajan leaf blotch begins on lowest leaves

**D06-PV-001** (PV, info, conf 0.85, tier A)

- **When:** Pre-season planning is initiated
- **Action (EN):** Issue the full prevention checklist in Kannad priority order: drainage first, then three-stage mulching, then Mahima with healthy seed, then planting by 7 June, then solarization, then Trichoderma with neem cake.
- **कृती (MR):** प्रतिबंधक यादी प्राधान्यक्रमाने द्या — प्रथम निचरा, मग तीन-टप्पी आच्छादन, मग महिमा जात व निरोगी बेणे, मग ७ जूनपर्यंत लागवड, मग सौरीकरण, मग ट्रायकोडर्मा व निंबोळी पेंड.
- **Basis:** Sixteen preventive measures are documented and six of them are entirely free. All are decisions taken before or at planting, which means the largest part of disease management is complete before the crop is in the ground. After that point soft rot and bacterial wilt offer no cure, only damage limitation.
- **Yield impact:** The stack collectively addresses the largest loss factor in the crop. Individual u-values range from 0.05 to 0.22.
- **References:** Domain 6 prevention stack; CJAST 39(35) 2020; Agrowon - Mali & Mahajan

### D07

**D07-CC-002** (CC, info, conf 0.78, tier A)

- **When:** Long term water infrastructure decision such as a well, borewell or farm pond
- **Action (EN):** Add a safety margin. Winter rainfall has declined by about 26 percent, which reduces groundwater recharge, and the monsoon trend is also negative. Historical averages are more likely to be exceeded on the dry side than the wet side.
- **कृती (MR):** सुरक्षिततेचा फरक ठेवा. हिवाळी पाऊस सुमारे २६ टक्क्यांनी घटला आहे, त्यामुळे भूजल पुनर्भरण कमी होते, आणि मान्सूनचा कलही ऋण आहे. ऐतिहासिक सरासरी भविष्यात कमी पडण्याची शक्यता जास्त.
- **Basis:** Winter rainfall is down 25.54 percent and Sen's slope is negative for monsoon rainfall across districts. Reduced winter recharge matters specifically because October to February is when ginger demand peaks and the well is under most pressure.
- **Yield impact:** Long term rather than seasonal.
- **References:** Arabian Journal of Geosciences 2022; ResearchGate 2021 Sen's slope

**D07-CL-001** (CL, info, conf 0.85, tier B)

- **When:** A farmer or partner asks whether ginger is suited to this area
- **Action (EN):** Answer honestly. The Koppen class is BSh, hot semi-arid steppe, which is not the class ginger belongs in. Then state what follows from it: the crop is viable here but it runs entirely on management, so drip, mulch and raised beds are preconditions rather than options.
- **कृती (MR):** प्रामाणिक उत्तर द्या. इथले हवामान BSh — उष्ण अर्ध-शुष्क — या वर्गात आहे, आणि अद्रकाचा वर्ग तो नाही. पण याचा अर्थ पीक घेता येणार नाही असा नाही. अर्थ एवढाच की इथे ते पूर्णपणे व्यवस्थापनावर उभे राहते — म्हणून ठिबक, आच्छादन आणि रुंद वरंबा या पूर्वअटी आहेत, पर्याय नाहीत.
- **Basis:** The climate is formally classified as local steppe with little rainfall through the year. Ginger's home belts are Af, Am and Aw. This is a classification fact rather than a judgement, and stating it up front prevents the three preconditions from being treated as optional extras.
- **Yield impact:** Framing. Prevents a farmer from omitting drip or mulch on the assumption that they are enhancements.
- **References:** climate-data.org Koppen classification

**D07-CL-003** (CL, info, conf 0.75, tier B)

- **When:** Seasonal strategy is being explained to the farmer
- **Action (EN):** Give the four-phase summary: May and June defend against heat, July to September defend against water, October to January let the crop fill, February build quality. The first two phases are defensive; yield is made in the third.
- **कृती (MR):** हंगाम चार टप्प्यांत मांडा — मे-जून उष्णतेपासून बचाव, जुलै-सप्टेंबर पाण्यापासून बचाव, ऑक्टोबर-जानेवारी पीक भरू देणे, फेब्रुवारी प्रत तयार करणे. पहिले दोन टप्पे बचावाचे; उत्पादन तिसऱ्यात ठरते.
- **Basis:** The temperature match table, the rainfall distribution and the disease calendar all divide the season the same way. Presenting one coherent framing helps the farmer understand why the effort profile changes through the year.
- **Yield impact:** Framing rather than a factor. Improves adherence by making the reasoning visible.
- **References:** Domain 7 season strategy; Domain 3 monthly water table

### D08

**D08-CA-002** (CA, info, conf 0.75, tier B)

- **When:** A calendar operation is overdue by more than five days
- **Action (EN):** Ask one question — was the operation done, and if not what got in the way? Offer options: labour, time, cost, did not seem necessary, other.
- **कृती (MR):** एकच प्रश्न विचारा — काम झाले का, आणि नसेल तर काय अडचण आली? पर्याय द्या: मजूर नाही, वेळ नाही, खर्च, गरज वाटली नाही, इतर.
- **Basis:** If the engine recommended something and it was not done, either the message failed or the recommendation was wrong for local conditions. Both are learnable, and both are only discoverable by asking.
- **Yield impact:** None this season. It is the input that reveals implementation barriers, which no sensor can see.
- **References:** Core C12.3 active learning queue; Domain 12 implementation barrier data

**D08-GR-002** (GR, info, conf 0.6, tier C)

- **When:** dap at or above 75 AND tiller count below variety expectation AND basic operations complete
- **Action (EN):** Ethephon at 200 ppm, three sprays at 15 day intervals from the 75th day, is reported to increase tiller number. Caution — it is a plant hormone and excess can yellow the foliage. Rule out nematodes first, since low tiller count is also their earliest sign.
- **कृती (MR):** इथेफॉन २०० ppm, ७५ व्या दिवसापासून १५ दिवसांच्या अंतराने तीन फवारण्या — फुटव्यांची संख्या वाढवण्यासाठी. सावधगिरी: हे वनस्पती संप्रेरक आहे, जास्त मात्रेत पाने पिवळी पडू शकतात. आधी सूत्रकृमी तपासा — कमी फुटवे हे त्यांचेही पहिले लक्षण आहे.
- **Basis:** Source reports ethephon for increasing tiller number. But low tiller count against the variety norm is also the earliest visible nematode symptom, so treating the symptom with a hormone without excluding the pest would mask the real problem.
- **Yield impact:** Unquantified. The diagnostic ordering carries more value than the treatment.
- **References:** AgroWorld ethephon; Agrowon - Mali and Mahajan nematode symptoms

**D08-IC-002** (IC, info, conf 0.75, tier B)

- **When:** Intercrop being considered
- **Action (EN):** Rank marigold first, then coriander, then tur, then guar. Marigold suppresses nematodes, gives cash at two to three months against ginger's eight, and attracts beneficial insects. Ensure the intercrop does not compete with the main crop.
- **कृती (MR):** क्रमाने — झेंडू, कोथिंबीर, तूर, गवार. झेंडू सूत्रकृमी दाबतो, दोन-तीन महिन्यांत रोख देतो (अद्रकाला आठ महिने लागतात), आणि मित्रकीटक आकर्षित करतो. आंतरपिकाची मुख्य पिकाशी स्पर्धा होणार नाही याची खबरदारी घ्या.
- **Basis:** Marigold appears in both the intercrop list and the nematode control list, so it does two jobs. Its two to three month cycle addresses the cash flow problem created by ginger's front-loaded investment and eight month duration.
- **Yield impact:** Reduces the 0.15 nematode value and improves cash flow rather than yield.
- **References:** AgroWorld intercrop list; Domain 5 marigold trap crop

**D08-LY-004** (LY, info, conf 0.7, tier A)

- **When:** Bed forming scheduled AND area_acre above 1 AND bed_former_arranged is false
- **Action (EN):** Arrange a tractor-drawn bed former in advance and settle the 60/60 setting with the operator before the day. Hand forming is not practical beyond a small area.
- **कृती (MR):** ट्रॅक्टरचे सरी यंत्र आधीच ठरवा, आणि ६०/६० रचनेसाठी यंत्राची मांडणी चालकाशी बोलून निश्चित करा. मोठ्या क्षेत्रावर हाताने वाफे बांधणे व्यवहार्य नाही.
- **Basis:** Bed geometry determines drainage, plant population and drip layout together. If the machine cannot be set correctly the layout decision fails at execution rather than at planning.
- **Yield impact:** Protects the 0.167 from being lost during implementation.
- **References:** Agrowon bed forming machinery method for onion

**D08-MU-003** (MU, info, conf 0.7, tier B)

- **When:** Mulch material is being sourced
- **Action (EN):** Prefer sugarcane trash and wheat straw, which are available locally. Ghaneri or nirgudi leaf from field bunds additionally reduces shoot borer. Weeds removed by hand weeding can be used and cost nothing.
- **कृती (MR):** उसाचे पाचट आणि गव्हाचे काड स्थानिक उपलब्ध आहेत. बांधावरील घाणेरी किंवा निर्गुडीचा पाला वापरल्यास खोडकिडा कमी होतो. खुरपून काढलेले तणही वापरता येते आणि ते फुकट आहे.
- **Basis:** Material choice affects cost more than effect. Sugarcane trash is abundant in the neighbouring cane belt. Ghaneri and nirgudi carry a documented secondary pest effect, so the same operation does two jobs.
- **Yield impact:** Reduces the cost of achieving the 0.20 mulch benefit.
- **References:** Domain 8 material list; Agrowon pest notes on nirgudi

### D09

**D09-DR-001** (DR, info, conf 0.78, tier C)

- **When:** Dry ginger route selected
- **Action (EN):** Use simple sun drying as the first option. Wash, remove roots, soak overnight, scrape the skin with a bamboo edge, wash again, then sun dry 7 to 8 days in a layer no thicker than 1 to 1.5 inches on clean plastic or tarpaulin, turning frequently, until moisture reaches 8 to 10 percent.
- **कृती (MR):** साधी वाळवणी पद्धत प्रथम वापरा. धुवा, मुळे काढा, रात्रभर भिजवा, बांबूच्या कडेने साल खरडून काढा, पुन्हा धुवा, मग स्वच्छ प्लॅस्टिक किंवा ताडपत्रीवर १ ते १.५ इंचापेक्षा जाड नाही अशा थरात ७ ते ८ दिवस उन्हात वाळवा, वरचेवर हात घालत रहा, पाण्याचा अंश ८ ते १०% येईपर्यंत.
- **Basis:** This method uses no chemicals, needs no equipment beyond tarpaulin, and gives 20 to 25 percent recovery. The February and March climate here — 2 to 3 mm rainfall, dry semi-arid sun, low humidity — is close to ideal for it, which is not true of Kerala at harvest time.
- **Yield impact:** Enables the price-timing route at negligible cost and with no safety or residue exposure.
- **References:** AgroWorld simple drying method; Domain 7 February rainfall

**D09-GD-003** (GD, info, conf 0.65, tier B)

- **When:** Grading criteria are needed
- **Action (EN):** Present the seven determinants and flag which are still changeable. Size, rot and fibre are already fixed by this point; skin condition, cleanliness, uniformity and freshness are still in the farmer's hands.
- **कृती (MR):** सात निकष सांगा आणि कोणते अजून बदलता येतात ते स्पष्ट करा. आकार, कूज आणि तंतू आता ठरलेले आहेत; सालीची स्थिती, स्वच्छता, एकसारखेपणा आणि ताजेपणा अजून शेतकऱ्याच्या हातात आहेत.
- **Basis:** No published grading standard for ginger was located, so the list is reasoned from the price observation and from handling practice. Separating the fixed determinants from the changeable ones directs effort where it can still act.
- **Yield impact:** Directs the grading effort.
- **References:** Domain 9 grading determinants; absence of a published standard

**D09-MK-002** (MK, info, conf 0.72, tier B)

- **When:** Market selection for a consignment
- **Action (EN):** Split the consignment rather than choosing one market. Send 20 to 30 percent of the best grade to a small or local market where arrivals are low and prices higher, 50 to 60 percent to a large market that can absorb volume, and consider processing the lowest 10 to 20 percent instead of selling it.
- **कृती (MR):** एकच बाजार निवडण्याऐवजी माल विभागून पाठवा. सर्वोत्तम प्रतीचा २० ते ३०% भाग लहान किंवा स्थानिक बाजारात — तिथे आवक कमी आणि भाव जास्त. ५० ते ६०% मोठ्या बाजारात — तो मोठे प्रमाण शोषतो. आणि खालच्या प्रतीचा १० ते २०% भाग विकण्याऐवजी सुंठ करण्याचा विचार करा.
- **Basis:** Chandrapur took the highest price of the day on an arrival of 8 to 25 quintal, while Mumbai handled 884 to 1,556 quintal at a lower range. Small arrivals command higher prices but a small market cannot absorb a large consignment — sending it all there would collapse the price.
- **Yield impact:** Pure price capture. Costs transport planning.
- **References:** News18 Marathi market-wise arrivals and prices

**D09-MK-003** (MK, info, conf 0.78, tier B)

- **When:** Market access is being assessed before planting
- **Action (EN):** State that this is a thin market. State-wide daily arrivals run 1,297 to 3,695 quintal against 330,007 for onion — roughly one percent. The local APMC does not appear in the arrival lists at all, so enquire directly with local traders before planting a large area.
- **कृती (MR):** हा पातळ बाजार आहे. राज्यभर दैनिक आवक १,२९७ ते ३,६९५ क्विंटल, तर कांद्याची ३,३०,००७ — म्हणजे सुमारे एक टक्का. स्थानिक बाजार समिती आवकेच्या यादीत कुठेही नाही, म्हणून मोठे क्षेत्र लावण्यापूर्वी स्थानिक व्यापाऱ्यांकडे थेट चौकशी करा.
- **Basis:** A thin market means a modest increase in arrivals moves the price a long way, and it means the local outlet may not exist at all. Both matter more for a high-value crop with a large sunk cost than for a staple.
- **Yield impact:** Informs the area decision before the money is spent.
- **References:** News18 Marathi state arrival figures; absence of local APMC from arrival lists

**D09-MK-004** (MK, info, conf 0.9, tier B)

- **When:** Any market price is about to be displayed
- **Action (EN):** Display the date of the observation and state that prices change daily. Never present a stored price as current. Direct the farmer to check the live rate before selling.
- **कृती (MR):** भाव कोणत्या तारखेचा आहे ते दाखवा आणि भाव रोज बदलतात हे सांगा. साठवलेला भाव चालू म्हणून दाखवू नका. विक्रीपूर्वी चालू भाव तपासण्यास सांगा.
- **Basis:** The prices recorded here are dated observations from mid-2026, kept to illustrate the spread and the market structure rather than to state current values. Presenting them as current would be actively misleading in a market this volatile.
- **Yield impact:** None. Protects credibility and prevents a decision on stale data.
- **References:** Domain 9 metadata review_by date

**D09-MT-004** (MT, info, conf 0.7, tier C)

- **When:** Market price is high and the crop is around 75 percent mature
- **Action (EN):** Note that produce at about 75 percent maturity is acceptable to the market. Present the trade-off honestly — lower weight, lower dry recovery, poorer storability — and let the farmer decide.
- **कृती (MR):** साधारण ७५% पक्वतेचा माल बाजारात चालतो. तडजोड स्पष्ट सांगा — वजन कमी, सुंठ उतारा कमी, साठवण कमी — आणि निर्णय शेतकऱ्यावर सोडा.
- **Basis:** The source states that harvest at about 75 percent maturity is marketable. This is a genuine flexibility point that lets the grower respond to a good price rather than being locked to a date.
- **Yield impact:** Trades weight for timing. Whether it pays depends on the price differential, not on agronomy.
- **References:** AgroWorld harvest timing

**D09-PH-002** (PH, info, conf 0.8, tier A)

- **When:** Harvest complete AND part of the crop is destined for seed
- **Action (EN):** Separate the seed fraction now, break off the thick roots, and treat before storage. The pre-storage treatment is the step most often skipped because the next crop feels distant in December.
- **कृती (MR):** बेण्याचा भाग आत्ताच वेगळा काढा, जाड मुळ्या तोडा, आणि साठवणीपूर्वी प्रक्रिया करा. डिसेंबरमध्ये पुढचे पीक दूर वाटते, म्हणून साठवणीपूर्वीची प्रक्रिया हीच सर्वात जास्त वेळा वगळली जाते.
- **Basis:** Seed rhizome is treated twice, once before storage and once before planting. Treating only at planting does not address infection established inside the rhizome during four to five months of storage.
- **Yield impact:** Affects next season's establishment ceiling and seed cost.
- **References:** Domain 6 twice-treated seed rule; AgroWorld root removal

**D09-PR-003** (PR, info, conf 0.8, tier B)

- **When:** A processing method is being chosen
- **Action (EN):** Rank simple sun drying first in every case. It uses no chemicals, is completely safe, suits this climate, needs almost no capital, and can be started today. Only move to a chemical method if a verified price premium justifies it and the safety and residue questions are settled.
- **कृती (MR):** प्रत्येक वेळी साधी वाळवणी पद्धत प्रथम. तिला रसायन लागत नाही, ती पूर्णपणे सुरक्षित आहे, इथल्या हवामानाला अनुकूल आहे, भांडवल जवळपास शून्य आहे, आणि ती आजपासून करता येते. भाव-फरक निश्चित झाल्याशिवाय आणि सुरक्षा व अवशेषांचे प्रश्न सुटल्याशिवाय रासायनिक पद्धतीकडे जाऊ नये.
- **Basis:** Of the three methods, one uses no chemicals and two carry either a residue question or a serious hazard. The price differential that would justify the chemical methods has not been measured, so there is no basis for accepting the risk.
- **Yield impact:** Directs the route decision by evidence and safety rather than by product appearance.
- **References:** Domain 9 three-method comparison

**D09-PW-001** (PW, info, conf 0.65, tier C)

- **When:** Further value addition is being considered beyond dry ginger
- **Action (EN):** Powder is the next step — grind well-dried ginger, sieve through 50 to 60 mesh, pack airtight. Note that every step up the ladder raises value per kilo and reduces total weight, so the price multiple has to be checked at each step.
- **कृती (MR):** पुढील टप्पा पावडर — चांगली वाळलेली सुंठ दळून ५० ते ६० मेशच्या चाळणीतून चाळा आणि हवाबंद पिशवीत भरा. प्रत्येक टप्प्यावर प्रति किलो मूल्य वाढते पण एकूण वजन घटते, म्हणून प्रत्येक पायरीवर भावाचा पट तपासावा लागतो.
- **Basis:** Powder is used for oleoresin extraction and spice products. The value chain runs fresh, dry, powder, oleoresin, with value rising and weight falling at each stage.
- **Yield impact:** Depends entirely on prices that are not yet known.
- **References:** AgroWorld powder section

**D09-SL-001** (SL, info, conf 0.85, tier B)

- **When:** The sell-or-hold decision is being made
- **Action (EN):** Present the four options with their trade-offs and the arithmetic behind each. Do NOT recommend one. State plainly that the engine does not forecast prices — it shows today's actual rates, the storage loss and cost arithmetic, and what the net return would be at a given price.
- **कृती (MR):** चार पर्याय आणि त्यांच्या तडजोडी गणितासह मांडा, पण एकाची शिफारस करू नका. स्पष्ट सांगा — engine भाव वर्तवत नाही. ते आजचे प्रत्यक्ष भाव, साठवण घट व खर्चाचे गणित, आणि दिलेल्या भावाला निव्वळ परतावा किती होईल एवढेच दाखवते.
- **Basis:** In a thin market with high volatility a single recommendation would be a price forecast in disguise, and the engine has no basis for one. Presenting the arithmetic lets the farmer apply their own view of the price and their own cash position.
- **Yield impact:** None. It is the difference between decision support and a bet placed on the farmer's behalf.
- **References:** Core C8.4 thin market constraint

**D09-SL-002** (SL, info, conf 0.8, tier B)

- **When:** Processing is being considered as a route
- **Action (EN):** Show the break-even arithmetic. 100 kg fresh yields 20 to 25 kg dry, so the dry price must be four to five times the fresh price merely to break even, before labour, fuel, space and time. Processing more is not automatically earning more.
- **कृती (MR):** समतोल गणित दाखवा. १०० किलो ओल्या आल्यापासून २० ते २५ किलो सुंठ मिळते, म्हणजे सुंठेचा भाव ओल्या आल्याच्या चार ते पाच पट असल्याशिवाय बरोबरीही होत नाही — आणि त्यात श्रम, इंधन, जागा व वेळ धरलेला नाही. जास्त प्रक्रिया म्हणजे आपोआप जास्त पैसा नव्हे.
- **Basis:** Recovery of 20 to 25 percent sets the break-even multiple arithmetically. The assumption that processing always adds income is common and wrong, and the arithmetic settles it in one line.
- **Yield impact:** Prevents an unprofitable processing decision.
- **References:** AgroWorld recovery figures; Domain 9 value addition economics

**D09-SL-003** (SL, info, conf 0.72, tier B)

- **When:** Fresh price has crashed OR a substantial share of the produce is lower grade
- **Action (EN):** This is when processing becomes rational. At a crashed price, storing dry ginger buys time. For lower grade produce, appearance matters less once dried, so processing captures value that the fresh market would discount.
- **कृती (MR):** आता प्रक्रिया तर्कसंगत ठरते. भाव कोसळला असल्यास सुंठ करून साठवल्यास वेळ मिळतो. आणि खालच्या प्रतीच्या मालाची सुंठ केल्यास दिसण्याचे महत्व कमी होते — म्हणजे ओल्या बाजारात कमी भाव मिळणारा माल इथे मूल्य मिळवतो.
- **Basis:** Grade discounts apply to visual attributes that largely disappear in the dried product. So the produce that suffers most in the fresh market is the produce that gains most from processing.
- **Yield impact:** Recovers value from the fraction that would otherwise sell at the bottom of the 2.7 times spread.
- **References:** Domain 9 when processing is rational; grading spread observation

**D09-YD-002** (YD, info, conf 0.78, tier A)

- **When:** Actual yield recorded
- **Action (EN):** Compare against the target range of 60, 90 and 110 quintal per acre and against the state average of 53. Run the gap attribution using the season's operation record.
- **कृती (MR):** लक्ष्य श्रेणीशी तुलना करा — किमान ६०, लक्ष्य ९०, ताणून ११० क्विंटल प्रति एकर, आणि राज्य सरासरी ५३. हंगामातील कृती नोंदींवरून दरी-विश्लेषण चालवा.
- **Basis:** The gap between the ceiling and the actual yield is attributable to recorded events and omissions. Running that attribution is what turns a season's records into corrected coefficients.
- **Yield impact:** None directly. Produces the learning that improves later seasons.
- **References:** Domain 11 gap attribution method; Domain 1 yield targets

**D09-YD-003** (YD, info, conf 0.75, tier A)

- **When:** Dry ginger has been produced
- **Action (EN):** Record the actual dry recovery percentage. Planning uses 19 percent; published ranges run from 15 to 25 and vary by variety.
- **कृती (MR):** प्रत्यक्ष सुंठ उतारा नोंदवा. नियोजनात १९% वापरला आहे; प्रकाशित श्रेणी १५ ते २५% आहे आणि ती जातीनुसार बदलते.
- **Basis:** Recovery varies by variety from 18.7 to 23 percent among the four main options, and drying method affects it too. The actual figure for this variety under this method on this plot is not knowable from publications.
- **Yield impact:** Determines whether the processing route is economic.
- **References:** Agrowon variety recovery figures; AgroWorld 20 to 25 percent

**D09-YD-004** (YD, info, conf 0.8, tier B)

- **When:** Harvest complete
- **Action (EN):** Record the actual cost incurred line by line — seed, land preparation, mulch, fertiliser, plant protection, labour, harvest and transport. The Domain 13 model currently runs on estimates for several of these.
- **कृती (MR):** प्रत्यक्ष खर्च बाबनिहाय नोंदवा — बेणे, पूर्वमशागत, आच्छादन, खते, कीड-रोग नियंत्रण, मजुरी, काढणी आणि वाहतूक. सध्याचे आर्थिक गणित यांपैकी अनेक बाबींवर अंदाजाने चालते.
- **Basis:** The Kannad cost estimate of about Rs 1,45,000 per acre adds mulch, drainage and micronutrient lines that the standard published sheet omits, and several figures are estimates. Only recorded actuals can correct them.
- **Yield impact:** None. Corrects the economics model.
- **References:** Domain 13 cost structure; Domain 12 minimum record set

### D10

**D10-ACT-002** (ACT, info, conf 0.78, tier B)

- **When:** An institutional contact has been made and information received
- **Action (EN):** Record the answer against the specific open item it resolves, with the date and the source. Several open items across Domains 1 to 9 are waiting on single institutional answers.
- **कृती (MR):** मिळालेले उत्तर ज्या मोकळ्या जागेचे निराकरण करते तिच्याविरुद्ध, तारीख आणि स्रोतासह नोंदवा. Domain १ ते ९ मधील अनेक मोकळ्या जागा एकाच संस्थात्मक उत्तरावर थांबलेल्या आहेत.
- **Basis:** The broad ridge trial question alone unblocks the Domain 11 yield ceiling, which every u-value computation depends on. Recording answers against items rather than as loose notes is what converts a phone call into a resolved dependency.
- **Yield impact:** None directly. Converts institutional contact into corrected knowledge base state.
- **References:** Domain 11 blocking open item; Domain 10 action register

**D10-ACZ-001** (ACZ, info, conf 0.65, tier A)

- **When:** agro_climatic_zone is unknown or unverified
- **Action (EN):** Assume Marathwada western zone provisionally — 600 to 750 mm and mean temperature below 26 C — and mark it as inferred. Confirm with VNMKV Parbhani or the district office.
- **कृती (MR):** तात्पुरता पश्चिम विभाग गृहीत धरा — ६०० ते ७५० मिमी, सरासरी तापमान २६ अंशांखाली — पण हे अनुमान आहे. VNMKV परभणी किंवा जिल्हा कार्यालयाकडून पुष्टी घ्या.
- **Basis:** Three zones are identified within Marathwada on climate and soil criteria. Kannad sits in the western part of the district, above 600 m, near the Ajanta range, which places it in the western zone on the available criteria. The study does not assign talukas individually.
- **Yield impact:** Determines which regional recommendations apply.
- **References:** Agro-Climatic Zonation of Marathwada, IMD plus Hydrological Project Nashik

**D10-APP-002** (APP, info, conf 0.75, tier B)

- **When:** Multiple subsidy needs identified
- **Action (EN):** Apply for drip and farm pond together in one MahaDBT application. The portal allows multiple schemes in a single application.
- **कृती (MR):** ठिबक आणि शेततळे यांचा अर्ज एकाच वेळी करा. MahaDBT वर एकाच अर्जात अनेक योजनांसाठी अर्ज करता येतो.
- **Basis:** Both are needed at Kannad and both have the same document set and the same process. A single application halves the administrative work and keeps the two on the same timeline.
- **Yield impact:** None. Reduces friction in the highest-value institutional action.
- **References:** mahakisanyojana.com multi-scheme application

**D10-APP-004** (APP, info, conf 0.78, tier B)

- **When:** Farmer belongs to a priority category
- **Action (EN):** Note the priority order and ensure the supporting document is attached. Order is families of martyred soldiers, families of farmers who died by suicide, below poverty line, widowed or deserted women, small and marginal farmers, then others.
- **कृती (MR):** प्राधान्यक्रम लक्षात घ्या आणि त्याचे कागदपत्र जोडा. क्रम — शहीद जवानांचे कुटुंब, आत्महत्याग्रस्त शेतकरी कुटुंब, दारिद्र्य रेषेखालील, विधवा किंवा परित्यक्ता महिला, अल्प व अत्यल्प भूधारक, मग इतर.
- **Basis:** Priority affects both selection likelihood in the lottery and the applicable subsidy percentage. Small and marginal status alone is worth about 5 percentage points on the drip subsidy.
- **Yield impact:** None. Affects the capital cost outcome.
- **References:** govtyojanamaharashtra.com priority order

**D10-CROP-001** (CROP, info, conf 0.85, tier A)

- **When:** Area planning or market assessment before planting
- **Action (EN):** State that Maharashtra has only about 4,000 hectares under ginger, roughly 1.3 percent of India's area. Local supply is limited so prices can be good, but the market is thin, technical support is limited, and seed availability is uncertain.
- **कृती (MR):** महाराष्ट्रात अद्रकाखाली फक्त सुमारे ४,००० हेक्टर क्षेत्र आहे — भारताच्या क्षेत्राच्या सुमारे १.३%. स्थानिक पुरवठा कमी असल्याने भाव चांगला मिळू शकतो, पण बाजार पातळ आहे, स्थानिक तांत्रिक मदत मर्यादित आहे, आणि बेण्याची उपलब्धता अनिश्चित आहे.
- **Basis:** A small state area produces four consequences at once — limited local supply supporting price, a thin market that moves sharply on modest arrivals, sparse extension experience, and a correspondingly small seed market.
- **Yield impact:** None directly. Shapes the area decision and the seed procurement timeline.
- **References:** Directorate of Agriculture Maharashtra 2023 via AgriTimes

**D10-CROP-002** (CROP, info, conf 0.65, tier B)

- **When:** Local experience is being sought
- **Action (EN):** Ask older growers and seed sellers in the district. Aurangabad appears as a ginger district in two of three published lists and a landrace called Aurangabadi is separately recorded, so local tradition is probably deeper than assumed.
- **कृती (MR):** जिल्ह्यातील जुन्या शेतकऱ्यांकडे आणि बेणे विक्रेत्यांकडे चौकशी करा. तीनपैकी दोन यादींमध्ये औरंगाबाद अद्रक जिल्हा म्हणून नोंदवलेला आहे, आणि 'औरंगाबादी' नावाची स्थानिक जातही स्वतंत्रपणे नोंदवलेली आहे — म्हणजे इथली परंपरा वाटते त्यापेक्षा जुनी असावी.
- **Basis:** Two independent signals point the same way. A place-named landrace usually indicates sustained local cultivation over a long period, and that means adapted material and accumulated practical knowledge may exist locally.
- **Yield impact:** Could surface a locally adapted variety and practical knowledge that no publication contains.
- **References:** Agrowon district list; AgroWorld district list; AgroWorld variety list including Aurangabadi

**D10-CROP-003** (CROP, info, conf 0.85, tier A)

- **When:** Comparison against state benchmarks requested
- **Action (EN):** Use 53 quintal per acre as the state average benchmark. Reaching 90 is roughly 70 percent above it and 110 is more than double, which is the honest way to frame what good management is worth here.
- **कृती (MR):** राज्य सरासरी ५३ क्विंटल प्रति एकर हा संदर्भ वापरा. ९० क्विंटल म्हणजे त्याहून सुमारे ७०% जास्त, आणि ११० म्हणजे दुपटीहून जास्त — चांगल्या व्यवस्थापनाचे मूल्य मांडण्याचा हा प्रामाणिक मार्ग आहे.
- **Basis:** The state average of 13.2 tonnes per hectare converts to about 53 quintal per acre. The gap between that and the genetic ceiling is attributable to management rather than to climate or soil, which is the central argument of Domain 11.
- **Yield impact:** Framing rather than a factor. Sets a realistic and verifiable benchmark.
- **References:** Directorate of Agriculture Maharashtra 2023; Domain 11 gap analysis

**D10-INS-002** (INS, info, conf 0.7, tier B)

- **When:** Crop loan being considered AND scale_of_finance_per_acre is unknown
- **Action (EN):** Obtain the scale of finance for ginger from the district lead bank. It sets the credit limit, which matters for a crop costing about Rs 1.45 lakh per acre.
- **कृती (MR):** जिल्हा अग्रणी बँकेकडून अद्रकाचा scale of finance घ्या. त्यावरून कर्जाची मर्यादा ठरते, आणि एकरी सुमारे १.४५ लाख खर्चाच्या पिकात ती महत्वाची आहे.
- **Basis:** Scale of finance is set by the district technical committee per crop. If it is set low for ginger, or not set at all because the crop is uncommon here, the credit available will not match the actual cost.
- **Yield impact:** None. Affects whether the plan is financeable.
- **References:** Domain 13 cost structure

**D10-INS-003** (INS, info, conf 0.75, tier B)

- **When:** Inputs being purchased
- **Action (EN):** Keep seed purchase bills and all input receipts. They are needed for loan documentation and for any insurance claim.
- **कृती (MR):** बेणे खरेदीचे बिल आणि सर्व निविष्ठांच्या पावत्या जपून ठेवा. कर्ज आणि विमा दाव्यासाठी त्या लागतात.
- **Basis:** Claims and loan documentation require proof of expenditure. Seed is the largest single cost and the one most often bought informally, so it is the receipt most likely to be missing.
- **Yield impact:** None. Protects the claim.
- **References:** Domain 10 records note

**D10-INST-001** (INST, info, conf 0.85, tier A)

- **When:** research_centre_contacted is false
- **Action (EN):** Contact the Halad Sanshodhan Yojana at Kasbe Digraj, Sangli. Five domains rest primarily on this one centre. Ask about Marathwada-specific recommendations, the CIB&RC list for ginger, economic threshold levels, a reliable seed source, and whether the published variety trial yields already used broad ridge layout.
- **कृती (MR):** हळद संशोधन योजना, कसबे डिग्रज, सांगली येथे संपर्क करा. या knowledge base मधील पाच Domain याच एका केंद्रावर आधारित आहेत. विचारायचे — मराठवाडा व काळ्या जमिनीसाठी विशिष्ट शिफारसी, अद्रकासाठी CIB&RC नोंदणीकृत रसायने, किडींच्या ETL पातळ्या, बेण्याचा विश्वसनीय स्रोत, आणि जातींचे प्रकाशित उत्पादन आकडे रुंद वरंब्यात घेतले होते का.
- **Basis:** Domains 2, 4, 5, 6 and 8 draw primarily on this centre's published work. Turmeric and ginger are in the same family so its research applies directly, and one of the questions — the broad ridge trial question — is currently blocking the entire Domain 11 yield ceiling computation.
- **Yield impact:** Resolves a blocking open item that every u-value computation depends on.
- **References:** Agrowon articles by Kadam, Mali and Mahajan

**D10-INST-002** (INST, info, conf 0.75, tier A)

- **When:** University enquiry being prepared
- **Action (EN):** Direct the enquiry to the College of Horticulture at VNMKV Parbhani, not the general agronomy department. Ginger is a spice and horticultural crop.
- **कृती (MR):** चौकशी VNMKV परभणी येथील उद्यानविद्या महाविद्यालयाकडे करा, सामान्य कृषिविद्या विभागाकडे नाही. अद्रक हे मसाला व उद्यानविद्या पीक आहे.
- **Basis:** Crop classification determines which department holds the expertise. A ginger question sent to the agronomy department is likely to be redirected, which costs weeks in a season with a fixed planting deadline.
- **Yield impact:** None. Saves time on a time-constrained calendar.
- **References:** coh.vnmkv.ac.in

**D10-INST-003** (INST, info, conf 0.78, tier A)

- **When:** Local technical support or soil testing needed
- **Action (EN):** Contact KVK 1 at Paithan Road, Chhatrapati Sambhajinagar — the nearest extension centre. Ask about soil testing, local ginger experience, and the Aurangabadi landrace.
- **कृती (MR):** कृषि विज्ञान केंद्र १, पैठण रोड, छत्रपती संभाजीनगर येथे संपर्क करा — हे सर्वात जवळचे विस्तार केंद्र आहे. माती परीक्षण, स्थानिक अद्रक अनुभव, आणि 'औरंगाबादी' जातीबद्दल विचारा.
- **Basis:** KVK's mandate is exactly this — local technical guidance, soil testing, demonstrations and input advice. VNMKV women scientists have separately run a programme on organic turmeric guidance, and turmeric is the same family, so applicable local knowledge exists.
- **Yield impact:** Unblocks the soil test, which is a blocking item for Domains 2 and 4.
- **References:** kvkchhatrapatisambhajinagar.blogspot.com; promkvparbhani.blogspot.com turmeric programme

**D10-INST-004** (INST, info, conf 0.6, tier B)

- **When:** Shared processing capacity being considered for dry ginger
- **Action (EN):** Explore the MoFPI food processing scheme as the institutional route to a shared facility. Domain 9 identified a group or cooperative facility as the safe answer for chemical processing, and this is the funding path toward one.
- **कृती (MR):** सामायिक प्रक्रिया सुविधेसाठी अन्न प्रक्रिया उद्योग मंत्रालयाच्या योजनेची चौकशी करा. रासायनिक प्रक्रिया वैयक्तिक पातळीवर सुरक्षित नाही आणि गट किंवा सहकारी केंद्र हेच उत्तर आहे — ही योजना त्याचा आर्थिक मार्ग असू शकते.
- **Basis:** The caustic soda method produces export-grade dry ginger and is not safe at individual farm level. A shared facility resolves both the safety problem and the capital problem, and a food processing scheme is the normal route to funding one.
- **Yield impact:** None. Opens a value-addition route that is otherwise closed on safety grounds.
- **References:** Domain 9 soda khar safety block; VNMKV MoFPI project note

**D10-LAB-002** (LAB, info, conf 0.8, tier B)

- **When:** Soil assessment being planned
- **Action (EN):** Run the percolation pit test alongside the laboratory test. Dig a 30 cm pit, fill and drain fully, refill and time the second drain. It costs nothing, takes a day, and for ginger it matters more than the chemical panel.
- **कृती (MR):** प्रयोगशाळेच्या चाचणीसोबत खड्डा चाचणीही करा. ३० सेंमी खड्डा खणा, पाण्याने भरून पूर्ण मुरू द्या, पुन्हा भरा आणि वेळ मोजा. खर्च शून्य, वेळ एक दिवस — आणि अद्रकासाठी ती रासायनिक अहवालापेक्षा जास्त निर्णायक आहे.
- **Basis:** For ginger the governing soil risk is physical drainage rather than chemical fertility, and no laboratory report measures infiltration on this plot. Above 12 hours the recommendation is to avoid ginger there altogether.
- **Yield impact:** Determines bed height, channel design, and in the worst case the go or no-go decision.
- **References:** Domain 2 percolation test method

**D10-MKT-001** (MKT, info, conf 0.75, tier B)

- **When:** Market access being assessed before planting
- **Action (EN):** Enquire directly with the Chhatrapati Sambhajinagar APMC and local traders whether ginger is traded and at what price. It does not appear in the state arrival lists at all.
- **कृती (MR):** छत्रपती संभाजीनगर बाजार समिती आणि स्थानिक व्यापाऱ्यांकडे थेट चौकशी करा — इथे अद्रकाची खरेदी होते का आणि भाव काय. राज्याच्या आवक यादीत हा बाजार कुठेही दिसत नाही.
- **Basis:** Absence from the arrival lists means no reportable ginger arrival at the nearest market. The realistic outlets are Mumbai at roughly 350 km and Nagpur at roughly 500 km, so transport cost becomes a real component of net return.
- **Yield impact:** None. Informs the area decision and the transport budget.
- **References:** News18 Marathi APMC arrival lists; Domain 9 market registry

**D10-MKT-002** (MKT, info, conf 0.65, tier B)

- **When:** Alternative selling channels being explored
- **Action (EN):** Check whether the local APMC is linked to eNAM, whether a farmer producer company operates in the area, and whether any processing buyer exists. In a thin market an alternative channel can be worth more than a better price at the same channel.
- **कृती (MR):** स्थानिक बाजार समिती eNAM शी जोडलेली आहे का, भागात शेतकरी उत्पादक कंपनी आहे का, आणि प्रक्रिया उद्योगाचा खरेदीदार आहे का — हे तपासा. पातळ बाजारात पर्यायी मार्ग हा त्याच बाजारातील थोड्या जास्त भावापेक्षा मौल्यवान ठरू शकतो.
- **Basis:** State daily arrivals are roughly one percent of onion, so the crop is exposed to a single thin channel. An alternative outlet reduces that concentration risk more effectively than optimising within the same channel.
- **Yield impact:** None. Reduces market risk.
- **References:** Domain 9 thin market finding

**D10-SUB-005** (SUB, info, conf 0.7, tier B)

- **When:** Shadenet subsidy being considered for ginger
- **Action (EN):** Caution against it as a first step. The scheme funds a full shadenet house, whereas ginger needs about 25 percent shade for roughly the first two months. Test mulch, a tall intercrop such as tur, or temporary netting first.
- **कृती (MR):** हा पहिला पर्याय म्हणून घेऊ नका. योजना पूर्ण शेडनेट हाऊससाठी आहे, तर अद्रकाला साधारण पहिले दोन महिने सुमारे २५% सावली लागते. आधी आच्छादन, तूरसारखे उंच आंतरपीक, किंवा तात्पुरती जाळी तपासा.
- **Basis:** The crop's shade requirement is seasonal and partial, while the scheme funds a permanent full structure. Spending the capital on a disproportionate solution crowds out cheaper measures that address the same May heat problem.
- **Yield impact:** Prevents misallocated capital rather than adding yield.
- **References:** govtyojanamaharashtra.com shadenet ceiling; Domain 7 heat window; Domain 8 shade and aroma

**D10-SUB-006** (SUB, info, conf 0.8, tier B)

- **When:** Economic model being run for the enterprise
- **Action (EN):** Run the cost model twice — once with subsidy and once without. Ginger economics at Kannad differ fundamentally between the two, and the difference falls entirely on capital rather than on operating cost.
- **कृती (MR):** खर्चाचे गणित दोनदा चालवा — अनुदानासह आणि अनुदानाशिवाय. इथे अद्रकाचे अर्थशास्त्र या दोन परिस्थितींत मूलभूतपणे वेगळे आहे, आणि तो फरक पूर्णपणे भांडवली खर्चावर पडतो, चालू खर्चावर नाही.
- **Basis:** Drip is a precondition, so its cost is unavoidable. Subsidy at 75 to 80 percent changes who bears it, not whether it is incurred. Since selection is by lottery, both cases are live until the result is known.
- **Yield impact:** None. Determines viability and the area decision.
- **References:** Domain 10 subsidy rates; Domain 13 cost structure

**D10-VAR-002** (VAR, info, conf 0.75, tier A)

- **When:** Improved variety seed is not available locally
- **Action (EN):** Institutional sources exist — CPCRI at Kasaragod, Kerala for improved varieties, and ICAR-IISR at Kozhikode for Mahima, Rejatha and Varada. Allow for transport time and quarantine considerations.
- **कृती (MR):** संस्थात्मक स्रोत उपलब्ध आहेत — सुधारित जातींसाठी CPCRI, कासरगोड, केरळ; आणि महिमा, रीजाथा, वरदा यांसाठी ICAR-IISR, कोझिकोड. वाहतुकीचा वेळ आणि तपासणीचा विचार करा.
- **Basis:** The three recommended varieties all originate from ICAR-IISR Kozhikode. Going to the source is slower and more certain than hoping a local trader stocks them.
- **Yield impact:** Enables the variety choice rather than defaulting to whatever is available.
- **References:** AgroWorld CPCRI address; Domain 1 variety origins

### D11

**D11-AP-001** (AP, info, conf 0.75, tier B)

- **When:** Advisory priority is being computed for a set of pending actions
- **Action (EN):** Score by u-value multiplied by two if the factor is irrecoverable, multiplied by one and a half if the action window is open now. Irrecoverability and urgency both raise priority above the raw u-value.
- **कृती (MR):** गुण = u × (भरून निघत नसेल तर २) × (खिडकी आत्ता उघडी असेल तर १.५). भरून न निघणे आणि तातडी — दोन्ही केवळ u मूल्यापेक्षा प्राधान्य वर नेतात.
- **Basis:** A recoverable 0.15 factor and an irrecoverable 0.15 factor are not equally urgent. Nor are two identical factors when one window closes this week and the other in two months.
- **Yield impact:** Determines which advisory the farmer sees first when several are due.
- **References:** Domain 11 prioritisation formula; Core C6.2

**D11-AP-003** (AP, info, conf 0.85, tier A)

- **When:** Pre-season advisory calendar being generated
- **Action (EN):** Front-load it. Variety, seed source and seed treatment together carry a combined u-value of about 0.40 and all three are decided before day zero. Layout at 0.167 and planting date at 0.20 follow immediately.
- **कृती (MR):** कालदर्शिका सुरुवातीला भारी ठेवा. जात, बेण्याचा स्रोत आणि बेणे प्रक्रिया यांचे एकत्रित u मूल्य सुमारे ०.४० आहे आणि तिन्ही निर्णय दिवस शून्यापूर्वी होतात. त्यानंतर लगेच लागवड पद्धत ०.१६७ आणि लागवडीची तारीख ०.२०.
- **Basis:** Three irrecoverable decisions worth about 38 percent combined are taken before the crop exists. An advisory engine that starts at planting has already missed the largest block of controllable loss.
- **Yield impact:** Determines whether the highest-value advisory window is used at all.
- **References:** Domain 11 G0 factor group; Core C13.7 pre-season stage

**D11-CL-002** (CL, info, conf 0.82, tier A)

- **When:** Ceiling being explained to a farmer
- **Action (EN):** State that the ceiling is the theoretical maximum with all u-values at zero, which never happens. Present the target range of 60, 90 and 110 as the realistic frame, and the state average of 53 as the benchmark.
- **कृती (MR):** कमाल मर्यादा म्हणजे सर्व घटक शून्य असल्यास मिळणारे सैद्धांतिक उत्पादन — आणि तसे प्रत्यक्षात कधीच होत नाही. वास्तववादी चौकट म्हणून ६०, ९० आणि ११० ही श्रेणी द्या, आणि राज्य सरासरी ५३ हा संदर्भ.
- **Basis:** Presenting the ceiling as an expectation sets up failure. Scenario A with excellent management computes to 102, which is below the ceiling because some loss is unavoidable.
- **Yield impact:** None. Sets expectations correctly, which affects whether the advice is believed.
- **References:** Domain 1 yield targets; Domain 11 scenario A

**D11-EC-001** (EC, info, conf 0.85, tier A)

- **When:** A u-value is being converted to money
- **Action (EN):** Multiply the ceiling by the u-value to get quintal lost, then by the price. Always state the price assumed, and run it at a crashed price as well as the current one.
- **कृती (MR):** कमाल मर्यादा गुणिले u = गमावलेले क्विंटल, गुणिले भाव = रुपये. वापरलेला भाव नेहमी सांगा, आणि चालू भावासोबत कोसळलेल्या भावावरही गणित चालवा.
- **Basis:** The same u-value is worth very different amounts at Rs 4,000 and Rs 12,000 per quintal, and ginger prices are strongly cyclical. Presenting one figure without the price assumption gives a false sense of precision.
- **Yield impact:** None. Makes the economic case honest and checkable.
- **References:** Domain 11 economic conversion; Domain 9 price cyclicality

**D11-EC-002** (EC, info, conf 0.8, tier A)

- **When:** The value of the advisory is being explained
- **Action (EN):** Present the four decisions that account for about Rs 2.85 lakh per acre — timely planting, broad ridge layout, correct variety, and timely earthing up. Three cost nothing and the fourth costs about Rs 6,000 in labour. All four depend on timing rather than on money.
- **कृती (MR):** एकरी सुमारे २.८५ लाख रुपये ठरवणारे चार निर्णय मांडा — वेळेवर लागवड, रुंद वरंबा, योग्य जात, आणि वेळेवर उटाळणी. तीन पूर्णपणे मोफत आहेत आणि चौथ्याला सुमारे ६,००० रुपये मजुरी लागते. चारही पैशावर नव्हे, वेळेवर अवलंबून आहेत.
- **Basis:** The four combine to about Rs 2,84,800 at 113 quintal and Rs 4,000 per quintal, against a combined cost of about Rs 6,000. None requires an expensive input, and each has a fixed window.
- **Yield impact:** None directly. It is the clearest statement of what a timing engine is worth.
- **References:** Domain 11 economic conversion table

**D11-EC-004** (EC, info, conf 0.78, tier B)

- **When:** Prevention spending is being justified
- **Action (EN):** Show the ratio. Preventing soft rot costs about Rs 24,500 in mulch, drainage, seed treatment and Trichoderma, against an exposure of about Rs 3.16 lakh. That is roughly thirteen to one.
- **कृती (MR):** गुणोत्तर दाखवा. कंदकूज टाळण्याचा खर्च — आच्छादन, निचरा, बेणे प्रक्रिया, ट्रायकोडर्मा — सुमारे २४,५०० रुपये, आणि टाळलेले संभाव्य नुकसान सुमारे ३.१६ लाख. म्हणजे सुमारे तेरा पट परतावा.
- **Basis:** The prevention stack costs about 17 percent of the total cost of cultivation and addresses the largest single loss factor in the crop. No fertiliser or chemical in the knowledge base has a comparable ratio.
- **Yield impact:** None directly. Justifies the budget line that the standard cost sheet omits.
- **References:** Domain 6 prevention stack; Domain 13 cost structure

**D11-FM-001** (FM, info, conf 0.9, tier A)

- **When:** Cumulative yield loss is being computed from multiple factors
- **Action (EN):** Use the sub-additive formula: total loss equals one minus the product of one minus each u-value. Never add the u-values.
- **कृती (MR):** sub-additive सूत्र वापरा — एकूण घट = १ वजा (प्रत्येक घटकाच्या १ वजा u यांचा गुणाकार). u मूल्यांची बेरीज कधीही करू नका.
- **Basis:** Losses act on what remains, not on the original crop. Five factors of 0.20 each sum to 1.00, which would mean zero yield and is impossible; multiplied they give 0.67 loss with 33 percent remaining, which is realistic.
- **Yield impact:** Method rather than a factor. Wrong aggregation produces impossible predictions.
- **References:** Core Layer C9.1

**D11-FM-003** (FM, info, conf 0.85, tier A)

- **When:** A source states a loss directly
- **Action (EN):** Use it as given with no conversion. Earthing up skipped is stated as 10 to 15 percent loss, so the u-value is 0.125 directly.
- **कृती (MR):** जसे आहे तसे वापरा, रूपांतर करू नका. उटाळणी न केल्यास १० ते १५% घट असे थेट सांगितले आहे, म्हणून u = ०.१२५ थेट.
- **Basis:** Applying the gain-to-loss conversion to a figure already expressed as a loss would understate it. The conversion applies in one direction only.
- **Yield impact:** Prevents a systematic understatement of directly stated losses.
- **References:** Agrowon earthing up loss statement

**D11-FM-004** (FM, info, conf 0.75, tier B)

- **When:** The independence assumption is being relied on in a computation
- **Action (EN):** Flag the assumption. The formula assumes independence and in ginger the factors are linked through the rot pathway. Present the result with that caveat rather than as an exact figure.
- **कृती (MR):** हे गृहीतक स्पष्ट करा. सूत्र घटक स्वतंत्र असल्याचे धरते, पण अद्रकात ते कूजच्या साखळीतून जोडलेले आहेत. निकाल नेमका आकडा म्हणून न देता या मर्यादेसह द्या.
- **Basis:** Every major pest is a gateway to rot, mechanical injury reaches the same endpoint, and poor mulch raises rot incidence directly. The dependencies all run toward one terminal outcome, which is why grouping matters more here than in a crop with independent loss pathways.
- **Yield impact:** None. Prevents overconfidence in a computed figure.
- **References:** Domain 11 interdependence caveat; Domain 5 central finding

**D11-GA-003** (GA, info, conf 0.78, tier B)

- **When:** Gap attribution complete AND gap_unexplained_pct is large
- **Action (EN):** Treat it as a finding, not a failure. Investigate whether a factor is missing from the register or whether one of the applied u-values is wrong. Record the hypothesis for the next season.
- **कृती (MR):** हा अपयश नाही, निष्कर्ष आहे. नोंदवहीतून एखादा घटक सुटला आहे का, की लावलेले एखादे u मूल्य चुकीचे आहे — हे तपासा. पुढील हंगामासाठी गृहीतक नोंदवा.
- **Basis:** The register has thirty-five factors and twenty-two of them are estimates, so a large residual is expected in the first season. Its size and direction indicate where the register is weakest.
- **Yield impact:** None. Directs the improvement effort.
- **References:** Domain 11 residual meaning

**D11-PR-001** (PR, info, conf 0.8, tier B)

- **When:** A yield prediction is being issued
- **Action (EN):** Always issue it with an interval and name the stage: pre-season plus or minus 25 percent, end of G1 plus or minus 22, mid-season plus or minus 20, pre-harvest plus or minus 12 without sampling and plus or minus 8 with it.
- **कृती (MR):** अंदाज नेहमी अंतरालासह द्या आणि टप्पा सांगा — हंगामापूर्व ±२५%, G1 अखेर ±२२%, मध्य-हंगाम ±२०%, काढणीपूर्व नमुन्याशिवाय ±१२% आणि नमुना घेतल्यास ±८%.
- **Basis:** A point estimate implies precision the method does not have, particularly when twenty-two of thirty-five inputs are estimates and the yield organ cannot be observed. The interval is the honest part of the prediction.
- **Yield impact:** None. Determines whether the prediction is trusted after the first season.
- **References:** Core C9.2; Domain 11 prediction staging

**D11-PR-004** (PR, info, conf 0.85, tier B)

- **When:** Prediction accuracy is being compared against sugarcane or another crop
- **Action (EN):** State plainly that ginger prediction will not match sugarcane accuracy because the yield organ is invisible. Then state what this domain is actually for — knowing which factor puts how much at risk, before it happens, which does not require an accurate forecast.
- **कृती (MR):** स्पष्ट सांगा — अद्रकाचा अंदाज उसाइतका अचूक असणार नाही, कारण उत्पादन अवयव जमिनीखाली आहे. मग या Domain चा खरा उपयोग सांगा — कोणता घटक किती उत्पादन धोक्यात घालतो हे आधी कळणे, आणि त्यासाठी अचूक अंदाजाची गरज नाही.
- **Basis:** Sugarcane offers height, millable cane count and Brix as non-destructive mid-season measurements. Ginger offers leaves and tillers, which correlate weakly with rhizome mass. Claiming equivalent accuracy would fail at the first harvest.
- **Yield impact:** None. Sets expectations that the method can meet.
- **References:** Domain 11 comparison table

**D11-RC-003** (RC, info, conf 0.82, tier A)

- **When:** A scheduled operation is completed or missed
- **Action (EN):** Record the date if done and the reason if not. Seventeen of thirty-five factors are record-detectable rather than sensor or observation detectable, so the operation log is the largest single input to attribution.
- **कृती (MR):** झाले असल्यास तारीख नोंदवा, नसल्यास कारण नोंदवा. पस्तीसपैकी सतरा घटक फक्त नोंदीवरून कळतात — sensor किंवा निरीक्षणावरून नाही. म्हणून कामाची नोंदवही हा दरी-विश्लेषणाचा सर्वात मोठा एकच स्रोत आहे.
- **Basis:** Mulch stages, earthing up, fertiliser splits, micronutrient sprays and layout choice are all invisible at harvest. Only the record shows whether they happened, and the reason for an omission is what reveals implementation barriers.
- **Yield impact:** None directly. It is the majority of the attribution input.
- **References:** Domain 11 register summary; Domain 8 overdue operation query

**D11-SC-001** (SC, info, conf 0.78, tier A)

- **When:** Pre-season planning AND a yield expectation is requested
- **Action (EN):** Present the scenarios rather than a single number. Excellent management gives about 102 quintal, good management with some slips about 86, typical management about 50, and a disease event on good management about 34.
- **कृती (MR):** एक आकडा न देता परिस्थिती मांडा. उत्कृष्ट व्यवस्थापन सुमारे १०२ क्विंटल, चांगले व्यवस्थापन काही चुकांसह सुमारे ८६, सामान्य व्यवस्थापन सुमारे ५०, आणि चांगल्या व्यवस्थापनावर रोगाचा फटका बसल्यास सुमारे ३४.
- **Basis:** The scenarios make the consequences of specific omissions visible rather than abstract. The gap between B at 86 and C at 50 is five common management omissions, which is a concrete and actionable comparison.
- **Yield impact:** None. Makes the value of the advisory legible before the season starts.
- **References:** Domain 11 scenario computations

**D11-UV-001** (UV, info, conf 0.85, tier A)

- **When:** A u-value is being applied to a computation
- **Action (EN):** Carry its source class with it. Ten of thirty-five are quantitatively sourced, fourteen are descriptive or derived, and eleven are estimates. Report the aggregate confidence accordingly rather than presenting all values as equal.
- **कृती (MR):** u मूल्यासोबत त्याचा स्रोत वर्ग वापरा. पस्तीसपैकी दहा संख्यात्मक स्रोतातून, चौदा वर्णनात्मक किंवा derived, आणि अकरा अंदाजित आहेत. सर्व मूल्ये सारखी विश्वासार्ह म्हणून दाखवू नका.
- **Basis:** A prediction built mostly on estimates should not be reported with the same confidence as one built on measured values. Carrying the class through the computation lets the interval reflect the evidence.
- **Yield impact:** None. Makes the stated uncertainty honest.
- **References:** Domain 11 u-value register; Domain 1 source class definitions

**D11-UV-002** (UV, info, conf 0.82, tier B)

- **When:** First-season records become available for a factor
- **Action (EN):** Update that u-value from EST to FIELD class and record both the old and new values. Do not overwrite the original — the change itself is the learning.
- **कृती (MR):** त्या u मूल्याचा वर्ग EST वरून FIELD मध्ये बदला आणि जुने व नवे दोन्ही मूल्य नोंदवा. मूळ मूल्य पुसू नका — बदल हाच शिकण्याचा भाग आहे.
- **Basis:** Twenty-two of thirty-five values are estimates and can only become measurements through recorded outcomes. Keeping the original alongside the revision shows how far the estimate was off, which is information about the estimation method itself.
- **Yield impact:** None this season. It is the mechanism by which the whole register improves.
- **References:** Domain 11 gap attribution; Domain 12 learning layer

**D11-UV-003** (UV, info, conf 0.85, tier A)

- **When:** Factors are being ranked for attention
- **Action (EN):** Note that twenty-four of thirty-five factors are irrecoverable, about 69 percent. That means most advisory has to be preventive and issued before the window opens, not diagnostic after symptoms appear.
- **कृती (MR):** पस्तीसपैकी चोवीस घटक भरून निघत नाहीत — सुमारे ६९%. म्हणजे बहुतांश सल्ला प्रतिबंधात्मक असावा लागतो आणि खिडकी उघडण्यापूर्वी द्यावा लागतो, लक्षणे दिसल्यानंतरचा निदानात्मक नाही.
- **Basis:** For an irrecoverable factor, detection after the event has no remedial value. The advisory has to fire on the environmental precondition or the calendar rather than on the symptom.
- **Yield impact:** Determines the fundamental shape of the advisory engine.
- **References:** Domain 11 register summary; Domain 6 trigger-based escalation

**D11-UV-004** (UV, info, conf 0.78, tier B)

- **When:** Sensor coverage is being justified
- **Action (EN):** Note that only seven of thirty-five factors are sensor-detectable, but they include the largest ones — saturation, water exhaustion and critical window stress. Sensors cover few factors and the heaviest ones.
- **कृती (MR):** पस्तीसपैकी फक्त सात घटक sensor ने कळतात — पण त्यात सर्वात मोठे घटक येतात: पाणी साचणे, पाणी संपणे, आणि निर्णायक अवस्थेतील ताण. sensor कमी घटक व्यापतात, पण सर्वात जड घटक व्यापतात.
- **Basis:** Counting factors would understate the sensor's value and counting u-value would overstate the breadth. Both figures together give the accurate picture — narrow coverage, heavy weight.
- **Yield impact:** None. Frames the hardware investment honestly.
- **References:** Domain 11 register summary; Domain 5 sensor limitation; Domain 6 sensor strength

**D11-VL-001** (VL, info, conf 0.75, tier A)

- **When:** The u-value method is being justified to a partner or reviewer
- **Action (EN):** Present the validation. Scenario C uses five independently sourced u-values with no tuning and computes 50 quintal per acre. The Maharashtra state average is 53. Agreement is within about 6 percent.
- **कृती (MR):** पडताळणी मांडा. परिस्थिती C मध्ये स्वतंत्रपणे गोळा केलेली पाच u मूल्ये, कोणतेही समायोजन न करता, ५० क्विंटल प्रति एकर देतात. महाराष्ट्राचे प्रत्यक्ष राज्य सरासरी उत्पादन ५३ आहे. फरक सुमारे ६%.
- **Basis:** The five factors were gathered from separate sources over separate research sessions with no reference to the state average. That the aggregate reproduces the observed figure supports three things: the u-values are approximately right, the ceiling-to-average gap is management rather than environment, and the gap is therefore addressable.
- **Yield impact:** None directly. It is the numerical basis of the product's commercial argument.
- **References:** Directorate of Agriculture Maharashtra 2023; Domain 11 scenario C

### D12

**D12-AL-002** (AL, info, conf 0.78, tier B)

- **When:** A low-confidence decision, an unexpected outcome or a symptom outside the decision tree occurs
- **Action (EN):** Queue it for expert review with the full context. Include the rule that fired, the inputs it used, and the outcome if known.
- **कृती (MR):** संपूर्ण संदर्भासह तज्ज्ञ तपासणीसाठी रांगेत ठेवा — कोणता नियम लागू झाला, त्याला कोणती माहिती मिळाली, आणि निकाल माहीत असल्यास तोही.
- **Basis:** These are the cases where the rule base is weakest, and reviewing them is how the rules improve. Without the inputs alongside the decision, the reviewer cannot tell whether the rule or the data was at fault.
- **Yield impact:** None directly. It is the correction mechanism for the rule base.
- **References:** Core C12.3 active learning queue

**D12-ARCH-001** (ARCH, info, conf 0.88, tier B)

- **When:** Development priorities are being set
- **Action (EN):** Build layer 1 rules and layer 2 language first. Layer 3 learning depends on both plus accumulated records and cannot be built earlier. Layers 1 and 2 deliver full value on their own.
- **कृती (MR):** आधी थर १ — नियम, आणि थर २ — भाषा. थर ३ शिकण्यासाठी आधीचे दोन आणि जमा झालेल्या नोंदी लागतात, त्याआधी तो बांधता येत नाही. आणि थर १ व २ स्वतःच पूर्ण मूल्य देतात.
- **Basis:** The dependency runs one way. Rules need nothing, language needs rules, learning needs both plus data. Attempting layer 3 first produces a model trained on nothing.
- **Yield impact:** None. Determines whether the product ships at all in season one.
- **References:** Domain 12 layer model

**D12-CLS-002** (CLS, info, conf 0.85, tier B)

- **When:** A machine learning model is proposed for the yellowing problem
- **Action (EN):** Keep the decision tree. Every branch has a stated reason, errors are traceable to a branch, and it needs no training data. Later, image recognition can answer two of the five questions automatically — but the tree does not change.
- **कृती (MR):** निर्णय-वृक्षच ठेवा. प्रत्येक फांदीला स्पष्ट कारण आहे, चूक कुठे झाली ते कळते, आणि प्रशिक्षण डेटा लागत नाही. पुढे प्रतिमा-ओळख पाचपैकी दोन प्रश्नांची उत्तरे आपोआप देऊ शकेल — पण वृक्ष तोच राहील.
- **Basis:** A classifier trained on no data cannot outperform a tree built from documented differential diagnosis. The tree is also auditable, which matters when two of the six outcomes involve telling the farmer not to spray.
- **Yield impact:** None. Prevents replacing a working method with an untrained one.
- **References:** Domain 12 why tree not model

**D12-CLU-002** (CLU, info, conf 0.8, tier A)

- **When:** White grub is confirmed on any farm in the cluster
- **Action (EN):** Issue a simultaneous alert to all farms in the cluster asking for beetle collection on the same three evenings. Individual action does not work because the beetles fly.
- **कृती (MR):** cluster मधील सर्व शेतांना एकाच वेळी इशारा द्या — पुढील तीन संध्याकाळी सर्वांनी भुंगेरे गोळा करावेत. भुंगेरे उडतात, त्यामुळे एकट्याने केलेले नियंत्रण टिकत नाही.
- **Basis:** The source states that integrated management carried out collectively is beneficial for this pest. A single treated field is recolonised from neighbouring untreated ones, so simultaneity is what makes the control work.
- **Yield impact:** Raises the effectiveness of the 0.10 white grub control from partial to substantial.
- **References:** Agrowon - Mali and Mahajan white grub; Domain 5 cluster alert

**D12-COLD-001** (COLD, info, conf 0.85, tier A)

- **When:** A required input is missing — calibration, soil test, local weather record
- **Action (EN):** Degrade gracefully and say so. Fall back to the table, the safe default or the regional forecast, mark the confidence lower, and tell the user what is missing and what would improve it.
- **कृती (MR):** प्रणाली थांबवू नका — कमी अचूकतेने चालू ठेवा आणि ते सांगा. तक्ता, सुरक्षित default किंवा प्रादेशिक अंदाजावर परत जा, विश्वासार्हता कमी दाखवा, आणि काय उपलब्ध नाही व काय केल्यास सुधारेल हे वापरकर्त्याला सांगा.
- **Basis:** Season one has zero field data, incomplete calibration and no soil test. A system that refuses to operate without them delivers nothing in the season where the largest decisions are made.
- **Yield impact:** Determines whether the advisory functions at all in the first season.
- **References:** Domain 3 fallback rules; Domain 12 degradation table

**D12-EVAL-001** (EVAL, info, conf 0.85, tier B)

- **When:** System performance is being measured or reported
- **Action (EN):** Use action compliance rate as the primary metric — recommended actions completed on time divided by recommended actions issued. Target above 60 percent in season one and above 80 percent by season three. Do not report messages sent or app opens.
- **कृती (MR):** मुख्य मापदंड म्हणून कृती-पालन दर वापरा — वेळेवर पूर्ण झालेल्या कृती भागिले सुचवलेल्या कृती. पहिल्या हंगामात ६०% वर, तिसऱ्या हंगामापर्यंत ८०% वर हे लक्ष्य. पाठवलेले संदेश किंवा ॲप उघडण्याची संख्या नोंदवू नका.
- **Basis:** Four decisions worth about Rs 2.85 lakh per acre all depend on doing something at the right time. So system success is whether the farmer acted on time, and that requires a record rather than a model to measure.
- **Yield impact:** None directly. It is the metric that connects advisory to yield.
- **References:** Domain 12 evaluation; Domain 11 economic conversion

**D12-EVAL-002** (EVAL, info, conf 0.8, tier B)

- **When:** A trigger fired and the predicted event did not follow
- **Action (EN):** Record it as a false alarm but do not reflexively raise the threshold. For irrecoverable factors a high false alarm rate is the correct trade — ten unnecessary drainage inspections cost ten walks; one missed saturation event costs most of the crop.
- **कृती (MR):** ती खोटी सूचना म्हणून नोंदवा, पण लगेच मर्यादा वाढवू नका. भरून न निघणाऱ्या घटकांसाठी जास्त खोट्या सूचना हा योग्य सौदा आहे — दहा अनावश्यक निचरा तपासण्या म्हणजे दहा फेऱ्या; एक चुकलेली संपृक्तता घटना म्हणजे बहुतांश पीक.
- **Basis:** For a factor that cannot be recovered, detection after the event has no remedial value, so the trigger must fire on the precondition. The asymmetry between the cost of a false alarm and the cost of a miss justifies a high sensitivity setting.
- **Yield impact:** Protects the largest u-values in the register from being tuned away.
- **References:** Domain 6 trigger-based escalation; Domain 11 irrecoverability count

**D12-EVAL-003** (EVAL, info, conf 0.7, tier B)

- **When:** The effect of the advisory needs demonstrating
- **Action (EN):** Compare a new cluster against its own previous season rather than withholding advice from a control group. Withholding is ethically uncomfortable and practically difficult.
- **कृती (MR):** नियंत्रण गट ठेवून काही शेतांना सल्ला नाकारण्याऐवजी, नवीन cluster ची तुलना त्याच्याच मागील हंगामाशी करा. सल्ला नाकारणे नैतिकदृष्ट्या नाजूक आणि व्यावहारिकदृष्ट्या अवघड आहे.
- **Basis:** A true control group would give the cleanest evidence but requires denying advice to farmers who could benefit. A before-and-after comparison within the same cluster is weaker evidence but avoids that problem and is achievable.
- **Yield impact:** None. Determines whether the product's effect can be demonstrated to partners.
- **References:** Domain 12 control group note

**D12-IMG-002** (IMG, info, conf 0.75, tier B)

- **When:** Image recognition targets are being prioritised
- **Action (EN):** Rank central shoot death first at u equals 0.70, then interveinal versus uniform yellowing, then straight-line holes as a safe first technical target because the stakes are low.
- **कृती (MR):** क्रम — सुरळी मरणे प्रथम (u = ०.७०), मग शिरांमधील विरुद्ध एकसारखे पिवळे, मग सरळ रेषेतील छिद्रे. शेवटचा तांत्रिकदृष्ट्या सुरक्षित पहिला प्रयत्न आहे कारण त्यात चूक झाली तरी नुकसान कमी.
- **Basis:** Central shoot death is the earliest visible sign of the largest factor, so it has the highest value. Straight-line holes in the whorl are the most visually distinctive pattern in the set and carry only 0.05, which makes them a safe place for a first model that may be wrong.
- **Yield impact:** Directs the modelling effort toward value and away from what is merely easy.
- **References:** Domain 12 image candidates; Domain 11 u-value register

**D12-LANG-001** (LANG, info, conf 0.82, tier B)

- **When:** An advisory is being generated
- **Action (EN):** Generate both Marathi and English from one structured advisory object. Do not translate one into the other — translation loses agricultural terms.
- **कृती (MR):** एकाच संरचित सल्ला-वस्तूतून मराठी आणि इंग्रजी दोन्ही तयार करा. एकाचे दुसऱ्यात भाषांतर करू नका — भाषांतरात कृषी संज्ञा चुकतात.
- **Basis:** Utalni has no single English equivalent; earthing up loses the root-disturbance element that is the whole mechanism. Vafsa has no English equivalent at all. Generating both from one source keeps them consistent and keeps the terms correct in each.
- **Yield impact:** None directly. Determines whether the advice is understood.
- **References:** Core C12.2; Domain 12 vocabulary gap

**D12-LOG-003** (LOG, info, conf 0.78, tier B)

- **When:** Sensor sampling frequency is being configured
- **Action (EN):** Scale frequency by stage criticality — hourly in G1, G3 and G4, four-hourly in G2 and G5, daily in G0, and hourly at all stages during a rain alert. This is a power management decision as well as an agronomic one.
- **कृती (MR):** अवस्थेच्या निकडीनुसार वारंवारता ठरवा — G1, G3, G4 मध्ये तासाला, G2 आणि G5 मध्ये चार तासांनी, G0 मध्ये दिवसातून एकदा, आणि पावसाच्या इशाऱ्यादरम्यान सर्व अवस्थांत तासाला. हा agronomy इतकाच वीज-व्यवस्थापनाचा निर्णयही आहे.
- **Basis:** Saturation damage accrues over hours, so hourly sampling is needed when the crop is sensitive. Battery and LoRa airtime on the sub-node are finite, so uniform high-frequency sampling is not an option.
- **Yield impact:** Affects how early a saturation event is detected, which carries the largest u-value in the register.
- **References:** Domain 3 sensor binding; Core C6.2

**D12-MOAT-001** (MOAT, info, conf 0.82, tier B)

- **When:** The competitive position is being described
- **Action (EN):** Be accurate about what is and is not defensible. The language models are open, the agronomy is published and the hardware is purchasable. The defensible asset is the pairing of that knowledge with this plot's measurements and outcomes over several seasons.
- **कृती (MR):** काय बचावयोग्य आहे आणि काय नाही याबद्दल अचूक रहा. भाषा मॉडेल खुली आहेत, कृषिशास्त्र प्रकाशित आहे, आणि hardware विकत मिळते. बचावयोग्य मालमत्ता म्हणजे ते ज्ञान या शेताच्या मोजमापांशी आणि निकालांशी अनेक हंगामांत जोडणे.
- **Basis:** Claiming the knowledge base itself as proprietary would be false — every source in Domains 1 to 13 is public. What cannot be copied is a weather bias correction for this village, a crop coefficient series derived here, and sensor readings paired with outcomes from the same plot.
- **Yield impact:** None. Makes the commercial argument survivable under scrutiny.
- **References:** Domain 12 moat analysis

**D12-MOD-001** (MOD, info, conf 0.85, tier B)

- **When:** Language technology is being selected for seasons 1 and 2
- **Action (EN):** Use templated Marathi messages with no model. A template cannot generate wrong advice, which matters more in the first seasons than fluency does.
- **कृती (MR):** साचेबद्ध मराठी संदेश वापरा, मॉडेल नाही. साचा चुकीचा सल्ला तयार करू शकत नाही — आणि पहिल्या हंगामांत ते ओघवत्या भाषेपेक्षा जास्त महत्वाचे आहे.
- **Basis:** A generative model can produce a plausible sentence recommending a wrong dose or a blocklisted molecule. A template cannot. With chemical rules, CIB&RC gaps and safety blocks in the rule base, that containment is worth more than natural phrasing.
- **Yield impact:** None. Prevents a failure mode with real safety and legal exposure.
- **References:** Domain 12 language roadmap

**D12-MOD-002** (MOD, info, conf 0.75, tier B)

- **When:** A Marathi agricultural dataset is being sought
- **Action (EN):** Note that none exists. Bengali has KrishokChat and English has AgriGPT and AgroInstruct, but no Marathi agricultural instruction dataset was located. Farmer.Chat handled over 5 million queries and released nothing.
- **कृती (MR):** असा dataset उपलब्ध नाही. बंगालीसाठी KrishokChat आहे, इंग्रजीसाठी अनेक आहेत, पण मराठी कृषी instruction dataset सापडला नाही. Farmer.Chat ने ५० लाखांहून जास्त प्रश्न हाताळले आणि काहीही प्रकाशित केले नाही.
- **Basis:** The absence means no ready model can be adopted for Marathi agricultural dialogue, which is an obstacle. It also means a Marathi dataset built here would be scarce, which is relevant to research collaboration and to data partnership discussions.
- **Yield impact:** None. Shapes the technology roadmap and one commercial argument.
- **References:** KrishokChat arXiv review; AgriGPT; AgroInstruct; Farmer.Chat

**D12-POS-002** (POS, info, conf 0.85, tier A)

- **When:** The value proposition is being explained
- **Action (EN):** Lead with the timing value, not the technology. Four decisions worth about Rs 2.85 lakh per acre depend on doing something at the right time, and a rule engine delivers those from day one without any machine learning.
- **कृती (MR):** तंत्रज्ञानाने नव्हे, वेळेच्या मूल्याने सुरुवात करा. एकरी सुमारे २.८५ लाख रुपये ठरवणारे चार निर्णय वेळेवर कृती करण्यावर अवलंबून आहेत, आणि नियम-इंजिन ते दिवस एकपासून देते — कोणत्याही machine learning शिवाय.
- **Basis:** Three of the four decisions cost nothing and the fourth costs about Rs 6,000 in labour. None requires new technology; all require being reminded at the right moment, which is what a machine does reliably and a person does not.
- **Yield impact:** None directly. It is the clearest and most defensible statement of what the product is worth.
- **References:** Domain 11 economic conversion; Domain 12 layer model

**D12-ROAD-001** (ROAD, info, conf 0.82, tier B)

- **When:** Season 1 planning
- **Action (EN):** Season 1 delivers the rule engine, templated Marathi messages, the ten minimum records, sensor calibration, photograph collection without labelling, compliance measurement and the DPDP consent structure. No machine learning.
- **कृती (MR):** पहिला हंगाम — नियम-इंजिन कार्यरत, साचेबद्ध मराठी संदेश, दहा किमान नोंदी, sensor calibration, फोटो जमवणे (लेबल न लावता), कृती-पालन दर मोजणे, आणि DPDP संमती रचना. Machine learning नाही.
- **Basis:** Each season one item is either immediately valuable or is data that cannot be collected retrospectively. Nothing in the list depends on a model existing.
- **Yield impact:** Delivers the full layer 1 and layer 2 value in the first season.
- **References:** Domain 12 season roadmap

**D12-ROAD-002** (ROAD, info, conf 0.7, tier B)

- **When:** Season 4 or later AND the accumulated records support model training
- **Action (EN):** At this point local u-values can feed back into the rule engine, a fine-tuned Marathi dialogue model becomes viable, and multi-cluster federated learning becomes possible. This is when the word AI can be used honestly.
- **कृती (MR):** आता स्थानिक u मूल्ये नियम-इंजिनमध्ये परत जोडता येतील, मराठी संवाद मॉडेल fine-tune करता येईल, आणि अनेक cluster मध्ये federated learning शक्य होईल. याच टप्प्यावर 'AI' हा शब्द प्रामाणिकपणे वापरता येईल.
- **Basis:** Three or four seasons of gap attribution move a substantial share of the 22 estimated u-values into FIELD class, and by then the controlled vocabulary and labelled images exist. The learning layer improves accuracy; it does not enable anything that was impossible before.
- **Yield impact:** Improves accuracy of predictions and triggers rather than adding new capability.
- **References:** Domain 12 season roadmap; Domain 11 u-value validation

**D12-VOI-001** (VOI, info, conf 0.75, tier B)

- **When:** Voice input is being considered for seasons 1 or 2
- **Action (EN):** Defer it. Templated messages with simple button responses are sufficient and safer. Voice becomes necessary once farmers start asking free-form questions, by which time the rule base should be stable.
- **कृती (MR):** पुढे ढकला. साचेबद्ध संदेश आणि साधी बटण-उत्तरे पुरेशी आणि अधिक सुरक्षित आहेत. शेतकरी मुक्त प्रश्न विचारू लागल्यावर आवाजाची खरी गरज येते — आणि तोपर्यंत नियम-आधार स्थिर झालेला असावा.
- **Basis:** ASR tools exist for Marathi through IndicWhisper and IndicWav2Vec, but they will not reliably recognise ginger technical terms without vocabulary biasing. Building voice before the vocabulary is complete produces a system that mishears the most important words.
- **Yield impact:** None. Sequences the technology work correctly.
- **References:** AI4Bharat ASR tools; Domain 12 voice limitation

### D13

**D13-AD-004** (AD, info, conf 0.8, tier B)

- **When:** A farmer asks whether ginger is worth planting
- **Action (EN):** Answer with the structure, not a verdict. Break-even is about Rs 1,450 per quintal or 36 quintal per acre, the safety margin is two to three times, the real risk is soft rot rather than price, and roughly Rs 1.45 lakh goes out over eight months before any income.
- **कृती (MR):** निवाडा न देता रचना मांडा. समतोल भाव सुमारे १,४५० रुपये प्रति क्विंटल किंवा ३६ क्विंटल प्रति एकर, सुरक्षिततेचा पट्टा दोन ते तीन पट, खरी जोखीम भाव नव्हे तर कंदकूज, आणि सुमारे १.४५ लाख रुपये आठ महिन्यांत बाहेर जातात — उत्पन्न शेवटी.
- **Basis:** The decision depends on the farmer's water availability, cash position and risk tolerance, none of which the engine knows better than they do. What it can supply is the arithmetic and the risk structure.
- **Yield impact:** None. Supports the decision rather than making it.
- **References:** Domain 13 break-even; Domain 13 central finding

**D13-BE-001** (BE, info, conf 0.78, tier B)

- **When:** Viability is being assessed before planting
- **Action (EN):** Show the break-even. At Rs 1,45,000 cost and 100 quintal yield, break-even price is about Rs 1,450 per quintal. At Rs 4,000 per quintal, break-even yield is about 36 quintal per acre. Both leave a margin of two to three times against realistic outcomes.
- **कृती (MR):** समतोल बिंदू दाखवा. १,४५,००० खर्च आणि १०० क्विंटल उत्पादन धरल्यास समतोल भाव सुमारे १,४५० रुपये प्रति क्विंटल. ४,००० रुपये भावाला समतोल उत्पादन सुमारे ३६ क्विंटल प्रति एकर. दोन्हीत वास्तववादी निकालांविरुद्ध दोन ते तीन पट सुरक्षिततेचा पट्टा आहे.
- **Basis:** Costs are covered even if the price collapses to a third of the conservative planning figure or the yield falls to a third of target. This is the crop's genuine economic strength.
- **Yield impact:** None. Gives the farmer a floor rather than only a headline profit.
- **References:** Domain 13 break-even computation

**D13-CF-002** (CF, info, conf 0.75, tier B)

- **When:** Cash flow gap identified as a constraint
- **Action (EN):** Offer the mitigations. Marigold or coriander intercrop gives cash at two to three months against ginger's eight; a crop loan smooths the gap at an interest cost; splitting the area with a shorter crop works; and an early green harvest at six months gives partial cash at lower weight.
- **कृती (MR):** उपाय मांडा. झेंडू किंवा कोथिंबीर आंतरपीक दोन ते तीन महिन्यांत रोख देते, अद्रकाला आठ महिने लागतात. पीक कर्ज खंड भरून काढते पण व्याज लागते. क्षेत्र विभागून काही भाग कमी कालावधीच्या पिकाला देता येतो. आणि सहा महिन्यांत हिरवे आले काढल्यास कमी वजनात काही रोख मिळते.
- **Basis:** Marigold is the strongest option because it also suppresses nematodes and attracts beneficial insects, so the cash flow benefit comes with two agronomic ones. The others each trade something — interest, area, or weight.
- **Yield impact:** Marigold reduces the 0.15 nematode exposure as a side effect.
- **References:** Domain 5 marigold trap crop; Domain 8 intercrop ranking; Domain 9 early green harvest

**D13-CF-003** (CF, info, conf 0.7, tier B)

- **When:** Crop loan being considered
- **Action (EN):** Obtain the scale of finance for ginger from the district lead bank and include the interest in the cost model. If the scale of finance is set low or not set at all for this crop, the available credit will not match the actual cost.
- **कृती (MR):** जिल्हा अग्रणी बँकेकडून अद्रकाचा scale of finance घ्या आणि व्याज खर्चात धरा. या पिकासाठी तो कमी असेल किंवा ठरवलेलाच नसेल, तर उपलब्ध कर्ज प्रत्यक्ष खर्चाशी जुळणार नाही.
- **Basis:** Scale of finance is set per crop by the district technical committee. Ginger is uncommon here — about 4,000 hectares statewide — so it may be set low or absent, and that changes the viable area.
- **Yield impact:** None. Determines whether the plan is financeable at the intended area.
- **References:** Domain 10 scale of finance item

**D13-CP-002** (CP, info, conf 0.8, tier B)

- **When:** Capital planning in progress
- **Action (EN):** Model both cases — with subsidy and without. At 80 percent subsidy the farmer's annual share is about one fifth of the unsubsidised figure. Selection is by lottery, so both cases are live until the result is known.
- **कृती (MR):** दोन्ही परिस्थिती मांडा — अनुदानासह आणि अनुदानाशिवाय. ८०% अनुदानात शेतकऱ्याचा वार्षिक हिस्सा अनुदानाशिवायच्या सुमारे एक पंचमांश होतो. निवड लॉटरीने होते, म्हणून निकाल कळेपर्यंत दोन्ही शक्यता जिवंत आहेत.
- **Basis:** The difference between the two cases falls entirely on capital rather than on operating cost, and it is large enough that the viable area differs between them. Planning on one case and receiving the other means either an unplanned capital burden or an unnecessarily small planting.
- **Yield impact:** None. Determines the area decision.
- **References:** Domain 10 subsidy rules

**D13-CP-003** (CP, info, conf 0.72, tier B)

- **When:** Farm pond being evaluated
- **Action (EN):** Count both returns. It stores monsoon water that must be removed to prevent rot and supplies it back when the well is under pressure from October. Value it against both the irrigation saving and the rot exposure avoided.
- **कृती (MR):** दोन्ही परतावे मोजा. मान्सूनमध्ये जे पाणी कूज टाळण्यासाठी काढून टाकावे लागते तेच साठवते, आणि ऑक्टोबरनंतर विहिरीवर ताण असताना परत देते. सिंचन बचत आणि टाळलेला कूज-धोका — दोन्ही धरा.
- **Basis:** The pond addresses two separate exposures with one structure. Valuing it only on irrigation saving understates it by the rot exposure it also reduces, which is the larger of the two.
- **Yield impact:** Reduces exposure to both the waterlogging pathway and the late-season exhaustion pathway.
- **References:** Domain 10 farm pond dual benefit; Domain 3 October to February shortfall

**D13-CS-002** (CS, info, conf 0.78, tier C)

- **When:** Cost structure being explained
- **Action (EN):** Note that labour is about 34 percent of total across planting, earthing up and harvest, and harvest with transport alone is about 21 percent because ginger is heavy and the markets are far.
- **कृती (MR):** लागवड, उटाळणी आणि काढणी मिळून मजुरी एकूण खर्चाच्या सुमारे ३४% आहे, आणि एकट्या काढणी-वाहतुकीचा वाटा सुमारे २१% — कारण आले जड आहे आणि बाजार दूर आहेत.
- **Basis:** A hundred quintal crop is ten tonnes to lift, wash and move. Mumbai is roughly 350 km and Nagpur roughly 500 km from here, and the local APMC does not appear in the arrival lists at all.
- **Yield impact:** None. Explains why transport cost is a material unmeasured figure.
- **References:** Shetkari Marg cost breakdown; Domain 9 market distances

**D13-CS-003** (CS, info, conf 0.75, tier B)

- **When:** Labour planning for the season
- **Action (EN):** Record labour days per operation this season. No source gives per acre labour days for ginger, so the labour share of about 34 percent rests on rupee figures rather than on measured days.
- **कृती (MR):** या हंगामात प्रत्येक कामासाठी लागलेले मजूर-दिवस नोंदवा. अद्रकासाठी एकरी मजूर-दिवसांचा आकडा कोणत्याही स्रोतात नाही, त्यामुळे मजुरीचा सुमारे ३४% वाटा रुपयांवर आधारित आहे, मोजलेल्या दिवसांवर नाही.
- **Basis:** Rupee figures move with wage rates while day counts do not. Without day counts the cost model cannot be adjusted for a different wage level or a different area.
- **Yield impact:** None. Makes the cost model portable.
- **References:** Domain 8 labour gap; Domain 13 cost structure

**D13-RP-001** (RP, info, conf 0.75, tier B)

- **When:** The retain versus purchase decision is being made
- **Action (EN):** Include the opportunity cost. Retaining 1,308 kg is not free — at Rs 47 per kg it is about Rs 61,500 of produce not sold. Compare that against the purchase cost of about Rs 40,000, not against zero.
- **कृती (MR):** संधी-खर्च धरा. १,३०८ किलो बेणे राखणे फुकट नाही — प्रति किलो ४७ रुपये दराने ते सुमारे ६१,५०० रुपयांचा न विकलेला माल आहे. त्याची तुलना सुमारे ४०,००० रुपयांच्या खरेदी खर्चाशी करा, शून्याशी नाही.
- **Basis:** The comparison is normally made between a cash outlay and nothing, which makes retention look free. Including the foregone sale plus the storage loss makes the true retained cost about Rs 61,500 rather than zero.
- **Yield impact:** None. Corrects a systematically wrong comparison.
- **References:** Core C13.5; Domain 13 storage loss

**D13-SD-001** (SD, info, conf 0.8, tier C)

- **When:** Cost planning is being explained
- **Action (EN):** State that seed is the largest single cost at 28 to 35 percent, about Rs 40,000 per acre at roughly Rs 47 per kg. Every seed decision — variety, source, rate, treatment, storage — is therefore also a cost decision.
- **कृती (MR):** बेणे ही सर्वात मोठी खर्च रेषा आहे — एकूण खर्चाच्या २८ ते ३५%, एकरी सुमारे ४०,००० रुपये, प्रति किलो सुमारे ४७ रुपये. म्हणून बेण्याचा प्रत्येक निर्णय — जात, स्रोत, प्रमाण, प्रक्रिया, साठवण — हा खर्चाचाही निर्णय आहे.
- **Basis:** At 34.8 percent of the published breakdown, seed exceeds fertiliser, plant protection and land preparation combined. It is also spent before the season starts, which makes it unrecoverable if the crop fails.
- **Yield impact:** None directly. Frames why the seed rules across Domains 1, 6, 8 and 10 carry the priority they do.
- **References:** Shetkari Marg cost breakdown; Core C13

**D13-SD-003** (SD, info, conf 0.8, tier A)

- **When:** Seed treatment cost is being questioned
- **Action (EN):** Show the germination arithmetic. Untreated germination is 80 to 83 percent against 93 to 98 treated, a 15 percent difference worth about Rs 6,000 on an 850 kg requirement, against a treatment cost of Rs 2,000 to 3,000. The disease prevention value is separate and larger.
- **कृती (MR):** उगवणीचे गणित दाखवा. प्रक्रिया न केलेले बेणे ८० ते ८३% उगवते, प्रक्रिया केलेले ९३ ते ९८%. १५% फरक म्हणजे ८५० किलोवर सुमारे ६,००० रुपयांचे बेणे, आणि प्रक्रियेचा खर्च २,००० ते ३,००० रुपये. रोग प्रतिबंधाचे मूल्य यापेक्षा वेगळे आणि मोठे आहे.
- **Basis:** The return is at least two to one on germination alone. Adding the disease prevention value — seed rhizome is the primary introduction route for both soft rot and bacterial wilt — makes it substantially higher.
- **Yield impact:** u = 0.135 on establishment, which is a hard ceiling for the season.
- **References:** Springer soft rot management study germination figures; Domain 6 seed treatment rule

**D13-SL-002** (SL, info, conf 0.72, tier C)

- **When:** Storage method is being chosen
- **Action (EN):** Use the pit method rather than a shade heap. Reducing loss from 30 to 20 percent saves about 152 kg, roughly Rs 7,100, against a cost of digging, sand, a plank and thatch.
- **कृती (MR):** सावलीत रचून ठेवण्याऐवजी खड्डा पद्धत वापरा. घट ३०% वरून २०% आणल्यास सुमारे १५२ किलो वाचते — म्हणजे सुमारे ७,१०० रुपये — आणि खर्च फक्त खोदणे, वाळू, फळी आणि गवताचे छप्पर.
- **Basis:** Simple shade storage loses 25 to 30 percent. The pit method controls temperature and humidity through plaster, sand layering and an air hole, and the source explicitly warns against closed rooms of tin, cement or tile.
- **Yield impact:** None. A direct saving on the largest input.
- **References:** AgroWorld pit storage detail

**D13-SN-001** (SN, info, conf 0.78, tier B)

- **When:** Expected return is being presented
- **Action (EN):** Present the matrix, not a number. Show yield from 30 to 110 quintal against price from Rs 2,000 to 12,000. Loss occurs only where yield is below about 50 quintal and the price is low.
- **कृती (MR):** एक आकडा न देता मॅट्रिक्स मांडा — उत्पादन ३० ते ११० क्विंटल विरुद्ध भाव २,००० ते १२,००० रुपये. तोटा फक्त तिथेच होतो जिथे उत्पादन सुमारे ५० क्विंटलपेक्षा कमी आणि भाव कमी असेल.
- **Basis:** A single expected return figure hides the shape of the risk. The matrix shows immediately that the yield axis matters more than the price axis, which redirects attention to the agronomy where it belongs.
- **Yield impact:** None. Makes the risk structure visible before the money is committed.
- **References:** Domain 13 scenario matrix

**D13-SN-003** (SN, info, conf 0.78, tier B)

- **When:** The prevention budget is being questioned
- **Action (EN):** Show the ratio. Mulch, drainage, seed treatment and Trichoderma cost about Rs 24,500, roughly 17 percent of total, against an exposure of Rs 1.8 to 3.2 lakh. That is seven to thirteen times, and no fertiliser or variety choice approaches it.
- **कृती (MR):** गुणोत्तर दाखवा. आच्छादन, निचरा, बेणे प्रक्रिया आणि ट्रायकोडर्मा यांचा खर्च सुमारे २४,५०० रुपये — एकूण खर्चाच्या सुमारे १७% — आणि टाळलेले संभाव्य नुकसान १.८ ते ३.२ लाख. म्हणजे सात ते तेरा पट, आणि कोणतेही खत किंवा जातीची निवड याच्या जवळपासही येत नाही.
- **Basis:** The stack addresses the single loss factor capable of erasing the season. Its cost is known and its exposure is quantified, which makes this one of the few genuinely computable investment decisions in the crop.
- **Yield impact:** Protects u = 0.50 to 0.90.
- **References:** Domain 6 prevention stack; Domain 13 prevention economics
