#!/usr/bin/env python3
"""
Wave 3 — the remaining 62 triggers.

Wave 1 was the brakes, Wave 2 was the voice. This is the rest: mostly weather
and water, where the sensor half of a decision existed but the expression did
not.

Twenty-two of them are Domain 7. That is the domain whose triggers are almost
entirely station-driven, and it is where the hardware earns its place — the
temperature, humidity and rainfall conditions that no calendar can supply.
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W3 = {

# ===========================================================================
# D01 — Lifecycle
# ===========================================================================

'D01-PH-001': {
  'expr': "dap BETWEEN 0 AND 35 AND STAGE IN [G1]",
  'tests': [({'dap':20,'current_stage':'G1'}, T, 'उगवण अवस्था'),
            ({'dap':60,'current_stage':'G2'}, F, 'पुढे गेली')]},

'D01-PH-003': {
  'expr': "dap BETWEEN 90 AND 150 AND STAGE IN [G3]",
  'note': 'Rhizome initiation. Water and potassium matter most here.',
  'tests': [({'dap':120,'current_stage':'G3'}, T, 'गड्डा तयार होतोय'),
            ({'dap':60,'current_stage':'G2'}, F, '')]},

'D01-TM-001': {
  'expr': "air_temp_max_c > 35 AND STAGE IN [G0, G1]",
  'note': 'Expert amendment lowered this from 38 C. Protection begins where scorching is documented to start.',
  'tests': [({'air_temp_max_c':39,'current_stage':'G1'}, T, 'उष्णता संरक्षण'),
            ({'air_temp_max_c':32,'current_stage':'G1'}, F, 'सौम्य'),
            ({'air_temp_max_c':39,'current_stage':'G3'}, F, 'पुढील अवस्था')]},

'D01-HV-001': {
  'expr': "dap BETWEEN 205 AND 240 AND harvest_date IS NULL",
  'tests': [({'dap':220}, T, 'काढणीची तयारी'),
            ({'dap':220,'harvest_date':'done'}, F, 'झाली')]},

'D01-HV-004': {
  'expr': "harvest_route == 'seed_rhizome' AND dap < 235",
  'note': 'Immature seed does not survive four to five months of storage.',
  'tests': [({'harvest_route':'seed_rhizome','dap':200}, T, 'बेणे — पूर्ण पक्वता हवी'),
            ({'harvest_route':'green_full','dap':200}, F, 'बाजारासाठी'),
            ({'harvest_route':'seed_rhizome','dap':240}, F, 'पक्व')]},

'D01-VR-001': {
  'expr': "variety IS NULL AND days_to_planting > 30",
  'note': 'u = 0.138 between the best and weakest of the four main varieties.',
  'tests': [({'days_to_planting':60}, T, 'जात ठरवा'),
            ({'days_to_planting':60,'variety':'mahima'}, F, 'ठरली')]},

# ===========================================================================
# D03 — Water
# ===========================================================================

'D03-WR-003': {
  'expr': "STAGE IN [G3, G4] AND soil_moisture_vwc < vwc_stress_threshold",
  'note': 'The critical window. Stress here is irrecoverable.',
  'tests': [({'current_stage':'G3','soil_moisture_vwc':20,'vwc_stress_threshold':22}, T, 'ताण'),
            ({'current_stage':'G3','soil_moisture_vwc':30,'vwc_stress_threshold':22}, F, 'ठीक'),
            ({'current_stage':'G3','soil_moisture_vwc':20}, U, 'calibration नाही')]},

'D03-WR-004': {
  'expr': "STAGE IN [G3, G4] AND dry_spell_days >= 5",
  'tests': [({'current_stage':'G4','dry_spell_days':6}, T, 'निर्णायक अवस्थेत खंड'),
            ({'current_stage':'G2','dry_spell_days':6}, F, 'सामान्य नियम')]},

'D03-WL-004': {
  'expr': "DURATION(soil_moisture_vwc > vwc_saturation) > 6 HOURS AND STAGE IN [G1]",
  'note': 'Seed rhizome has no roots yet. Six hours is enough at G1.',
  'tests': [({'soil_moisture_vwc__duration':8,'current_stage':'G1'}, T, 'उगवणीत साचले'),
            ({'soil_moisture_vwc__duration':8,'current_stage':'G3'}, F, 'नंतरची अवस्था')]},

'D03-MN-003': {
  'expr': "rain_gap_days >= 10 AND STAGE IN [G1, G2]",
  'note': 'Superseded by D03-MN-004 at G3 and G4, where the point is 7 days.',
  'tests': [({'rain_gap_days':11,'current_stage':'G2'}, T, 'दहा दिवस खंड'),
            ({'rain_gap_days':11,'current_stage':'G3'}, F, 'G3 — सात दिवसांचा नियम')]},

'D03-WW-001': {
  'expr': "days_to_harvest BETWEEN 55 AND 62 AND water_withdrawal_start_date IS NULL",
  'tests': [({'days_to_harvest':60}, T, 'पाणी उतरण'),
            ({'days_to_harvest':60,'water_withdrawal_start_date':'done'}, F, 'सुरू')]},

'D03-WW-002': {
  'expr': "water_withdrawal_start_date IS NOT NULL AND soil_texture_class == 'heavy'",
  'tests': [({'water_withdrawal_start_date':'done','soil_texture_class':'heavy'}, T, 'हळू उतरण'),
            ({'water_withdrawal_start_date':'done','soil_texture_class':'light'}, F, '')]},

'D03-DS-001': {
  'expr': "has_drip IS TRUE AND drip_lateral_spacing_ft IS NULL AND soil_texture_class == 'heavy'",
  'note': 'Rewritten (§2.2): gate on soil_texture_class so it does not misfire on light/medium soils.',
  'tests': [({'has_drip':True,'soil_texture_class':'heavy'}, T, 'जड जमीन — ठिबक मांडणी ठरवा'),
            ({'has_drip':True,'soil_texture_class':'heavy','drip_lateral_spacing_ft':4}, F, 'ठरली'),
            ({'has_drip':True,'soil_texture_class':'light'}, F, 'हलकी जमीन — लागू नाही')]},

'D03-DS-002': {
  'expr': "has_drip IS TRUE AND drip_system_flow_lph IS NULL",
  'tests': [({'has_drip':True}, T, 'प्रवाह मोजा'),
            ({'has_drip':True,'drip_system_flow_lph':7380}, F, 'मोजला')]},

'D03-SC-001': {
  'expr': "has_drip IS TRUE AND drip_system_flow_lph IS NOT NULL AND dap BETWEEN 0 AND 225",
  'note': 'Litres per acre divided by system flow gives runtime in minutes. The engine computes this.',
  'tests': [({'has_drip':True,'drip_system_flow_lph':7380,'dap':100}, T, 'चालू वेळ काढा'),
            ({'has_drip':True,'dap':100}, F, 'प्रवाह माहीत नाही')]},

'D03-SC-004': {
  'expr': "STAGE IN [G5] AND days_to_harvest BETWEEN 0 AND 20",
  'tests': [({'current_stage':'G5','days_to_harvest':10}, T, 'काढणीपूर्व'),
            ({'current_stage':'G4','days_to_harvest':70}, F, '')]},

'D03-MU-001': {
  'expr': "dap BETWEEN 0 AND 4 AND mulch_stage_1_done IS FALSE",
  'note': 'Duplication group three_stage_mulch_programme. D06-MU-001 supersedes.',
  'tests': [({'dap':2,'mulch_stage_1_done':False}, T, 'आच्छादन'),
            ({'dap':2,'mulch_stage_1_done':True}, F, 'घातले')]},

# ===========================================================================
# D04 — Nutrient
# ===========================================================================

'D04-PK-003': {
  'expr': "dap > 150 AND k_late_split_2_date IS NULL",
  'tests': [({'dap':160}, T, 'पालाश राहिला'),
            ({'dap':160,'k_late_split_2_date':'done'}, F, 'दिला')]},

'D04-SN-002': {
  'expr': "soil_free_lime_pct > 10 AND micronutrient_spray_1_done IS FALSE",
  'note': 'Free lime locks up zinc and iron. Soil application does not reach the plant.',
  'tests': [({'soil_free_lime_pct':14,'micronutrient_spray_1_done':False}, T, 'चुनखडी — फवारणीच'),
            ({'soil_free_lime_pct':4,'micronutrient_spray_1_done':False}, F, 'कमी चुनखडी'),
            ({'micronutrient_spray_1_done':False}, U, 'माती परीक्षण नाही')]},

'D04-FG-001': {
  'expr': "has_drip IS TRUE AND fertigation_active IS FALSE AND dap BETWEEN 30 AND 150",
  'tests': [({'has_drip':True,'fertigation_active':False,'dap':60}, T, 'फर्टिगेशन सुरू करा'),
            ({'has_drip':True,'fertigation_active':True,'dap':60}, F, 'सुरू आहे')]},

'D04-DG-004': {
  'expr': "leaf_yellowing_pattern == 'margin_scorch' AND air_temp_max_c > 35",
  'tests': [({'leaf_yellowing_pattern':'margin_scorch','air_temp_max_c':38}, T, 'उष्णतेची इजा'),
            ({'leaf_yellowing_pattern':'margin_scorch','air_temp_max_c':29}, F, 'दुसरे कारण')]},

# ===========================================================================
# D05 — Pest
# ===========================================================================

'D05-PC-002': {
  'expr': "planting_date IS NOT NULL AND dap < 0",
  'note': 'Late planting exposes emergence to the rhizome fly peak. Duplication group late_planting.',
  'tests': [({'planting_date':'2026-06-20','dap':-5}, T, 'लागवड ठरली, अजून झाली नाही'),
            ({'dap':30}, F, 'झाली')]},

'D05-LR-001': {
  'expr': "STAGE IN [G3] AND MONTH IN [SEP, OCT, NOV]",
  'tests': [({'current_stage':'G3','current_month':10}, T, 'पाने गुंडाळणारी अळी'),
            ({'current_stage':'G2','current_month':10}, F, '')]},

'D05-CH-005': {
  'expr': "last_insecticide_group IS NOT NULL AND insecticide_group_repeated IS TRUE",
  'note': 'Rotate the mode of action group or resistance builds.',
  'tests': [({'last_insecticide_group':'organophosphate','insecticide_group_repeated':True}, T, 'तोच गट पुन्हा'),
            ({'last_insecticide_group':'neonicotinoid','insecticide_group_repeated':False}, F, 'गट बदलला')]},

'D05-CH-006': {
  'expr': "air_temp_max_c > 35 OR forecast_rain_48h_mm > 5",
  'note': 'Spray suppressor. Suppressed by D07-HS-004 which states the same condition.',
  'tests': [({'air_temp_max_c':38,'forecast_rain_48h_mm':0}, T, 'फवारणी पुढे ढकला'),
            ({'air_temp_max_c':29,'forecast_rain_48h_mm':1}, F, 'योग्य वेळ')]},

'D05-PC-004': {
  'expr': "previous_crops_3yr IS NOT NULL AND days_to_planting > 30",
  'tests': [({'previous_crops_3yr':'cotton,soybean,ginger','days_to_planting':60}, T, 'फेरपालट तपासा'),
            ({'days_to_planting':60}, F, 'नोंद नाही')]},

# ===========================================================================
# D06 — Disease
# ===========================================================================

'D06-CH-004': {
  'expr': "last_fungicide_group IS NOT NULL AND fungicide_group_repeated IS TRUE",
  'tests': [({'last_fungicide_group':'benzimidazole','fungicide_group_repeated':True}, T, 'तोच गट'),
            ({'last_fungicide_group':'phenylamide','fungicide_group_repeated':False}, F, 'बदलला')]},

'D06-SW-001': {
  'expr': "DURATION(rh_pct > 85) > 48 HOURS AND MONTH IN [JUL, AUG, SEP]",
  'tests': [({'rh_pct__duration':60,'current_month':8}, T, 'रोगाचे हवामान'),
            ({'rh_pct__duration':60,'current_month':1}, F, 'हिवाळा')]},

'D06-SW-002': {
  'expr': "soil_temp_c BETWEEN 25 AND 32 AND DURATION(soil_moisture_vwc > vwc_field_capacity) > 24 HOURS",
  'note': 'Pythium optimum. Soil temperature plus sustained wetness is the signature.',
  'tests': [({'soil_temp_c':28,'soil_moisture_vwc__duration':30}, T, 'कूजसाठी अनुकूल'),
            ({'soil_temp_c':18,'soil_moisture_vwc__duration':30}, F, 'थंड'),
            ({'soil_moisture_vwc__duration':30}, U, 'मातीचे तापमान नाही')]},

'D06-SW-003': {
  'expr': "MONTH IN [OCT, NOV] AND forecast_rain_48h_mm > 40",
  'note': 'Duplication group post_monsoon_cyclone_saturation. D07-CY-001 supersedes.',
  'tests': [({'current_month':10,'forecast_rain_48h_mm':60}, T, 'चक्रीवादळ'),
            ({'current_month':8,'forecast_rain_48h_mm':60}, F, 'मान्सून')]},

# ===========================================================================
# D07 — Weather. Twenty-two rules, almost entirely station-driven.
# ===========================================================================

'D07-TM-001': {
  'expr': "air_temp_max_c > 35 AND STAGE IN [G0, G1]",
  'tests': [({'air_temp_max_c':40,'current_stage':'G1'}, T, 'उगवणीत उष्णता'),
            ({'air_temp_max_c':30,'current_stage':'G1'}, F, '')]},

'D07-CY-WX-001': {
  'expr': "rainfall_24h_mm >= 75 OR wind_gust_kmph >= 40",
  'note': 'AGRO_GUARDIAN_CUSTOM_OPERATIONAL_RULE (VJH-V1.0 section 8). Sibling to D07-CY-001; rain-OR-wind operational trigger, not the calendar rule. Not an IMD warning.',
  'tests': [({'rainfall_24h_mm':74.9,'wind_gust_kmph':20}, F, 'पाऊस मर्यादेखाली'),
            ({'rainfall_24h_mm':75.0,'wind_gust_kmph':20}, T, 'पाऊस मर्यादेवर'),
            ({'rainfall_24h_mm':75.1,'wind_gust_kmph':20}, T, 'पाऊस मर्यादेवर'),
            ({'rainfall_24h_mm':30,'wind_gust_kmph':39.9}, F, 'वारा मर्यादेखाली'),
            ({'rainfall_24h_mm':30,'wind_gust_kmph':40.0}, T, 'वारा मर्यादेवर'),
            ({'rainfall_24h_mm':30,'wind_gust_kmph':40.1}, T, 'वारा मर्यादेवर'),
            ({}, U, 'दोन्ही अनुपलब्ध — गृहीत धरू नये'),
            ({'wind_gust_kmph':45.0}, T, 'फक्त वारा'),
            ({'rainfall_24h_mm':80.0}, T, 'फक्त पाऊस')]},

'D07-TM-002': {
  'expr': "air_temp_min_c < 12 AND STAGE IN [G4]",
  'note': 'The Marathwada winter suits bulking, but a cold snap still slows it.',
  'tests': [({'air_temp_min_c':9,'current_stage':'G4'}, T, 'थंडीची लाट'),
            ({'air_temp_min_c':18,'current_stage':'G4'}, F, 'सामान्य')]},

'D07-TM-003': {
  'expr': "soil_temp_c > 32 AND STAGE IN [G1, G2]",
  'tests': [({'soil_temp_c':35,'current_stage':'G1'}, T, 'मातीचे तापमान जास्त'),
            ({'soil_temp_c':27,'current_stage':'G1'}, F, 'ठीक')]},

'D07-HS-001': {
  'expr': "air_temp_max_c > 35 AND STAGE IN [G0, G1]",
  'note': 'Expert amendment: lowered from 38 C, matching D01-TM-001.',
  'tests': [({'air_temp_max_c':37,'current_stage':'G0'}, T, 'उष्णता व्यवस्थापन'),
            ({'air_temp_max_c':33,'current_stage':'G0'}, F, '')]},

'D07-HS-002': {
  'expr': "heat_stress_days_count >= 3 AND STAGE IN [G1, G2, G3]",
  'tests': [({'heat_stress_days_count':4,'current_stage':'G2'}, T, 'सलग उष्णता'),
            ({'heat_stress_days_count':1,'current_stage':'G2'}, F, 'एकच दिवस')]},

'D07-HS-003': {
  'expr': "MONTH IN [OCT] AND heat_stress_days_count >= 3",
  'note': 'October heat after the monsoon withdraws. The action text names the month, so the trigger must too.',
  'tests': [({'current_month':10,'heat_stress_days_count':4}, T, 'ऑक्टोबरची उष्णता'),
            ({'current_month':4,'heat_stress_days_count':4}, F, 'एप्रिल — वेगळा नियम'),
            ({'current_month':10,'heat_stress_days_count':1}, F, 'एकच दिवस')]},

'D07-HS-004': {
  'expr': "air_temp_max_c > 35 OR forecast_rain_48h_mm > 5",
  'note': 'The spray suppressor. Suppresses D04-MC-001, D04-MC-002 and D05-CH-006.',
  'tests': [({'air_temp_max_c':39}, T, 'फवारणी दडपा'),
            ({'air_temp_max_c':29,'forecast_rain_48h_mm':0}, F, 'योग्य')]},

'D07-RF-002': {
  'expr': "rainfall_ytd_mm IS NOT NULL AND rainfall_deviation_pct < -25",
  'note': '55 percent of years fall below the long-term average here.',
  'tests': [({'rainfall_ytd_mm':420,'rainfall_deviation_pct':-32}, T, 'कमी पाऊस'),
            ({'rainfall_ytd_mm':700,'rainfall_deviation_pct':-5}, F, 'सामान्य')]},

'D07-RF-003': {
  'expr': "rainfall_mm > 60",
  'note': 'A single heavy day. Deduct from irrigation and check the channels.',
  'tests': [({'rainfall_mm':75}, T, 'मोठा पाऊस'),
            ({'rainfall_mm':20}, F, 'सामान्य')]},

'D07-MO-002': {
  'expr': "dry_spell_days >= 7 AND STAGE IN [G3, G4]",
  'note': 'Duplication group critical_stage_moisture_stress.',
  'tests': [({'dry_spell_days':9,'current_stage':'G3'}, T, 'निर्णायक ताण'),
            ({'dry_spell_days':9,'current_stage':'G2'}, F, '')]},

'D07-MO-003': {
  'expr': "MONTH IN [SEP, OCT] AND dry_spell_days >= 10",
  'note': 'Monsoon withdrawal. The well has to carry the crop from here.',
  'tests': [({'current_month':10,'dry_spell_days':12}, T, 'पाऊस संपला'),
            ({'current_month':7,'dry_spell_days':12}, F, 'मान्सूनमध्ये खंड')]},

'D07-HU-002': {
  'expr': "leaf_wetness_hours > 8 AND MONTH IN [DEC, JAN, FEB]",
  'note': 'Winter fog is the second disease season — foliar, not soil-borne.',
  'tests': [({'leaf_wetness_hours':11,'current_month':1}, T, 'पाने ओली राहतात'),
            ({'leaf_wetness_hours':2,'current_month':1}, F, 'कोरडी'),
            ({'leaf_wetness_hours':11,'current_month':8}, F, 'हंगामाबाहेर')]},

'D07-HU-003': {
  'expr': "DURATION(rh_pct > 80) > 72 HOURS AND MONTH IN [JUL, AUG, SEP, OCT]",
  'tests': [({'rh_pct__duration':80,'current_month':9}, T, 'कीड-दाब वाढला'),
            ({'rh_pct__duration':20,'current_month':9}, F, 'कमी कालावधी')]},

'D07-HU-004': {
  'expr': "(fog_observed IS TRUE AND MONTH IN [DEC, JAN, FEB]) OR (saturation_hours > 12 AND MONTH IN [JUL, AUG, SEP])",
  'note': 'Two disease seasons with different mechanisms — soil-borne in monsoon, foliar in winter fog.',
  'tests': [({'fog_observed':True,'current_month':1}, T, 'हिवाळी हंगाम'),
            ({'saturation_hours':14,'current_month':8}, T, 'पावसाळी हंगाम'),
            ({'fog_observed':False,'saturation_hours':2,'current_month':4}, F, 'दोन्ही नाही')]},

'D07-CY-002': {
  'expr': "MONTH IN [OCT, NOV] AND STAGE IN [G3, G4]",
  'tests': [({'current_month':11,'current_stage':'G4'}, T, 'चर तपासा'),
            ({'current_month':11,'current_stage':'G2'}, F, '')]},

'D07-WS-001': {
  'expr': "wind_speed_ms > 8",
  'tests': [({'wind_speed_ms':11}, T, 'जोराचा वारा'),
            ({'wind_speed_ms':3}, F, 'सौम्य')]},

'D07-WS-002': {
  'expr': "wind_speed_ms > 5 AND air_temp_max_c > 33",
  'note': 'Wind plus heat raises transpiration faster than either alone.',
  'tests': [({'wind_speed_ms':7,'air_temp_max_c':36}, T, 'बाष्पोत्सर्जन वाढले'),
            ({'wind_speed_ms':7,'air_temp_max_c':28}, F, 'थंड')]},

'D07-WS-003': {
  'expr': "wind_speed_ms > 4 AND forecast_rain_48h_mm < 2",
  'note': 'Spray drift. Not a suppressor, a timing note.',
  'tests': [({'wind_speed_ms':6,'forecast_rain_48h_mm':0}, T, 'फवारणी सकाळी करा'),
            ({'wind_speed_ms':2,'forecast_rain_48h_mm':0}, F, 'शांत')]},

'D07-WS-004': {
  'expr': "station_data_age_hours > 24",
  'note': 'The station is down. Fall back to the regional forecast and say so.',
  'tests': [({'station_data_age_hours':40}, T, 'station बंद'),
            ({'station_data_age_hours':2}, F, 'चालू'),
            ({}, U, 'माहिती नाही')]},

'D07-RF-004': {
  'expr': "rainfall_deviation_pct < -25 AND rainfall_ytd_mm IS NOT NULL",
  'note': 'Below the expected accumulation. Reduce area rather than water per acre.',
  'tests': [({'rainfall_ytd_mm':400,'rainfall_deviation_pct':-33}, T, 'हंगाम कोरडा'),
            ({'rainfall_ytd_mm':700,'rainfall_deviation_pct':-8}, F, 'सामान्य')]},

'D07-RF-005': {
  'expr': "rainfall_mm > 2 AND percolation_class IS NOT NULL",
  'note': 'Effective rainfall, not gross. On heavy soil with poor percolation, much of it runs off.',
  'tests': [({'rainfall_mm':25,'percolation_class':'moderate'}, T, 'प्रभावी पाऊस काढा'),
            ({'rainfall_mm':0.5,'percolation_class':'moderate'}, F, 'नगण्य')]},

'D07-MO-004': {
  'expr': "rainfall_mm > 20 AND STAGE IN [G2, G3] AND drainage_levels_present < 3",
  'tests': [({'rainfall_mm':40,'current_stage':'G2','drainage_levels_present':2}, T, 'निचरा अपूर्ण'),
            ({'rainfall_mm':40,'current_stage':'G2','drainage_levels_present':3}, F, 'पूर्ण')]},

'D07-BC-001': {
  'expr': "bias_observation_count >= 30",
  'note': 'The bias correction flywheel. Thirty paired observations make the local correction meaningful.',
  'tests': [({'bias_observation_count':45}, T, 'सुधारणा लागू करा'),
            ({'bias_observation_count':10}, F, 'अजून पुरेशी नाहीत')]},

'D07-BC-002': {
  'expr': "forecast_bias_correction_mm IS NOT NULL",
  'tests': [({'forecast_bias_correction_mm':-4.2}, T, 'सुधारणा उपलब्ध'),
            ({}, F, 'अजून नाही')]},

'D07-CL-002': {
  'expr': "agro_climatic_zone IS NULL",
  'tests': [({}, T, 'विभाग निश्चित नाही'),
            ({'agro_climatic_zone':'marathwada_western'}, F, 'निश्चित')]},

'D07-CC-003': {
  'expr': "rainfall_ytd_mm IS NOT NULL AND season_water_plan_basis IS NULL",
  'note': 'Any historical average cited without stating the plan basis is misleading here.',
  'tests': [({'rainfall_ytd_mm':600}, T, 'नियोजनाचा आधार सांगा'),
            ({'rainfall_ytd_mm':600,'season_water_plan_basis':'poor_year'}, F, 'सांगितला')]},

'D07-BC-003': {
  'expr': "bias_observation_count < 30 AND bias_observation_count > 0",
  'tests': [({'bias_observation_count':12}, T, 'जमा होत आहेत'),
            ({'bias_observation_count':45}, F, 'पुरेशी')]},

# ===========================================================================
# D08 — Operations
# ===========================================================================

'D08-WD-003': {
  'expr': "dap BETWEEN 25 AND 60 AND weeding_count < 2",
  'note': 'Heavy FYM brings weed seed. More weeding means more chance of rhizome injury.',
  'tests': [({'dap':40,'weeding_count':0}, T, 'खुरपणी'),
            ({'dap':40,'weeding_count':3}, F, 'पुरेशा')]},

'D08-GR-001': {
  'expr': "dap BETWEEN 58 AND 78 AND earthing_up_date IS NOT NULL AND mulch_stage_2_done IS TRUE",
  'note': 'Optional enhancement. Only surfaced once the basic operations are complete.',
  'tests': [({'dap':70,'earthing_up_date':'done','mulch_stage_2_done':True}, T, 'ऐच्छिक सुधारणा'),
            ({'dap':70,'mulch_stage_2_done':True}, F, 'उटाळणी बाकी')]},

'D08-IC-003': {
  'expr': "target_product == 'dry_ginger' AND shade_pct IS NULL",
  'note': 'Excess sunlight reduces aroma, which is the main quality determinant for dry ginger.',
  'tests': [({'target_product':'dry_ginger'}, T, 'सावलीचा विचार'),
            ({'target_product':'green','shade_pct':0}, F, 'हिरवे आले')]},

'D08-BN-001': {
  'expr': "dap IN [0, 82, 120]",
  'note': 'The farmer visits the field once. Three notifications on three days produce three ignored notifications.',
  'tests': [({'dap':82}, T, 'गुच्छ दिवस'),
            ({'dap':95}, F, 'सामान्य दिवस')]},

'D08-LB-001': {
  'expr': "dap BETWEEN 58 AND 64 AND labour_arranged_date IS NULL",
  'tests': [({'dap':60}, T, 'मजूर ठरवा'),
            ({'dap':60,'labour_arranged_date':'set'}, F, 'ठरले')]},

# ===========================================================================
# D09 — Harvest
# ===========================================================================

'D09-MT-003': {
  'expr': "harvest_route == 'seed_rhizome' AND skin_scrape_result == 'peels_easily'",
  'tests': [({'harvest_route':'seed_rhizome','skin_scrape_result':'peels_easily'}, T, 'अपक्व बेणे'),
            ({'harvest_route':'seed_rhizome','skin_scrape_result':'firmly_attached'}, F, 'पक्व')]},

'D09-HV-004': {
  'expr': "days_to_harvest BETWEEN 0 AND 2 AND air_temp_max_c > 33",
  'note': 'Early morning harvest. Rhizomes are cooler and the crew works in less heat.',
  'tests': [({'days_to_harvest':1,'air_temp_max_c':36}, T, 'सकाळी काढा'),
            ({'days_to_harvest':1,'air_temp_max_c':27}, F, 'थंड')]},

'D09-ST-003': {
  'expr': "drying_method IS NOT NULL AND moisture_pct_final > 10",
  'tests': [({'drying_method':'simple_sun','moisture_pct_final':14}, T, 'अजून वाळवा'),
            ({'drying_method':'simple_sun','moisture_pct_final':9}, F, 'साठवण्यायोग्य')]},

# ===========================================================================
# D13 — Economics
# ===========================================================================

'D13-RP-003': {
  'expr': "dap BETWEEN 178 AND 184 AND seed_retained_or_purchased IS NULL",
  'note': 'Seed selection is a mid-season observation task disguised as a post-harvest one.',
  'tests': [({'dap':180}, T, 'बेणे खुणावा'),
            ({'dap':180,'seed_retained_or_purchased':'retained'}, F, 'ठरले')]},

'D13-RR-002': {
  'expr': "harvest_date IS NOT NULL AND action_compliance_rate IS NOT NULL",
  'note': 'Four avoidable risks worth Rs 50,000 to a lakh per acre, all depending on a timely reminder.',
  'tests': [({'harvest_date':'done','action_compliance_rate':78}, T, 'हंगामाचा आढावा'),
            ({'harvest_date':'done'}, F, 'दर मोजलेला नाही')]},

'D13-RR-004': {
  'expr': "days_to_planting BETWEEN 140 AND 160 AND seed_supplier_identified IS FALSE",
  'note': 'Duplication group with D10-VAR-001 — same action, one message.',
  'tests': [({'days_to_planting':150,'seed_supplier_identified':False}, T, 'बेणे मागवा'),
            ({'days_to_planting':150,'seed_supplier_identified':True}, F, 'मागवले')]},
}
