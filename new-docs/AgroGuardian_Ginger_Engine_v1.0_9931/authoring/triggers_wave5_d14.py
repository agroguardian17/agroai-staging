#!/usr/bin/env python3
"""
Wave 5 — Domain 14 (Satellite & Remote Sensing Intelligence), additive.

Forty-seven triggers added across NV, NR, NM, SR, LT, PH, AN, FU, PL, POS, DP.
Purpose is to give the authoring surface (used by test_runtime_loader.py to
compare against the knowledge base) the same 47 expressions that Domain 14
now carries in JSON.

Runtime does not read this file — production loads rules from the database
(architecture §11A). This file exists so that regression_gate.py stops
reporting a build-vs-KB drift after the D14 patch.

Discipline held throughout:
  - Zero SUPPRESSES / SUPERSEDES anywhere. Satellite never silences an
    agronomic domain.
  - The three D14→D03 BUNDLES entries (NM-003, LT-003, FU-002) supply
    confidence tags to D03-SC-001 rather than emit farmer messages.
  - The two D14→D06 SEQUENCES entries (NV-004, SR-002) stage the
    differential-diagnosis branch for the returning scout report.
  - Eight IMMUTABLE rules — seven POS prohibited-claim guards and one
    DPDP display guard (DP-001). Author estimates cannot lift these.
  - RAW MASTER Domain 14 (Phase 1, 17 Sep 2026) is the source document.
"""

T, F, U = 'TRUE', 'FALSE', 'UNKNOWN'

