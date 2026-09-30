#!/usr/bin/env python3
"""Wave 6 - Batches 3-9 firing-intent rules (36). All dormant until fields are sourced."""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W6 = {

'D04-BI-002': {
  'expr': 'biological_input_date IS NOT NULL AND chemical_input_date IS NOT NULL AND biological_input_date == chemical_input_date',
  'tests': [({'biological_input_date': '2026-06-10', 'chemical_input_date': '2026-06-10'}, T, 'same day - warn'),
            ({'biological_input_date': '2026-06-10', 'chemical_input_date': '2026-06-12'}, F, 'different days - ok')]},

'D04-DG-002': {
  'expr': "leaf_yellowing_pattern == 'interveinal_new' AND scout_report_days_ago <= 3",
  'tests': [({'leaf_yellowing_pattern': 'interveinal_new', 'scout_report_days_ago': 2}, T, 'interveinal new - Fe/Zn'),
            ({'leaf_yellowing_pattern': 'uniform', 'scout_report_days_ago': 2}, F, 'uniform - not micronutrient')]},

'D04-SN-001': {
  'expr': 'basal_planning_active IS TRUE AND dap IS NULL',
  'tests': [({'basal_planning_active': True}, T, 'pre-plant basal planning'),
            ({'basal_planning_active': True, 'dap': 5}, F, 'planting past')]},

'D05-CH-002': {
  'expr': 'chemical_option_about_to_be_shown IS TRUE',
  'tests': [({'chemical_option_about_to_be_shown': True}, T, 'run IPM+diagnosis+CIBRC checks'),
            ({'chemical_option_about_to_be_shown': False}, F, 'no chemical pending')]},

'D05-IP-001': {
  'expr': 'pest_recommendation_pending IS TRUE',
  'tests': [({'pest_recommendation_pending': True}, T, 'inject IPM priority'),
            ({'pest_recommendation_pending': False}, F, 'no pest rec pending')]},

'D05-PC-001': {
  'expr': 'pest_planning_active IS TRUE AND dap < 0',
  'tests': [({'pest_planning_active': True, 'dap': -10}, T, 'pre-plant pest calendar'),
            ({'pest_planning_active': True, 'dap': 10}, F, 'past pre-plant window')]},

'D05-SC-002': {
  'expr': "pest_count > provisional_threshold AND threshold_source == 'EST'",
  'tests': [({'pest_count': 15, 'provisional_threshold': 10, 'threshold_source': 'EST'}, T, 'over provisional ETL'),
            ({'pest_count': 15, 'threshold_source': 'A'}, F, 'calibrated source - no warning')]},

'D10-ACT-002': {
  'expr': 'institutional_contact_made IS TRUE',
  'tests': [({'institutional_contact_made': True}, T, 'log institutional contact'),
            ({'institutional_contact_made': False}, F, 'no contact')]},

'D10-APP-001': {
  'expr': 'subsidy_application_pending IS TRUE AND subsidy_documents_ready IS FALSE',
  'tests': [({'subsidy_application_pending': True, 'subsidy_documents_ready': False}, T, 'activate doc checklist'),
            ({'subsidy_application_pending': True, 'subsidy_documents_ready': True}, F, 'docs ready')]},

'D10-CROP-002': {
  'expr': 'local_experience_sought IS TRUE',
  'tests': [({'local_experience_sought': True}, T, 'connect VNMKV/KVK'),
            ({'local_experience_sought': False}, F, 'not sought')]},

'D10-REG-001': {
  'expr': 'chemical_recommendation_pending IS TRUE AND cibrc_verified IS FALSE',
  'tests': [({'chemical_recommendation_pending': True, 'cibrc_verified': False}, T, 'block until CIBRC verified'),
            ({'chemical_recommendation_pending': True, 'cibrc_verified': True}, F, 'permitted')]},

'D11-GA-001': {
  'expr': 'harvest_complete IS TRUE AND actual_yield_recorded IS TRUE',
  'tests': [({'harvest_complete': True, 'actual_yield_recorded': True}, T, 'kick off gap-attribution'),
            ({'harvest_complete': True, 'actual_yield_recorded': False}, F, 'yield not recorded')]},

'D11-GA-002': {
  'expr': 'season_starting IS TRUE AND season_record_complete IS FALSE',
  'tests': [({'season_starting': True, 'season_record_complete': False}, T, 'prior season incomplete'),
            ({'season_starting': True, 'season_record_complete': True}, F, 'prior season complete')]},

'D11-GA-003': {
  'expr': 'gap_attribution_complete IS TRUE AND gap_unexplained_pct > 25',
  'tests': [({'gap_attribution_complete': True, 'gap_unexplained_pct': 30}, T, '>25% unexplained - escalate'),
            ({'gap_attribution_complete': True, 'gap_unexplained_pct': 15}, F, 'within tolerance')]},

'D11-RC-002': {
  'expr': 'saturation_event_occurred IS TRUE OR moisture_stress_period_started IS TRUE',
  'tests': [({'saturation_event_occurred': True}, T, 'log water event'),
            ({'saturation_event_occurred': False, 'moisture_stress_period_started': False}, F, 'no event')]},

'D11-RC-003': {
  'expr': 'scheduled_operation_completed IS TRUE OR scheduled_operation_missed IS TRUE',
  'tests': [({'scheduled_operation_completed': True}, T, 'log op status'),
            ({'scheduled_operation_completed': False, 'scheduled_operation_missed': False}, F, 'no status')]},

'D11-SC-001': {
  'expr': 'preseason_planning IS TRUE AND yield_expectation_requested IS TRUE',
  'tests': [({'preseason_planning': True, 'yield_expectation_requested': True}, T, 'yield expectation'),
            ({'preseason_planning': True, 'yield_expectation_requested': False}, F, 'not requested')]},

'D11-SC-002': {
  'expr': 'season_omissions_recorded IS TRUE',
  'tests': [({'season_omissions_recorded': True}, T, 'project omission loss'),
            ({'season_omissions_recorded': False}, F, 'none')]},

'D11-SC-003': {
  'expr': 'disease_event_recorded_in_season IS TRUE',
  'tests': [({'disease_event_recorded_in_season': True}, T, 'update forecast'),
            ({'disease_event_recorded_in_season': False}, F, 'none')]},

'D09-DR-001': {
  'expr': "processing_route == 'dry_ginger'",
  'tests': [({'processing_route': 'dry_ginger'}, T, 'dry-ginger route'),
            ({'processing_route': 'fresh_market'}, F, 'fresh market')]},

'D09-DR-002': {
  'expr': 'skin_removal_in_progress IS TRUE',
  'tests': [({'skin_removal_in_progress': True}, T, 'skin removal QC'),
            ({'skin_removal_in_progress': False}, F, 'not in progress')]},

'D09-DR-003': {
  'expr': 'drying_in_progress IS TRUE AND local_hour >= 16',
  'tests': [({'drying_in_progress': True, 'local_hour': 17}, T, 'evening - cover'),
            ({'drying_in_progress': True, 'local_hour': 10}, F, 'mid-morning')]},

'D09-PW-001': {
  'expr': "value_addition_being_considered IS TRUE AND processing_route == 'dry_ginger'",
  'tests': [({'value_addition_being_considered': True, 'processing_route': 'dry_ginger'}, T, 'value addition'),
            ({'value_addition_being_considered': True, 'processing_route': 'fresh_market'}, F, 'fresh route')]},

'D09-SL-003': {
  'expr': 'fresh_price_crashed IS TRUE OR fresh_share_low IS TRUE',
  'tests': [({'fresh_price_crashed': True}, T, 'price crash - consider dry'),
            ({'fresh_price_crashed': False, 'fresh_share_low': False}, F, 'no signal')]},

'D09-ST-002': {
  'expr': 'dry_ginger_in_storage IS TRUE AND storage_loss_monthly_pct IS NULL',
  'tests': [({'dry_ginger_in_storage': True}, T, 'log monthly loss'),
            ({'dry_ginger_in_storage': True, 'storage_loss_monthly_pct': 1.5}, F, 'logged')]},

'D09-YD-002': {
  'expr': 'actual_yield_recorded IS TRUE',
  'tests': [({'actual_yield_recorded': True}, T, 'attribution trigger'),
            ({'actual_yield_recorded': False}, F, 'not recorded')]},

'D09-YD-003': {
  'expr': 'dry_ginger_produced IS TRUE',
  'tests': [({'dry_ginger_produced': True}, T, 'record dry ratio'),
            ({'dry_ginger_produced': False}, F, 'not produced')]},

'D09-YD-004': {
  'expr': 'harvest_complete IS TRUE',
  'tests': [({'harvest_complete': True}, T, 'log fresh yield'),
            ({'harvest_complete': False}, F, 'not harvested')]},

'D12-AL-001': {
  'expr': 'action_not_recorded_within_3days IS TRUE',
  'tests': [({'action_not_recorded_within_3days': True}, T, 'ask why no action'),
            ({'action_not_recorded_within_3days': False}, F, 'recorded')]},

'D12-AL-002': {
  'expr': 'low_confidence_decision IS TRUE OR unexpected_outcome IS TRUE OR symptom_diagnosis_pending IS TRUE',
  'tests': [({'low_confidence_decision': True}, T, 'escalate to agronomist'),
            ({'low_confidence_decision': False, 'unexpected_outcome': False, 'symptom_diagnosis_pending': False}, F, 'none')]},

'D12-IMG-001': {
  'expr': 'season_number <= 2 AND photo_submitted IS TRUE',
  'tests': [({'season_number': 1, 'photo_submitted': True}, T, 'enqueue for labelling'),
            ({'season_number': 3, 'photo_submitted': True}, F, 'past priority window')]},

'D12-LOG-002': {
  'expr': 'durable_fact_learned_in_conversation IS TRUE',
  'tests': [({'durable_fact_learned_in_conversation': True}, T, 'append to profile'),
            ({'durable_fact_learned_in_conversation': False}, F, 'none')]},

'D12-VOC-002': {
  'expr': 'local_terminology_used IS TRUE AND differs_from_standard_marathi IS TRUE',
  'tests': [({'local_terminology_used': True, 'differs_from_standard_marathi': True}, T, 'append to glossary'),
            ({'local_terminology_used': True, 'differs_from_standard_marathi': False}, F, 'standard term')]},

'D01-PH-005': {
  'expr': 'dap == 35 AND emergence_observed IS NULL',
  'tests': [({'dap': 35}, T, 'DAP 35 - prompt emergence'),
            ({'dap': 35, 'emergence_observed': 'full'}, F, 'recorded')]},

'D03-SB-004': {
  'expr': 'hardware_upgrade_pending IS TRUE',
  'tests': [({'hardware_upgrade_pending': True}, T, 'suspend moisture advisory'),
            ({'hardware_upgrade_pending': False}, F, 'no upgrade')]},

'D03-WS-002': {
  'expr': "water_supply_status == 'marginal' AND month IN [MAR, APR, MAY]",
  'tests': [({'water_supply_status': 'marginal', 'current_month': 4}, T, 'summer marginal water'),
            ({'water_supply_status': 'marginal', 'current_month': 1}, F, 'outside summer')]},
}
