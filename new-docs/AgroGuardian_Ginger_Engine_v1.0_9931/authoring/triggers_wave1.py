#!/usr/bin/env python3
"""
Wave 1 — formal triggers for the 49 blocking and red rules.

Each entry carries:
  expr   : the DSL expression
  tests  : golden cases  (context, expected outcome)

Tests are written WITH the trigger, not after. A trigger without a test that
proves it does NOT fire on the near-miss case is not finished.

The two expert-amended rules (D02-DR-001, D03-WS-001) are first, because the
amendment made them per-plot computations rather than fixed thresholds and
that has to be expressed here or the amendment is not actually implemented.
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS = {

# ===========================================================================
# EXPERT-AMENDED — these two changed from fixed numbers to per-plot judgement
# ===========================================================================

'D02-DR-001': {
  'expr': ("(soil_texture_class == 'heavy' AND percolation_time_hours > 12) OR "
           "(soil_texture_class == 'medium' AND percolation_time_hours > 8) OR "
           "(soil_texture_class == 'light' AND percolation_time_hours > 6)"),
  'note': ('Expert amendment: judge against soil texture, not one fixed hour count. '
           'Outlet and observed standing water are checked in the action, not the trigger, '
           'because they refine the advice rather than gate it.'),
  'tests': [
    ({'soil_texture_class':'heavy','percolation_time_hours':14}, T, 'भारी जमीन, १४ तास — फिरतो'),
    ({'soil_texture_class':'heavy','percolation_time_hours':10}, F, 'भारी जमीन, १० तास — फिरत नाही'),
    ({'soil_texture_class':'light','percolation_time_hours':10}, T, 'हलकी जमीन, तेच १० तास — आता फिरतो'),
    ({'soil_texture_class':'medium','percolation_time_hours':7}, F, 'मध्यम, ७ तास — मर्यादेखाली'),
    ({'percolation_time_hours':14}, U, 'मातीचा प्रकार नाही — UNKNOWN, गृहीत धरू नये'),
    ({'soil_texture_class':'heavy'}, U, 'चाचणी झालेली नाही — UNKNOWN'),
  ]},

'D03-WS-001': {
  'expr': ("water_available_oct_feb_litres IS NULL OR "
           "water_available_oct_feb_litres < seasonal_water_requirement_litres"),
  'note': ('Expert amendment: no universal 27 lakh litre figure. '
           'seasonal_water_requirement_litres is computed per plot from soil texture, '
           'local evaporation and measured drip efficiency before this trigger runs.'),
  'tests': [
    ({'water_available_oct_feb_litres':2_000_000,'seasonal_water_requirement_litres':2_700_000}, T, 'पुरवठा कमी — फिरतो'),
    ({'water_available_oct_feb_litres':3_200_000,'seasonal_water_requirement_litres':2_700_000}, F, 'पुरवठा पुरेसा'),
    ({'seasonal_water_requirement_litres':2_700_000}, T, 'उपलब्धता माहीत नाही — मूल्यांकन करा'),
    ({'water_available_oct_feb_litres':2_000_000}, U, 'गरज अजून काढलेली नाही — UNKNOWN'),
    ({'water_available_oct_feb_litres':900_000,'seasonal_water_requirement_litres':1_400_000}, T, 'हलकी जमीन, कमी गरज — तरीही कमी'),
  ]},

# ===========================================================================
# D01 — Lifecycle
# ===========================================================================

'D01-PW-001': {
  'expr': "planting_date IS NULL AND MONTH IN [JUN, JUL] AND dap IS NULL",
  'note': 'Planting window has closed and nothing is planted.',
  'tests': [
    ({'current_month':6}, T, 'जून, लागवड नाही — अडवा'),
    ({'current_month':6,'planting_date':'2026-06-05','dap':40}, F, 'लागवड झाली आहे'),
    ({'current_month':4}, F, 'एप्रिल — अजून वेळ आहे'),
  ]},

'D01-HW-001': {
  'expr': "moisture_probe_depth_cm > 20",
  'note': 'Probe outside the rhizome zone invalidates every moisture rule.',
  'tests': [
    ({'moisture_probe_depth_cm':45}, T, '४५ सेंमी — खूप खोल'),
    ({'moisture_probe_depth_cm':15}, F, '१५ सेंमी — बरोबर'),
    ({}, U, 'खोली नोंदवलेली नाही'),
  ]},

'D01-HV-002': {
  'expr': "leaf_yellowing_pattern IS NOT NULL AND dap < 200",
  'note': 'Yellowing before 200 DAP is not maturity.',
  'tests': [
    ({'leaf_yellowing_pattern':'uniform_old','dap':150}, T, '१५० दिवस, पिवळी — पक्वता नाही'),
    ({'leaf_yellowing_pattern':'uniform_old','dap':215}, F, '२१५ दिवस — पक्वता शक्य'),
    ({'dap':150}, F, 'पिवळेपणा नोंदवलेला नाही'),
  ]},

# ===========================================================================
# D02 — Soil
# ===========================================================================

'D02-CA-002': {
  'expr': "leaf_yellowing_pattern IS NOT NULL",
  'note': 'Any yellowing enters the diagnosis sequence before any input is advised.',
  'tests': [
    ({'leaf_yellowing_pattern':'interveinal_new'}, T, 'नव्या पानांत — निदान करा'),
    ({'leaf_yellowing_pattern':'none'}, T, 'नोंद आहे — तपासा'),
    ({}, F, 'नोंदच नाही'),
  ]},

'D02-CL-002': {
  'expr': "has_drip IS FALSE AND WITHIN(planting_date, 30 DAYS)",
  'note': 'Planting readiness blocked without operational drip.',
  'tests': [
    ({'has_drip':False,'days_to_planting':20}, T, 'ठिबक नाही, २० दिवस उरले'),
    ({'has_drip':True,'days_to_planting':20}, F, 'ठिबक आहे'),
    ({'days_to_planting':20}, U, 'ठिबकाची स्थिती माहीत नाही'),
  ]},

'D02-DR-002': {
  'expr': "(drainage_levels_present < 3 OR main_drain_connected IS FALSE) AND dap IS NULL",
  'note': 'All three drainage levels required BEFORE planting.',
  'tests': [
    ({'drainage_levels_present':2,'main_drain_connected':True}, T, 'दोनच पातळ्या'),
    ({'drainage_levels_present':3,'main_drain_connected':False}, T, 'मुख्य चर जोडलेला नाही'),
    ({'drainage_levels_present':3,'main_drain_connected':True}, F, 'तिन्ही पूर्ण'),
    ({'drainage_levels_present':2,'main_drain_connected':True,'dap':40}, F, 'लागवड झाली — आता हा नियम नाही'),
  ]},

# ===========================================================================
# D03 — Water
# ===========================================================================

'D03-DS-003': {
  'expr': "has_drip IS FALSE AND WITHIN(planting_date, 15 DAYS)",
  'tests': [
    ({'has_drip':False,'days_to_planting':10}, T, '१० दिवस, ठिबक नाही'),
    ({'has_drip':False,'days_to_planting':40}, F, '४० दिवस — अजून वेळ'),
  ]},

'D03-MN-002': {
  'expr': "soil_moisture_vwc >= vwc_saturation",
  'note': 'Hard interlock. Overrides the water balance computation.',
  'tests': [
    ({'soil_moisture_vwc':48,'vwc_saturation':45}, T, 'संपृक्त — पाणी बंद'),
    ({'soil_moisture_vwc':30,'vwc_saturation':45}, F, 'संपृक्त नाही'),
    ({'soil_moisture_vwc':48}, U, 'calibration नाही — स्वयंचलित सिंचन बंद ठेवा'),
  ]},

'D03-MN-004': {
  'expr': "rain_gap_days >= 7 AND STAGE IN [G3, G4]",
  'tests': [
    ({'rain_gap_days':8,'current_stage':'G3'}, T, 'G3 मध्ये ८ दिवस खंड'),
    ({'rain_gap_days':8,'current_stage':'G2'}, F, 'G2 — सामान्य नियम लागू'),
    ({'rain_gap_days':5,'current_stage':'G3'}, F, '५ दिवस — अजून नाही'),
  ]},

'D03-SB-001': {
  'expr': "moisture_probe_depth_cm > 20",
  'tests': [
    ({'moisture_probe_depth_cm':30}, T, 'खोल probe'),
    ({'moisture_probe_depth_cm':10}, F, 'योग्य खोली'),
  ]},

'D03-WL-001': {
  'expr': "DURATION(soil_moisture_vwc > vwc_saturation) > 12 HOURS",
  'note': 'Duration, not instantaneous level. Damage is time dependent.',
  'tests': [
    ({'soil_moisture_vwc__duration':14}, T, '१४ तास संपृक्त'),
    ({'soil_moisture_vwc__duration':6}, F, '६ तास — अजून धोका नाही'),
    ({'soil_moisture_vwc':48}, U, 'कालावधी मोजलेला नाही'),
  ]},

'D03-WL-002': {
  'expr': "DURATION(soil_moisture_vwc > vwc_saturation) > 12 HOURS AND STAGE IN [G2, G3]",
  'tests': [
    ({'soil_moisture_vwc__duration':14,'current_stage':'G3'}, T, 'G3 मध्ये — तीव्रता वाढवा'),
    ({'soil_moisture_vwc__duration':14,'current_stage':'G5'}, F, 'G5 — सामान्य इशारा'),
  ]},

'D03-WL-003': {
  'expr': "MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40",
  'note': 'Post-monsoon cyclone. Duplication group: post_monsoon_cyclone_saturation.',
  'tests': [
    ({'current_month':10,'forecast_rain_48h_mm':55}, T, 'ऑक्टोबर, ५५ मिमी'),
    ({'current_month':7,'forecast_rain_48h_mm':55}, F, 'जुलै — वेगळा नियम'),
    ({'current_month':10,'forecast_rain_48h_mm':20}, F, '२० मिमी — मर्यादेखाली'),
  ]},

# ===========================================================================
# D04 — Nutrient
# ===========================================================================

'D04-DG-001': {
  'expr': "leaf_yellowing_pattern IS NOT NULL",
  'tests': [
    ({'leaf_yellowing_pattern':'margin_scorch'}, T, 'निदान क्रम चालवा'),
    ({}, F, 'नोंद नाही'),
  ]},

'D04-DG-003': {
  'expr': "leaf_yellowing_pattern IN [with_soft_stem, sudden_green_wilt]",
  'note': 'Stop nutrient advisory and hand over to Domain 6.',
  'tests': [
    ({'leaf_yellowing_pattern':'with_soft_stem'}, T, 'कूज — खत थांबवा'),
    ({'leaf_yellowing_pattern':'sudden_green_wilt'}, T, 'मर रोग — खत थांबवा'),
    ({'leaf_yellowing_pattern':'uniform_old'}, F, 'नत्र कमतरता — खत चालेल'),
  ]},

'D04-FG-002': {
  'expr': "fertigation_active IS TRUE AND dap BETWEEN 130 AND 140",
  'note': 'Calcium nitrate and phosphoric acid windows overlap here.',
  'tests': [
    ({'fertigation_active':True,'dap':135}, T, 'overlap खिडकी'),
    ({'fertigation_active':True,'dap':120}, F, 'overlap नाही'),
    ({'dap':135}, U, 'फर्टिगेशन चालू आहे का माहीत नाही'),
  ]},

'D04-NP-002': {
  'expr': "yield_target_quintal_per_acre > ceiling_quintal_per_acre",
  'note': 'Amended in spirit by D01-YD-002 — compare against computed ceiling.',
  'tests': [
    ({'yield_target_quintal_per_acre':150,'ceiling_quintal_per_acre':113}, T, 'लक्ष्य मर्यादेपेक्षा जास्त'),
    ({'yield_target_quintal_per_acre':100,'ceiling_quintal_per_acre':113}, F, 'मर्यादेत'),
    ({'yield_target_quintal_per_acre':150}, U, 'मर्यादा काढलेली नाही'),
  ]},

'D04-NS-003': {
  'expr': "dap > 80 AND n_applied_kg_per_acre IS NOT NULL",
  'note': 'No nitrogen after 80 DAP.',
  'tests': [
    ({'dap':95,'n_applied_kg_per_acre':10}, T, '९५ दिवसांनी नत्र — नाकारा'),
    ({'dap':60,'n_applied_kg_per_acre':24}, F, '६० दिवस — चालेल'),
  ]},

'D04-SB-001': {
  'expr': "ec_current IS NOT NULL AND soil_test_available IS FALSE",
  'note': 'Refuse to set doses from the probe.',
  'tests': [
    ({'ec_current':0.45,'soil_test_available':False}, T, 'probe वापरून मात्रा — नाकारा'),
    ({'ec_current':0.45,'soil_test_available':True}, F, 'माती परीक्षण आहे'),
  ]},

# ===========================================================================
# D05 — Pest
# ===========================================================================

'D05-CH-001': {
  'expr': "last_insecticide_group IN [BHC, lindane, monocrotophos]",
  'note': 'Hard blocklist.',
  'tests': [
    ({'last_insecticide_group':'BHC'}, T, 'प्रतिबंधित'),
    ({'last_insecticide_group':'monocrotophos'}, T, 'प्रतिबंधित'),
    ({'last_insecticide_group':'quinalphos'}, F, 'परवानगी'),
  ]},

'D05-CH-003': {
  'expr': "phi_days_remaining IS NULL AND WITHIN(harvest_date, 30 DAYS)",
  'note': 'Duplication group: pre_harvest_interval_block.',
  'tests': [
    ({'days_to_harvest':20}, T, 'PHI माहीत नाही, २० दिवस — अडवा'),
    ({'days_to_harvest':20,'phi_days_remaining':0}, F, 'PHI संपला'),
    ({'days_to_harvest':60}, F, '६० दिवस — वेळ आहे'),
  ]},

'D05-TC-002': {
  'expr': "intercrop_selected IN [chilli, brinjal, tomato, potato]",
  'tests': [
    ({'intercrop_selected':'chilli'}, T, 'मिरची — नाकारा'),
    ({'intercrop_selected':'marigold'}, F, 'झेंडू — चालेल'),
  ]},

# ===========================================================================
# D06 — Disease
# ===========================================================================

'D06-CH-001': {
  'expr': "ooze_test_result == 'milky_thread' OR stem_ooze_type == 'milky_yellowish' OR wilt_while_green IS TRUE",
  'note': 'Bacterial wilt confirmed — no fungicide, ever.',
  'tests': [
    ({'ooze_test_result':'milky_thread'}, T, 'दुधाळ धागा — मर रोग'),
    ({'wilt_while_green':True}, T, 'हिरवीच असताना कोमेजली'),
    ({'ooze_test_result':'no_thread','stem_ooze_type':'watery_foul','wilt_while_green':False}, F, 'कूज — बुरशीनाशक चालेल'),
  ]},

'D06-CH-003': {
  'expr': "phi_days_remaining IS NULL AND WITHIN(harvest_date, 30 DAYS)",
  'note': 'Duplication group: pre_harvest_interval_block.',
  'tests': [
    ({'days_to_harvest':15}, T, 'PHI अज्ञात'),
    ({'days_to_harvest':15,'phi_days_remaining':5}, F, 'PHI माहीत आहे'),
  ]},

'D06-DX-001': {
  'expr': "leaf_yellowing_pattern IS NOT NULL OR wilt_while_green IS TRUE OR central_shoot_dead IS TRUE",
  'note': 'Diagnosis before any treatment.',
  'tests': [
    ({'central_shoot_dead':True}, T, 'सुरळी मेली'),
    ({'leaf_yellowing_pattern':'uniform_old'}, T, 'पिवळेपणा'),
    ({'central_shoot_dead':False,'wilt_while_green':False}, F, 'लक्षण नाही'),
  ]},

'D06-DX-002': {
  'expr': "ooze_test_result == 'milky_thread' OR stem_ooze_type == 'milky_yellowish' OR wilt_while_green IS TRUE",
  'tests': [
    ({'stem_ooze_type':'milky_yellowish'}, T, 'दुधाळ स्राव'),
    ({'stem_ooze_type':'watery_foul','ooze_test_result':'no_thread','wilt_while_green':False}, F, 'पाणीदार + धागा नाही + हिरवी नाही — कूज'),
    ({'stem_ooze_type':'watery_foul'}, U, 'फक्त एक निकष — उरलेल्या दोन चाचण्या करा'),
  ]},

'D06-SR-001': {
  'expr': ("(DURATION(soil_moisture_vwc > vwc_saturation) > 12 HOURS OR "
           "DURATION(rh_pct > 85) > 72 HOURS) AND MONTH IN [AUG, SEP] AND STAGE IN [G2, G3]"),
  'note': 'Preventive — fires on the environmental signature, before symptoms.',
  'tests': [
    ({'soil_moisture_vwc__duration':14,'current_month':8,'current_stage':'G3'}, T, 'संपृक्तता + ऑगस्ट + G3'),
    ({'rh_pct__duration':80,'current_month':8,'current_stage':'G3'}, T, 'आर्द्रता ८० तास'),
    ({'soil_moisture_vwc__duration':14,'current_month':11,'current_stage':'G3'}, F, 'नोव्हेंबर — वेगळा नियम'),
    ({'soil_moisture_vwc__duration':6,'rh_pct__duration':20,'current_month':8,'current_stage':'G3'}, F, 'दोन्ही मर्यादेखाली'),
  ]},

# ===========================================================================
# D07 — Weather
# ===========================================================================

'D07-CY-001': {
  'expr': "MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40",
  'note': 'Duplication group: post_monsoon_cyclone_saturation. Same event as D03-WL-003.',
  'tests': [
    ({'current_month':11,'forecast_rain_48h_mm':50}, T, 'नोव्हेंबर चक्रीवादळ'),
    ({'current_month':9,'forecast_rain_48h_mm':50}, F, 'सप्टेंबर — मान्सून नियम'),
  ]},

'D07-RF-001': {
  'expr': "season_water_plan_basis IS NULL OR season_water_plan_basis != 'poor_year'",
  'note': 'Area must be sized on a poor year.',
  'tests': [
    ({'season_water_plan_basis':'average_year'}, T, 'सरासरीवर नियोजन — इशारा'),
    ({'season_water_plan_basis':'poor_year'}, F, 'वाईट वर्षावर — बरोबर'),
    ({}, T, 'आधारच ठरवलेला नाही'),
  ]},

# ===========================================================================
# D08 — Operations
# ===========================================================================

'D08-WD-001': {
  'expr': "(emergence_started IS TRUE OR dap >= 15) AND herbicide_post_emergent_date IS NULL",
  'note': 'Glyphosate is non-selective. This kills the crop if it fires late.',
  'tests': [
    ({'dap':18}, T, '१८ दिवस — तणनाशक अडवा'),
    ({'emergence_started':True,'dap':12}, T, 'उगवण सुरू — अडवा'),
    ({'dap':10,'emergence_started':False}, F, '१० दिवस, उगवण नाही — खिडकी उघडी'),
  ]},

'D08-LY-001': {
  'expr': "soil_type == 'vertisol' AND has_drip IS TRUE AND planting_layout != 'broad_ridge'",
  'tests': [
    ({'soil_type':'vertisol','has_drip':True,'planting_layout':'flat_bed'}, T, 'काळी + ठिबक + सपाट'),
    ({'soil_type':'vertisol','has_drip':True,'planting_layout':'broad_ridge'}, F, 'रुंद वरंबा — बरोबर'),
  ]},

'D08-IC-001': {
  'expr': "intercrop_selected IN [chilli, brinjal, tomato, potato]",
  'tests': [
    ({'intercrop_selected':'tomato'}, T, 'टोमॅटो — नाकारा'),
    ({'intercrop_selected':'coriander'}, F, 'कोथिंबीर — चालेल'),
  ]},

'D08-GR-003': {
  'expr': "brand_name_proposed IS NOT NULL",
  'note': 'Emit active ingredient only.',
  'tests': [
    ({'brand_name_proposed':'SomeProduct'}, T, 'ब्रँड नाव — अडवा'),
    ({}, F, 'ब्रँड नाही'),
  ]},

'D08-EU-002': {
  'expr': "flowering_observed IS TRUE AND earthing_up_date IS NULL",
  'note': 'Window closed. Do NOT attempt earthing up now.',
  'tests': [
    ({'flowering_observed':True}, T, 'फुलोरा आला, उटाळणी नाही'),
    ({'flowering_observed':True,'earthing_up_date':'2026-08-20'}, F, 'उटाळणी झाली'),
    ({'flowering_observed':False}, F, 'फुलोरा नाही — खिडकी उघडी'),
  ]},

# ===========================================================================
# D09 — Harvest
# ===========================================================================

'D09-MT-002': {
  'expr': "leaf_yellowing_pattern IS NOT NULL AND dap < 200",
  'tests': [
    ({'leaf_yellowing_pattern':'uniform_old','dap':170}, T, 'लवकर पिवळेपणा'),
    ({'leaf_yellowing_pattern':'uniform_old','dap':220}, F, 'पक्वता शक्य'),
  ]},

'D09-PR-001': {
  'expr': "drying_method == 'soda_khar'",
  'tests': [
    ({'drying_method':'soda_khar'}, T, 'सुरक्षा इशारा प्रथम'),
    ({'drying_method':'simple_sun'}, F, 'साधी वाळवणी'),
  ]},

'D09-PR-002': {
  'expr': "drying_method == 'malabar_lime_sulphur'",
  'tests': [
    ({'drying_method':'malabar_lime_sulphur'}, T, 'SO2 मर्यादा तपासा'),
    ({'drying_method':'simple_sun'}, F, ''),
  ]},

'D09-SF-001': {
  'expr': ("drying_method IN [soda_khar, malabar_lime_sulphur] AND "
           "(ppe_available IS FALSE OR processing_trained_operator IS FALSE)"),
  'tests': [
    ({'drying_method':'soda_khar','ppe_available':False,'processing_trained_operator':True}, T, 'PPE नाही'),
    ({'drying_method':'soda_khar','ppe_available':True,'processing_trained_operator':True}, F, 'दोन्ही आहेत'),
    ({'drying_method':'simple_sun','ppe_available':False}, F, 'साधी पद्धत — लागू नाही'),
  ]},

'D09-SF-002': {
  'expr': "phi_days_remaining IS NULL AND WITHIN(harvest_date, 30 DAYS)",
  'note': 'Duplication group: pre_harvest_interval_block.',
  'tests': [
    ({'days_to_harvest':10}, T, 'PHI अज्ञात, काढणी जवळ'),
    ({'days_to_harvest':10,'phi_days_remaining':0}, F, 'PHI पूर्ण'),
  ]},

'D09-GD-002': {
  'expr': "graded_separately IS FALSE AND WITHIN(harvest_date, 7 DAYS)",
  'tests': [
    ({'graded_separately':False,'days_to_harvest':3}, T, 'प्रतवारी नाही'),
    ({'graded_separately':True,'days_to_harvest':3}, F, 'प्रतवारी झाली'),
  ]},

# ===========================================================================
# D10 / D12 / D13
# ===========================================================================

'D10-SUB-002': {
  'expr': "pre_sanction_received IS FALSE AND subsidy_scheme_applied IS NOT NULL",
  'note': 'Work before pre-sanction forfeits the subsidy.',
  'tests': [
    ({'pre_sanction_received':False,'subsidy_scheme_applied':'drip'}, T, 'पूर्वसंमती नाही'),
    ({'pre_sanction_received':True,'subsidy_scheme_applied':'drip'}, F, 'पूर्वसंमती मिळाली'),
  ]},

'D10-FRESH-002': {
  'expr': "data_review_due IS NOT NULL",
  'tests': [
    ({'data_review_due':'2027-03-31'}, T, 'नेमकी रक्कम सांगू नका'),
    ({}, F, ''),
  ]},

'D12-POS-001': {
  'expr': "capability_claim_proposed IS NOT NULL",
  'tests': [
    ({'capability_claim_proposed':'learning_ai'}, T, 'दावा अडवा'),
    ({}, F, ''),
  ]},

'D12-POS-003': {
  'expr': "capability_claim_proposed IN [learning_ai, ai_yield_prediction, ml_optimises, npk_probe_measures, weather_forecast]",
  'tests': [
    ({'capability_claim_proposed':'npk_probe_measures'}, T, 'प्रतिबंधित दावा'),
    ({'capability_claim_proposed':'decision_support'}, F, 'योग्य वर्णन'),
  ]},

'D12-DPDP-001': {
  'expr': "consent_advisory IS FALSE OR consent_advisory IS NULL",
  'tests': [
    ({'consent_advisory':False}, T, 'संमती नाही — डेटा गोळा करू नका'),
    ({'consent_advisory':True}, F, 'संमती आहे'),
    ({}, T, 'संमतीची नोंदच नाही'),
  ]},

'D12-DPDP-002': {
  'expr': "consent_research IS FALSE OR consent_research IS NULL",
  'tests': [
    ({'consent_research':False,'consent_advisory':True}, T, 'संशोधन संमती नाही'),
    ({'consent_research':True}, F, 'दोन्ही संमती'),
  ]},

'D12-DPDP-003': {
  'expr': "cluster_anonymised IS FALSE AND consent_research IS TRUE",
  'tests': [
    ({'cluster_anonymised':False,'consent_research':True}, T, 'निर्देशांक ढोबळ करा'),
    ({'cluster_anonymised':True,'consent_research':True}, F, 'अनामीकृत'),
  ]},

'D13-RP-002': {
  'expr': "seed_retained_or_purchased == 'retained' AND (field_history_rot IS TRUE OR field_history_wilt IS TRUE)",
  'note': 'Arithmetic is overruled by field history.',
  'tests': [
    ({'seed_retained_or_purchased':'retained','field_history_wilt':True}, T, 'मर रोगाचा इतिहास — बेणे राखू नका'),
    ({'seed_retained_or_purchased':'retained','field_history_wilt':False,'field_history_rot':False}, F, 'इतिहास स्वच्छ'),
    ({'seed_retained_or_purchased':'purchased','field_history_wilt':True}, F, 'विकत घेतले — लागू नाही'),
  ]},

'D13-AD-002': {
  'expr': "profit_guarantee_proposed IS TRUE OR price_forecast_proposed IS TRUE",
  'tests': [
    ({'profit_guarantee_proposed':True}, T, 'हमी अडवा'),
    ({'price_forecast_proposed':True}, T, 'भाकीत — अडवा'),
    ({'profit_guarantee_proposed':False,'price_forecast_proposed':False}, F, 'दोन्ही नाही'),
  ]},

'D07-MO-002': {
  'expr': "dry_spell_days >= 7 AND STAGE IN [G3, G4]",
  'note': 'Duplication group: critical_stage_moisture_stress. Same factor as D03-MN-004.',
  'tests': [
    ({'dry_spell_days':9,'current_stage':'G4'}, T, 'G4 मध्ये ९ दिवस खंड'),
    ({'dry_spell_days':9,'current_stage':'G2'}, F, 'G2 — सामान्य १० दिवस नियम'),
    ({'dry_spell_days':4,'current_stage':'G3'}, F, '४ दिवस'),
    ({'current_stage':'G3'}, U, 'खंड मोजलेला नाही'),
  ]},

'D13-RV-001': {
  'expr': "sale_price_per_quintal IS NOT NULL AND breakeven_price_per_quintal IS NULL",
  'note': 'Never show a price without the break-even beside it.',
  'tests': [
    ({'sale_price_per_quintal':12000}, T, 'भाव आहे पण समतोल बिंदू नाही'),
    ({'sale_price_per_quintal':12000,'breakeven_price_per_quintal':1450}, F, 'दोन्ही आहेत'),
  ]},

'D13-SRC-001': {
  'expr': "yield_target_quintal_per_acre IS NOT NULL AND ceiling_basis == 'unverified'",
  'note': 'Commercial yield claims must not set the target while the ceiling is unresolved.',
  'tests': [
    ({'yield_target_quintal_per_acre':150,'ceiling_basis':'unverified'}, T, 'मर्यादा अनिश्चित'),
    ({'yield_target_quintal_per_acre':110,'ceiling_basis':'variety_plus_broad_ridge_113'}, F, 'मर्यादा निश्चित'),
  ]},

# ===========================================================================
# G4 — the bulking stage. Added after the season simulation showed a 39-day
# silence here, which is where the yield is actually made.
# ===========================================================================

'D04-PK-001': {
  'expr': "dap BETWEEN 108 AND 115 AND k_late_split_1_date IS NULL",
  'note': 'The most commonly skipped operation in the schedule, because by 110 DAP the crop looks healthy.',
  'tests': [
    ({'dap':110}, T, '११० दिवस, पालाश बाकी'),
    ({'dap':110,'k_late_split_1_date':'done'}, F, 'दिला आहे'),
    ({'dap':100}, F, 'अजून वेळ आहे'),
  ]},

'D04-PK-002': {
  'expr': "dap BETWEEN 138 AND 145 AND k_late_split_2_date IS NULL",
  'tests': [
    ({'dap':140}, T, '१४० दिवस, दुसरा हप्ता बाकी'),
    ({'dap':140,'k_late_split_2_date':'done'}, F, 'दिला आहे'),
  ]},

'D08-EU-004': {
  'expr': "dap BETWEEN 115 AND 130 AND earthing_up_2_date IS NULL AND earthing_up_date IS NOT NULL",
  'tests': [
    ({'dap':120,'earthing_up_date':'done'}, T, 'दुसरी उटाळणी बाकी'),
    ({'dap':120,'earthing_up_date':'done','earthing_up_2_date':'done'}, F, 'झाली'),
    ({'dap':120}, F, 'पहिली उटाळणीच झालेली नाही — दुसरी सुचवू नये'),
  ]},

'D08-MU-002': {
  'expr': "((dap BETWEEN 40 AND 60 AND mulch_stage_2_done IS FALSE) OR (dap BETWEEN 90 AND 120 AND mulch_stage_3_done IS FALSE))",
  'tests': [
    ({'dap':50,'mulch_stage_2_done':False}, T, 'दुसरा टप्पा बाकी'),
    ({'dap':100,'mulch_stage_3_done':False}, T, 'तिसरा टप्पा बाकी'),
    ({'dap':50,'mulch_stage_2_done':True}, F, 'झाला'),
  ]},

'D03-SC-006': {
  'expr': "dap BETWEEN 150 AND 210 AND has_drip IS TRUE",
  'note': 'Bulking needs consistency, not level. This is where drip pays for itself.',
  'tests': [
    ({'dap':180,'has_drip':True}, T, 'गड्डा भरतोय — सातत्य ठेवा'),
    ({'dap':100,'has_drip':True}, F, 'अजून G3'),
  ]},

'D09-WW-001': {
  'expr': "days_to_harvest BETWEEN 55 AND 62 AND water_withdrawal_start_date IS NULL",
  'note': 'Skin condition is a grading determinant and the spread is 2.7 times.',
  'tests': [
    ({'days_to_harvest':60}, T, 'पाणी उतरण सुरू करा'),
    ({'days_to_harvest':60,'water_withdrawal_start_date':'done'}, F, 'सुरू आहे'),
    ({'days_to_harvest':30}, F, 'खिडकी गेली'),
  ]},

'D13-SD-002': {
  'expr': "cost_seed IS NOT NULL AND (plants_per_acre IS NULL OR seed_piece_weight_g IS NULL)",
  'tests': [
    ({'cost_seed':40000}, T, 'गणिताचा आधार नाही'),
    ({'cost_seed':40000,'plants_per_acre':24300,'seed_piece_weight_g':35}, F, 'गणित पूर्ण'),
  ]},
}
