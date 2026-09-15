#!/usr/bin/env python3
"""
Wave 2 — triggers for the yellow and info rules that carry the season.

Wave 1 covered every blocking and red rule. The season simulation then showed
what that leaves: a 22-day silence through G1 and a 39-day silence through G4.
Wave 1 is the engine's brakes; this is its voice.

Selection principle: a rule earns a trigger in this wave if it either
  (a) fills a silence the simulation found, or
  (b) protects a u-value of 0.10 or more, or
  (c) is the sensor-driven half of a decision Wave 1 only half covered.

Rules that are pure product policy (Domain 11 and 12 method rules) do not get
triggers at all. They are not farmer-facing and there is nothing to evaluate.
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W2 = {

# ===========================================================================
# G0 — pre-season. 38 percent of controllable loss is decided before day zero.
# ===========================================================================

'D02-CL-001': {
  'expr': "days_to_planting BETWEEN 55 AND 95 AND deep_ploughing_done IS FALSE",
  'note': 'March ploughing anchors the whole chain. Losing it compresses everything downstream.',
  'tests': [
    ({'days_to_planting':80,'deep_ploughing_done':False}, T, 'मार्च — नांगरट सुरू करा'),
    ({'days_to_planting':80,'deep_ploughing_done':True}, F, 'झाली आहे'),
    ({'days_to_planting':20,'deep_ploughing_done':False}, F, 'खिडकी गेली, वेगळा नियम'),
  ]},

'D08-CA-001': {
  'expr': "days_to_planting BETWEEN 85 AND 95",
  'note': 'Issue the full operations calendar once, at the top of the chain.',
  'tests': [
    ({'days_to_planting':90}, T, 'कालदर्शिका द्या'),
    ({'days_to_planting':40}, F, 'उशीर'),
  ]},

'D02-SN-001': {
  'expr': "MONTH IN [APR, MAY] AND days_to_planting > 30 AND solarization_done IS FALSE",
  'note': 'April and May maxima of 40 to 45 C make this belt unusually good for solarization.',
  'tests': [
    ({'current_month':4,'days_to_planting':50,'solarization_done':False}, T, 'एप्रिल — सौरीकरण'),
    ({'current_month':4,'days_to_planting':50,'solarization_done':True}, F, 'झाले'),
    ({'current_month':6,'days_to_planting':50,'solarization_done':False}, F, 'जून — उशीर'),
  ]},

'D02-TL-003': {
  'expr': "vafsa_state == 'workable' AND deep_ploughing_done IS FALSE",
  'note': 'Vertisol has a few workable days after rain. Duplication group vafsa_workable_window.',
  'tests': [
    ({'vafsa_state':'workable','deep_ploughing_done':False}, T, 'वाफसा आला — मशागत करा'),
    ({'vafsa_state':'too_wet','deep_ploughing_done':False}, F, 'खूप ओली'),
    ({'deep_ploughing_done':False}, U, 'वाफसा माहीत नाही'),
  ]},

'D08-TL-002': {
  'expr': "vafsa_state == 'workable' AND kulav_passes < 3",
  'tests': [
    ({'vafsa_state':'workable','kulav_passes':1}, T, 'अजून पाळ्या बाकी'),
    ({'vafsa_state':'workable','kulav_passes':4}, F, 'पुरेशा झाल्या'),
  ]},

'D10-VAR-001': {
  'expr': "days_to_planting BETWEEN 140 AND 160 AND seed_supplier_identified IS FALSE",
  'note': 'A 4,000 hectare state crop has a seed trade to match. Late ordering forfeits u=0.138.',
  'tests': [
    ({'days_to_planting':150,'seed_supplier_identified':False}, T, 'पाच महिने — बेणे ठरवा'),
    ({'days_to_planting':150,'seed_supplier_identified':True}, F, 'ठरले आहे'),
    ({'days_to_planting':40,'seed_supplier_identified':False}, F, 'खिडकी गेली'),
  ]},

'D10-INS-001': {
  'expr': "days_to_planting BETWEEN 40 AND 60 AND pmfby_notified_for_ginger == 'unverified'",
  'tests': [
    ({'days_to_planting':50,'pmfby_notified_for_ginger':'unverified'}, T, 'विमा तपासा'),
    ({'days_to_planting':50,'pmfby_notified_for_ginger':'no'}, F, 'तपासले आहे'),
  ]},

'D13-RR-001': {
  'expr': "days_to_planting BETWEEN 85 AND 95",
  'tests': [
    ({'days_to_planting':90}, T, 'जोखीम यादी द्या'),
    ({'days_to_planting':30}, F, ''),
  ]},

'D05-CH-007': {
  'expr': "days_to_planting BETWEEN 1 AND 8 AND hot_water_treatment_done IS FALSE",
  'note': 'Chemical then dry then biological. Easy to collapse into one step on a busy day.',
  'tests': [
    ({'days_to_planting':5,'hot_water_treatment_done':False}, T, 'बेणे प्रक्रिया'),
    ({'days_to_planting':5,'hot_water_treatment_done':True}, F, 'झाली'),
  ]},

'D01-PW-002': {
  'expr': "MONTH IN [MAY, JUN] AND days_to_planting BETWEEN 1 AND 20",
  'note': 'The habit conflict: every other kharif crop says wait for rain, ginger says do not.',
  'tests': [
    ({'current_month':5,'days_to_planting':15}, T, 'मुदत जवळ'),
    ({'current_month':7,'days_to_planting':15}, F, 'जुलै — मुदत गेली'),
  ]},

'D07-MO-001': {
  'expr': "MONTH IN [MAY, JUN] AND days_to_planting BETWEEN 1 AND 20",
  'tests': [
    ({'current_month':6,'days_to_planting':10}, T, 'पावसाची वाट पाहू नका'),
    ({'current_month':4,'days_to_planting':60}, F, 'अजून वेळ'),
  ]},

'D07-CC-001': {
  'expr': "days_to_planting BETWEEN 20 AND 40 AND has_drip IS FALSE",
  'note': 'Pre-monsoon rainfall is down about 31 percent; the traditional practice assumes water that no longer arrives.',
  'tests': [
    ({'days_to_planting':30,'has_drip':False}, T, 'सरींवर अवलंबून राहू नका'),
    ({'days_to_planting':30,'has_drip':True}, F, 'ठिबक आहे'),
  ]},

'D03-SB-002': {
  'expr': "calibration_done IS FALSE",
  'note': 'Capacitive sensors on vertisol need two-point calibration. Until then, table plus rain deduction.',
  'tests': [
    ({'calibration_done':False}, T, 'calibration करा'),
    ({'calibration_done':True}, F, 'झाले'),
    ({}, U, 'स्थिती माहीत नाही'),
  ]},

# ===========================================================================
# G1 — the 22-day silence the simulation found
# ===========================================================================

'D08-MU-001': {
  'expr': "dap BETWEEN 0 AND 4 AND mulch_stage_1_done IS FALSE",
  'note': 'Not a moisture improvement here. Bare black soil in May exceeds the 25-26 C sprouting optimum.',
  'tests': [
    ({'dap':1,'mulch_stage_1_done':False}, T, 'लगेच आच्छादन'),
    ({'dap':1,'mulch_stage_1_done':True}, F, 'घातले'),
    ({'dap':20,'mulch_stage_1_done':False}, F, 'खिडकी गेली'),
  ]},

'D03-SC-005': {
  'expr': "dap BETWEEN 2 AND 5",
  'note': 'Ambavani — the first light irrigation after planting into vafsa.',
  'tests': [
    ({'dap':3}, T, 'आंबवणी'),
    ({'dap':10}, F, ''),
  ]},

'D03-SC-003': {
  'expr': "STAGE IN [G1] AND air_temp_max_c > 33",
  'note': 'Two shifts of 30 to 45 minutes. Seed rhizome has no roots and rots in saturated soil.',
  'tests': [
    ({'current_stage':'G1','air_temp_max_c':38}, T, 'दोन पाळ्यांत पाणी'),
    ({'current_stage':'G1','air_temp_max_c':29}, F, 'सौम्य'),
    ({'current_stage':'G2','air_temp_max_c':38}, F, 'G2 — वेगळा नियम'),
  ]},

'D08-WD-002': {
  'expr': "dap BETWEEN 10 AND 13 AND herbicide_post_emergent_date IS NULL AND emergence_started IS FALSE",
  'note': 'The window closes in three days and emergence follows immediately.',
  'tests': [
    ({'dap':11,'emergence_started':False}, T, 'शेवटची संधी'),
    ({'dap':11,'emergence_started':True}, F, 'उगवण सुरू — अडवा'),
    ({'dap':11,'herbicide_post_emergent_date':'done','emergence_started':False}, F, 'झाले'),
  ]},

'D01-PH-002': {
  'expr': "dap BETWEEN 33 AND 40 AND establishment_pct IS NULL",
  'note': 'Establishment is a hard ceiling and the count has a narrow window.',
  'tests': [
    ({'dap':35}, T, 'उगवण मोजा'),
    ({'dap':35,'establishment_pct':88}, F, 'मोजली'),
    ({'dap':60}, F, 'खिडकी गेली'),
  ]},

'D08-GF-001': {
  'expr': "dap BETWEEN 33 AND 40 AND establishment_pct < 85",
  'note': 'Find the cause first. If it is rot, gap filling wastes a second lot of the most expensive input.',
  'tests': [
    ({'dap':35,'establishment_pct':72}, T, 'कारण शोधा'),
    ({'dap':35,'establishment_pct':90}, F, 'चांगली उगवण'),
  ]},

'D05-RF-001': {
  'expr': "dap BETWEEN 28 AND 33 AND castor_bait_prepared_date IS NULL",
  'note': 'The bait needs 8 to 10 days to develop and the pest peaks in July. Starting when the pest is seen is already late.',
  'tests': [
    ({'dap':30}, T, 'एरंडी आमिष भिजत घाला'),
    ({'dap':30,'castor_bait_prepared_date':'done'}, F, 'घातले'),
    ({'dap':50}, F, 'उशीर'),
  ]},

# ===========================================================================
# G2 — vegetative
# ===========================================================================

'D04-NS-001': {
  'expr': "dap BETWEEN 57 AND 64 AND n_split_1_date IS NULL",
  'tests': [
    ({'dap':60}, T, 'नत्राचा पहिला हप्ता'),
    ({'dap':60,'n_split_1_date':'done'}, F, 'दिला'),
  ]},

'D04-MC-001': {
  'expr': "dap BETWEEN 45 AND 60 AND micronutrient_spray_1_done IS FALSE",
  'note': 'Suppressed by D04-MC-004 above 35 C or before rain. Zinc deficiency averages 49 percent of Indian soils.',
  'tests': [
    ({'dap':50,'micronutrient_spray_1_done':False}, T, 'फवारणी करा'),
    ({'dap':50,'micronutrient_spray_1_done':True}, F, 'झाली'),
  ]},

'D04-MC-004': {
  'expr': "air_temp_max_c > 35 OR forecast_rain_48h_mm > 5",
  'note': 'The suppressor. Leaves scorch above 35 C and rain washes foliar application off.',
  'tests': [
    ({'air_temp_max_c':39,'forecast_rain_48h_mm':0}, T, 'उष्णता — थांबा'),
    ({'air_temp_max_c':30,'forecast_rain_48h_mm':12}, T, 'पाऊस — थांबा'),
    ({'air_temp_max_c':30,'forecast_rain_48h_mm':0}, F, 'फवारणी योग्य'),
  ]},

'D05-SH-001': {
  'expr': "dap BETWEEN 45 AND 60 AND light_trap_installed IS FALSE",
  'tests': [
    ({'dap':50,'light_trap_installed':False}, T, 'प्रकाश सापळा'),
    ({'dap':50,'light_trap_installed':True}, F, 'लावला'),
  ]},

'D05-PC-003': {
  'expr': "dap BETWEEN 58 AND 64 AND labour_arranged_date IS NULL",
  'note': 'August competes with cotton and soybean intercultivation for the same workers.',
  'tests': [
    ({'dap':60}, T, 'मजूर ठरवा'),
    ({'dap':60,'labour_arranged_date':'set'}, F, 'ठरले'),
  ]},

'D05-SW-001': {
  'expr': "DURATION(rh_pct > 80) > 72 HOURS AND MONTH IN [JUL, AUG, SEP, OCT]",
  'note': 'Pest pressure alert, not a spray instruction. Doubles scouting frequency.',
  'tests': [
    ({'rh_pct__duration':80,'current_month':8}, T, 'कीड-दाब वाढला'),
    ({'rh_pct__duration':80,'current_month':1}, F, 'हंगामाबाहेर'),
    ({'rh_pct__duration':20,'current_month':8}, F, 'कमी कालावधी'),
  ]},

'D06-SR-003': {
  'expr': "earthing_up_date IS NULL AND dap BETWEEN 70 AND 95",
  'note': 'Injury during weeding or earthing is a pest-free route into the same rot.',
  'tests': [
    ({'dap':80}, T, 'गड्ड्याला इजा टाळा'),
    ({'dap':80,'earthing_up_date':'done'}, F, 'झाली'),
  ]},

# ===========================================================================
# G3 — the most important field day of the season
# ===========================================================================

'D08-EU-001': {
  'expr': "dap BETWEEN 75 AND 90 AND earthing_up_date IS NULL AND flowering_observed IS FALSE",
  'note': 'Six operations from five domains in one visit. Suppressed by D08-EU-002 once flowering opens.',
  'tests': [
    ({'dap':82,'flowering_observed':False}, T, 'उटाळणीची वेळ'),
    ({'dap':82,'earthing_up_date':'done','flowering_observed':False}, F, 'झाली'),
    ({'dap':82,'flowering_observed':True}, F, 'फुलोरा — खिडकी गेली'),
  ]},

'D08-BN-002': {
  'expr': "dap BETWEEN 73 AND 77 AND earthing_up_date IS NULL",
  'note': 'A week of preparation lead time protects three u-values totalling half the season controllable loss.',
  'tests': [
    ({'dap':75}, T, 'तयारीची यादी'),
    ({'dap':82}, F, 'दिवस आला'),
  ]},

'D04-NS-002': {
  'expr': "dap BETWEEN 78 AND 88 AND n_split_2_date IS NULL",
  'tests': [
    ({'dap':82}, T, 'शेवटचा नत्र हप्ता'),
    ({'dap':82,'n_split_2_date':'done'}, F, 'दिला'),
  ]},

'D08-EU-003': {
  'expr': "earthing_up_date IS NOT NULL AND water_stress_after_earthing_done IS FALSE",
  'note': 'An instruction to do less, in another domain. Easily lost.',
  'tests': [
    ({'earthing_up_date':'done','water_stress_after_earthing_done':False}, T, 'ठिबक कमी करा'),
    ({'earthing_up_date':'done','water_stress_after_earthing_done':True}, F, 'केले'),
    ({'water_stress_after_earthing_done':False}, F, 'उटाळणीच झालेली नाही'),
  ]},

'D04-MC-002': {
  'expr': "dap BETWEEN 75 AND 90 AND micronutrient_spray_2_done IS FALSE",
  'tests': [
    ({'dap':85,'micronutrient_spray_2_done':False}, T, 'दुसरी फवारणी'),
    ({'dap':85,'micronutrient_spray_2_done':True}, F, 'झाली'),
  ]},

'D05-NE-001': {
  'expr': "dap IN [60, 90] AND tillers_per_plant < 9",
  'note': 'Tiller shortfall is the earliest nematode sign and is routinely read as nitrogen deficiency.',
  'tests': [
    ({'dap':60,'tillers_per_plant':7}, T, 'फुटवे कमी — सूत्रकृमी तपासा'),
    ({'dap':60,'tillers_per_plant':12}, F, 'सामान्य'),
    ({'dap':60}, U, 'मोजले नाहीत'),
  ]},

'D07-HU-001': {
  'expr': "DURATION(rh_pct > 85) > 72 HOURS AND MONTH IN [AUG, SEP]",
  'tests': [
    ({'rh_pct__duration':80,'current_month':8}, T, 'कंदकूज प्रतिबंध'),
    ({'rh_pct__duration':80,'current_month':12}, F, 'हिवाळा — वेगळा नियम'),
  ]},

# ===========================================================================
# G4 — bulking. Wave 1 added six here; these complete it.
# ===========================================================================

'D01-PH-006': {
  'expr': "dap BETWEEN 118 AND 124 AND sample_dig_120_done IS FALSE",
  'note': 'The yield organ is invisible. A dug sample is the only real measurement.',
  'tests': [
    ({'dap':120,'sample_dig_120_done':False}, T, 'नमुना खोदा'),
    ({'dap':120,'sample_dig_120_done':True}, F, 'खोदला'),
  ]},

'D01-VR-002': {
  'expr': "dap BETWEEN 178 AND 184 AND sample_dig_180_done IS FALSE",
  'note': 'Seed selection is a mid-season observation task disguised as a post-harvest one.',
  'tests': [
    ({'dap':180,'sample_dig_180_done':False}, T, 'नमुना व बेणे खुणावा'),
    ({'dap':180,'sample_dig_180_done':True}, F, 'झाले'),
  ]},

'D06-LS-001': {
  'expr': "DURATION(leaf_wetness_hours > 8) > 48 HOURS AND dap < 210",
  'note': 'Seven months from a June planting reaches the winter fog period exactly.',
  'tests': [
    ({'leaf_wetness_hours__duration':60,'dap':180}, T, 'पानांवरील रोग वेळापत्रक'),
    ({'leaf_wetness_hours__duration':60,'dap':230}, F, 'सात महिन्यांनंतर'),
  ]},

'D06-DX-005': {
  'expr': "leaf_spot_rings_visible IS NOT NULL AND air_temp_max_c > 35",
  'note': 'Sun-held ring test separates leaf spot from heat scorch. In a belt reaching 45.9 C this fires often.',
  'tests': [
    ({'leaf_spot_rings_visible':True,'air_temp_max_c':38}, T, 'वर्तुळे तपासा'),
    ({'leaf_spot_rings_visible':True,'air_temp_max_c':30}, F, 'उष्णता नाही'),
  ]},

'D01-TM-002': {
  'expr': "MONTH IN [NOV, DEC, JAN] AND STAGE IN [G4]",
  'note': 'The Marathwada winter is close to ideal for bulking. Kerala does not have this.',
  'tests': [
    ({'current_month':12,'current_stage':'G4'}, T, 'अनुकूल — पीक भरू द्या'),
    ({'current_month':8,'current_stage':'G2'}, F, ''),
  ]},

'D04-NU-002': {
  'expr': "dap > 180 AND k_late_split_2_date IS NOT NULL",
  'note': 'Do not stop potassium because foliage growth slowed. The rhizome develops until harvest.',
  'tests': [
    ({'dap':190,'k_late_split_2_date':'done'}, T, 'आधार चालू ठेवा'),
    ({'dap':150,'k_late_split_2_date':'done'}, F, 'अजून लवकर'),
  ]},

# ===========================================================================
# G5 — harvest
# ===========================================================================

'D09-MT-001': {
  'expr': "dap > 200 AND skin_scrape_result IS NULL",
  'note': 'The simplest high-value test in the knowledge base. It needs a thumb.',
  'tests': [
    ({'dap':215}, T, 'सालीची चाचणी करा'),
    ({'dap':215,'skin_scrape_result':'firmly_attached'}, F, 'केली'),
    ({'dap':180}, F, 'अजून लवकर'),
  ]},

'D09-WW-002': {
  'expr': "water_withdrawal_start_date IS NOT NULL AND soil_texture_class == 'heavy'",
  'note': 'Abrupt drying cracks vertisol; harvest injury becomes storage rot.',
  'tests': [
    ({'water_withdrawal_start_date':'done','soil_texture_class':'heavy'}, T, 'उतरण हळू ठेवा'),
    ({'water_withdrawal_start_date':'done','soil_texture_class':'light'}, F, 'हलकी जमीन'),
  ]},

'D09-HV-001': {
  'expr': "days_to_harvest BETWEEN 0 AND 3 AND skin_scrape_result == 'firmly_attached'",
  'tests': [
    ({'days_to_harvest':1,'skin_scrape_result':'firmly_attached'}, T, 'काढणीचा क्रम'),
    ({'days_to_harvest':1,'skin_scrape_result':'peels_easily'}, F, 'अपक्व'),
  ]},

'D09-PH-001': {
  'expr': "harvest_date IS NOT NULL AND produce_washed IS FALSE",
  'note': 'Cleanliness is one of three grading determinants still in the farmer hands at this point.',
  'tests': [
    ({'harvest_date':'done','produce_washed':False}, T, 'धुवा'),
    ({'harvest_date':'done','produce_washed':True}, F, 'धुतले'),
  ]},

'D09-GD-001': {
  'expr': "days_to_harvest BETWEEN 25 AND 35",
  'note': 'A 2.7 times spread was recorded within one market on one day, purely on quality.',
  'tests': [
    ({'days_to_harvest':30}, T, 'प्रतवारीचा फरक सांगा'),
    ({'days_to_harvest':60}, F, ''),
  ]},

'D09-YD-001': {
  'expr': "harvest_date IS NOT NULL AND yield_quintal_per_acre_actual IS NULL",
  'note': 'Twenty-two of thirty-five u-values are estimates. This is how they become measurements.',
  'tests': [
    ({'harvest_date':'done'}, T, 'उत्पादन नोंदवा'),
    ({'harvest_date':'done','yield_quintal_per_acre_actual':92}, F, 'नोंदवले'),
  ]},

'D09-DR-004': {
  'expr': "dap BETWEEN 195 AND 205 AND drying_space_ready IS FALSE",
  'note': 'Dry ginger is insurance against a price crash and insurance must be in place before the event.',
  'tests': [
    ({'dap':200,'drying_space_ready':False}, T, 'वाळवणीची जागा तयार आहे का'),
    ({'dap':200,'drying_space_ready':True}, F, 'तयार'),
  ]},

# ===========================================================================
# Cross-stage sensor rules
# ===========================================================================

'D03-WR-001': {
  'expr': "has_drip IS TRUE AND pan_evaporation_mm_day IS NULL AND dap BETWEEN 0 AND 225",
  'note': 'Table fallback. This alone can run the whole season irrigation.',
  'tests': [
    ({'has_drip':True,'dap':100}, T, 'तक्त्यानुसार पाणी'),
    ({'has_drip':True,'dap':100,'pan_evaporation_mm_day':5.2}, F, 'सूत्र वापरा'),
  ]},

'D03-WR-002': {
  'expr': "pan_evaporation_mm_day IS NOT NULL AND dap BETWEEN 0 AND 225",
  'note': 'Evaporation is the only locally variable term. A competitor without hardware in the village cannot produce this.',
  'tests': [
    ({'pan_evaporation_mm_day':5.2,'dap':100}, T, 'सूत्राने गरज काढा'),
    ({'dap':100}, F, 'station डेटा नाही'),
  ]},

'D03-MN-001': {
  'expr': "rainfall_mm > 2 AND dap BETWEEN 0 AND 225",
  'note': 'Ten millimetres is 40,000 litres per acre — about two days in September, not a week.',
  'tests': [
    ({'rainfall_mm':12,'dap':100}, T, 'पाऊस वजा करा'),
    ({'rainfall_mm':0.5,'dap':100}, F, 'नगण्य'),
  ]},

'D02-DR-003': {
  'expr': "forecast_rain_48h_mm > 50 AND STAGE IN [G2, G3]",
  'note': 'Channels silt up and are noticed only when they fail.',
  'tests': [
    ({'forecast_rain_48h_mm':60,'current_stage':'G2'}, T, 'चर तपासा'),
    ({'forecast_rain_48h_mm':60,'current_stage':'G5'}, F, ''),
  ]},

'D07-CY-002': {
  'expr': "MONTH IN [OCT, NOV] AND STAGE IN [G3, G4]",
  'note': 'A monthly reminder protecting a 0.30 exposure. The channels exist; the failure mode is neglect.',
  'tests': [
    ({'current_month':10,'current_stage':'G4'}, T, 'चर तपासा — पावसाळा संपला तरी'),
    ({'current_month':10,'current_stage':'G2'}, F, ''),
  ]},

'D07-HS-004': {
  'expr': "air_temp_max_c > 35 OR forecast_rain_48h_mm > 5",
  'note': 'Suppressor for any foliar spray. Same condition as D04-MC-004, different domain.',
  'tests': [
    ({'air_temp_max_c':40,'forecast_rain_48h_mm':0}, T, 'फवारणी पुढे ढकला'),
    ({'air_temp_max_c':28,'forecast_rain_48h_mm':1}, F, 'योग्य वेळ'),
  ]},

'D04-SB-002': {
  'expr': "fertigation_active IS TRUE AND fertigation_last_ec_response IS NULL",
  'note': 'The one genuinely useful thing the NPK probe does. A fertigation failure otherwise goes unnoticed for weeks.',
  'tests': [
    ({'fertigation_active':True}, T, 'खत पोहोचले का तपासा'),
    ({'fertigation_active':True,'fertigation_last_ec_response':0.12}, F, 'पोहोचले'),
  ]},

'D04-SB-003': {
  'expr': "ec_trend_pct > 20 AND rainfall_mm < 2",
  'note': 'Drip concentrates salts and low rainfall means no leaching event to reset it.',
  'tests': [
    ({'ec_trend_pct':28,'rainfall_mm':0}, T, 'क्षार साचताहेत'),
    ({'ec_trend_pct':28,'rainfall_mm':15}, F, 'पाऊस — लीचिंग'),
  ]},

'D03-SC-002': {
  'expr': "drip_runtime_min > 60 AND soil_texture_class == 'heavy'",
  'note': 'Application rate must not exceed infiltration. A long run on vertisol ponds and runs off.',
  'tests': [
    ({'drip_runtime_min':85,'soil_texture_class':'heavy'}, T, 'दोन पाळ्यांत विभागा'),
    ({'drip_runtime_min':40,'soil_texture_class':'heavy'}, F, 'ठीक'),
  ]},

'D08-EU-005': {
  'expr': "MONTH IN [JUL, AUG, SEP] AND exposed_rhizomes_observed IS TRUE",
  'note': 'A standing instruction, not a scheduled operation. Exposure recurs between earthings.',
  'tests': [
    ({'current_month':8,'exposed_rhizomes_observed':True}, T, 'गड्डे झाका'),
    ({'current_month':8,'exposed_rhizomes_observed':False}, F, 'नाहीत'),
  ]},

'D05-WG-002': {
  'expr': "plant_pulls_easily IS TRUE",
  'tests': [
    ({'plant_pulls_easily':True}, T, 'हुमणी'),
    ({'plant_pulls_easily':False}, F, ''),
  ]},

'D05-SC-001': {
  'expr': "dap BETWEEN 40 AND 200 AND pest_scouting_date IS NULL",
  'note': 'No published ETLs exist for ginger. Recorded percentages are what eventually create them.',
  'tests': [
    ({'dap':100}, T, 'निरीक्षण करा'),
    ({'dap':100,'pest_scouting_date':'done'}, F, 'केले'),
  ]},
}
