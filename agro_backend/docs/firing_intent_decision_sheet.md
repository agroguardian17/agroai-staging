# Firing-intent diagnostic rules — backend wiring decision sheet

**Source:** `backend_handoff/01_AGRONOMY_COMPLIANCE/firing_intent_diagnostic_rules.xlsx` — 48 rules + 1 field-flip  
**Prepared by:** Backend for agronomy + product review · **Status:** all `proposed_pending_backend_wire`.

## Executive summary

- **48 rules, 11 domains** (D01–D06, D08–D12). Against the live KB's **365 declared farm-brain fields**:
  - **5 rules reference only existing fields** → ready to wire once their delivery class + golden tests are confirmed (see *Ready to wire*).
  - **43 rules need new fields** — **53 distinct new fields**, most of them new data-capture surfaces (farmer app / scouting / ops / processing) with no ingestion path today.
- Backend cannot wire a rule until: (1) its `firing_condition` is confirmed as canonical `trigger_dsl`; (2) each new field has a **type + capture source** (a field with no source evaluates UNKNOWN and never fires); (3) a **delivery class** is chosen (absent from the sheet). Final Marathi is a separate Meta-template step.
- Mechanics per rule (backend, once decisions land): field → `farm_brain_schema` + `kb_farm_brain_fields`; DSL → JSON `trigger.expr` + a trigger wave + `notification_policy`; golden tests; regenerate SQL; reload migration. Drift + golden gates enforce cross-surface consistency.

**Owner legend:** `auto` engine-silent · `agronomy` agronomist message · `field_ops` field action · `ops` admin/scheme.  
**Delivery (suggested by backend, agronomy confirms):** `SILENT_GUARD` internal guard · `EVENT` fires once · `ONCE_UNTIL_RESOLVED` repeats until acted · `WINDOW` recurring in a stage window (default).