TRIGGERS_W5 = {

# ===========================================================================
# D14 — NV: NDVI / vegetation index (7 rules)
# ===========================================================================

'D14-NV-001': {
  'expr': "sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15",
  'note': ('Computation trigger. Populates ndvi_mean, ndvi_std, evi_mean, savi_mean, '
           'ndvi_freshness_days. SILENT_GUARD; no farmer message.'),
  'tests': [
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':72,'plot_cloud_pct':8}, T, 'clear scene'),
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':45,'plot_cloud_pct':8}, F, 'insufficient valid pixels'),
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':72,'plot_cloud_pct':25}, F, 'ढग जास्त'),
    ({'sat_source':None,'scene_valid_pixel_pct':72,'plot_cloud_pct':8}, U, 'source unknown'),
  ]},

'D14-NV-002': {
  'expr': "ndvi_freshness_days > 5 AND ndvi_freshness_days <= 20",
  'note': ('Confidence degradation. Linear ramp from 1.0 at day 5 to 0.0 at day 20. '
           'sat_advisory_confidence is set by pipeline; every downstream rule multiplies '
           'its base confidence by this scalar.'),
  'tests': [
    ({'ndvi_freshness_days':3}, F, 'ताजे — full confidence'),
    ({'ndvi_freshness_days':8}, T, 'मध्यम — degrade'),
    ({'ndvi_freshness_days':17}, T, 'शिळे — heavy degrade'),
    ({'ndvi_freshness_days':22}, F, 'खूप शिळे — PL-002 branch'),
    ({'ndvi_freshness_days':None}, U, 'freshness अज्ञात'),
  ]},

'D14-NV-003': {
  'expr': ("plot_ndvi_gap_regional < -0.10 AND scene_valid_pixel_pct >= 60 AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': 'Regional baseline anomaly. Investigation-only; requires double-signal to reach farmer message.',
  'tests': [
    ({'plot_ndvi_gap_regional':-0.14,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'clear anomaly'),
    ({'plot_ndvi_gap_regional':-0.07,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'noise band'),
    ({'plot_ndvi_gap_regional':-0.14,'scene_valid_pixel_pct':45,'sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'scene rejected'),
    ({'plot_ndvi_gap_regional':-0.14,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.30,'current_stage':'G3'}, F, 'confidence low'),
    ({'plot_ndvi_gap_regional':-0.14,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G1'}, F, 'wrong stage'),
  ]},

'D14-NV-004': {
  'expr': ("ndvi_delta_10d <= -0.15 AND scene_valid_pixel_pct >= 60 AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': 'Rapid decline — URGENT scout. SEQUENCES with D06-DX-001 for returning scout report.',
  'tests': [
    ({'ndvi_delta_10d':-0.18,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'urgent'),
    ({'ndvi_delta_10d':-0.08,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'हळू घसरण'),
    ({'ndvi_delta_10d':-0.25,'scene_valid_pixel_pct':50,'sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'scene bad'),
    ({'ndvi_delta_10d':-0.18,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G5'}, F, 'senescence'),
    ({'ndvi_delta_10d':None,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85,'current_stage':'G3'}, U, 'delta अज्ञात'),
  ]},

'D14-NV-005': {
  'expr': "plot_ndvi_gap_peer < -0.10 AND dap >= 60 AND sat_advisory_confidence >= 0.5",
  'note': 'Peer-cluster drift. Requires 3+ peer plots (gated by AN-001); DAP ≥ 60 for maturity.',
  'tests': [
    ({'plot_ndvi_gap_peer':-0.14,'dap':80,'sat_advisory_confidence':0.85}, T, 'peer gap'),
    ({'plot_ndvi_gap_peer':-0.06,'dap':80,'sat_advisory_confidence':0.85}, F, 'noise'),
    ({'plot_ndvi_gap_peer':-0.14,'dap':40,'sat_advisory_confidence':0.85}, F, 'लवकर आहे'),
    ({'plot_ndvi_gap_peer':None,'dap':80,'sat_advisory_confidence':0.85}, U, 'peer baseline नाही'),
  ]},

'D14-NV-006': {
  'expr': "days_to_planting BETWEEN 5 AND 30 AND ndvi_mean > 0.25 AND scene_valid_pixel_pct >= 60",
  'note': 'Pre-plant weed / residue check. Bare-soil NDVI in Kannad basalt is 0.10-0.20; >0.25 means green.',
  'tests': [
    ({'days_to_planting':15,'ndvi_mean':0.32,'scene_valid_pixel_pct':72}, T, 'weed flush'),
    ({'days_to_planting':15,'ndvi_mean':0.18,'scene_valid_pixel_pct':72}, F, 'clean field'),
    ({'days_to_planting':45,'ndvi_mean':0.32,'scene_valid_pixel_pct':72}, F, 'too early'),
    ({'days_to_planting':15,'ndvi_mean':0.32,'scene_valid_pixel_pct':45}, F, 'scene bad'),
  ]},

'D14-NV-007': {
  'expr': "nbr_delta_10d <= -0.20 AND scene_valid_pixel_pct >= 60",
  'note': 'Residue burning candidate. Compliance-only; NEVER shown as accusation to farmer.',
  'tests': [
    ({'nbr_delta_10d':-0.25,'scene_valid_pixel_pct':72}, T, 'burn scar'),
    ({'nbr_delta_10d':-0.10,'scene_valid_pixel_pct':72}, F, 'no burn'),
    ({'nbr_delta_10d':-0.25,'scene_valid_pixel_pct':45}, F, 'scene bad'),
  ]},

# ===========================================================================
# D14 — NR: NDRE / red-edge (3 rules)
# ===========================================================================

'D14-NR-001': {
  'expr': "sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15",
  'note': 'Compute NDRE and its 5-day slope. SILENT_GUARD.',
  'tests': [
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':72,'plot_cloud_pct':8}, T, 'compute'),
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':45,'plot_cloud_pct':8}, F, 'insufficient'),
    ({'sat_source':'sentinel-1','scene_valid_pixel_pct':72,'plot_cloud_pct':8}, F, 'SAR — no NDRE'),
  ]},

'D14-NR-002': {
  'expr': ("current_stage == 'G2' AND dap BETWEEN 40 AND 80 AND ndvi_delta_10d > 0.05 AND "
           "ndre_slope_5d < 0.005 AND sat_advisory_confidence >= 0.5"),
  'note': 'Volume-without-quality — canopy expanding but chlorophyll thin. Routes to D04 nitrogen check.',
  'tests': [
    ({'current_stage':'G2','dap':55,'ndvi_delta_10d':0.08,'ndre_slope_5d':0.002,'sat_advisory_confidence':0.85}, T, 'N stress'),
    ({'current_stage':'G2','dap':55,'ndvi_delta_10d':0.08,'ndre_slope_5d':0.012,'sat_advisory_confidence':0.85}, F, 'healthy'),
    ({'current_stage':'G3','dap':100,'ndvi_delta_10d':0.08,'ndre_slope_5d':0.002,'sat_advisory_confidence':0.85}, F, 'wrong stage'),
  ]},

'D14-NR-003': {
  'expr': "current_stage IN [G3, G4] AND plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5",
  'note': 'Closed-canopy NDRE gap. NDVI has saturated; NDRE is the sensitive nitrogen channel.',
  'tests': [
    ({'current_stage':'G3','plot_ndre_gap_regional':-0.13,'sat_advisory_confidence':0.85}, T, 'gap'),
    ({'current_stage':'G3','plot_ndre_gap_regional':-0.05,'sat_advisory_confidence':0.85}, F, 'small gap'),
    ({'current_stage':'G2','plot_ndre_gap_regional':-0.12,'sat_advisory_confidence':0.85}, F, 'लवकर — NR-002'),
  ]},

# ===========================================================================
# D14 — NM: NDMI / canopy moisture (3 rules)
# ===========================================================================

'D14-NM-001': {
  'expr': "sat_source == 'sentinel-2' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15",
  'note': 'Compute NDMI and 10-day delta. SILENT_GUARD.',
  'tests': [
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':72,'plot_cloud_pct':8}, T, 'compute'),
    ({'sat_source':'sentinel-2','scene_valid_pixel_pct':45,'plot_cloud_pct':8}, F, 'insufficient'),
  ]},

'D14-NM-002': {
  'expr': ("ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == 'adequate' AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': ('Non-water stress signature — leaves drying while soil wet. Investigation for '
           'drip clogging, pest, or root damage. §10.2 case A.'),
  'tests': [
    ({'ndmi_delta_10d':-0.12,'sub_node_moisture_status':'adequate','sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'non-water stress'),
    ({'ndmi_delta_10d':-0.12,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'water stress — NM-003'),
    ({'ndmi_delta_10d':-0.05,'sub_node_moisture_status':'adequate','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'small'),
    ({'ndmi_delta_10d':-0.12,'sub_node_moisture_status':'stale','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'stale — FU-001'),
  ]},

'D14-NM-003': {
  'expr': ("ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == 'low' AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': 'BUNDLES with D03-SC-001. Contributes canopy-moisture confirmation tag, not a separate message.',
  'tests': [
    ({'ndmi_delta_10d':-0.12,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'double signal'),
    ({'ndmi_delta_10d':-0.12,'sub_node_moisture_status':'adequate','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'handled NM-002'),
    ({'ndmi_delta_10d':-0.05,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'small NDMI'),
  ]},

# ===========================================================================
# D14 — SR: SAR / Sentinel-1 (5 rules)
# ===========================================================================

'D14-SR-001': {
  'expr': "sat_source == 'sentinel-1' AND sar_gap_days IS NOT NULL",
  'note': 'Compute VV, VH, RVI, delta_vv, coherence. SILENT_GUARD.',
  'tests': [
    ({'sat_source':'sentinel-1','sar_gap_days':3}, T, 'compute'),
    ({'sat_source':'sentinel-2','sar_gap_days':3}, F, 'optical'),
    ({'sat_source':'sentinel-1','sar_gap_days':None}, F, 'gap अज्ञात — IS NOT NULL returns FALSE'),
  ]},

'D14-SR-002': {
  'expr': "sar_vv_delta_db < -4.0 AND rainfall_last_48h_mm > 20 AND sar_gap_days <= 12",
  'note': ('URGENT standing-water detection — cloud-independent. SEQUENCES with D06-SW-003 '
           'for post-monsoon rot risk assessment.'),
  'tests': [
    ({'sar_vv_delta_db':-5.5,'rainfall_last_48h_mm':45,'sar_gap_days':6}, T, 'drainage failure'),
    ({'sar_vv_delta_db':-5.5,'rainfall_last_48h_mm':5,'sar_gap_days':6}, F, 'no rain'),
    ({'sar_vv_delta_db':-2.0,'rainfall_last_48h_mm':45,'sar_gap_days':6}, F, 'noise band'),
    ({'sar_vv_delta_db':-5.5,'rainfall_last_48h_mm':45,'sar_gap_days':20}, F, 'SAR शिळे'),
  ]},

'D14-SR-003': {
  'expr': ("sar_coherence < 0.4 AND STAGE IN [G4, G5] AND rainfall_last_48h_mm < 20 AND "
           "sar_gap_days <= 12"),
  'note': 'Probable harvest activity in late stage. LOW priority; farmer confirmation closes.',
  'tests': [
    ({'sar_coherence':0.25,'current_stage':'G5','rainfall_last_48h_mm':5,'sar_gap_days':6}, T, 'harvest?'),
    ({'sar_coherence':0.25,'current_stage':'G3','rainfall_last_48h_mm':5,'sar_gap_days':6}, F, 'wrong stage'),
    ({'sar_coherence':0.25,'current_stage':'G5','rainfall_last_48h_mm':45,'sar_gap_days':6}, F, 'rain explains'),
    ({'sar_coherence':0.75,'current_stage':'G5','rainfall_last_48h_mm':5,'sar_gap_days':6}, F, 'high coherence'),
  ]},

'D14-SR-004': {
  'expr': ("(sar_vv_delta_db > 2.0 OR sar_vv_delta_db < -2.0) AND rainfall_last_48h_mm >= 10 AND "
           "sar_gap_days <= 12"),
  'note': 'Rainfall-on-plot confirmation. Tags D07 rainfall with confidence flag.',
  'tests': [
    ({'sar_vv_delta_db':3.5,'rainfall_last_48h_mm':25,'sar_gap_days':6}, T, 'wetting event'),
    ({'sar_vv_delta_db':-3.0,'rainfall_last_48h_mm':15,'sar_gap_days':6}, T, 'drying event'),
    ({'sar_vv_delta_db':1.5,'rainfall_last_48h_mm':25,'sar_gap_days':6}, F, 'within noise'),
  ]},

'D14-SR-005': {
  'expr': "optical_gap_days > 14 AND sar_gap_days <= 6",
  'note': 'Monsoon SAR-only mode. Suppresses optical-dependent rules; SR rules stay active.',
  'tests': [
    ({'optical_gap_days':18,'sar_gap_days':5}, T, 'SAR-only'),
    ({'optical_gap_days':8,'sar_gap_days':5}, F, 'optical fresh'),
    ({'optical_gap_days':18,'sar_gap_days':15}, F, 'दोन्ही शिळे — PL-002'),
  ]},

# ===========================================================================
# D14 — LT: Landsat LST / CWSI (3 rules)
# ===========================================================================

'D14-LT-001': {
  'expr': "sat_source IN ['landsat-8', 'landsat-9'] AND air_temp_max_c IS NOT NULL",
  'note': 'Compute lst_c and CWSI via Idso formulation with Phase-1 baselines. SILENT_GUARD.',
  'tests': [
    ({'sat_source':'landsat-9','air_temp_max_c':32}, T, 'compute'),
    ({'sat_source':'sentinel-2','air_temp_max_c':32}, F, 'wrong sensor'),
    ({'sat_source':'landsat-9','air_temp_max_c':None}, F, 'हवा तापमान गहाळ — IS NOT NULL returns FALSE'),
  ]},

'D14-LT-002': {
  'expr': ("cwsi > 0.60 AND sub_node_moisture_status == 'adequate' AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': 'Thermal non-water stress. Same investigation branch as NM-002; do not open duplicate task.',
  'tests': [
    ({'cwsi':0.72,'sub_node_moisture_status':'adequate','sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'thermal non-water'),
    ({'cwsi':0.72,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'water stress — LT-003'),
    ({'cwsi':0.35,'sub_node_moisture_status':'adequate','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'सौम्य'),
  ]},

'D14-LT-003': {
  'expr': ("cwsi > 0.60 AND sub_node_moisture_status == 'low' AND "
           "sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]"),
  'note': 'BUNDLES with D03-SC-001. Thermal confirmation tag; no separate farmer message.',
  'tests': [
    ({'cwsi':0.72,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, T, 'thermal confirms'),
    ({'cwsi':0.35,'sub_node_moisture_status':'low','sat_advisory_confidence':0.85,'current_stage':'G3'}, F, 'सौम्य'),
  ]},

# ===========================================================================
# D14 — PH: Phenology (4 rules)
# ===========================================================================

'D14-PH-001': {
  'expr': "dap >= 60 AND ndvi_freshness_days <= 20",
  'note': 'Fit double-logistic curve; store estimated stage-transition dates.',
  'tests': [
    ({'dap':75,'ndvi_freshness_days':6}, T, 'fit करा'),
    ({'dap':40,'ndvi_freshness_days':6}, F, 'लवकर'),
    ({'dap':75,'ndvi_freshness_days':25}, F, 'शिळे'),
  ]},

'D14-PH-002': {
  'expr': "dap >= 60 AND ndvi_freshness_days <= 20",
  'note': ('Cross-check curve-fitted stage vs DAP-derived stage. If differ ≥ 1 step, '
           'verify planting date with farmer via D01.'),
  'tests': [
    ({'dap':100,'ndvi_freshness_days':6}, T, 'cross-check'),
    ({'dap':50,'ndvi_freshness_days':6}, F, 'लवकर'),
  ]},

'D14-PH-003': {
  'expr': ("current_stage == 'G3' AND ndvi_mean < 0.60 AND scene_valid_pixel_pct >= 60 AND "
           "sat_advisory_confidence >= 0.5"),
  'note': 'Peak NDVI undershooting healthy band. Fires D04/D02/D03/D06 differential.',
  'tests': [
    ({'current_stage':'G3','ndvi_mean':0.52,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85}, T, 'below band'),
    ({'current_stage':'G3','ndvi_mean':0.68,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85}, F, 'in band'),
    ({'current_stage':'G2','ndvi_mean':0.52,'scene_valid_pixel_pct':72,'sat_advisory_confidence':0.85}, F, 'लवकर'),
  ]},

'D14-PH-004': {
  'expr': ("current_stage IN [G3, G4] AND dap < 180 AND ndvi_delta_10d <= -0.12 AND "
           "sat_advisory_confidence >= 0.5"),
  'note': 'Early senescence — D06 wilt / D03 water branch.',
  'tests': [
    ({'current_stage':'G4','dap':160,'ndvi_delta_10d':-0.14,'sat_advisory_confidence':0.85}, T, 'early senescence'),
    ({'current_stage':'G5','dap':210,'ndvi_delta_10d':-0.14,'sat_advisory_confidence':0.85}, F, 'normal'),
    ({'current_stage':'G4','dap':160,'ndvi_delta_10d':-0.05,'sat_advisory_confidence':0.85}, F, 'sharp नाही'),
  ]},

# ===========================================================================
# D14 — AN: Anomaly / baseline (4 rules)
# ===========================================================================

'D14-AN-001': {
  'expr': ("plot_ndvi_baseline_regional IS NOT NULL AND "
           "(plot_ndvi_baseline_peer IS NULL OR plot_area_ha >= 0.10)"),
  'note': 'Baseline mode selector — REGIONAL-only until 3+ peer plots enrolled.',
  'tests': [
    ({'plot_ndvi_baseline_regional':0.55,'plot_ndvi_baseline_peer':None,'plot_area_ha':0.5}, T, 'regional-only'),
    ({'plot_ndvi_baseline_regional':0.55,'plot_ndvi_baseline_peer':0.6,'plot_area_ha':0.5}, T, 'दोन्ही'),
  ]},

'D14-AN-002': {
  'expr': "plot_area_ha < 0.05 OR ndvi_std > 0.15",
  'note': 'Plot-quality downgrade — sets plot_advisory_class = INFORMATIONAL_ONLY.',
  'tests': [
    ({'plot_area_ha':0.03,'ndvi_std':0.08}, T, 'लहान'),
    ({'plot_area_ha':0.30,'ndvi_std':0.20}, T, 'heterogeneous'),
    ({'plot_area_ha':0.50,'ndvi_std':0.06}, F, 'सामान्य'),
  ]},

'D14-AN-003': {
  'expr': ("monsoon_days_since_onset BETWEEN 0 AND 20 AND ndvi_delta_10d > 0.15 AND "
           "STAGE IN [G0, G1, G2]"),
  'note': 'Weed-flush guard. Sets internal flag; suppresses false-positive high-NDVI anomalies.',
  'tests': [
    ({'monsoon_days_since_onset':8,'ndvi_delta_10d':0.20,'current_stage':'G1'}, T, 'flush window'),
    ({'monsoon_days_since_onset':30,'ndvi_delta_10d':0.20,'current_stage':'G2'}, F, 'past window'),
    ({'monsoon_days_since_onset':8,'ndvi_delta_10d':0.05,'current_stage':'G1'}, F, 'no flush'),
  ]},

'D14-AN-004': {
  'expr': ("scout_request_pending IS FALSE AND farmer_scout_report_days_ago IS NOT NULL AND "
           "farmer_scout_report_days_ago <= 3"),
  'note': 'Anomaly-closure hook. Scout report resolves or escalates open satellite anomalies.',
  'tests': [
    ({'scout_request_pending':False,'farmer_scout_report_days_ago':1}, T, 'process'),
    ({'scout_request_pending':True,'farmer_scout_report_days_ago':None}, F, 'waiting'),
    ({'scout_request_pending':False,'farmer_scout_report_days_ago':10}, F, 'जुना'),
  ]},

# ===========================================================================
# D14 — FU: Fusion (5 rules)
# ===========================================================================

'D14-FU-001': {
  'expr': ("sub_node_moisture_status == 'stale' AND (ndmi_delta_10d <= -0.10 OR cwsi > 0.60) AND "
           "sat_advisory_confidence >= 0.5"),
  'note': '§10.2 case E — sub-node silent, satellite stress; ask farmer to visit.',
  'tests': [
    ({'sub_node_moisture_status':'stale','ndmi_delta_10d':-0.12,'cwsi':0.30,'sat_advisory_confidence':0.85}, T, 'sub-node stale'),
    ({'sub_node_moisture_status':'adequate','ndmi_delta_10d':-0.12,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'NM-002 case'),
    ({'sub_node_moisture_status':'stale','ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'no stress'),
  ]},

'D14-FU-002': {
  'expr': ("sub_node_moisture_status == 'low' AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND "
           "sat_advisory_confidence >= 0.5"),
  'note': 'BUNDLES with D03-SC-001. Early-action-window leading indicator tag. §10.2 case B.',
  'tests': [
    ({'sub_node_moisture_status':'low','ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, T, 'early window'),
    ({'sub_node_moisture_status':'low','ndmi_delta_10d':-0.12,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'NM-003 case'),
    ({'sub_node_moisture_status':'adequate','ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'no call'),
  ]},

'D14-FU-003': {
  'expr': ("sar_vv_delta_db < -3.0 AND sub_node_moisture_status == 'adequate' AND sar_gap_days <= 12"),
  'note': '§10.2 case F — surface water, root zone fine. Furrow blockage advisory (EVENT).',
  'tests': [
    ({'sar_vv_delta_db':-4.5,'sub_node_moisture_status':'adequate','sar_gap_days':6}, T, 'surface WL'),
    ({'sar_vv_delta_db':-4.5,'sub_node_moisture_status':'saturated','sar_gap_days':6}, F, 'SR-002 branch'),
    ({'sar_vv_delta_db':-1.5,'sub_node_moisture_status':'adequate','sar_gap_days':6}, F, 'noise'),
  ]},

'D14-FU-004': {
  'expr': ("sub_node_ec_status == 'normal' AND current_stage IN [G3, G4] AND "
           "plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5"),
  'note': '§10.2 case G — micronutrient suspected. D04 leaf-tissue test scheduling.',
  'tests': [
    ({'sub_node_ec_status':'normal','current_stage':'G3','plot_ndre_gap_regional':-0.13,'sat_advisory_confidence':0.85}, T, 'micronutrient'),
    ({'sub_node_ec_status':'normal','current_stage':'G2','plot_ndre_gap_regional':-0.12,'sat_advisory_confidence':0.85}, F, 'wrong stage'),
    ({'sub_node_ec_status':'high','current_stage':'G3','plot_ndre_gap_regional':-0.13,'sat_advisory_confidence':0.85}, F, 'EC branch'),
  ]},

'D14-FU-005': {
  'expr': ("sub_node_moisture_status == 'adequate' AND sub_node_ec_status == 'normal' AND "
           "ndvi_mean >= 0.45 AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND "
           "sat_advisory_confidence >= 0.5"),
  'note': 'Green-flag log. SILENT_GUARD; feeds season review, buyer attestation, DPDP sharing.',
  'tests': [
    ({'sub_node_moisture_status':'adequate','sub_node_ec_status':'normal','ndvi_mean':0.65,'ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, T, 'green flag'),
    ({'sub_node_moisture_status':'low','sub_node_ec_status':'normal','ndvi_mean':0.65,'ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'sub-node calls'),
    ({'sub_node_moisture_status':'adequate','sub_node_ec_status':'normal','ndvi_mean':0.35,'ndmi_delta_10d':-0.02,'cwsi':0.30,'sat_advisory_confidence':0.85}, F, 'NDVI low'),
  ]},

# ===========================================================================
# D14 — PL: Pipeline / freshness / plot-quality guards (4 rules)
# ===========================================================================

'D14-PL-001': {
  'expr': "plot_polygon_wkt IS NULL OR plot_area_ha IS NULL",
  'note': 'Precondition. Without polygon: suspend all D14 rules for the plot, prompt farmer app.',
  'tests': [
    ({'plot_polygon_wkt':None,'plot_area_ha':None}, T, 'polygon गहाळ'),
    ({'plot_polygon_wkt':'POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))','plot_area_ha':0.5}, F, 'polygon आहे'),
  ]},

'D14-PL-002': {
  'expr': ("optical_gap_days > 21 AND sar_gap_days > 12 AND "
           "(farmer_scout_report_days_ago IS NULL OR farmer_scout_report_days_ago > 5)"),
  'note': 'Blind-plot mode. Suspend D14 advisory; high-priority farmer visit request.',
  'tests': [
    ({'optical_gap_days':25,'sar_gap_days':15,'farmer_scout_report_days_ago':10}, T, 'blind'),
    ({'optical_gap_days':25,'sar_gap_days':5,'farmer_scout_report_days_ago':10}, F, 'SAR fresh'),
    ({'optical_gap_days':25,'sar_gap_days':15,'farmer_scout_report_days_ago':2}, F, 'scout fresh'),
  ]},

'D14-PL-003': {
  'expr': "sat_pipeline_version IS NOT NULL",
  'note': ('Pipeline-drift guard. Compare against last stored version; recompute deltas '
           'against same version before AN/PH rules fire.'),
  'tests': [
    ({'sat_pipeline_version':'pipeline-1.2.0'}, T, 'version log'),
    ({'sat_pipeline_version':None}, F, 'अज्ञात — IS NOT NULL returns FALSE'),
  ]},

'D14-PL-004': {
  'expr': "scene_valid_pixel_pct < 60 AND sat_source == 'sentinel-2'",
  'note': 'Fail-closed on low valid-pixel scenes. Do NOT update ndvi_freshness_days.',
  'tests': [
    ({'scene_valid_pixel_pct':45,'sat_source':'sentinel-2'}, T, 'reject'),
    ({'scene_valid_pixel_pct':72,'sat_source':'sentinel-2'}, F, 'accept'),
    ({'scene_valid_pixel_pct':45,'sat_source':'sentinel-1'}, F, 'SAR — not gated'),
  ]},

# ===========================================================================
# D14 — POS: Prohibited claims (IMMUTABLE, 7 rules)
# ===========================================================================
# Each POS rule fires on a specific claim_type; SILENT_GUARD blocks the outgoing
# customer message. These cannot be overridden by any author or automation.

'D14-POS-001': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_001'",
  'note': 'IMMUTABLE — block "satellite detects ginger rhizome rot" claim. RAW MASTER §5, §16.1.',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_001'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_001'}, F, 'no claim'),
    ({'outgoing_message_contains_claim':True,'claim_type':'other'}, F, 'different POS'),
  ]},

'D14-POS-002': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_002'",
  'note': 'IMMUTABLE — block "NDVI tells you when to harvest".',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_002'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_002'}, F, 'no claim'),
  ]},

'D14-POS-003': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_003'",
  'note': 'IMMUTABLE — block "yield prediction from space" (mirrors D12 prohibition).',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_003'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_003'}, F, 'no claim'),
  ]},

'D14-POS-004': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_004'",
  'note': 'IMMUTABLE — block "AI counts ginger plants from orbit".',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_004'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_004'}, F, 'no claim'),
  ]},

'D14-POS-005': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_005'",
  'note': 'IMMUTABLE — block "cloud is not a problem for us".',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_005'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_005'}, F, 'no claim'),
  ]},

'D14-POS-006': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_006'",
  'note': 'IMMUTABLE — block "satellite replaces your soil sensor". Cardinal principle §1.4.',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_006'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_006'}, F, 'no claim'),
  ]},

'D14-POS-007': {
  'expr': "outgoing_message_contains_claim IS TRUE AND claim_type == 'pos_007'",
  'note': 'IMMUTABLE — block "our satellite is always up-to-date".',
  'tests': [
    ({'outgoing_message_contains_claim':True,'claim_type':'pos_007'}, T, 'block'),
    ({'outgoing_message_contains_claim':False,'claim_type':'pos_007'}, F, 'no claim'),
  ]},

# ===========================================================================
# D14 — DP: DPDP (2 rules; DP-001 IMMUTABLE)
# ===========================================================================

'D14-DP-001': {
  'expr': ("sat_public_display_context IN ['third_party', 'cluster_aggregate'] AND "
           "third_party_share_consent_given IS FALSE"),
  'note': 'IMMUTABLE — block third-party plot display without DPDP purpose-limited consent. §13.6.',
  'tests': [
    ({'sat_public_display_context':'third_party','third_party_share_consent_given':False}, T, 'block'),
    ({'sat_public_display_context':'third_party','third_party_share_consent_given':True}, F, 'consent'),
    ({'sat_public_display_context':'own_plot','third_party_share_consent_given':False}, F, 'own plot'),
  ]},

'D14-DP-002': {
  'expr': "sat_source IS NOT NULL AND sat_attribution_shown IS FALSE",
  'note': 'Attribution enforcement — Copernicus/USGS/Bhuvan/Planet source line must render. §13.7.',
  'tests': [
    ({'sat_source':'sentinel-2','sat_attribution_shown':False}, T, 'attribution गहाळ'),
    ({'sat_source':'sentinel-2','sat_attribution_shown':True}, F, 'attribution present'),
    ({'sat_source':None,'sat_attribution_shown':False}, F, 'nothing to attribute — IS NOT NULL returns FALSE'),
  ]},

}

if __name__ == '__main__':
    from collections import Counter
    cats = Counter(k.split('-')[1] for k in TRIGGERS_W5)
    tests = sum(len(v['tests']) for v in TRIGGERS_W5.values())
    print(f"Wave 5 (D14): {len(TRIGGERS_W5)} triggers, {tests} golden tests")
    print(f"  by category: {dict(cats)}")
