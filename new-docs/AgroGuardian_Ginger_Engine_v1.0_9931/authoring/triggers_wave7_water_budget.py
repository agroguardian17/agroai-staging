#!/usr/bin/env python3
"""Wave 7 - Water Budget engine rules (9). Dormant until compute_water_budget() + geometry land."""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W7 = {

'D03-WB-001': {
  'expr': "stage_water_deficit_ratio > 0.25 AND days_since_last_irrigation >= 2 AND vwc_status != 'saturated'",
  'tests': [({'stage_water_deficit_ratio': 0.3, 'days_since_last_irrigation': 3, 'vwc_status': 'low'}, T, 'moderate deficit - irrigate'),
            ({'stage_water_deficit_ratio': 0.3, 'days_since_last_irrigation': 3, 'vwc_status': 'saturated'}, F, 'saturated - VWC veto')]},

'D03-WB-002': {
  'expr': "((STAGE IN [G3] AND stage_water_deficit_ratio > 0.40) OR (STAGE IN [G2, G4] AND stage_water_deficit_ratio > 0.50)) AND vwc_status != 'saturated'",
  'tests': [({'current_stage': 'G3', 'stage_water_deficit_ratio': 0.45, 'vwc_status': 'low'}, T, 'G3 severe deficit - RED'),
            ({'current_stage': 'G2', 'stage_water_deficit_ratio': 0.45, 'vwc_status': 'low'}, F, 'G2 below 0.50 threshold')]},

'D03-WB-003': {
  'expr': "per_plant_dose_l_last_event > variety_max_per_event_l AND current_stage != 'G5'",
  'tests': [({'per_plant_dose_l_last_event': 5.0, 'variety_max_per_event_l': 4.0, 'current_stage': 'G3'}, T, 'over max per-event'),
            ({'per_plant_dose_l_last_event': 3.5, 'variety_max_per_event_l': 4.0, 'current_stage': 'G3'}, F, 'within max')]},

'D03-WB-004': {
  'expr': "per_plant_dose_l_last_event < variety_min_per_event_l AND days_since_last_irrigation <= 1 AND STAGE IN [G2, G3, G4] AND vwc_status != 'saturated'",
  'tests': [({'per_plant_dose_l_last_event': 0.5, 'variety_min_per_event_l': 1.5, 'days_since_last_irrigation': 1, 'current_stage': 'G3', 'vwc_status': 'low'}, T, 'under-dose - supplement'),
            ({'per_plant_dose_l_last_event': 2.0, 'variety_min_per_event_l': 1.5, 'days_since_last_irrigation': 1, 'current_stage': 'G3', 'vwc_status': 'low'}, F, 'adequate dose')]},

'D03-WB-005': {
  'expr': 'dap > 0 AND per_plant_water_stage_cumulative_l IS NOT NULL',
  'tests': [({'dap': 100, 'per_plant_water_stage_cumulative_l': 150.0}, T, 'daily cumulative log (silent)'),
            ({'dap': 100}, F, 'no cumulative yet')]},

'D03-WB-006': {
  'expr': 'days_since_last_flow_reading > 3 AND flow_telemetry_field_exists IS TRUE',
  'tests': [({'days_since_last_flow_reading': 4, 'flow_telemetry_field_exists': True}, T, 'flow sensor silent'),
            ({'days_since_last_flow_reading': 2, 'flow_telemetry_field_exists': True}, F, 'recent reading')]},

'D03-WB-007': {
  'expr': 'per_plant_cumulative_vs_lifecycle_ratio > 1.20 AND dap >= 100',
  'tests': [({'per_plant_cumulative_vs_lifecycle_ratio': 1.25, 'dap': 180}, T, 'season over-irrigation'),
            ({'per_plant_cumulative_vs_lifecycle_ratio': 1.1, 'dap': 180}, F, 'within season budget')]},

'D03-WB-008': {
  'expr': 'dap < 0 AND planting_geometry_incomplete IS TRUE',
  'tests': [({'dap': -5, 'planting_geometry_incomplete': True}, T, 'geometry incomplete pre-plant'),
            ({'dap': -5, 'planting_geometry_incomplete': False}, F, 'geometry complete')]},

'D03-ST-001': {
  'expr': 'dap > 60 AND stage_water_deficit_ratio IS NOT NULL',
  'tests': [({'dap': 100, 'stage_water_deficit_ratio': 0.3}, T, 'factor-7 deficit log (silent)'),
            ({'dap': 40, 'stage_water_deficit_ratio': 0.3}, F, 'before DAP 60')]},
}