## Ready to wire now — fields already exist (5)
These reference only declared fields, so backend can wire them without new ingestion. Still need: confirmed DSL grammar, a delivery class, and golden tests. (Fields may still be UNKNOWN until a source populates them — the rule simply won't fire yet, which is safe.)

| rule_id | owner | firing_condition | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|
| **D01-PH-004** | agronomy | `flowering_observed == true AND dap >= 150` | EVENT | फुलोरा दिसला — गड्डा भरण्याची अवस्था सुरू. आता नत्र न देता उटाळणी व पालाश पूर्ण करा. |
| **D02-DR-004** | agronomy | `percolation_class == "poor" AND planting_layout == "broad_ridge" AND dap < 15` | WINDOW | तुमच्या शेतात निचरा कमी दिसतो. Broad-ridge layout केला असला तरी वरंब्याखाली मुख्य चर तपा… |
| **D02-LY-001** | agronomy | `soil_type == "vertisol" AND has_drip == true AND planting_layout IS NULL AND dap IS NULL` | ONCE_UNTIL_RESOLVED | काळी माती + ठिबक + लागवडीपूर्वी — Broad-ridge layout (60/40 cm) शिफारसीय. Flat layout नको. |
| **D02-ST-002** | field_ops | `dap IS NULL AND percolation_time_hours IS NULL` | ONCE_UNTIL_RESOLVED | लागवडीपूर्वी एक-वेळेस percolation test करा — ३० cm खड्डा, संपृक्त करून पाणी घसरण्याची वे… |
| **D03-SB-003** | auto | `current_stage != previous_stage` | EVENT | पिकाची अवस्था बदलली — sub-node moisture bands आपोआप update होतील. काहीही action ची गरज न… |

## Need new field(s) + a capture source (43)

### D01 (1)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D01-PH-005** | agronomy | `dap == 35 AND emergence_observed IS NULL` | `emergence_observed` | ONCE_UNTIL_RESOLVED | DAP 35 पूर्ण — उगवण नोंदवा (100% झाली/अंशतः/नाही). नोंद न झाल्यास पुढील stage-… |

### D03 (2)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D03-SB-004** | ops | `hardware_upgrade_pending == true` | `hardware_upgrade_pending` | SILENT_GUARD | Sub-node hardware upgrade सुरू आहे — पुढील ३ दिवस moisture-based advisory थांब… |
| **D03-WS-002** | agronomy | `water_supply_status == "marginal" AND month IN [MAR, APR, MAY]` | `month`, `water_supply_status` | WINDOW | तुमच्या शेताचा पाणीपुरवठा उन्हाळ्यात कमी होऊ शकतो. लागवडीपूर्वी backup source … |

### D04 (3)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D04-BI-002** | agronomy | `biological_input_date == chemical_input_date` | `biological_input_date` | WINDOW | त्याच दिवशी जैविक आणि रासायनिक निविष्ठा देऊ नका — जैविक जिवाणू मरतात. दोन्हीत … |
| **D04-DG-002** | agronomy | `leaf_yellowing_pattern == "interveinal_new" AND scout_report_days_ago <= 3` | `scout_report_days_ago` | WINDOW | नव्या पानांवरील शिरांमधील पिवळेपणा — बहुदा लोह/जस्त कमतरता. पर्ण-चाचणी करून mi… |
| **D04-SN-001** | agronomy | `basal_planning_active == true AND dap IS NULL` | `basal_planning_active` | ONCE_UNTIL_RESOLVED | मूळ खताचे नियोजन सुरू — 60% खत लागवडीच्या वेळी, 40% top-dressing मध्ये विभागा.… |

### D05 (4)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D05-CH-002** | auto | `chemical_option_about_to_be_shown == true` | `chemical_option_about_to_be_shown` | SILENT_GUARD | रासायनिक पर्याय दाखवण्यापूर्वी: (१) निदान झाले आहे का, (२) IPM पर्याय अपुरा आह… |
| **D05-IP-001** | auto | `pest_recommendation_pending == true` | `pest_recommendation_pending` | SILENT_GUARD | कोणतीही pest शिफारस देण्यापूर्वी IPM प्राधान्य — cultural, biological, mechani… |
| **D05-PC-001** | agronomy | `pest_planning_active == true AND dap < 0` | `pest_planning_active` | WINDOW | लागवडीच्या नियोजनात pest calendar जोडा — कंदमाशी जुलै-ऑगस्ट, thrips ऑगस्ट-सप्ट… |
| **D05-SC-002** | auto | `pest_count > provisional_threshold AND threshold_source == "EST"` | `pest_count`, `threshold_source` | WINDOW | तात्पुरत्या मर्यादेवर pest count गेला — नियंत्रण सुचवले जाईल, पण ETL local cal… |

### D06 (6)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D06-BW-001** | agronomy | `field_history_wilt == true AND years_since_last_wilt < 5` | `years_since_last_wilt` | ONCE_UNTIL_RESOLVED | या शेतात मागील ५ वर्षांत बॅक्टेरियल विल्ट झाले होते — रोगाणू माती-वहन आहे. लाग… |
| **D06-CH-002** | auto | `fungicide_option_about_to_be_shown == true` | `fungicide_option_about_to_be_shown` | SILENT_GUARD | बुरशीनाशक दाखवण्यापूर्वी: (१) निदान bacterial नाही ना, (२) FRAC group rotation… |
| **D06-FH-001** | agronomy | `harvest_complete == true` | `harvest_complete` | EVENT | काढणी झाली — शेतातील disease history (rot/wilt/leaf spot severity) नोंदवा. पुढ… |
| **D06-FH-002** | agronomy | `soft_rot_confirmed_in_cluster == true` | `soft_rot_confirmed_in_cluster` | WINDOW | तुमच्या cluster मध्ये soft rot confirm झाला — तुमच्या शेतात preventive drenchi… |
| **D06-ST-001** | agronomy | `seed_treatment_planned == true AND dap < 0` | `seed_treatment_planned` | WINDOW | बेणे प्रक्रिया नियोजन: उष्ण जल (५०°C, १० मिनिटे) + Trichoderma + copper drench… |
| **D06-ST-002** | agronomy | `biological_seed_treatment_date == chemical_seed_treatment_date` | `biological_seed_treatment_date` | WINDOW | बेणे प्रक्रिया — जैविक व रासायनिक एकाच दिवशी नकोत. Copper drench, कोरडे केल्या… |

### D08 (1)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D08-SS-001** | agronomy | `seed_going_to_storage == true` | `seed_going_to_storage` | WINDOW | बेणे साठवणीत जात आहे — कोरडे, हवेशीर, अंधार जागा; padlayer coating; monthly we… |

### D09 (9)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D09-DR-001** | agronomy | `processing_route == "dry_ginger"` | `processing_route` | WINDOW | सुंठ प्रक्रिया निवडली — skin removal → 5-day sun dry → moisture <10%. FSSAI SO… |
| **D09-DR-002** | agronomy | `skin_removal_in_progress == true` | `skin_removal_in_progress` | EVENT | साल काढणी सुरू — घर्षण drum किंवा manual scraping, दोन्हीत पूर्ण साल जावी. उर्… |
| **D09-DR-003** | agronomy | `drying_in_progress == true AND local_hour >= 16` | `drying_in_progress`, `local_hour` | EVENT | संध्याकाळ जवळ — सुंठ आत आणा किंवा tarpaulin ने झाका. Night dew टिकल्यास बुरशी … |
| **D09-PW-001** | agronomy | `value_addition_being_considered == true AND processing_route == "dry_ginger"` | `processing_route`, `value_addition_being_considered` | WINDOW | सुंठाच्या पुढे powder/oleoresin विचार करत आहात — bulk sale आणि processed produ… |
| **D09-SL-003** | agronomy | `fresh_price_crashed == true OR fresh_share_low == true` | `fresh_price_crashed`, `fresh_share_low` | ONCE_UNTIL_RESOLVED | ताज्या आल्याचा भाव पडला किंवा विक्री कमी — उर्वरित सुंठ बनवण्याचा विचार करा. स… |
| **D09-ST-002** | field_ops | `dry_ginger_in_storage == true AND storage_loss_monthly_pct IS NULL` | `dry_ginger_in_storage` | ONCE_UNTIL_RESOLVED | सुंठ साठवणीत — दर महिन्याला वजन तपासा आणि monthly loss % नोंदवा. १०%+ loss = p… |
| **D09-YD-002** | auto | `actual_yield_recorded == true` | `actual_yield_recorded` | EVENT | प्रत्यक्ष उत्पन्न नोंदवले — धन्यवाद. आता Season 1 gap-attribution engine start… |
| **D09-YD-003** | field_ops | `dry_ginger_produced == true` | `dry_ginger_produced` | WINDOW | सुंठ तयार झाली — dry ratio (fresh:dry) आणि total dry weight नोंदवा. Season eco… |
| **D09-YD-004** | field_ops | `harvest_complete == true` | `harvest_complete` | EVENT | काढणी झाली — पुढील ३ दिवसांत fresh yield (क्विंटल/एकर) नोंदवा. Season 1 baseli… |

### D10 (4)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D10-ACT-002** | agronomy | `institutional_contact_made == true` | `institutional_contact_made` | EVENT | संस्थात्मक संपर्क झाला (VNMKV/ICAR/KVK) — मिळालेली माहिती नोंदवा. Future advis… |
| **D10-APP-001** | ops | `subsidy_application_pending == true AND subsidy_documents_ready == false` | `subsidy_application_pending` | SILENT_GUARD | अनुदान अर्ज करण्यापूर्वी सर्व कागदपत्रे तयार करा: 7/12, आधार, बँक, पूर्वसंमती … |
| **D10-CROP-002** | agronomy | `local_experience_sought == true` | `local_experience_sought` | WINDOW | स्थानिक अनुभव विचारला जात आहे — VNMKV Parbhani + KVK Sambhajinagar शी संपर्क ह… |
| **D10-REG-001** | auto | `chemical_recommendation_pending == true AND cibrc_verified == false` | `chemical_recommendation_pending`, `cibrc_verified` | SILENT_GUARD | रासायनिक शिफारस देण्यापूर्वी CIB&RC label पडताळणी अनिवार्य. Pesticide registry… |

### D11 (8)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D11-GA-001** | auto | `harvest_complete == true AND actual_yield_recorded == true` | `actual_yield_recorded`, `harvest_complete` | EVENT | gap-attribution engine तयार — season observation vs. potential vs. actual, U-v… |
| **D11-GA-002** | field_ops | `season_starting == true AND season_record_complete == false` | `season_starting` | WINDOW | नवीन हंगाम — मागील हंगामाची पूर्ण नोंद अद्याप incomplete. डेटा गॅप भरा किंवा g… |
| **D11-GA-003** | agronomy | `gap_attribution_complete == true AND gap_unexplained_pct > 25` | `gap_attribution_complete` | ONCE_UNTIL_RESOLVED | gap-attribution झाले — पण २५%+ unexplained. कृषी सल्लागार review करेल आणि miss… |
| **D11-RC-002** | auto | `saturation_event_occurred == true OR moisture_stress_period_started == true` | `moisture_stress_period_started`, `saturation_event_occurred` | EVENT | साचणे किंवा ताण event नोंदला — season log मध्ये entered, gap-attribution साठी … |
| **D11-RC-003** | auto | `scheduled_operation_completed == true OR scheduled_operation_missed == true` | `scheduled_operation_completed`, `scheduled_operation_missed` | EVENT | नियोजित operation पूर्ण/चुकले — season log मध्ये नोंदले. compliance rate वर पर… |
| **D11-SC-001** | auto | `preseason_planning == true AND yield_expectation_requested == true` | `preseason_planning`, `yield_expectation_requested` | WINDOW | हंगामपूर्व yield expectation विचारले जात आहे — variety potential × site index … |
| **D11-SC-002** | auto | `season_omissions_recorded == true` | `season_omissions_recorded` | EVENT | हंगामातील नोंदलेल्या चुकांचे projection — u-value × intensity च्या माध्यमातून … |
| **D11-SC-003** | auto | `disease_event_recorded_in_season == true` | `disease_event_recorded_in_season` | WINDOW | हंगामात रोग event नोंदला — u-value applied to yield forecast, farmer alert tri… |

### D12 (5)

| rule_id | owner | proposed firing_condition | new field(s) *(type + source = decide)* | delivery *(suggested)* | message intent (mr) |
|---|---|---|---|---|---|
| **D12-AL-001** | auto | `action_not_recorded_within_3days == true` | `action_not_recorded_within_3days` | ONCE_UNTIL_RESOLVED | शिफारशीवर ३ दिवसांत कारवाईची नोंद नाही — कारण विचारा (already_done/cost/unavai… |
| **D12-AL-002** | auto | `low_confidence_decision == true OR unexpected_outcome == true OR symptom_diagnosis_pending == true` | `low_confidence_decision`, `symptom_diagnosis_pending`, `unexpected_outcome` | SILENT_GUARD | AI ला कमी विश्वास/अनपेक्षित निकाल/अनिश्चित निदान — human agronomist escalate. |
| **D12-IMG-001** | auto | `season_number <= 2 AND photo_submitted == true` | `photo_submitted`, `season_number` | EVENT | शेतकऱ्याने फोटो पाठवला — labelling backlog मध्ये गेला. D06 categories (rot/wil… |
| **D12-LOG-002** | agronomy | `durable_fact_learned_in_conversation == true` | `durable_fact_learned_in_conversation` | EVENT | फोन/scout report मध्ये durable fact सापडला — season records मध्ये append व्हाव… |
| **D12-VOC-002** | agronomy | `local_terminology_used == true AND differs_from_standard_marathi == true` | `differs_from_standard_marathi`, `local_terminology_used` | EVENT | शेतकऱ्याने स्थानिक शब्द वापरला — glossary मध्ये add करा (उदा. "हुरडे" = flower… |

## New fields required (53) — grouped by likely capture source
Agronomy/product to confirm the source for each; backend adds them to the schema as sources land.

```
action_not_recorded_within_3days, actual_yield_recorded, basal_planning_active, biological_input_date, biological_seed_treatment_date, chemical_option_about_to_be_shown, chemical_recommendation_pending, cibrc_verified, differs_from_standard_marathi, disease_event_recorded_in_season, dry_ginger_in_storage, dry_ginger_produced, drying_in_progress, durable_fact_learned_in_conversation, emergence_observed, fresh_price_crashed, fresh_share_low, fungicide_option_about_to_be_shown, gap_attribution_complete, hardware_upgrade_pending, harvest_complete, institutional_contact_made, local_experience_sought, local_hour, local_terminology_used, low_confidence_decision, moisture_stress_period_started, month, pest_count, pest_planning_active, pest_recommendation_pending, photo_submitted, preseason_planning, processing_route, saturation_event_occurred, scheduled_operation_completed, scheduled_operation_missed, scout_report_days_ago, season_number, season_omissions_recorded, season_starting, seed_going_to_storage, seed_treatment_planned, skin_removal_in_progress, soft_rot_confirmed_in_cluster, subsidy_application_pending, symptom_diagnosis_pending, threshold_source, unexpected_outcome, value_addition_being_considered, water_supply_status, years_since_last_wilt, yield_expectation_requested
```

## Field-flip row (already done)
`__soil_texture_class_source__` (re-derive `soil_texture_class`, set source=`lab` on lab entry) — **implemented in PR #78**. No action.

## Recommended sequencing
1. **Batch 1 (ready):** wire the 5 existing-field rules as one CI-green PR once agronomy confirms their delivery class + golden tests. (Needs a reload migration — sequence after the DPDP migration chain to avoid migration-number collisions.)
2. **Batch 2+ (per domain):** as each domain's new fields get a type + capture source, wire that domain as a PR. D09/D11/D12 carry the most new fields (processing, gap-attribution, QA-loop).