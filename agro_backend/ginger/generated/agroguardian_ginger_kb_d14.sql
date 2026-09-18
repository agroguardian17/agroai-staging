-- Domain 14 (Satellite/Remote Sensing) + D07 VPD retrofit delta
-- Extracted from kb_ginger_d14_v1.0.sql; data-only, idempotent.
-- Tables/indexes/trigger already exist (migration 0010).

INSERT INTO kb_domains (domain_id,name_en,name_mr,crop,source_document,version,status,agronomist_validated,total_rules,review_by,purpose,central_finding,author_note) VALUES
 (14, 'Satellite & Remote Sensing Intelligence', 'उपग्रह व दूरसंवेदन बुद्धिमत्ता', 'ginger', NULL, 'draft-1.0', 'PHASE_1_RAW_UNVALIDATED', FALSE, 47, NULL, NULL, NULL, NULL)
ON CONFLICT (domain_id) DO NOTHING;

INSERT INTO kb_rule_categories (domain_id, category, description) VALUES
 (7, 'VP', 'vapour pressure deficit — transpiration and spray-efficacy driver derived from air temperature and relative humidity'),
 (14, 'AN', 'Anomaly and baseline rules — regional, peer, and self-plot deviation detection'),
 (14, 'DP', 'DPDP and licensing compliance rules for satellite-derived plot data'),
 (14, 'FU', 'Fusion and conflict-resolution rules between satellite and ground-truth IoT sensors'),
 (14, 'LT', 'Land Surface Temperature and CWSI rules — canopy transpiration and water stress'),
 (14, 'NM', 'NDMI and canopy moisture rules — leaf water content proxy'),
 (14, 'NR', 'NDRE and red-edge rules — chlorophyll / nitrogen sensitive canopy state'),
 (14, 'NV', 'NDVI and vegetation index rules — canopy vigour and biomass tracking'),
 (14, 'PH', 'Phenology and stage detection rules — NDVI curve fit and stage-transition confirmation'),
 (14, 'PL', 'Pipeline and freshness guard rules — data quality gates, plot polygon checks, fallback modes'),
 (14, 'POS', 'Positioning and prohibited-claim rules — immutable customer-facing claim restrictions'),
 (14, 'SR', 'SAR (Sentinel-1) rules — cloud-independent soil moisture, standing water, tillage, harvest change detection')
ON CONFLICT DO NOTHING;

INSERT INTO kb_farm_brain_fields (field_name, spec, declared_in_domain) VALUES
 ('claim_type', 'text — enum tagging POS-rule dispatch: pos_001 through pos_007', 14),
 ('cwsi', 'number — Crop Water Stress Index in [0,1] from LST minus air temperature', 14),
 ('days_to_planting', 'integer — days from today to the plot''s planned planting date (positive before, negative after). Populated in G0 stage from D01 planting schedule; NV-006 uses this to gate the pre-plant weed check window.', 14),
 ('evi_mean', 'number — enhanced vegetation index; used where NDVI saturates', 14),
 ('farmer_scout_report_days_ago', 'integer — days since farmer submitted the last scout report', 14),
 ('lst_c', 'number — Land Surface Temperature in Celsius from most recent Landsat overpass', 14),
 ('monsoon_days_since_onset', 'integer — days since IMD-declared monsoon onset for Marathwada (or, if unavailable, since first significant rain of the season). Used by AN-003 weed-flush guard.', 14),
 ('nbr_delta_10d', 'number — NBR change over the last 10 days', 14),
 ('nbr_mean', 'number — normalized burn ratio; residue burning detection', 14),
 ('ndmi_delta_10d', 'number — NDMI change over the last 10 days', 14),
 ('ndmi_mean', 'number — mean NDMI canopy moisture index', 14),
 ('ndre_mean', 'number — mean NDRE red-edge chlorophyll index', 14),
 ('ndre_slope_5d', 'number — NDRE trend over last 5 days (per day)', 14),
 ('ndvi_delta_10d', 'number — NDVI change over the last 10 days (positive means greening, negative means decline)', 14),
 ('ndvi_freshness_days', 'integer — age of ndvi_mean in days; used to degrade advisory confidence linearly', 14),
 ('ndvi_mean', 'number — mean NDVI over valid pixels in the most recent cloud-clear Sentinel-2 scene', 14),
 ('ndvi_smoothed', 'number — Whittaker-smoothed NDVI interpolated to today''s date between scenes', 14),
 ('ndvi_std', 'number — standard deviation of NDVI across the plot; high value in a supposedly uniform plot means confounder', 14),
 ('optical_gap_days', 'integer — days since the last cloud-clear Sentinel-2 scene at the plot', 14),
 ('outgoing_message_contains_claim', 'boolean — set by the outbound-message QA layer before a message is delivered; POS rules gate on this', 14),
 ('plot_advisory_class', 'text — enum: normal, informational_only — set by AN-002 for small/heterogeneous plots', 14),
 ('plot_area_ha', 'number — plot area in hectares, derived from plot_polygon_wkt', 14),
 ('plot_cloud_pct', 'number — cloud percentage over the plot polygon in the most recent Sentinel-2 scene', 14),
 ('plot_ndre_baseline_regional', 'number — regional expected NDRE for the current stage', 14),
 ('plot_ndre_gap_regional', 'number — signed difference plot NDRE minus regional NDRE baseline; parallel to plot_ndvi_gap_regional', 14),
 ('plot_ndvi_baseline_peer', 'number — mean peer NDVI in the cluster at the same DAP; available season 1 once 3+ plots enrolled', 14),
 ('plot_ndvi_baseline_regional', 'number — regional expected NDVI for the current stage; Phase-1 uses author model', 14),
 ('plot_ndvi_baseline_self', 'number — this plot''s NDVI at the same DAP in the previous season; available season 2+', 14),
 ('plot_ndvi_gap_peer', 'number — signed difference plot NDVI minus peer mean', 14),
 ('plot_ndvi_gap_regional', 'number — signed difference plot NDVI minus regional baseline', 14),
 ('plot_polygon_wkt', 'text — plot boundary as Well-Known Text; the geometry every satellite extract runs against', 14),
 ('rainfall_last_48h_mm', 'number — cumulative rainfall in the last 48 hours in mm from the cluster station (D07-authoritative). D14 rules read this to reason about standing water and drying events.', 14),
 ('sar_coherence', 'number — InSAR coherence between last two same-orbit acquisitions, 0 to 1', 14),
 ('sar_gap_days', 'integer — days since the last Sentinel-1 acquisition at the plot', 14),
 ('sar_rvi', 'number — radar vegetation index, 4*VH/(VV+VH)', 14),
 ('sar_vh_db', 'number — Sentinel-1 sigma-nought VH in dB', 14),
 ('sar_vv_db', 'number — Sentinel-1 sigma-nought VV in dB', 14),
 ('sar_vv_delta_db', 'number — change in VV between last two acquisitions from the same relative orbit', 14),
 ('sat_advisory_confidence', 'number — confidence in [0,1] the current satellite advisory should carry; set by pipeline', 14),
 ('sat_attribution_shown', 'boolean — true when the required source attribution line has been rendered to the farmer app for the current satellite product', 14),
 ('sat_pipeline_version', 'text — version tag of the processing chain that produced the current indices', 14),
 ('sat_public_display_context', 'text — enum: own_plot, cluster_aggregate, third_party — governs DPDP display rules', 14),
 ('sat_source', 'text — enum: sentinel-2, sentinel-1, landsat-8, landsat-9, planet, other', 14),
 ('savi_mean', 'number — soil-adjusted NDVI; used in G0 and early G1 when soil dominates the pixel', 14),
 ('scene_valid_pixel_pct', 'number — percentage of plot pixels that are neither cloud nor shadow nor water nor saturated', 14),
 ('scout_request_pending', 'boolean — a scouting task has been dispatched to the farmer but no report received yet', 14),
 ('spray_scheduled_today', 'boolean — true when a foliar spray of any kind is queued for the current day; used by SILENT_GUARD rules to check safety before the recommendation leaves the engine', 7),
 ('sub_node_ec_status', 'text — enum: normal, high, low, stale — resolved from D04 sub-node data', 14),
 ('sub_node_moisture_status', 'text — enum: adequate, low, saturated, stale — resolved from D03 sub-node data', 14),
 ('third_party_share_consent_given', 'boolean — DPDP purpose-limited consent for sharing plot-level indices with an insurer, buyer, or government scheme', 14),
 ('vpd_kpa', 'number — vapour pressure deficit in kilopascals; derived from air_temp_max_c and rh_pct via Tetens'' equation; 0.8–1.5 kPa is the plant-friendly band', 7),
 ('vpd_night_mean_kpa', 'number — mean nighttime VPD (2200–0600 local) in kilopascals; below 0.3 signals almost certain dew and leaf wetness', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D07-VP-001', 7, 'VP', 4, 'info', 'ALL',
  'A daily station reading is received AND both air_temp_max_c and rh_pct are present',
  'दिवसाची हवामान केंद्राची नोंद आली आणि कमाल तापमान व सापेक्ष आर्द्रता दोन्ही उपलब्ध आहेत',
  'air_temp_max_c IS NOT NULL AND rh_pct IS NOT NULL', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compute vpd_kpa = 0.6108 * exp(17.27 * air_temp_max_c / (air_temp_max_c + 237.3)) * (1 - rh_pct/100) and store it on the daily record. Also update vpd_night_mean_kpa from the nighttime hourly readings where available. Emit nothing to the farmer.',
  'vpd_kpa या नोंदीची गणना करा — Tetens समीकरणाने. रात्रीच्या तासांतील सरासरी vpd_night_mean_kpa सुद्धा नोंदवा. शेतकऱ्याला कोणतीही सूचना पाठवू नका — ही केवळ आतील गणना आहे.',
  'Relative humidity conflates two very different agronomic situations at different temperatures. VPD is the temperature-corrected form and is what plants and spray droplets actually respond to. Storing it once per day lets every downstream rule read the same value and lets the count-once check succeed.',
  'None directly. Enables D07-VP-002 (spray safety) and D07-VP-003 (leaf wetness confidence).',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'The cluster weather station already logs temperature and humidity, so VPD is arithmetic on the master unit and needs no new hardware. This closes a real gap without any capital cost.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D07-VP-001', 'air_temp_max_c'),
 ('D07-VP-001', 'rh_pct'),
 ('D07-VP-001', 'vpd_kpa'),
 ('D07-VP-001', 'vpd_night_mean_kpa'),
 ('D07-VP-001', 'station_data_age_hours')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D07-VP-001', 0, '{"air_temp_max_c": 30, "rh_pct": 60}'::jsonb, 'TRUE', 'compute vpd for a normal reading'),
 ('D07-VP-001', 1, '{"air_temp_max_c": 30, "rh_pct": null}'::jsonb, 'UNKNOWN', 'missing rh must not fire and must not read as false'),
 ('D07-VP-001', 2, '{"air_temp_max_c": null, "rh_pct": 60}'::jsonb, 'UNKNOWN', 'missing temperature must not fire and must not read as false')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D07-VP-001', 'FAO-56 chapter 3, Penman–Monteith reference evapotranspiration'),
 ('D07-VP-001', 'Tetens 1930, saturation vapour pressure equation')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D07-VP-001', 'feeds_into', 3),
 ('D07-VP-001', 'feeds_into', 5),
 ('D07-VP-001', 'feeds_into', 6),
 ('D07-VP-001', 'feeds_into', 8)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D07-VP-002', 7, 'VP', 4, 'info', 'ALL',
  'A foliar spray is scheduled AND vpd_kpa is either below 0.4 or above 2.0',
  'फवारणी नियोजित आहे आणि vpd_kpa एकतर ०.४ पेक्षा कमी किंवा २.० पेक्षा जास्त आहे',
  'spray_scheduled_today IS TRUE AND (vpd_kpa < 0.4 OR vpd_kpa > 2.0)', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Delay the spray to the next window inside VPD 0.8 to 1.5 kPa, typically 2 to 4 hours later or the following morning. Below 0.4 kPa the droplets do not dry and disease pressure is amplified rather than reduced. Above 2.0 kPa evaporation is faster than uptake and effective dose collapses. If D07-HS-004 also fires, present one combined message: temperature or rain plus VPD, one recommended new window.',
  'फवारणी VPD ०.८ ते १.५ kPa च्या पट्ट्यात होईल अशा वेळेवर पुढे ढकला — बहुतेक वेळा २–४ तासांनी किंवा दुसऱ्या दिवशी सकाळी. VPD ०.४ पेक्षा कमी असेल तर थेंब वाळत नाहीत आणि रोगदाब कमी होण्याऐवजी वाढतो. VPD २.० च्या वर असेल तर पानांवर बसण्यापूर्वीच बाष्पीभवन होते आणि प्रभावी मात्रा खूप कमी होते. D07-HS-004 देखील लागू होत असल्यास एकच एकत्रित संदेश द्या — तापमान/पाऊस आणि VPD, एकच पुढील वेळ.',
  'Spray efficacy is a function of droplet residence on the leaf, which in turn tracks VPD, not temperature or rainfall alone. D07-HS-004 catches high temperature and imminent rain but is blind to the two humidity extremes. This rule adds only that missing discrimination, without changing D07-HS-004''s behaviour.',
  'Grouped under the existing spray-timing duplication group. Not counted separately; see v_u_values_deduplicated.',
  0.78, 'B', 'DERIVED', NULL, 'same_season',
  'Marathwada''s May pre-monsoon and December–February fog months hit both VPD extremes within the same season. Kannad''s daytime maxima of 40+ C push VPD past 3.0 kPa, while pre-dawn winter fog drops it below 0.2 kPa. The two spray-failure windows are not exotic; they are the normal spring afternoon and the normal winter morning here.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D07-VP-002', 'spray_scheduled_today'),
 ('D07-VP-002', 'vpd_kpa'),
 ('D07-VP-002', 'air_temp_max_c'),
 ('D07-VP-002', 'forecast_rain_48h_mm')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D07-VP-002', 0, '{"spray_scheduled_today": true, "vpd_kpa": 0.25}'::jsonb, 'TRUE', 'very humid — droplets will not dry, spray amplifies disease'),
 ('D07-VP-002', 1, '{"spray_scheduled_today": true, "vpd_kpa": 2.4}'::jsonb, 'TRUE', 'very dry — droplets evaporate before uptake'),
 ('D07-VP-002', 2, '{"spray_scheduled_today": true, "vpd_kpa": 1.1}'::jsonb, 'FALSE', 'plant-friendly band — no block'),
 ('D07-VP-002', 3, '{"spray_scheduled_today": false, "vpd_kpa": 0.25}'::jsonb, 'FALSE', 'no spray attempted — silent guard stays silent'),
 ('D07-VP-002', 4, '{"spray_scheduled_today": true, "vpd_kpa": null}'::jsonb, 'UNKNOWN', 'missing vpd — do not silently pass; report gap')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D07-VP-002', 'Foliar spray drift and efficacy studies, ICAR-CPCRI 2019'),
 ('D07-VP-002', 'FAO-56 chapter 3'),
 ('D07-VP-002', 'Ministry of Agriculture, Government of India — spray timing guidelines')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D07-VP-002', 'feeds_into', 4),
 ('D07-VP-002', 'feeds_into', 5),
 ('D07-VP-002', 'feeds_into', 6),
 ('D07-VP-002', 'feeds_into', 8),
 ('D07-VP-002', 'depends_on', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D07-VP-003', 7, 'VP', 3, 'info', 'G4',
  'vpd_night_mean_kpa is below 0.3 AND fog is not observed AND month is December, January or February',
  'रात्रीचा सरासरी VPD ०.३ पेक्षा कमी, धुके नोंदवलेले नाही, आणि महिना डिसेंबर–जानेवारी–फेब्रुवारी आहे',
  'vpd_night_mean_kpa < 0.3 AND fog_observed IS FALSE AND MONTH IN [DEC, JAN, FEB]', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Tag tonight''s estimated leaf_wetness_hours with a high dew-probability confidence flag and log the reason (very low nighttime VPD with clear sky). Do not raise a new disease alert. If D07-HU-002 fires overnight or the next morning, the confidence flag travels with it. This is the interim substitute for the missing leaf wetness sensor logged as D07-OI-05.',
  'आजच्या रात्रीच्या अंदाजित leaf_wetness_hours नोंदीवर उच्च-दव-संभाव्यता ध्वज लावा आणि कारण नोंदवा (रात्रीचा VPD अत्यंत कमी, आकाश निरभ्र). नवीन रोग सूचना देऊ नका. रात्रभर किंवा सकाळी D07-HU-002 सुरू झाल्यास हा ध्वज त्याच्यासोबत जातो. हा पानावरील ओलावा सेन्सर बसेपर्यंतचा (D07-OI-05) तात्पुरता पर्याय आहे.',
  'Dew formation on ginger leaves requires the leaf surface to reach the dew point of the surrounding air. Low nighttime VPD means the air is already close to saturation and radiative cooling of the leaf will cross that threshold. Fog observations catch part of this signal; low VPD catches the other part, especially on cold clear nights when fog does not form but dew still soaks the canopy.',
  'None directly. Improves the reliability of D07-HU-002 and future disease-forecast rules that depend on it.',
  0.75, 'B', 'DERIVED', NULL, 'same_season',
  'Marathwada winter mornings are the local advantage for rhizome bulking mentioned in D07 key_innovations, but they are also when the second foliar disease season starts. VPD makes the dew half of that pattern measurable without waiting for a leaf wetness sensor purchase.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D07-VP-003', 'vpd_night_mean_kpa'),
 ('D07-VP-003', 'fog_observed'),
 ('D07-VP-003', 'leaf_wetness_hours'),
 ('D07-VP-003', 'current_stage')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D07-VP-003', 0, '{"vpd_night_mean_kpa": 0.2, "fog_observed": false, "current_month": "JAN"}'::jsonb, 'TRUE', 'cold clear night — dew almost certain even without fog observation'),
 ('D07-VP-003', 1, '{"vpd_night_mean_kpa": 0.2, "fog_observed": true, "current_month": "JAN"}'::jsonb, 'FALSE', 'fog already recorded — D07-HU-002 has the signal, no tag needed'),
 ('D07-VP-003', 2, '{"vpd_night_mean_kpa": 0.6, "fog_observed": false, "current_month": "JAN"}'::jsonb, 'FALSE', 'dry night — dew unlikely'),
 ('D07-VP-003', 3, '{"vpd_night_mean_kpa": 0.2, "fog_observed": false, "current_month": "JUL"}'::jsonb, 'FALSE', 'monsoon — different disease season, driven by saturation not by dew')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D07-VP-003', 'Grantz 1990, Plant, Cell & Environment'),
 ('D07-VP-003', 'IMD Marathwada winter humidity records'),
 ('D07-VP-003', 'Domain 6 leaf wetness estimation notes')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D07-VP-003', 'feeds_into', 6),
 ('D07-VP-003', 'feeds_into', 7),
 ('D07-VP-003', 'depends_on', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-001', 14, 'NV', 4, 'info', 'ALL',
  'A cloud-clear Sentinel-2 scene is received for the plot AND scene_valid_pixel_pct is at least 60',
  'प्लॉटवर ढगमुक्त Sentinel-2 दृश्य प्राप्त झाले आणि scene_valid_pixel_pct किमान ६० आहे',
  'sat_source == ''sentinel-2'' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compute and store ndvi_mean, ndvi_std, evi_mean, savi_mean using the standard Sentinel-2 L2A band arithmetic (NDVI = (B8-B4)/(B8+B4)). Log scene id and pipeline version. Do not emit anything to the farmer app; this rule is a pipeline hook, not a message.',
  'ndvi_mean, ndvi_std, evi_mean, savi_mean यांची गणना करून नोंदवा. दृश्याचा id व pipeline version log करा. शेतकऱ्याला कोणतीही सूचना पाठवू नका — हा फक्त pipeline hook आहे.',
  'Cloud-clear valid-pixel gating is required before any index is trustworthy. Values below 60% valid pixels give a plot mean dominated by mask edges; above 60% is the industry consensus for smallholder analysis. See RAW MASTER §4 and §12.4.',
  'None directly. Enables every downstream NV, AN, and PH rule.',
  0.9, 'A', 'DERIVED', NULL, 'none',
  'Marathwada tile 43QGD gets a cloud-clear Sentinel-2 scene roughly once every 5-6 days in Nov-Mar and every 15-20 days in Jul-Aug. The gate is not there to be strict; it is there because a bad scene teaches the engine wrong things about the plot.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-001', 'sat_source'),
 ('D14-NV-001', 'scene_valid_pixel_pct'),
 ('D14-NV-001', 'plot_cloud_pct'),
 ('D14-NV-001', 'ndvi_mean'),
 ('D14-NV-001', 'ndvi_std'),
 ('D14-NV-001', 'evi_mean'),
 ('D14-NV-001', 'savi_mean'),
 ('D14-NV-001', 'ndvi_freshness_days'),
 ('D14-NV-001', 'sat_pipeline_version')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-001', 0, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 72, "plot_cloud_pct": 8}'::jsonb, 'TRUE', 'clear scene — compute indices'),
 ('D14-NV-001', 1, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 45, "plot_cloud_pct": 8}'::jsonb, 'FALSE', 'not enough valid pixels — skip'),
 ('D14-NV-001', 2, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 72, "plot_cloud_pct": 25}'::jsonb, 'FALSE', 'too much cloud over plot — skip'),
 ('D14-NV-001', 3, '{"sat_source": null, "scene_valid_pixel_pct": 72, "plot_cloud_pct": 8}'::jsonb, 'UNKNOWN', 'unknown source — do not silently pass')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-001', 'ESA Sentinel-2 L2A product specification'),
 ('D14-NV-001', 'Rouse et al. 1974 (NDVI)'),
 ('D14-NV-001', 'RAW MASTER Domain 14 §4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-001', 'feeds_into', 1),
 ('D14-NV-001', 'feeds_into', 3),
 ('D14-NV-001', 'feeds_into', 4),
 ('D14-NV-001', 'feeds_into', 6)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-002', 14, 'NV', 3, 'info', 'ALL',
  'ndvi_freshness_days exceeds the confidence-full threshold — degrade advisory confidence',
  'ndvi_freshness_days confidence-full मर्यादेपेक्षा जास्त — सल्ल्याचा विश्वास कमी करा',
  'ndvi_freshness_days > 5 AND ndvi_freshness_days <= 20', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compute sat_advisory_confidence = max(0, 1 - (ndvi_freshness_days - 5) / 15). Downstream NV/NR/NM/AN rules multiply their base confidence by this scalar before delivery. This is the same pattern as D07 station_data_age_hours degradation.',
  'sat_advisory_confidence = max(0, 1 - (ndvi_freshness_days - 5) / 15) या सूत्राने गणना करा. NV/NR/NM/AN नियम delivery पूर्वी त्यांचा base confidence याने गुणतील. D07 station_data_age_hours degradation प्रमाणे.',
  'A plot state that was valid 3 days ago is still probably valid; a state valid 15 days ago is not. Linear degradation is the honest simplification.',
  'None directly. Protects downstream advisory quality.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'Kannad Jul-Aug monsoon regularly pushes freshness past 15 days. Without this degradation an operator would get the same recommendation on day 3 and day 18 with identical confidence — dishonest and unsafe.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-002', 'ndvi_freshness_days'),
 ('D14-NV-002', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-002', 0, '{"ndvi_freshness_days": 3}'::jsonb, 'FALSE', 'very fresh — full confidence'),
 ('D14-NV-002', 1, '{"ndvi_freshness_days": 8}'::jsonb, 'TRUE', 'moderately fresh — degrade'),
 ('D14-NV-002', 2, '{"ndvi_freshness_days": 17}'::jsonb, 'TRUE', 'stale — heavy degrade'),
 ('D14-NV-002', 3, '{"ndvi_freshness_days": 22}'::jsonb, 'FALSE', 'too stale — separate rule PL-002 handles'),
 ('D14-NV-002', 4, '{"ndvi_freshness_days": null}'::jsonb, 'UNKNOWN', 'no freshness known')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-002', 'RAW MASTER §3.4 working definitions'),
 ('D14-NV-002', 'D07 station_data_age_hours pattern')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-002', 'feeds_into', 14),
 ('D14-NV-002', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-003', 14, 'NV', 3, 'yellow', 'G2',
  'Plot NDVI is more than 0.10 below the regional baseline for the current stage AND scene is trusted AND advisory confidence is at least 0.5',
  'प्लॉट NDVI सध्याच्या अवस्थेसाठी अपेक्षित regional baseline पेक्षा ०.१० पेक्षा जास्त कमी आहे',
  'plot_ndvi_gap_regional < -0.10 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Open an investigation task for this plot: check sub-node moisture and EC over the last 7 days, and schedule a farmer scout report. Do NOT recommend any chemical intervention on this signal alone. If the sub-node shows a matching anomaly, escalate through the appropriate domain (D03 water, D04 nutrient, or D06 disease). If sub-node shows nothing, request the scout and hold.',
  'या प्लॉटसाठी तपासणी task उघडा — सर्व सब-नोड मृदा-ओलावा व EC मागील ७ दिवसांची तपासा आणि शेतकऱ्याला scout अहवाल पाठवण्याची विनंती करा. फक्त या सिग्नलवर कोणतीही रासायनिक शिफारस करू नका. सब-नोडवर तीच अनियमितता आढळल्यास योग्य डोमेनमार्फत (D03/D04/D06) escalate करा; काहीच नसल्यास scout अहवालाची वाट पहा.',
  'Regional-baseline deviation is a coarse signal; the underlying model is Phase-1 author-estimated. Requires cross-check by §8.4 double-signal principle.',
  'Grouped under investigation_dispatched — not counted separately from downstream domain-specific u-values.',
  0.55, 'B', 'EST', NULL, 'same_season',
  'Kannad regional NDVI baseline for ginger is not published; the author-estimate model used here is coarse. Season-1 log will replace it with an empirical mean, at which point this rule''s confidence bumps to 0.75. Do not sell this alert as a diagnosis; it is a call for a look, not a prescription.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-003', 'plot_ndvi_gap_regional'),
 ('D14-NV-003', 'scene_valid_pixel_pct'),
 ('D14-NV-003', 'sat_advisory_confidence'),
 ('D14-NV-003', 'current_stage'),
 ('D14-NV-003', 'ndvi_mean'),
 ('D14-NV-003', 'plot_ndvi_baseline_regional')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-003', 0, '{"plot_ndvi_gap_regional": -0.14, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'clear anomaly — investigate'),
 ('D14-NV-003', 1, '{"plot_ndvi_gap_regional": -0.07, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'small deviation — noise band'),
 ('D14-NV-003', 2, '{"plot_ndvi_gap_regional": -0.14, "scene_valid_pixel_pct": 45, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'scene not trusted'),
 ('D14-NV-003', 3, '{"plot_ndvi_gap_regional": -0.14, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.3, "current_stage": "G3"}'::jsonb, 'FALSE', 'confidence too low'),
 ('D14-NV-003', 4, '{"plot_ndvi_gap_regional": -0.14, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G1"}'::jsonb, 'FALSE', 'wrong stage — G1 handled by pre-plant/emergence rules')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-003', 'RAW MASTER §8, §9'),
 ('D14-NV-003', 'Domain 6 double-signal principle')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-003', 'feeds_into', 3),
 ('D14-NV-003', 'feeds_into', 4),
 ('D14-NV-003', 'feeds_into', 6),
 ('D14-NV-003', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-004', 14, 'NV', 5, 'red', 'G3',
  'Plot NDVI has dropped by 0.15 or more over the last 10 days AND scene is trusted',
  'प्लॉट NDVI मागील १० दिवसांत ०.१५ किंवा अधिक कमी झाले आहे',
  'ndvi_delta_10d <= -0.15 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Send an URGENT scout request to the farmer today. Message: canopy has declined sharply on satellite view; check for waterlogging, disease, pest, hail damage, or herbicide drift, and report back with a photo. Simultaneously, pull last 7 days of sub-node soil moisture, EC, and rainfall for automatic cross-check and stage this for the D06 differential branch.',
  'शेतकऱ्याला आजच URGENT scout विनंती पाठवा. संदेश: उपग्रह दृश्यात पिकाचा हिरवेपणा झपाट्याने कमी झाला आहे; पाणी साचणे, रोग, कीड, गारपीट, तणनाशक drift पैकी काय झाले ते फोटोसह कळवा. एकाच वेळी सब-नोडचे मागील ७ दिवसांचे मृदा-ओलावा, EC व पाऊस स्वयंचलितपणे ओढून D06 differential शाखेसाठी तयारी करा.',
  'A 15-point NDVI drop in 10 days is well outside the normal senescence trajectory in G2-G4 and reflects a real change. The signal itself is trustworthy; the CAUSE requires the ground check and D06 differential.',
  'Counted under investigation_dispatched; the yield-impact number is assigned by the confirmed downstream domain (D06 disease, D03 water, etc.), not by this rule.',
  0.75, 'B', 'DERIVED', NULL, 'same_season',
  'In Kannad Sep-Oct, a sharp NDVI drop coincides with post-monsoon waterlogging risk more often than with disease. Do not skip the scout request in favour of a chemical recommendation — the standing water is not visible without the ground check.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-004', 'ndvi_delta_10d'),
 ('D14-NV-004', 'scene_valid_pixel_pct'),
 ('D14-NV-004', 'sat_advisory_confidence'),
 ('D14-NV-004', 'current_stage'),
 ('D14-NV-004', 'ndvi_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-004', 0, '{"ndvi_delta_10d": -0.18, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'sharp drop — urgent scout'),
 ('D14-NV-004', 1, '{"ndvi_delta_10d": -0.08, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'gradual — not urgent'),
 ('D14-NV-004', 2, '{"ndvi_delta_10d": -0.25, "scene_valid_pixel_pct": 50, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'scene not trusted'),
 ('D14-NV-004', 3, '{"ndvi_delta_10d": -0.18, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G5"}'::jsonb, 'FALSE', 'senescence — natural drop expected'),
 ('D14-NV-004', 4, '{"ndvi_delta_10d": null, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'UNKNOWN', 'delta not computed yet')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-004', 'RAW MASTER §8.3, §9.2'),
 ('D14-NV-004', 'Domain 6 differential-diagnosis rules'),
 ('D14-NV-004', 'Zhu & Woodcock 2014')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-004', 'feeds_into', 3),
 ('D14-NV-004', 'feeds_into', 6),
 ('D14-NV-004', 'feeds_into', 8),
 ('D14-NV-004', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-005', 14, 'NV', 3, 'yellow', 'G3',
  'Plot NDVI is more than 0.10 below the peer cluster mean at the same DAP AND at least 3 peer plots contribute AND DAP is at least 60',
  'प्लॉट NDVI त्याच DAP वरील peer cluster mean पेक्षा ०.१० पेक्षा जास्त कमी आहे, किमान ३ peer plots मध्ये आहेत',
  'plot_ndvi_gap_peer < -0.10 AND dap >= 60 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Open a plot-specific investigation. This plot is developing slower than its cluster peers. Likely causes in order of frequency: nitrogen shortfall (D04), waterlogging on this plot (D03), variety difference (D01), planting-date mismatch (D01). Cross-check the last farmer-reported input dates.',
  'प्लॉट-विशिष्ट तपासणी उघडा. हा प्लॉट cluster peers पेक्षा हळू विकसित होत आहे. वारंवारतेने: नत्र कमतरता (D04), पाणी साचणे (D03), वाणातील फरक (D01), लागवडीच्या तारखेतील फरक (D01). शेतकऱ्याने नोंदवलेल्या शेवटच्या तारखांची तपासणी करा.',
  'Peer-cluster comparison neutralises weather, soil zone, and market-level variety effects. It isolates plot-specific management differences.',
  'Investigation_dispatched grouping.',
  0.72, 'B', 'DERIVED', NULL, 'same_season',
  'In Kannad the first commercial season likely has 5-10 farmer clusters; peer baselines mature by DAP 60. Do not fire before that day.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-005', 'plot_ndvi_gap_peer'),
 ('D14-NV-005', 'dap'),
 ('D14-NV-005', 'sat_advisory_confidence'),
 ('D14-NV-005', 'ndvi_mean'),
 ('D14-NV-005', 'plot_ndvi_baseline_peer')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-005', 0, '{"plot_ndvi_gap_peer": -0.14, "dap": 80, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'clear peer gap'),
 ('D14-NV-005', 1, '{"plot_ndvi_gap_peer": -0.06, "dap": 80, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'small gap — noise'),
 ('D14-NV-005', 2, '{"plot_ndvi_gap_peer": -0.14, "dap": 40, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'too early — peers not yet differentiated'),
 ('D14-NV-005', 3, '{"plot_ndvi_gap_peer": null, "dap": 80, "sat_advisory_confidence": 0.85}'::jsonb, 'UNKNOWN', 'peer baseline not built')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-005', 'RAW MASTER §9.1 baseline construction'),
 ('D14-NV-005', 'Precision agriculture peer-benchmarking studies')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-005', 'feeds_into', 1),
 ('D14-NV-005', 'feeds_into', 3),
 ('D14-NV-005', 'feeds_into', 4),
 ('D14-NV-005', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-006', 14, 'NV', 3, 'info', 'G0',
  'It is 5 to 30 days before planned planting AND plot NDVI exceeds the pre-plant bare-soil threshold',
  'नियोजित लागवडीच्या ५-३० दिवस आधी आणि प्लॉट NDVI pre-plant bare-soil मर्यादेपेक्षा जास्त आहे',
  'days_to_planting BETWEEN 5 AND 30 AND ndvi_mean > 0.25 AND scene_valid_pixel_pct >= 60', 'dsl-1.0', 'EVENT', FALSE, NULL,
  'Send an ADVISORY (not alarm) to the farmer: satellite view shows green vegetation on the plot 15-30 days before your planned planting. Verify — this is likely weed flush or uncleared residue. Land preparation instructions from D02 apply. If it is inter-crop cover (green manure being incorporated), no action is needed — reply to close the advisory.',
  'शेतकऱ्याला सूचना पाठवा (धोक्याची घंटा नाही): नियोजित लागवडीच्या १५-३० दिवस आधी उपग्रह दृश्यात प्लॉटवर हिरवी वनस्पती दिसते. तपासा — बहुधा तण किंवा मागील पिकाचे कचरे. D02 चे भूमी-तयारीचे सल्ले लागू. हिरवळीचे खत (green manure) मुद्दाम पेरले असेल तर कारवाईची गरज नाही — reply देऊन सूचना बंद करा.',
  'Bare-soil NDVI in Kannad basaltic soils is 0.10-0.20. Anything above 0.25 in a supposedly bare plot has active vegetation.',
  'Land-preparation quality — grouped under D02 preparation compliance.',
  0.8, 'B', 'EST', NULL, 'same_season',
  'In Kannad, May pre-monsoon showers commonly trigger a 2-week weed flush right before planting; farmers who plough late without spraying carry the flush into the crop period. This rule catches it while there is time to act.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-006', 'days_to_planting'),
 ('D14-NV-006', 'ndvi_mean'),
 ('D14-NV-006', 'scene_valid_pixel_pct')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-006', 0, '{"days_to_planting": 15, "ndvi_mean": 0.32, "scene_valid_pixel_pct": 72}'::jsonb, 'TRUE', 'weed / residue flush before planting'),
 ('D14-NV-006', 1, '{"days_to_planting": 15, "ndvi_mean": 0.18, "scene_valid_pixel_pct": 72}'::jsonb, 'FALSE', 'clean field — as expected'),
 ('D14-NV-006', 2, '{"days_to_planting": 45, "ndvi_mean": 0.32, "scene_valid_pixel_pct": 72}'::jsonb, 'FALSE', 'too early to act'),
 ('D14-NV-006', 3, '{"days_to_planting": 15, "ndvi_mean": 0.32, "scene_valid_pixel_pct": 45}'::jsonb, 'FALSE', 'scene not trusted')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-006', 'RAW MASTER §4.2, §4.5'),
 ('D14-NV-006', 'ISRO NRSC bare-soil reference')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-006', 'feeds_into', 2),
 ('D14-NV-006', 'feeds_into', 8),
 ('D14-NV-006', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NV-007', 14, 'NV', 3, 'yellow', 'ALL',
  'Plot NBR has dropped by 0.20 or more over the last 10 days AND scene is trusted',
  'प्लॉट NBR मागील १० दिवसांत ०.२० किंवा अधिक कमी झाले आहे',
  'nbr_delta_10d <= -0.20 AND scene_valid_pixel_pct >= 60', 'dsl-1.0', 'EVENT', FALSE, NULL,
  'Log a residue-burning-candidate event on the plot. Notify the operations team for verification. Do not display any punitive message to the farmer; this is compliance intelligence, not an accusation. False positives include intentional black plastic mulching, which needs a farmer confirmation reply.',
  'प्लॉटवर residue-burning-candidate घटना नोंदवा. संचालन टीमला पडताळणीसाठी कळवा. शेतकऱ्याला दंडात्मक संदेश दाखवू नका — ही अनुपालन-गुप्तवार्ता आहे, आरोप नाही. काळी पॉलिथिन आच्छादन असल्यास खोटा इशारा असू शकतो — शेतकऱ्याच्या पुष्टीने बंद करा.',
  'Burnt residue reflects strongly in SWIR (B12) and weakly in NIR (B8), collapsing NBR. The signal is unambiguous for a real burn.',
  'Compliance-only. No direct yield mapping.',
  0.75, 'B', 'DERIVED', NULL, 'none',
  'Marathwada residue-burning enforcement is patchy but tightening under state pollution rules. Building the log now positions Agro-Guardian well when audit comes; misusing it as a farmer-facing accusation destroys trust.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NV-007', 'nbr_delta_10d'),
 ('D14-NV-007', 'scene_valid_pixel_pct'),
 ('D14-NV-007', 'nbr_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NV-007', 0, '{"nbr_delta_10d": -0.25, "scene_valid_pixel_pct": 72}'::jsonb, 'TRUE', 'burn scar'),
 ('D14-NV-007', 1, '{"nbr_delta_10d": -0.1, "scene_valid_pixel_pct": 72}'::jsonb, 'FALSE', 'no burn'),
 ('D14-NV-007', 2, '{"nbr_delta_10d": -0.25, "scene_valid_pixel_pct": 45}'::jsonb, 'FALSE', 'scene not trusted')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NV-007', 'Key & Benson 2006 NBR'),
 ('D14-NV-007', 'RAW MASTER §4.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NV-007', 'feeds_into', 13),
 ('D14-NV-007', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NR-001', 14, 'NR', 4, 'info', 'ALL',
  'A cloud-clear Sentinel-2 scene is received AND red-edge bands B5, B6, B7 are valid',
  'ढगमुक्त Sentinel-2 दृश्य आणि लाल-किनार बँड्स वैध',
  'sat_source == ''sentinel-2'' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compute ndre_mean = (B8 - B5) / (B8 + B5) over valid pixels. Compute ndre_slope_5d as the slope of the last 5 days of NDRE values. Store both.',
  'ndre_mean = (B8 - B5) / (B8 + B5) वैध पिक्सेल्सवर मोजा. मागील ५ दिवसांतील NDRE मूल्यांवरून ndre_slope_5d मोजा.',
  'Red-edge stays sensitive to canopy chlorophyll well past the saturation point of NDVI (LAI ~ 3.5). Necessary for closed-canopy nitrogen work.',
  'Enables NR-002/003.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'Ginger closes canopy around DAP 90; from that point NDRE becomes the useful nitrogen index rather than NDVI. Compute both anyway — they answer different questions.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NR-001', 'sat_source'),
 ('D14-NR-001', 'scene_valid_pixel_pct'),
 ('D14-NR-001', 'plot_cloud_pct'),
 ('D14-NR-001', 'ndre_mean'),
 ('D14-NR-001', 'ndre_slope_5d')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NR-001', 0, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 72, "plot_cloud_pct": 8}'::jsonb, 'TRUE', 'compute NDRE'),
 ('D14-NR-001', 1, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 45, "plot_cloud_pct": 8}'::jsonb, 'FALSE', 'insufficient valid pixels'),
 ('D14-NR-001', 2, '{"sat_source": "sentinel-1", "scene_valid_pixel_pct": 72, "plot_cloud_pct": 8}'::jsonb, 'FALSE', 'SAR doesn''t produce NDRE')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NR-001', 'Gitelson & Merzlyak 1996'),
 ('D14-NR-001', 'RAW MASTER §4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NR-001', 'feeds_into', 4)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NR-002', 14, 'NR', 3, 'yellow', 'G2',
  'NDVI is rising in early G2 but NDRE slope is near-flat AND advisory confidence is at least 0.5',
  'लवकर G2 मध्ये NDVI वाढते आहे पण NDRE जवळजवळ सपाट आहे',
  'current_stage == ''G2'' AND dap BETWEEN 40 AND 80 AND ndvi_delta_10d > 0.05 AND ndre_slope_5d < 0.005 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Route to D04 nitrogen check. Do NOT prescribe a nitrogen top-dressing on satellite signal alone; D04 must confirm from soil-test-derived N budget and leaf tissue proxy. If confirmed, D04''s own top-dressing rule fires.',
  'D04 नत्र तपासणीकडे पाठवा. फक्त उपग्रह सिग्नलवर वरखत शिफारस करू नका; D04 ने माती-परीक्षणावर आधारित N अर्थसंकल्प व पर्ण-ऊतक प्रतिनिधीने पुष्टी करावी. पुष्टी झाल्यास D04 चा स्वतःचा top-dressing नियम कार्यरत होतो.',
  'Ginger''s canopy expansion in early G2 can outrun N supply, giving a large but thin canopy. NDVI/NDRE divergence is the recognised satellite signature.',
  'Under D04 nitrogen u-value grouping.',
  0.7, 'B', 'EST', NULL, 'same_season',
  'In Kannad the pattern shows up around 8-10 weeks after planting on plots that skipped a first top-dressing or where the split doses got compressed by weather. Do not recommend urea from the sky; D04 does the honest budget.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NR-002', 'current_stage'),
 ('D14-NR-002', 'dap'),
 ('D14-NR-002', 'ndvi_delta_10d'),
 ('D14-NR-002', 'ndre_slope_5d'),
 ('D14-NR-002', 'sat_advisory_confidence'),
 ('D14-NR-002', 'ndre_mean'),
 ('D14-NR-002', 'ndvi_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NR-002', 0, '{"current_stage": "G2", "dap": 55, "ndvi_delta_10d": 0.08, "ndre_slope_5d": 0.002, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'N stress pattern'),
 ('D14-NR-002', 1, '{"current_stage": "G2", "dap": 55, "ndvi_delta_10d": 0.08, "ndre_slope_5d": 0.012, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'both rising — healthy'),
 ('D14-NR-002', 2, '{"current_stage": "G3", "dap": 100, "ndvi_delta_10d": 0.08, "ndre_slope_5d": 0.002, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'wrong stage')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NR-002', 'ICAR-IISS Bhopal red-edge nitrogen studies'),
 ('D14-NR-002', 'RAW MASTER §4.4, §8.3')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NR-002', 'feeds_into', 4),
 ('D14-NR-002', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NR-003', 14, 'NR', 3, 'yellow', 'G3',
  'NDRE is 0.10 or more below the regional baseline in closed-canopy stage AND advisory confidence is at least 0.5',
  'बंद पर्णसमूह अवस्थेत NDRE regional baseline पेक्षा ०.१० किंवा अधिक कमी',
  'current_stage IN [G3, G4] AND plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Route to D04 nitrogen check with ''closed-canopy NDRE gap'' as the reason code. Same D04-authoritative discipline as NR-002.',
  'D04 नत्र तपासणीकडे ''closed-canopy NDRE gap'' कारणासह पाठवा. NR-002 प्रमाणेच D04 प्राधिकरण.',
  'Once LAI passes ~3.5 the NDVI saturation floor makes NDRE the only satellite channel with meaningful nitrogen sensitivity.',
  'Under D04 nitrogen u-value grouping.',
  0.68, 'B', 'EST', NULL, 'same_season',
  'The regional NDRE baseline for Kannad ginger is another Phase-1 estimate; season-1 log elevates it. Rule fires but confidence stays around 0.7 until then.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NR-003', 'current_stage'),
 ('D14-NR-003', 'plot_ndre_baseline_regional'),
 ('D14-NR-003', 'ndre_mean'),
 ('D14-NR-003', 'sat_advisory_confidence'),
 ('D14-NR-003', 'plot_ndre_gap_regional')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NR-003', 0, '{"current_stage": "G3", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.13}'::jsonb, 'TRUE', 'clear closed-canopy NDRE gap'),
 ('D14-NR-003', 1, '{"current_stage": "G3", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.05}'::jsonb, 'FALSE', 'small gap'),
 ('D14-NR-003', 2, '{"current_stage": "G2", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.12}'::jsonb, 'FALSE', 'early stage — different rule NR-002')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NR-003', 'Fitzgerald et al. 2010'),
 ('D14-NR-003', 'ICAR-IISS Bhopal red-edge studies')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NR-003', 'feeds_into', 4),
 ('D14-NR-003', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NM-001', 14, 'NM', 4, 'info', 'ALL',
  'A cloud-clear Sentinel-2 scene is received AND B11 SWIR is valid',
  'ढगमुक्त Sentinel-2 दृश्य आणि B11 SWIR बँड वैध',
  'sat_source == ''sentinel-2'' AND scene_valid_pixel_pct >= 60 AND plot_cloud_pct <= 15', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compute ndmi_mean = (B8 - B11) / (B8 + B11). Compute ndmi_delta_10d against value from ten days ago.',
  'ndmi_mean = (B8 - B11) / (B8 + B11) मोजा. १० दिवसांपूर्वीच्या मूल्याच्या तुलनेत ndmi_delta_10d नोंदवा.',
  'NDMI is the reflectance-side canopy moisture indicator and is available every cloud-clear Sentinel-2 scene, unlike CWSI which needs Landsat thermal timing.',
  'Enables NM-002/003.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'In Kannad''s dry Feb-May months NDMI runs low across all plots; use the delta not the absolute value for stress detection.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NM-001', 'sat_source'),
 ('D14-NM-001', 'scene_valid_pixel_pct'),
 ('D14-NM-001', 'plot_cloud_pct'),
 ('D14-NM-001', 'ndmi_mean'),
 ('D14-NM-001', 'ndmi_delta_10d')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NM-001', 0, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 72, "plot_cloud_pct": 8}'::jsonb, 'TRUE', 'compute NDMI'),
 ('D14-NM-001', 1, '{"sat_source": "sentinel-2", "scene_valid_pixel_pct": 45, "plot_cloud_pct": 8}'::jsonb, 'FALSE', 'insufficient')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NM-001', 'Gao 1996'),
 ('D14-NM-001', 'RAW MASTER §4.1, §7.5')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NM-001', 'feeds_into', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NM-002', 14, 'NM', 3, 'yellow', 'G3',
  'NDMI has dropped 0.10 or more over 10 days AND sub-node moisture reads adequate AND advisory confidence is at least 0.5',
  'NDMI १० दिवसांत ०.१० किंवा अधिक कमी झाले परंतु सब-नोड मृदा-ओलावा पुरेसा दाखवत आहे',
  'ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == ''adequate'' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Open a plot-specific investigation. Likely non-water causes: (1) drip line partly blocked or emitter uneven — check flow at 3 points; (2) pest — check root and stem base; (3) root damage from tillage. Do NOT increase irrigation on this signal alone.',
  'प्लॉट-विशिष्ट तपासणी उघडा. संभाव्य पाणी-नसलेली कारणे: (१) ठिबक अंशतः बंद किंवा emitter असमान — ३ ठिकाणी flow तपासा; (२) कीड — मूळ व खोड-आधार तपासा; (३) मशागतीमुळे मूळ इजा. फक्त या सिग्नलवर सिंचन वाढवू नका.',
  'NDMI drop with adequate root-zone moisture is definitionally not a water shortage. The signal is real but the cause is something else — Section 10 case A.',
  'Investigation_dispatched.',
  0.72, 'B', 'DERIVED', NULL, 'same_season',
  'Drip clogging in Kannad basaltic soils is the most common culprit for this pattern in G3-G4. Farmers who irrigate more when the leaves droop make the drip problem worse — this rule catches it before that mistake.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NM-002', 'ndmi_delta_10d'),
 ('D14-NM-002', 'sub_node_moisture_status'),
 ('D14-NM-002', 'sat_advisory_confidence'),
 ('D14-NM-002', 'current_stage'),
 ('D14-NM-002', 'ndmi_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NM-002', 0, '{"ndmi_delta_10d": -0.12, "sub_node_moisture_status": "adequate", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'leaves dry, soil wet — non-water stress'),
 ('D14-NM-002', 1, '{"ndmi_delta_10d": -0.12, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'normal water stress — different rule'),
 ('D14-NM-002', 2, '{"ndmi_delta_10d": -0.05, "sub_node_moisture_status": "adequate", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'small change'),
 ('D14-NM-002', 3, '{"ndmi_delta_10d": -0.12, "sub_node_moisture_status": "stale", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'sub-node stale — different rule FU-004')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NM-002', 'RAW MASTER §7.5, §10.2 case A')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NM-002', 'feeds_into', 3),
 ('D14-NM-002', 'feeds_into', 5),
 ('D14-NM-002', 'feeds_into', 8),
 ('D14-NM-002', 'depends_on', 14),
 ('D14-NM-002', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-NM-003', 14, 'NM', 2, 'info', 'G3',
  'NDMI has dropped 0.10 or more over 10 days AND sub-node moisture reads low AND advisory confidence is at least 0.5',
  'NDMI १० दिवसांत ०.१० किंवा अधिक कमी आणि सब-नोड मृदा-ओलावा कमी',
  'ndmi_delta_10d <= -0.10 AND sub_node_moisture_status == ''low'' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Do not emit a separate message. Contribute a confidence-tag (''canopy_moisture_confirms'') to whichever D03 irrigation rule is currently active for this plot. This upgrades D03''s own alert from moderate to strong confidence. If no D03 rule is currently active, log a tag for the next one that fires.',
  'स्वतंत्र संदेश देऊ नका. सध्या सक्रिय असलेल्या D03 सिंचन नियमाला ''canopy_moisture_confirms'' हा confidence-tag जोडा. D03 चा सल्ला मध्यम पासून प्रबळ विश्वासाला वाढवा. D03 चा कोणताही नियम सध्या सक्रिय नसल्यास पुढच्यासाठी tag नोंदवा.',
  'Section 10 case C — both signals agree. The canonical high-confidence green flag for the sub-node''s water shortage story.',
  'Confidence increment on existing D03 rule; no separate u-value.',
  0.8, 'B', 'DERIVED', NULL, 'same_season',
  'This is where satellite genuinely adds value — confirming what the sub-node already saw. The message stays with D03; the confidence bump is invisible to the farmer but shows up as a stronger recommendation.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-NM-003', 'ndmi_delta_10d'),
 ('D14-NM-003', 'sub_node_moisture_status'),
 ('D14-NM-003', 'sat_advisory_confidence'),
 ('D14-NM-003', 'current_stage'),
 ('D14-NM-003', 'ndmi_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-NM-003', 0, '{"ndmi_delta_10d": -0.12, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'double signal — water stress'),
 ('D14-NM-003', 1, '{"ndmi_delta_10d": -0.12, "sub_node_moisture_status": "adequate", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'handled by NM-002'),
 ('D14-NM-003', 2, '{"ndmi_delta_10d": -0.05, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'small NDMI change')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-NM-003', 'RAW MASTER §10.2 case C'),
 ('D14-NM-003', 'Domain 3 irrigation rules')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-NM-003', 'feeds_into', 3),
 ('D14-NM-003', 'depends_on', 14),
 ('D14-NM-003', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-SR-001', 14, 'SR', 4, 'info', 'ALL',
  'A Sentinel-1 GRD scene is received for the plot polygon',
  'प्लॉट polygon साठी Sentinel-1 GRD दृश्य प्राप्त',
  'sat_source == ''sentinel-1'' AND sar_gap_days IS NOT NULL', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Run the standard SNAP or Sentinel-Hub chain (orbit, noise removal, calibration, terrain flattening, speckle filter, terrain correction, multi-look over polygon). Store sigma-nought values, compute RVI, delta_vv, and coherence against the last acquisition from the same relative orbit.',
  'मानक SNAP किंवा Sentinel-Hub साखळी चालवा. सिग्मा-नॉट मूल्ये साठवा; RVI, delta_vv, आणि coherence त्याच relative orbit च्या मागील acquisition विरुद्ध मोजा.',
  'SAR is monsoon-primary for Kannad ginger — it is the only satellite signal available with reasonable frequency in Jul-Aug when optical is blinded.',
  'Enables all SR rules and the monsoon SAR-only mode PL-001.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'Kannad falls in Sentinel-1 relative orbits 92 (ascending) and 165 (descending); both give data. Do not mix the two in delta_vv or coherence — the look angles differ.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-SR-001', 'sat_source'),
 ('D14-SR-001', 'sar_gap_days'),
 ('D14-SR-001', 'sar_vv_db'),
 ('D14-SR-001', 'sar_vh_db'),
 ('D14-SR-001', 'sar_rvi'),
 ('D14-SR-001', 'sar_vv_delta_db'),
 ('D14-SR-001', 'sar_coherence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-SR-001', 0, '{"sat_source": "sentinel-1", "sar_gap_days": 3}'::jsonb, 'TRUE', 'SAR scene arrived'),
 ('D14-SR-001', 1, '{"sat_source": "sentinel-2", "sar_gap_days": 3}'::jsonb, 'FALSE', 'optical scene — different pipeline'),
 ('D14-SR-001', 2, '{"sat_source": "sentinel-1", "sar_gap_days": null}'::jsonb, 'FALSE', 'gap unknown')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-SR-001', 'ESA Sentinel-1 handbook'),
 ('D14-SR-001', 'RAW MASTER §6')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-SR-001', 'feeds_into', 3),
 ('D14-SR-001', 'feeds_into', 6),
 ('D14-SR-001', 'feeds_into', 9)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-SR-002', 14, 'SR', 5, 'red', 'ALL',
  'SAR VV has dropped by more than 4 dB against the previous same-orbit acquisition AND rainfall event exists in the last 48 hours',
  'SAR VV त्याच orbit च्या मागील acquisition विरुद्ध ४ dB पेक्षा जास्त घसरले आणि मागील ४८ तासांत पाऊस झाला',
  'sar_vv_delta_db < -4.0 AND rainfall_last_48h_mm > 20 AND sar_gap_days <= 12', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Send an URGENT alert to the farmer: satellite radar shows probable standing water on the plot after the recent rain. Inspect drainage channels and remove blockages today. Ginger cannot tolerate more than 24 hours of waterlogging without rhizome damage. If sub-node is available, it will confirm; if it is not (monsoon LoRa fade common), do not wait for confirmation to act.',
  'शेतकऱ्याला URGENT इशारा पाठवा: नुकत्याच झालेल्या पावसानंतर उपग्रह रडार दाखवत आहे प्लॉटवर पाणी साचले आहे. आजच निचरा नाल्यांची तपासणी करा व अडथळे काढा. आले २४ तासांपेक्षा जास्त पाण्यात राहू शकत नाही — गड्ड्याला इजा होते. सब-नोड उपलब्ध असल्यास पुष्टी देईल; नसल्यास (मान्सूनमध्ये LoRa fade सामान्य) पुष्टीची वाट पाहू नका.',
  'Water is specular at C-band, causing near-total backscatter loss. A 4 dB drop is well outside speckle noise. See RAW MASTER §6.6 caveats.',
  'Waterlogging in G2-G4 for 48+ hours cuts yield 10-25% depending on stage; D06 has the drainage-failure branch.',
  0.78, 'A', 'DERIVED', NULL, 'same_season',
  'Kannad''s Sep-Oct cyclonic rainfall events are the most common trigger of this rule. Farmers often assume the field ''drained overnight'' because the surface looks dry; the SAR sees standing water hidden in furrows for 2-3 days. This is one of the highest-value satellite signals for this crop.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-SR-002', 'sar_vv_delta_db'),
 ('D14-SR-002', 'rainfall_last_48h_mm'),
 ('D14-SR-002', 'sar_gap_days'),
 ('D14-SR-002', 'sar_vv_db')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-SR-002', 0, '{"sar_vv_delta_db": -5.5, "rainfall_last_48h_mm": 45, "sar_gap_days": 6}'::jsonb, 'TRUE', 'drainage failure suspected'),
 ('D14-SR-002', 1, '{"sar_vv_delta_db": -5.5, "rainfall_last_48h_mm": 5, "sar_gap_days": 6}'::jsonb, 'FALSE', 'VV drop without rain — likely other cause'),
 ('D14-SR-002', 2, '{"sar_vv_delta_db": -2.0, "rainfall_last_48h_mm": 45, "sar_gap_days": 6}'::jsonb, 'FALSE', 'VV drop within noise band'),
 ('D14-SR-002', 3, '{"sar_vv_delta_db": -5.5, "rainfall_last_48h_mm": 45, "sar_gap_days": 20}'::jsonb, 'FALSE', 'SAR too stale for reliable delta')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-SR-002', 'Torres et al. 2012 Sentinel-1 mission'),
 ('D14-SR-002', 'Small 2011'),
 ('D14-SR-002', 'ICAR-CRIDA drainage studies'),
 ('D14-SR-002', 'RAW MASTER §6.3, §6.6')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-SR-002', 'feeds_into', 3),
 ('D14-SR-002', 'feeds_into', 6),
 ('D14-SR-002', 'depends_on', 14),
 ('D14-SR-002', 'depends_on', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-SR-003', 14, 'SR', 3, 'info', 'G4',
  'SAR coherence between the last two same-orbit acquisitions has dropped below 0.4 AND stage is G4 or later AND rainfall in the last 48 hours is under 20 mm',
  'मागील दोन SAR acquisitions मधील coherence ०.४ पेक्षा कमी झाले आणि अवस्था G4 पुढे व अलीकडे मोठा पाऊस नाही',
  'sar_coherence < 0.4 AND STAGE IN [G4, G5] AND rainfall_last_48h_mm < 20 AND sar_gap_days <= 12', 'dsl-1.0', 'EVENT', FALSE, NULL,
  'Log a probable-harvest event on the plot. Prompt the farmer (LOW priority, EVENT delivery) to confirm the harvest date and record yield if actually harvested. If not harvesting, ask what mechanical activity happened — the operations team may want to know.',
  'प्लॉटवर संभाव्य काढणी घटना नोंदवा. शेतकऱ्याला LOW priority ने विचारा — काढणी सुरू आहे का, तारीख व उत्पन्न नोंदवा. काढणी नसेल तर काय यांत्रिक क्रिया झाली विचारा.',
  'Coherence between two same-orbit acquisitions falls when the scattering surface changes. Harvest of a ginger plot is one such change; so is deep tillage or heavy foot traffic.',
  'Compliance and yield-tracking data collection. No direct treatment.',
  0.68, 'B', 'DERIVED', NULL, 'none',
  'Kannad ginger is harvested Jan-Feb; SAR coherence loss on a G4/G5 plot in that window is very likely the actual harvest and useful for the season-close reconciliation with the farmer''s reported date.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-SR-003', 'sar_coherence'),
 ('D14-SR-003', 'current_stage'),
 ('D14-SR-003', 'rainfall_last_48h_mm'),
 ('D14-SR-003', 'sar_gap_days')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-SR-003', 0, '{"sar_coherence": 0.25, "current_stage": "G5", "rainfall_last_48h_mm": 5, "sar_gap_days": 6}'::jsonb, 'TRUE', 'probable harvest activity'),
 ('D14-SR-003', 1, '{"sar_coherence": 0.25, "current_stage": "G3", "rainfall_last_48h_mm": 5, "sar_gap_days": 6}'::jsonb, 'FALSE', 'wrong stage'),
 ('D14-SR-003', 2, '{"sar_coherence": 0.25, "current_stage": "G5", "rainfall_last_48h_mm": 45, "sar_gap_days": 6}'::jsonb, 'FALSE', 'rain explains it'),
 ('D14-SR-003', 3, '{"sar_coherence": 0.75, "current_stage": "G5", "rainfall_last_48h_mm": 5, "sar_gap_days": 6}'::jsonb, 'FALSE', 'high coherence — no change')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-SR-003', 'Bamler & Hartl 1998 InSAR coherence'),
 ('D14-SR-003', 'RAW MASTER §6.5')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-SR-003', 'feeds_into', 9),
 ('D14-SR-003', 'feeds_into', 13),
 ('D14-SR-003', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-SR-004', 14, 'SR', 2, 'info', 'ALL',
  'SAR VV delta exceeds ±2 dB between two consecutive same-orbit acquisitions AND rainfall in the same window is at least 10 mm',
  'दोन एकाच orbit च्या SAR acquisitions मध्ये VV बदल २ dB पेक्षा जास्त आणि त्याच काळात पाऊस १० mm पेक्षा जास्त',
  '(sar_vv_delta_db > 2.0 OR sar_vv_delta_db < -2.0) AND rainfall_last_48h_mm >= 10 AND sar_gap_days <= 12', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Tag rainfall_last_48h_mm with confidence flag ''confirmed_by_sar''. No message. This upgrades D07''s forecast bias record with an in-situ confirmation, useful for BC series over time.',
  'rainfall_last_48h_mm ला ''confirmed_by_sar'' विश्वास ध्वज जोडा. संदेश नाही. D07 चा forecast bias रेकॉर्ड यामुळे अधिक अचूक बनतो.',
  'The cluster weather station covers ~1-2 km reliably; convective monsoon cells can land on one plot and miss the station.',
  'Bias-correction data quality; indirect.',
  0.75, 'B', 'DERIVED', NULL, 'none',
  'In Kannad''s Sep-Oct cyclonic rain regime the station-to-plot mismatch is common; this rule turns the SAR into a cheap plot-level rain gauge check.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-SR-004', 'sar_vv_delta_db'),
 ('D14-SR-004', 'rainfall_last_48h_mm'),
 ('D14-SR-004', 'sar_gap_days')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-SR-004', 0, '{"sar_vv_delta_db": 3.5, "rainfall_last_48h_mm": 25, "sar_gap_days": 6}'::jsonb, 'TRUE', 'clear wetting event'),
 ('D14-SR-004', 1, '{"sar_vv_delta_db": -3.0, "rainfall_last_48h_mm": 15, "sar_gap_days": 6}'::jsonb, 'TRUE', 'drying event after rain'),
 ('D14-SR-004', 2, '{"sar_vv_delta_db": 1.5, "rainfall_last_48h_mm": 25, "sar_gap_days": 6}'::jsonb, 'FALSE', 'within noise')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-SR-004', 'RAW MASTER §6.3'),
 ('D14-SR-004', 'Domain 7 BC series')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-SR-004', 'feeds_into', 7),
 ('D14-SR-004', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-SR-005', 14, 'SR', 3, 'info', 'ALL',
  'Optical gap has exceeded 14 days AND a Sentinel-1 acquisition is fresh (sar_gap_days at most 6)',
  'optical_gap_days १४ पेक्षा जास्त आणि Sentinel-1 acquisition ताजे (sar_gap_days जास्तीत जास्त ६)',
  'optical_gap_days > 14 AND sar_gap_days <= 6', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Set operating mode to SAR_ONLY for this plot. Suppress NV-003/004/005, NR-002/003, NM-002/003 for the duration. Continue SR-001 through SR-004. Reset when optical_gap_days drops below 10.',
  'प्लॉटला SAR_ONLY मोडमध्ये ठेवा. NV-003/004/005, NR-002/003, NM-002/003 तात्पुरते बंद करा. SR-001 ते SR-004 चालू ठेवा. optical_gap_days १० पेक्षा कमी झाल्यावर सामान्य मोडवर परत या.',
  'Kannad Jul-Aug delivers exactly this pattern for weeks at a time; ignoring it produces stale-optical false alarms.',
  'Prevents false-alarm-driven interventions.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'The Kannad ginger crop lives most of its high-stress period under monsoon cloud. Building the rule engine to work in SAR-only mode for weeks was a design goal, not an afterthought.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-SR-005', 'optical_gap_days'),
 ('D14-SR-005', 'sar_gap_days')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-SR-005', 0, '{"optical_gap_days": 18, "sar_gap_days": 5}'::jsonb, 'TRUE', 'monsoon SAR-only mode'),
 ('D14-SR-005', 1, '{"optical_gap_days": 8, "sar_gap_days": 5}'::jsonb, 'FALSE', 'optical still fresh enough'),
 ('D14-SR-005', 2, '{"optical_gap_days": 18, "sar_gap_days": 15}'::jsonb, 'FALSE', 'both stale — different rule PL-002')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-SR-005', 'RAW MASTER §3.2, §12.4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-SR-005', 'feeds_into', 14),
 ('D14-SR-005', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-LT-001', 14, 'LT', 4, 'info', 'ALL',
  'A Landsat-8 or Landsat-9 Collection-2 Level-2 ST band scene is received AND cluster air temperature is present',
  'Landsat-8/9 ST band scene प्राप्त आणि क्लस्टर हवा तापमान उपलब्ध',
  'sat_source IN [''landsat-8'', ''landsat-9''] AND air_temp_max_c IS NOT NULL', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Store lst_c from the ST band. Compute CWSI using Idso formulation with author-estimated wet/dry baselines. Log baseline set version. CWSI values above 1.0 or below 0 are clipped to [0,1].',
  'ST band वरून lst_c साठवा. Idso सूत्राने CWSI मोजा — Phase-1 च्या तात्पुरत्या baselines सह. baseline सेट आवृत्ती log करा. [०,१] बाहेरील मूल्ये clip करा.',
  'Landsat is currently the only free thermal at 100 m; MODIS at 1 km is too coarse. The 8-day combined revisit is thin but acceptable as confirmation channel.',
  'Enables LT-002/003.',
  0.75, 'A', 'DERIVED', NULL, 'none',
  'Kannad summer Landsat overpass ~10:30 IST is earlier than peak stress; the CWSI value under-detects afternoon stress. Interpret with this in mind; do not push the rule into replacing the sub-node.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-LT-001', 'sat_source'),
 ('D14-LT-001', 'air_temp_max_c'),
 ('D14-LT-001', 'lst_c'),
 ('D14-LT-001', 'cwsi')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-LT-001', 0, '{"sat_source": "landsat-9", "air_temp_max_c": 32}'::jsonb, 'TRUE', 'compute LST + CWSI'),
 ('D14-LT-001', 1, '{"sat_source": "sentinel-2", "air_temp_max_c": 32}'::jsonb, 'FALSE', 'wrong sensor'),
 ('D14-LT-001', 2, '{"sat_source": "landsat-9", "air_temp_max_c": null}'::jsonb, 'FALSE', 'missing air temperature')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-LT-001', 'USGS Landsat Collection-2 Level-2 documentation'),
 ('D14-LT-001', 'Idso et al. 1981'),
 ('D14-LT-001', 'RAW MASTER §7')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-LT-001', 'feeds_into', 3),
 ('D14-LT-001', 'depends_on', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-LT-002', 14, 'LT', 3, 'yellow', 'G3',
  'CWSI is above 0.60 AND sub-node moisture reads adequate AND advisory confidence is at least 0.5',
  'CWSI ०.६० पेक्षा जास्त आणि सब-नोड मृदा-ओलावा पुरेसा',
  'cwsi > 0.60 AND sub_node_moisture_status == ''adequate'' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Open non-water investigation, same branch as NM-002. If NM-002 has already opened one for this plot in the last 5 days, do NOT open a second — link the CWSI evidence to the existing task.',
  'NM-002 प्रमाणेच पाणी-नसलेली तपासणी उघडा. मागील ५ दिवसांत NM-002 ने आधीच task उघडलेला असल्यास नवीन उघडू नका — CWSI पुरावा त्या विद्यमान task ला जोडा.',
  'CWSI > 0.6 with wet soil is thermodynamically strong evidence of non-water stress. Section 10 case A confirmed thermally.',
  'Under NM-002 investigation grouping.',
  0.72, 'B', 'EST', NULL, 'same_season',
  'In Kannad''s summer peak, plot-scale CWSI often runs 0.5-0.7 for reasons of atmospheric noise more than plant stress; the sub-node check is not optional here.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-LT-002', 'cwsi'),
 ('D14-LT-002', 'sub_node_moisture_status'),
 ('D14-LT-002', 'sat_advisory_confidence'),
 ('D14-LT-002', 'current_stage'),
 ('D14-LT-002', 'lst_c')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-LT-002', 0, '{"cwsi": 0.72, "sub_node_moisture_status": "adequate", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'thermal non-water stress'),
 ('D14-LT-002', 1, '{"cwsi": 0.72, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'confirms water stress — LT-003'),
 ('D14-LT-002', 2, '{"cwsi": 0.35, "sub_node_moisture_status": "adequate", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'mild stress only')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-LT-002', 'Idso et al. 1981'),
 ('D14-LT-002', 'RAW MASTER §7.3, §7.5, §10.2 case A')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-LT-002', 'feeds_into', 3),
 ('D14-LT-002', 'feeds_into', 5),
 ('D14-LT-002', 'feeds_into', 8),
 ('D14-LT-002', 'depends_on', 14),
 ('D14-LT-002', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-LT-003', 14, 'LT', 2, 'info', 'G3',
  'CWSI is above 0.60 AND sub-node moisture reads low AND advisory confidence is at least 0.5',
  'CWSI ०.६० पेक्षा जास्त आणि सब-नोड मृदा-ओलावा कमी',
  'cwsi > 0.60 AND sub_node_moisture_status == ''low'' AND sat_advisory_confidence >= 0.5 AND STAGE IN [G2, G3, G4]', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Tag active D03 irrigation rule with ''thermal_confirms''. Do not emit separate message.',
  'सक्रिय D03 सिंचन नियमाला ''thermal_confirms'' tag जोडा. वेगळा संदेश देऊ नका.',
  'Section 10 case C confirmed thermally. Both sub-node moisture and canopy transpiration signal the same water shortage; thermal confirmation raises D03''s own irrigation rule from moderate to strong confidence. This is the archetypal high-confidence green flag for a real water stress episode.',
  'Confidence increment.',
  0.78, 'B', 'DERIVED', NULL, 'same_season',
  'This rule silently strengthens D03 advisories without adding to farmer message count.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-LT-003', 'cwsi'),
 ('D14-LT-003', 'sub_node_moisture_status'),
 ('D14-LT-003', 'sat_advisory_confidence'),
 ('D14-LT-003', 'current_stage')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-LT-003', 0, '{"cwsi": 0.72, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'TRUE', 'thermal confirms water stress'),
 ('D14-LT-003', 1, '{"cwsi": 0.35, "sub_node_moisture_status": "low", "sat_advisory_confidence": 0.85, "current_stage": "G3"}'::jsonb, 'FALSE', 'mild thermal')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-LT-003', 'RAW MASTER §10.2 case C')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-LT-003', 'feeds_into', 3),
 ('D14-LT-003', 'depends_on', 14),
 ('D14-LT-003', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PH-001', 14, 'PH', 3, 'info', 'ALL',
  'The plot has at least 8 NDVI observations across the season AND DAP is at least 60',
  'प्लॉटवर हंगामात किमान ८ NDVI निरीक्षणे उपलब्ध व DAP किमान ६०',
  'dap >= 60 AND ndvi_freshness_days <= 20', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Fit double-logistic to NDVI series with 4 parameters (greenup mid, senescence mid, amplitude, background). Store fitted stage-transition dates for cross-check against DAP-driven stage.',
  'NDVI मालिकेवर ४-पॅरामीटर double-logistic fit करा (greenup mid, senescence mid, amplitude, background). DAP-आधारित अवस्थेच्या तुलनेसाठी fit केलेल्या अवस्था-संक्रमण तारखा साठवा.',
  'Curve fit gives a phenology view independent of farmer-reported planting date; catches planting-date misreports.',
  'Enables PH-002.',
  0.75, 'A', 'DERIVED', NULL, 'none',
  'For Kannad''s May-15 to Jun-15 planting window, PH-001 becomes ready by mid-August, exactly when farmers most need a stage-check.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PH-001', 'dap'),
 ('D14-PH-001', 'ndvi_freshness_days'),
 ('D14-PH-001', 'ndvi_mean')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PH-001', 0, '{"dap": 75, "ndvi_freshness_days": 6}'::jsonb, 'TRUE', 'sufficient observations — fit'),
 ('D14-PH-001', 1, '{"dap": 40, "ndvi_freshness_days": 6}'::jsonb, 'FALSE', 'too early'),
 ('D14-PH-001', 2, '{"dap": 75, "ndvi_freshness_days": 25}'::jsonb, 'FALSE', 'too stale to fit')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PH-001', 'Zhang et al. 2003'),
 ('D14-PH-001', 'RAW MASTER §8.2')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PH-001', 'feeds_into', 1),
 ('D14-PH-001', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PH-002', 14, 'PH', 3, 'info', 'ALL',
  'Curve-fit-estimated stage differs from DAP-derived stage by at least one step',
  'curve-fit वरून काढलेली अवस्था DAP वरून काढलेल्या अवस्थेपेक्षा किमान एक step ने वेगळी आहे',
  'dap >= 60 AND ndvi_freshness_days <= 20', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Compare fitted stage vs DAP-derived stage. If they differ by one or more steps, dispatch a verification ask to the farmer: ''Please confirm the planting date on record is correct.'' D01 records the response and, if planting date changes, rebuilds the stage series.',
  'fit केलेली अवस्था व DAP-आधारित अवस्थेची तुलना करा. एक किंवा अधिक step ने वेगळ्या असल्यास शेतकऱ्याला पडताळणी विनंती पाठवा: ''नोंदवलेली लागवडीची तारीख बरोबर आहे का याची पुष्टी द्या.'' D01 उत्तर नोंदवते आणि गरजेनुसार stage series पुन्हा बांधते.',
  'Wrong planting date breaks every stage-conditioned rule downstream; catching it early saves an entire season of miscalibrated advisories.',
  'Prevents downstream u_value miscount rather than adding a new one.',
  0.72, 'B', 'DERIVED', NULL, 'same_season',
  'Marathwada farmers occasionally report the day the rhizome was cut rather than the day it went into the soil, or vice versa; the two can differ by a week. Curve fit catches these.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PH-002', 'dap'),
 ('D14-PH-002', 'ndvi_freshness_days'),
 ('D14-PH-002', 'current_stage')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PH-002', 0, '{"dap": 100, "ndvi_freshness_days": 6}'::jsonb, 'TRUE', 'cross-check due'),
 ('D14-PH-002', 1, '{"dap": 50, "ndvi_freshness_days": 6}'::jsonb, 'FALSE', 'too early')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PH-002', 'Sakamoto et al. 2010'),
 ('D14-PH-002', 'RAW MASTER §8.2, §8.4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PH-002', 'feeds_into', 1),
 ('D14-PH-002', 'depends_on', 14),
 ('D14-PH-002', 'depends_on', 1)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PH-003', 14, 'PH', 3, 'yellow', 'G3',
  'Peak NDVI in G3 is below 0.60 AND scenes are trusted AND advisory confidence is at least 0.5',
  'G3 अवस्थेत peak NDVI ०.६० पेक्षा कमी आणि scenes विश्वसनीय',
  'current_stage == ''G3'' AND ndvi_mean < 0.60 AND scene_valid_pixel_pct >= 60 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Dispatch a differential investigation: (a) D04 nitrogen check, (b) D02 salinity check, (c) sub-node saturation-hours history for hidden waterlogging, (d) farmer report on early emergence issues that might indicate seed vigour. This is one of the few satellite signals worth firing across four domains in parallel.',
  'differential तपासणी सुरू करा: (अ) D04 नत्र तपासणी, (आ) D02 क्षारता तपासणी, (इ) लपलेल्या पाणी साचण्यासाठी सब-नोड saturation-hours इतिहास, (ई) बियाणे शक्तीचे संकेत लवकर उगवणीच्या नोंदींतून. हा उपग्रह सिग्नल चार डोमेनवर एकाच वेळी चालवण्यायोग्य आहे.',
  'Peak canopy that undershoots a full stage window carries a strong integrated signal.',
  'Investigation branch — yield mapping through confirmed downstream domain.',
  0.72, 'B', 'EST', NULL, 'same_season',
  'Kannad''s basaltic soils occasionally hide sodicity that expresses only as chronic low canopy — invisible until we compare against expectations. This rule surfaces it.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PH-003', 'current_stage'),
 ('D14-PH-003', 'ndvi_mean'),
 ('D14-PH-003', 'scene_valid_pixel_pct'),
 ('D14-PH-003', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PH-003', 0, '{"current_stage": "G3", "ndvi_mean": 0.52, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'below healthy band'),
 ('D14-PH-003', 1, '{"current_stage": "G3", "ndvi_mean": 0.68, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'in band'),
 ('D14-PH-003', 2, '{"current_stage": "G2", "ndvi_mean": 0.52, "scene_valid_pixel_pct": 72, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'wrong stage — G2 expected lower')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PH-003', 'RAW MASTER §8.3'),
 ('D14-PH-003', 'Domain 6 differential-diagnosis architecture')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PH-003', 'feeds_into', 2),
 ('D14-PH-003', 'feeds_into', 3),
 ('D14-PH-003', 'feeds_into', 4),
 ('D14-PH-003', 'feeds_into', 6),
 ('D14-PH-003', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PH-004', 14, 'PH', 3, 'yellow', 'G4',
  'NDVI shows accelerating decline before DAP 180 AND stage is G3 or G4 AND advisory confidence is at least 0.5',
  'DAP १८० आधीच NDVI मध्ये वेगवान घसरण, अवस्था G3 किंवा G4',
  'current_stage IN [G3, G4] AND dap < 180 AND ndvi_delta_10d <= -0.12 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Dispatch to D06 wilt differential and D03 water branch. If a farmer has started lifting early, close the investigation with the lifting confirmation.',
  'D06 wilt differential व D03 पाणी शाखेकडे पाठवा. शेतकऱ्याने लवकर काढणी सुरू केली असल्यास त्यांच्या पुष्टीने तपासणी बंद करा.',
  'The senescence curve shape is stage-informative; an early decline is diagnostic across three families of causes.',
  'Under D06/D03 confirmed diagnosis.',
  0.68, 'B', 'DERIVED', NULL, 'same_season',
  'The Kannad harvest window opens in Jan; an early senescence in Nov-Dec is worth catching before it becomes an unrecoverable wilt.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PH-004', 'current_stage'),
 ('D14-PH-004', 'dap'),
 ('D14-PH-004', 'ndvi_delta_10d'),
 ('D14-PH-004', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PH-004', 0, '{"current_stage": "G4", "dap": 160, "ndvi_delta_10d": -0.14, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'early senescence'),
 ('D14-PH-004', 1, '{"current_stage": "G5", "dap": 210, "ndvi_delta_10d": -0.14, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'normal senescence stage'),
 ('D14-PH-004', 2, '{"current_stage": "G4", "dap": 160, "ndvi_delta_10d": -0.05, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'not a sharp decline')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PH-004', 'RAW MASTER §8.1, §8.3')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PH-004', 'feeds_into', 3),
 ('D14-PH-004', 'feeds_into', 6),
 ('D14-PH-004', 'feeds_into', 9),
 ('D14-PH-004', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-AN-001', 14, 'AN', 3, 'info', 'ALL',
  'Regional baseline is available AND peer baseline has fewer than 3 contributing plots',
  'Regional baseline उपलब्ध पण peer baseline मध्ये ३ पेक्षा कमी plots',
  'plot_ndvi_baseline_regional IS NOT NULL AND (plot_ndvi_baseline_peer IS NULL OR plot_area_ha >= 0.10)', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Set anomaly-mode = REGIONAL or REGIONAL+PEER. NV-003 always fires when in scope; NV-005 fires only when peer baseline is populated with 3 or more plots.',
  'anomaly-mode = REGIONAL किंवा REGIONAL+PEER निर्धारित करा. NV-003 नेहमी लागू; NV-005 फक्त peer baseline मध्ये ३+ plots असल्यास.',
  'Cluster-peer baselines mature in season 1; before that regional is all we have.',
  'Routing rule, no direct yield.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'The first Kannad commercial cluster starts with regional-only mode; peer mode kicks in around late June once 3+ plots have data.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-AN-001', 'plot_ndvi_baseline_regional'),
 ('D14-AN-001', 'plot_ndvi_baseline_peer'),
 ('D14-AN-001', 'plot_area_ha')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-AN-001', 0, '{"plot_ndvi_baseline_regional": 0.55, "plot_ndvi_baseline_peer": null, "plot_area_ha": 0.5}'::jsonb, 'TRUE', 'regional-only mode'),
 ('D14-AN-001', 1, '{"plot_ndvi_baseline_regional": 0.55, "plot_ndvi_baseline_peer": 0.6, "plot_area_ha": 0.5}'::jsonb, 'TRUE', 'both available')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-AN-001', 'RAW MASTER §9.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-AN-001', 'feeds_into', 14),
 ('D14-AN-001', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-AN-002', 14, 'AN', 2, 'info', 'ALL',
  'Plot area is below the informational-only threshold OR NDVI standard deviation across plot exceeds 0.15',
  'प्लॉट क्षेत्रफळ फार लहान किंवा प्लॉटवरील NDVI मध्ये फार जास्त विचरण',
  'plot_area_ha < 0.05 OR ndvi_std > 0.15', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Set plot_advisory_class = INFORMATIONAL_ONLY. NV/NR/NM/LT rules can still fire but their delivery downgrades to EVENT with ''informational'' severity. Farmer app labels the message with a plot-size note explaining the reduced confidence.',
  'plot_advisory_class = INFORMATIONAL_ONLY. NV/NR/NM/LT नियम चालू शकतात पण delivery EVENT + ''informational'' severity ला उतरते. शेतकऱ्याच्या app मध्ये लहान प्लॉटमुळे कमी विश्वास असल्याची स्पष्ट नोंद दिसते.',
  'A 4-6 pixel plot has more edge than interior; a mean is dominated by mixed pixels.',
  'Prevents low-quality advisory from driving action.',
  0.85, 'A', 'DERIVED', NULL, 'none',
  'Small ginger plots are common in Kannad (0.1-0.25 acre); telling farmers honestly that satellite confidence is reduced is better than pretending it isn''t.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-AN-002', 'plot_area_ha'),
 ('D14-AN-002', 'ndvi_std')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-AN-002', 0, '{"plot_area_ha": 0.03, "ndvi_std": 0.08}'::jsonb, 'TRUE', 'too small'),
 ('D14-AN-002', 1, '{"plot_area_ha": 0.3, "ndvi_std": 0.2}'::jsonb, 'TRUE', 'too heterogeneous'),
 ('D14-AN-002', 2, '{"plot_area_ha": 0.5, "ndvi_std": 0.06}'::jsonb, 'FALSE', 'normal-confidence plot')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-AN-002', 'RAW MASTER §11.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-AN-002', 'feeds_into', 14),
 ('D14-AN-002', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-AN-003', 14, 'AN', 2, 'info', 'ALL',
  'It is within the first 20 days after monsoon onset AND NDVI has risen sharply',
  'मान्सून सुरू झाल्यावर पहिल्या २० दिवसांत NDVI झपाट्याने वाढले',
  'monsoon_days_since_onset BETWEEN 0 AND 20 AND ndvi_delta_10d > 0.15 AND STAGE IN [G0, G1, G2]', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Set an internal flag: recent_ndvi_rise_may_be_weeds = TRUE. Any AN rule that would treat NDVI rise as a positive-anomaly signal checks this flag and stays silent for the flush window.',
  'अंतर्गत ध्वज नोंदवा — recent_ndvi_rise_may_be_weeds = TRUE. NDVI वाढ चांगली अनियमितता म्हणून हाताळणारे AN नियम हा ध्वज तपासतील आणि weed-flush खिडकीत शांत राहतील.',
  'Post-monsoon weed emergence in Marathwada is intense in the two weeks after onset. Historically documented.',
  'False-alarm prevention; indirect.',
  0.8, 'B', 'DERIVED', NULL, 'none',
  'Weed flush + young ginger together look identical to a super-vigorous crop from space. Suppressing the false positive is cheap; letting it through erodes trust.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-AN-003', 'monsoon_days_since_onset'),
 ('D14-AN-003', 'ndvi_delta_10d'),
 ('D14-AN-003', 'current_stage')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-AN-003', 0, '{"monsoon_days_since_onset": 8, "ndvi_delta_10d": 0.2, "current_stage": "G1"}'::jsonb, 'TRUE', 'weed flush window — suppress'),
 ('D14-AN-003', 1, '{"monsoon_days_since_onset": 30, "ndvi_delta_10d": 0.2, "current_stage": "G2"}'::jsonb, 'FALSE', 'past flush window'),
 ('D14-AN-003', 2, '{"monsoon_days_since_onset": 8, "ndvi_delta_10d": 0.05, "current_stage": "G1"}'::jsonb, 'FALSE', 'no flush')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-AN-003', 'RAW MASTER §4.5, §9.3'),
 ('D14-AN-003', 'Marathwada agronomy field notes')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-AN-003', 'feeds_into', 14),
 ('D14-AN-003', 'depends_on', 7)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-AN-004', 14, 'AN', 2, 'info', 'ALL',
  'A farmer scout report has arrived on a plot where a satellite anomaly is open',
  'उपग्रह अनियमितता उघडलेल्या प्लॉटवर शेतकऱ्याचा scout अहवाल आला',
  'scout_request_pending IS FALSE AND farmer_scout_report_days_ago IS NOT NULL AND farmer_scout_report_days_ago <= 3', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Read the scout report. If it confirms a specific cause, escalate that cause through its home domain (D03/D04/D06). If it clears the plot, close the satellite anomaly. Log the resolution against the anomaly rule that opened it.',
  'scout अहवाल वाचा. विशिष्ट कारण पुष्टी झाल्यास त्याच्या मूळ डोमेनमार्फत (D03/D04/D06) escalate करा. प्लॉट मोकळा असल्याची पुष्टी झाल्यास उपग्रह अनियमितता बंद करा. निराकरण मूळ नियमाशी जोडून log करा.',
  'Section 8.4 double-signal principle. Satellite opens an investigation; ground truth closes it.',
  'Closure tracking; indirect.',
  0.85, 'A', 'DERIVED', NULL, 'same_season',
  'The scout-report loop is the difference between an alert system and a working advisory system.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-AN-004', 'scout_request_pending'),
 ('D14-AN-004', 'farmer_scout_report_days_ago')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-AN-004', 0, '{"scout_request_pending": false, "farmer_scout_report_days_ago": 1}'::jsonb, 'TRUE', 'recent scout — process'),
 ('D14-AN-004', 1, '{"scout_request_pending": true, "farmer_scout_report_days_ago": null}'::jsonb, 'FALSE', 'still waiting'),
 ('D14-AN-004', 2, '{"scout_request_pending": false, "farmer_scout_report_days_ago": 10}'::jsonb, 'FALSE', 'too old to link')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-AN-004', 'RAW MASTER §8.4'),
 ('D14-AN-004', 'Domain 6 differential architecture')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-AN-004', 'feeds_into', 3),
 ('D14-AN-004', 'feeds_into', 4),
 ('D14-AN-004', 'feeds_into', 6),
 ('D14-AN-004', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-FU-001', 14, 'FU', 4, 'info', 'ALL',
  'Sub-node moisture is stale AND satellite indicates canopy stress',
  'सब-नोड शिळा आणि उपग्रह पर्णसमूह ताण दाखवत आहे',
  'sub_node_moisture_status == ''stale'' AND (ndmi_delta_10d <= -0.10 OR cwsi > 0.60) AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Send an INVESTIGATIVE advisory: ''Sub-node reading not received recently. Satellite view shows canopy stress. Please visit the plot and check moisture manually.'' Priority: high; delivery: ONCE_UNTIL_RESOLVED. Do NOT auto-schedule irrigation.',
  'तपासणी सल्ला पाठवा: ''सब-नोडची अलीकडची नोंद मिळाली नाही. उपग्रह दृश्यात पर्णसमूह ताण दिसतो. कृपया प्लॉटवर जाऊन हाताने ओलावा तपासा.'' प्राधान्य: उच्च; delivery: ONCE_UNTIL_RESOLVED. स्वयंचलित सिंचन ठरवू नका.',
  'Section 10 case E — one input silent, the other present. The living response is to have a human look, not to guess.',
  'Under D03/D06 confirmed downstream.',
  0.68, 'B', 'DERIVED', NULL, 'same_season',
  'Monsoon LoRa fade is the common cause of sub-node staleness in Kannad. This rule keeps the advisory alive without pretending we still have ground truth.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-FU-001', 'sub_node_moisture_status'),
 ('D14-FU-001', 'ndmi_delta_10d'),
 ('D14-FU-001', 'cwsi'),
 ('D14-FU-001', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-FU-001', 0, '{"sub_node_moisture_status": "stale", "ndmi_delta_10d": -0.12, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'satellite steps in'),
 ('D14-FU-001', 1, '{"sub_node_moisture_status": "adequate", "ndmi_delta_10d": -0.12, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'handled by NM-002'),
 ('D14-FU-001', 2, '{"sub_node_moisture_status": "stale", "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'no clear satellite stress')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-FU-001', 'RAW MASTER §10.2 case E')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-FU-001', 'feeds_into', 3),
 ('D14-FU-001', 'feeds_into', 6),
 ('D14-FU-001', 'depends_on', 14),
 ('D14-FU-001', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-FU-002', 14, 'FU', 3, 'info', 'ALL',
  'Sub-node moisture reads low AND satellite canopy looks healthy AND advisory confidence at least 0.5',
  'सब-नोड मृदा-ओलावा कमी पण उपग्रहावर पर्णसमूह निरोगी दिसतो',
  'sub_node_moisture_status == ''low'' AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Tag D03 irrigation rule with ''early_action_window''. Do NOT emit a separate message. D03''s own irrigation rule fires with its own message and takes credit for the action; this rule contributes a leading-indicator confidence increment.',
  'D03 सिंचन नियमाला ''early_action_window'' tag जोडा. वेगळा संदेश देऊ नका. D03 चा स्वतःचा सिंचन नियम त्याच्या संदेशासह चालतो; हा नियम फक्त leading-indicator विश्वास वाढवतो.',
  'Section 10 case B — the sub-node is the authority, and the satellite is a leading confidence indicator.',
  'Under D03.',
  0.75, 'B', 'DERIVED', NULL, 'same_season',
  'This is the case where satellite adds the most predictive value — sub-node says act, satellite says the canopy hasn''t punished you yet, so acting now avoids the punishment.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-FU-002', 'sub_node_moisture_status'),
 ('D14-FU-002', 'ndmi_delta_10d'),
 ('D14-FU-002', 'cwsi'),
 ('D14-FU-002', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-FU-002', 0, '{"sub_node_moisture_status": "low", "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'early-action window'),
 ('D14-FU-002', 1, '{"sub_node_moisture_status": "low", "ndmi_delta_10d": -0.12, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'canopy already stressed — NM-003'),
 ('D14-FU-002', 2, '{"sub_node_moisture_status": "adequate", "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'sub-node not calling')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-FU-002', 'RAW MASTER §10.2 case B')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-FU-002', 'feeds_into', 3),
 ('D14-FU-002', 'depends_on', 14),
 ('D14-FU-002', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-FU-003', 14, 'FU', 3, 'info', 'ALL',
  'SAR indicates surface standing water AND sub-node moisture reads adequate',
  'SAR वरून प्लॉटवर पाणी साचल्याचे दिसते पण सब-नोड मृदा-ओलावा पुरेसा दाखवतो',
  'sar_vv_delta_db < -3.0 AND sub_node_moisture_status == ''adequate'' AND sar_gap_days <= 12', 'dsl-1.0', 'EVENT', FALSE, NULL,
  'Send an ADVISORY (not URGENT): ''Satellite shows standing water on part of your plot. Root-zone moisture is still normal. Check surface drainage — likely a blocked furrow or edge that needs clearing before the next rain.'' Delivery: EVENT.',
  'सल्ला पाठवा (URGENT नाही): ''उपग्रहावर तुमच्या प्लॉटच्या भागावर पाणी साचलेले दिसते. रूट-झोन ओलावा अजून सामान्य आहे. पुढच्या पावसाआधी बंद पडलेला वाफा किंवा कडा साफ करा.'' Delivery: EVENT.',
  'Section 10 case F — sub-node monitors depth, satellite monitors surface. Both true, different problems.',
  'Preventive; averts full waterlogging.',
  0.72, 'B', 'DERIVED', NULL, 'same_season',
  'In Kannad''s furrow-planted ginger, blocked furrows accumulate surface water for days before it either drains or reaches the rhizome. Catching it at the surface stage is much cheaper.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-FU-003', 'sar_vv_delta_db'),
 ('D14-FU-003', 'sub_node_moisture_status'),
 ('D14-FU-003', 'sar_gap_days')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-FU-003', 0, '{"sar_vv_delta_db": -4.5, "sub_node_moisture_status": "adequate", "sar_gap_days": 6}'::jsonb, 'TRUE', 'surface waterlogging'),
 ('D14-FU-003', 1, '{"sar_vv_delta_db": -4.5, "sub_node_moisture_status": "saturated", "sar_gap_days": 6}'::jsonb, 'FALSE', 'root zone also flooded — SR-002 branch'),
 ('D14-FU-003', 2, '{"sar_vv_delta_db": -1.5, "sub_node_moisture_status": "adequate", "sar_gap_days": 6}'::jsonb, 'FALSE', 'within noise')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-FU-003', 'RAW MASTER §10.2 case F'),
 ('D14-FU-003', 'ICAR-CRIDA drainage studies')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-FU-003', 'feeds_into', 3),
 ('D14-FU-003', 'feeds_into', 8),
 ('D14-FU-003', 'depends_on', 14),
 ('D14-FU-003', 'depends_on', 3)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-FU-004', 14, 'FU', 3, 'info', 'ALL',
  'Sub-node EC reads normal AND satellite NDRE is below expected in closed canopy',
  'सब-नोड EC सामान्य पण बंद पर्णसमूह अवस्थेत NDRE अपेक्षेपेक्षा कमी',
  'sub_node_ec_status == ''normal'' AND current_stage IN [G3, G4] AND plot_ndre_gap_regional < -0.10 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Dispatch D04 leaf-tissue test scheduling. Do not recommend a specific micro-nutrient without the test.',
  'D04 पर्ण-ऊतक चाचणी नियोजनाकडे पाठवा. चाचणीशिवाय विशिष्ट सूक्ष्म-अन्नद्रव्य शिफारस करू नका.',
  'Bulk EC misses localised deficiencies of Zn, Fe, Mn — which the leaf-side NDRE picks up.',
  'Under D04.',
  0.65, 'B', 'EST', NULL, 'same_season',
  'Kannad basaltic soils are Zn-deficient in many pockets; D02 baseline test flags it if performed, but many plots skip micronutrient panels. This rule catches what D02 missed.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-FU-004', 'sub_node_ec_status'),
 ('D14-FU-004', 'current_stage'),
 ('D14-FU-004', 'plot_ndre_baseline_regional'),
 ('D14-FU-004', 'ndre_mean'),
 ('D14-FU-004', 'sat_advisory_confidence'),
 ('D14-FU-004', 'plot_ndre_gap_regional')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-FU-004', 0, '{"sub_node_ec_status": "normal", "current_stage": "G3", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.13}'::jsonb, 'TRUE', 'micro-nutrient suspected'),
 ('D14-FU-004', 1, '{"sub_node_ec_status": "normal", "current_stage": "G2", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.12}'::jsonb, 'FALSE', 'wrong stage'),
 ('D14-FU-004', 2, '{"sub_node_ec_status": "high", "current_stage": "G3", "sat_advisory_confidence": 0.85, "plot_ndre_gap_regional": -0.13}'::jsonb, 'FALSE', 'EC also suggests issue — different branch')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-FU-004', 'RAW MASTER §10.2 case G'),
 ('D14-FU-004', 'Marathwada Zn deficiency literature')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-FU-004', 'feeds_into', 4),
 ('D14-FU-004', 'depends_on', 14),
 ('D14-FU-004', 'depends_on', 4)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-FU-005', 14, 'FU', 2, 'info', 'ALL',
  'Sub-node moisture adequate AND EC normal AND all satellite indices in healthy band',
  'सब-नोड ओलावा व EC सामान्य आणि सर्व उपग्रह निर्देशांक निरोगी पल्ल्यात',
  'sub_node_moisture_status == ''adequate'' AND sub_node_ec_status == ''normal'' AND ndvi_mean >= 0.45 AND ndmi_delta_10d > -0.05 AND cwsi < 0.40 AND sat_advisory_confidence >= 0.5', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Log a plot_health_green_flag entry with timestamp and contributing evidence. No farmer message. Used by season-review, buyer attestation, and DPDP consent-limited third-party sharing.',
  'plot_health_green_flag नोंद वेळेसह व पुराव्यासह log करा. शेतकऱ्याला संदेश नाही. हंगाम-आढावा, खरेदीदार-प्रमाणीकरण व DPDP-अनुमत तृतीय-पक्ष सामायिकीकरणासाठी वापर.',
  'Section 10 case H. High-confidence positive attestation is a business asset.',
  'Indirect — attestation value.',
  0.82, 'A', 'DERIVED', NULL, 'none',
  'For Kannad market linkages this is the log that lets Agro-Guardian tell a buyer, honestly, that a plot has been under continuous good-health confirmation.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-FU-005', 'sub_node_moisture_status'),
 ('D14-FU-005', 'sub_node_ec_status'),
 ('D14-FU-005', 'ndvi_mean'),
 ('D14-FU-005', 'ndmi_delta_10d'),
 ('D14-FU-005', 'cwsi'),
 ('D14-FU-005', 'sat_advisory_confidence')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-FU-005', 0, '{"sub_node_moisture_status": "adequate", "sub_node_ec_status": "normal", "ndvi_mean": 0.65, "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'TRUE', 'all green'),
 ('D14-FU-005', 1, '{"sub_node_moisture_status": "low", "sub_node_ec_status": "normal", "ndvi_mean": 0.65, "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'sub-node calling'),
 ('D14-FU-005', 2, '{"sub_node_moisture_status": "adequate", "sub_node_ec_status": "normal", "ndvi_mean": 0.35, "ndmi_delta_10d": -0.02, "cwsi": 0.3, "sat_advisory_confidence": 0.85}'::jsonb, 'FALSE', 'NDVI too low')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-FU-005', 'RAW MASTER §10.2 case H')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-FU-005', 'feeds_into', 13),
 ('D14-FU-005', 'depends_on', 14),
 ('D14-FU-005', 'depends_on', 3),
 ('D14-FU-005', 'depends_on', 4)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PL-001', 14, 'PL', 4, 'info', 'ALL',
  'Plot polygon geometry is missing or fails validation',
  'प्लॉट polygon भूगोलनोंद उपलब्ध नाही किंवा वैधता चाचणी अपयशी',
  'plot_polygon_wkt IS NULL OR plot_area_ha IS NULL', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Suspend all D14 rules for this plot. Send a low-priority prompt to the farmer app requesting plot boundary capture. Restore when polygon is provided.',
  'या प्लॉटवरील सर्व D14 नियम स्थगित करा. शेतकऱ्याच्या app वर कमी-प्राधान्य विनंती पाठवा — प्लॉट सीमा नोंदवा. Polygon दिल्यावर पुन्हा सक्रिय.',
  'Precondition rule. Every satellite advisory rule in Domain 14 requires a valid plot polygon; without one the pixel extract, all indices, all baselines and all anomaly detections are meaningless. Failing closed with a farmer-side prompt is the honest response.',
  'None; enables all downstream.',
  0.95, 'A', 'DERIVED', NULL, 'none',
  'New farmer onboarding step. The Kannad app team owns polygon capture UX; polygon quality is the single biggest determinant of D14 usefulness.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PL-001', 'plot_polygon_wkt'),
 ('D14-PL-001', 'plot_area_ha')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PL-001', 0, '{"plot_polygon_wkt": null, "plot_area_ha": null}'::jsonb, 'TRUE', 'no polygon'),
 ('D14-PL-001', 1, '{"plot_polygon_wkt": "POLYGON((...))", "plot_area_ha": 0.5}'::jsonb, 'FALSE', 'polygon present')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PL-001', 'RAW MASTER §12.4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PL-001', 'feeds_into', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PL-002', 14, 'PL', 3, 'info', 'ALL',
  'Both optical and SAR are stale beyond the maximum advisory freshness AND scout report is also older than 5 days',
  'optical व SAR दोन्ही maximum ताजेपणापेक्षा शिळे आणि scout अहवाल ५ पेक्षा जास्त दिवसांचा',
  'optical_gap_days > 21 AND sar_gap_days > 12 AND (farmer_scout_report_days_ago IS NULL OR farmer_scout_report_days_ago > 5)', 'dsl-1.0', 'ONCE_UNTIL_RESOLVED', FALSE, NULL,
  'Set operating mode to BLIND_PLOT. Suspend NV/NR/NM/AN/FU rules. Send a high-priority prompt: ''We have not seen your plot from any source for over 3 weeks. Please visit and send a photo.'' Reset when any source comes back.',
  'operating mode = BLIND_PLOT. NV/NR/NM/AN/FU स्थगित. उच्च-प्राधान्य विनंती पाठवा: ''३ आठवड्यांहून अधिक काळ आम्हाला तुमचा प्लॉट कोणत्याही स्रोतातून दिसलेला नाही. कृपया भेट देऊन फोटो पाठवा.'' कोणताही स्रोत परत आल्यावर सामान्य मोड.',
  'Advisory in blindness is worse than no advisory.',
  'Prevents low-confidence action.',
  0.9, 'A', 'DERIVED', NULL, 'none',
  'Extremely rare in Kannad — even peak monsoon delivers a Sentinel-1 pass every 6-12 days. When it does happen, honesty is the only response.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PL-002', 'optical_gap_days'),
 ('D14-PL-002', 'sar_gap_days'),
 ('D14-PL-002', 'farmer_scout_report_days_ago')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PL-002', 0, '{"optical_gap_days": 25, "sar_gap_days": 15, "farmer_scout_report_days_ago": 10}'::jsonb, 'TRUE', 'fully blind'),
 ('D14-PL-002', 1, '{"optical_gap_days": 25, "sar_gap_days": 5, "farmer_scout_report_days_ago": 10}'::jsonb, 'FALSE', 'SAR still fresh'),
 ('D14-PL-002', 2, '{"optical_gap_days": 25, "sar_gap_days": 15, "farmer_scout_report_days_ago": 2}'::jsonb, 'FALSE', 'scout fresh')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PL-002', 'RAW MASTER §12.4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PL-002', 'feeds_into', 14),
 ('D14-PL-002', 'depends_on', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PL-003', 14, 'PL', 2, 'info', 'ALL',
  'Pipeline version has changed since the last stored indices',
  'मागील साठवलेल्या निर्देशांकांच्या तुलनेत pipeline आवृत्ती बदलली आहे',
  'sat_pipeline_version IS NOT NULL', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Compare sat_pipeline_version to last stored version for the plot. If different, run baseline recomputation of ndvi_delta_10d, ndmi_delta_10d, ndre_slope_5d against the same pipeline version before any AN or PH rule fires. Log the migration event.',
  'sat_pipeline_version प्लॉटवरील मागील साठवलेल्या आवृत्तीशी तुलना करा. वेगळी असल्यास AN किंवा PH नियम चालण्यापूर्वी त्याच आवृत्तीत ndvi_delta_10d, ndmi_delta_10d, ndre_slope_5d ची पुनर्गणना करा. migration घटना log करा.',
  'Trend analysis across pipeline versions is a known source of false anomalies in satellite pipelines.',
  'None; protects downstream.',
  0.9, 'A', 'DERIVED', NULL, 'none',
  'This is exactly the kind of gate the D07 station_data_age_hours pattern was designed to enforce — extend it to D14.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PL-003', 'sat_pipeline_version')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PL-003', 0, '{"sat_pipeline_version": "pipeline-1.2.0"}'::jsonb, 'TRUE', 'log version'),
 ('D14-PL-003', 1, '{"sat_pipeline_version": null}'::jsonb, 'FALSE', 'pipeline unknown — different rule fires')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PL-003', 'RAW MASTER §12.4')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PL-003', 'feeds_into', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-PL-004', 14, 'PL', 3, 'info', 'ALL',
  'Scene valid pixel percentage is below the minimum trusted threshold',
  'scene_valid_pixel_pct विश्वसनीय minimum पेक्षा कमी',
  'scene_valid_pixel_pct < 60 AND sat_source == ''sentinel-2''', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Skip index computation for the scene. Log ''scene_rejected_low_valid_pixel''. Do not update ndvi_freshness_days from this scene — treat as if the scene did not arrive.',
  'दृश्यासाठी निर्देशांक गणना वगळा. ''scene_rejected_low_valid_pixel'' log करा. या दृश्यावरून ndvi_freshness_days अद्ययावत करू नका — दृश्य आले नाही असे मानून पुढे जा.',
  'Bad scenes generate false anomalies; fail closed rather than fail loud.',
  'None; false alarm prevention.',
  0.9, 'A', 'DERIVED', NULL, 'none',
  'Kannad monsoon delivers many partial scenes; enforcing the 60% floor keeps season data clean.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-PL-004', 'scene_valid_pixel_pct'),
 ('D14-PL-004', 'sat_source')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-PL-004', 0, '{"scene_valid_pixel_pct": 45, "sat_source": "sentinel-2"}'::jsonb, 'TRUE', 'reject scene'),
 ('D14-PL-004', 1, '{"scene_valid_pixel_pct": 72, "sat_source": "sentinel-2"}'::jsonb, 'FALSE', 'accept'),
 ('D14-PL-004', 2, '{"scene_valid_pixel_pct": 45, "sat_source": "sentinel-1"}'::jsonb, 'FALSE', 'SAR not gated this way')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-PL-004', 'RAW MASTER §9.3')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-PL-004', 'feeds_into', 14)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-001', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''the satellite detects ginger rhizome rot''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''उपग्रह आल्यातील गड्डा कूज ओळखतो'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_001''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. The underground rhizome is invisible to every current satellite; canopy signal is late and shared with several other causes. See RAW MASTER §5.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. भूमिगत गड्डा कोणत्याही उपग्रहाला दिसत नाही; पर्णसमूह-सिग्नल उशीरचा व अनेक कारणांचा common आहे. RAW MASTER §5 पहा.',
  'The underground rhizome is invisible to every current satellite; canopy signal is late and shared with several other causes. See RAW MASTER §5.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-001', 'outgoing_message_contains_claim'),
 ('D14-POS-001', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-001', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_001"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-001', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_001"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-001', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-001', 'RAW MASTER §5'),
 ('D14-POS-001', 'Domain 6 rhizome-canopy decoupling architecture note')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-001', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-002', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''NDVI tells you when to harvest''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''NDVI काढणीची अचूक वेळ सांगते'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_002''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Canopy senescence signals a stage window, not maturity precision. Harvest timing is a D09 rule with sub-node + DAP inputs.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. पर्णसमूह senescence अवस्थेची खिडकी सांगते, माग्युरिटीची अचूक वेळ नाही. काढणीचा निर्णय D09 चा सब-नोड + DAP आधारित नियम.',
  'Canopy senescence signals a stage window, not maturity precision. Harvest timing is a D09 rule with sub-node + DAP inputs.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-002', 'outgoing_message_contains_claim'),
 ('D14-POS-002', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-002', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_002"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-002', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_002"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-002', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-002', 'RAW MASTER §16.1'),
 ('D14-POS-002', 'Domain 9 harvest rules')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-002', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-003', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''we predict your yield from space''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''आम्ही अवकाशातून तुमचे उत्पन्न सांगतो'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_003''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Domain 12 already prohibits yield prediction as a customer claim; satellite-derived estimates carry the same prohibition.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. Domain 12 आधीच उत्पन्न-भविष्यवाणी ग्राहक-दाव्यासाठी प्रतिबंधित करते; उपग्रह-आधारित अंदाजांना तीच बंदी.',
  'Domain 12 already prohibits yield prediction as a customer claim; satellite-derived estimates carry the same prohibition.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-003', 'outgoing_message_contains_claim'),
 ('D14-POS-003', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-003', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_003"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-003', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_003"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-003', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-003', 'RAW MASTER §16.1'),
 ('D14-POS-003', 'Domain 12 prohibited claims')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-003', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-004', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''our AI counts your ginger plants from orbit''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''आमचा AI कक्षेतून तुमच्या आल्याची झाडे मोजतो'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_004''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Plant count from 10 m Sentinel-2 pixels is not physically possible. Sub-metre commercial imagery is prohibitively expensive per farmer.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. १० मी Sentinel-2 पिक्सेल्सवरून झाडांची गणना भौतिकदृष्ट्या शक्य नाही. Sub-metre व्यावसायिक imagery प्रति शेतकरी अत्यंत महाग.',
  'Plant count from 10 m Sentinel-2 pixels is not physically possible. Sub-metre commercial imagery is prohibitively expensive per farmer.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-004', 'outgoing_message_contains_claim'),
 ('D14-POS-004', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-004', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_004"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-004', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_004"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-004', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-004', 'RAW MASTER §16.1'),
 ('D14-POS-004', 'ESA Sentinel-2 resolution specification')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-004', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-005', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''cloud is not a problem for us''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''ढग आमच्यासाठी अडचण नाहीत'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_005''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Cloud is a real problem; SAR reduces but does not eliminate the gap; be honest.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. ढग खरे अडथळे आहेत; SAR ते कमी करते पण संपवत नाही; प्रामाणिक रहा.',
  'Cloud is a real problem; SAR reduces but does not eliminate the gap; be honest.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-005', 'outgoing_message_contains_claim'),
 ('D14-POS-005', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-005', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_005"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-005', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_005"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-005', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-005', 'RAW MASTER §3, §16.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-005', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-006', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''we replace your soil sensor with satellite''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''आम्ही तुमच्या मृदा सेन्सरची जागा उपग्रहाने घेतो'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_006''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Sub-node soil moisture and EC are the authorities in their domains; satellite provides context, never replaces them.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. सब-नोड मृदा-ओलावा व EC त्यांच्या डोमेनवर अधिकारी आहेत; उपग्रह संदर्भ देतो, त्यांची जागा घेत नाही.',
  'Sub-node soil moisture and EC are the authorities in their domains; satellite provides context, never replaces them.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-006', 'outgoing_message_contains_claim'),
 ('D14-POS-006', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-006', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_006"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-006', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_006"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-006', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-006', 'RAW MASTER §1.4, §16.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-006', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-POS-007', 14, 'POS', 5, 'red', 'ALL',
  'An outgoing customer message or marketing artefact contains a claim that ''our satellite view is always up-to-date''',
  'बाहेर जाणाऱ्या ग्राहक संदेशात किंवा विपणन मजकुरात ''आमचे उपग्रह दृश्य नेहमी ताजे असते'' असा दावा आहे',
  'outgoing_message_contains_claim IS TRUE AND claim_type == ''pos_007''', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the outgoing message. Log the attempted claim, the source (rule id, template, human author), and the block event. Revisit is 5-20 days depending on cloud. Freshness varies and must be shown, not hidden.',
  'बाहेर जाणारा संदेश थांबवा. प्रयत्न केलेला दावा, स्रोत (नियम id, template, लेखक) व block घटना log करा. पुनरागमन ढगांवर अवलंबून ५-२० दिवस. ताजेपणा बदलतो — तो दाखवायचा, लपवायचा नाही.',
  'Revisit is 5-20 days depending on cloud. Freshness varies and must be shown, not hidden.',
  'Reputation and truthfulness protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Kannad ginger buyers and farmers alike remember overpromises. Every one of these prohibited claims is a claim we could technically make and would regret.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-POS-007', 'outgoing_message_contains_claim'),
 ('D14-POS-007', 'claim_type')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-POS-007', 0, '{"outgoing_message_contains_claim": true, "claim_type": "pos_007"}'::jsonb, 'TRUE', 'block'),
 ('D14-POS-007', 1, '{"outgoing_message_contains_claim": false, "claim_type": "pos_007"}'::jsonb, 'FALSE', 'no claim in message'),
 ('D14-POS-007', 2, '{"outgoing_message_contains_claim": true, "claim_type": "other_pos"}'::jsonb, 'FALSE', 'different POS rule')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-POS-007', 'RAW MASTER §3, §16.1')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-POS-007', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-DP-001', 14, 'DP', 5, 'red', 'ALL',
  'A satellite chip or image would show a plot other than the current viewer''s own plot without aggregation',
  'current viewer च्या स्वतःच्या प्लॉट व्यतिरिक्त कोणत्याही प्लॉटचे उपग्रह चित्र / भाग aggregation शिवाय दाखवायचा प्रयत्न',
  'sat_public_display_context IN [''third_party'', ''cluster_aggregate''] AND third_party_share_consent_given IS FALSE', 'dsl-1.0', 'SILENT_GUARD', TRUE, NULL,
  'Block the display. Aggregate to cluster mean if legitimate cluster context is needed. Log the block event with viewer identity, plot identity, and requested purpose.',
  'प्रदर्शन थांबवा. कायदेशीर cluster context आवश्यक असल्यास cluster mean वर aggregate करा. block घटना viewer, plot, हेतू यांच्यासह log करा.',
  'DPDP Act 2023 personal data definition. See RAW MASTER §13.6.',
  'Regulatory and reputation protection.',
  0.95, 'A', 'SRC-Q', NULL, 'none',
  'Cluster displays are useful to farmers but must aggregate; showing a neighbour''s plot NDVI curve without consent is a DPDP violation. This rule is immutable for the same reason D12-DPDP-* are.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-DP-001', 'sat_public_display_context'),
 ('D14-DP-001', 'third_party_share_consent_given')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-DP-001', 0, '{"sat_public_display_context": "third_party", "third_party_share_consent_given": false}'::jsonb, 'TRUE', 'block'),
 ('D14-DP-001', 1, '{"sat_public_display_context": "third_party", "third_party_share_consent_given": true}'::jsonb, 'FALSE', 'consent given'),
 ('D14-DP-001', 2, '{"sat_public_display_context": "own_plot", "third_party_share_consent_given": false}'::jsonb, 'FALSE', 'own plot — allowed')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-DP-001', 'DPDP Act 2023'),
 ('D14-DP-001', 'RAW MASTER §13.6'),
 ('D14-DP-001', 'Domain 12 DPDP rules')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-DP-001', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_rules (rule_id,domain_id,category,priority,severity,stage_code,trigger_en,trigger_mr,trigger_expr,trigger_expr_version,delivery,immutable,immutable_reason,action_en,action_mr,agronomic_basis,yield_impact,confidence_score,source_tier,source_class,u_value,recoverability,kannad_note) VALUES
 ('D14-DP-002', 14, 'DP', 3, 'info', 'ALL',
  'A satellite product is being displayed to any user AND attribution has not yet been rendered on the current view',
  'उपग्रह उत्पादन कोणत्याही वापरकर्त्याला दाखवले जात आहे आणि श्रेय (attribution) रेंडर झालेले नाही',
  'sat_source IS NOT NULL AND sat_attribution_shown IS FALSE', 'dsl-1.0', 'SILENT_GUARD', FALSE, NULL,
  'Ensure the UI renders the required attribution before the satellite product is shown. Block if the UI cannot render attribution.',
  'उपग्रह उत्पादन दाखवण्यापूर्वी UI ने आवश्यक श्रेय रेंडर करावे. UI ते रेंडर करू शकत नसल्यास प्रदर्शन थांबवा.',
  'Every displayed satellite product carries a licence-compliance attribution requirement (Copernicus, USGS, Bhuvan, Planet). RAW MASTER Section 13.7 specifies the exact wording for each source. Silent guard enforces the UI-side template before the product renders to any user.',
  'None; regulatory.',
  0.9, 'A', 'SRC-Q', NULL, 'none',
  'Simple UI check; a template line satisfies the requirement, but the rule ensures the template is never omitted.')
ON CONFLICT (rule_id) DO NOTHING;

INSERT INTO kb_rule_fields (rule_id, field_name) VALUES
 ('D14-DP-002', 'sat_source'),
 ('D14-DP-002', 'sat_attribution_shown')
ON CONFLICT DO NOTHING;

INSERT INTO kb_golden_tests (rule_id, seq, context, expect, label) VALUES
 ('D14-DP-002', 0, '{"sat_source": "sentinel-2", "sat_attribution_shown": false}'::jsonb, 'TRUE', 'attribution missing'),
 ('D14-DP-002', 1, '{"sat_source": "sentinel-2", "sat_attribution_shown": true}'::jsonb, 'FALSE', 'attribution present'),
 ('D14-DP-002', 2, '{"sat_source": null, "sat_attribution_shown": false}'::jsonb, 'FALSE', 'no product to attribute')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_references (rule_id, reference) VALUES
 ('D14-DP-002', 'RAW MASTER §13.7'),
 ('D14-DP-002', 'Copernicus attribution requirement')
ON CONFLICT DO NOTHING;

INSERT INTO kb_rule_dependencies (rule_id, direction, target_domain_id) VALUES
 ('D14-DP-002', 'feeds_into', 12)
ON CONFLICT DO NOTHING;

INSERT INTO kb_precedence (subject_rule, relation, object_rule, reason_en, reason_mr) VALUES
 ('D07-VP-002', 'BUNDLES', 'D07-HS-004', 'Both guards fire on the same scheduled foliar spray event. One field visit, one message: list temperature or rain, VPD, and the next recommended window together.', 'दोन्ही नियम एकाच फवारणी घटनेवर लागू होतात. एकाच शेतफेरीत एकच संदेश द्या — तापमान/पाऊस, VPD, आणि पुढील शिफारशीत वेळ एकत्र सांगा.'),
 ('D14-NM-003', 'BUNDLES', 'D03-SC-001', 'NM-003 supplies a canopy-moisture confirmation tag to the active D03 scheduled-irrigation rule rather than emitting a separate farmer message. RAW MASTER §10.2 case C.', 'NM-003 सक्रिय D03 नियोजित सिंचन नियमाला canopy-moisture पुष्टी tag पुरवते — शेतकऱ्याला वेगळा संदेश नाही. RAW MASTER §10.2 case C.'),
 ('D14-LT-003', 'BUNDLES', 'D03-SC-001', 'LT-003 supplies a thermal confirmation tag to the active D03 irrigation rule. Same BUNDLES pattern as NM-003; both agree on the sub-node water story.', 'LT-003 सक्रिय D03 सिंचन नियमाला थर्मल पुष्टी tag जोडते. NM-003 सारखाच BUNDLES पॅटर्न — दोन्ही सब-नोडच्या पाणी-कथेला दुजोरा देतात.'),
 ('D14-FU-002', 'BUNDLES', 'D03-SC-001', 'FU-002 supplies an early-action-window leading-indicator tag to the active D03 irrigation rule. Sub-node says act; satellite canopy has not yet punished the plot — acting now avoids the punishment. RAW MASTER §10.2 case B.', 'FU-002 सक्रिय D03 सिंचन नियमाला early-action-window leading indicator tag जोडते. सब-नोड कारवाई मागते; उपग्रह-पर्णसमूह अजून त्रास दाखवत नाही — आता कारवाई केल्यास पुढचा त्रास टळतो. §10.2 case B.'),
 ('D14-NV-004', 'SEQUENCES', 'D06-DX-001', 'A sharp satellite NDVI drop triggers an urgent scout AND stages the D06 differential-diagnosis branch for the returning scout report. Both fire in order; the satellite alert opens the investigation, D06 closes it.', 'उपग्रह-दिसणारी झपाट्याने NDVI घसरण urgent scout चालवते आणि scout अहवाल परत आल्यावर D06 differential-diagnosis branch तयार ठेवते. दोन्ही क्रमाने चालतात — उपग्रह तपासणी उघडतो, D06 ती बंद करतो.'),
 ('D14-SR-002', 'SEQUENCES', 'D06-SW-003', 'SAR-detected standing water after heavy rain triggers URGENT drainage advisory AND stages D06''s post-monsoon saturation branch. The SR-002 alert acts immediately; D06-SW-003 handles the downstream rot-risk assessment.', 'SAR-वरून पाणी साचणे झपाट्याने URGENT निचरा सल्ला चालवते आणि D06 च्या post-monsoon saturation शाखेला क्रमाने तयार करते. SR-002 त्वरित कारवाई करते; D06-SW-003 पुढील कूज-जोखीम मूल्यांकन हाताळते.')
ON CONFLICT DO NOTHING;

INSERT INTO kb_open_items (open_item_id,domain_id,item,owner,source_class,blocking,time_sensitive,note) VALUES
 ('D07-OI-09', 7, 'Local calibration of VPD spray-window thresholds (0.4 / 0.8 / 1.5 / 2.0 kPa) against season-one spray-outcome records', 'field trial, season 1', 'EST', FALSE, FALSE, 'Current thresholds are agronomic consensus for foliar crops in general. Ginger-specific and Kannad-specific values may shift by 0.1 to 0.2 kPa in either direction after one season of paired spray-and-outcome records.'),
 ('D14-OI-01', 14, 'Publish or acquire a Kannad-region ginger NDVI baseline (season 1 log will produce this)', 'season 1 field data', 'EST', FALSE, FALSE, 'The plot_ndvi_baseline_regional field is populated by an author estimate curve; season-1 empirical data replaces it and elevates NV-003 confidence from 0.55 to ~0.75.'),
 ('D14-OI-02', 14, 'Confirm plot polygon capture UX in the farmer app', 'app team', 'EST', TRUE, FALSE, 'PL-001 blocks all D14 output for a plot without a polygon; the UX must produce clean polygons.'),
 ('D14-OI-03', 14, 'Choose one primary processing platform between GEE and Sentinel Hub for production', 'engineering', 'EST', FALSE, FALSE, 'Both work for pilot; production commitment shapes cost line and SLA.'),
 ('D14-OI-04', 14, 'Land calibrated CWSI wet/dry baselines for Kannad ginger', 'season 1 field data', 'EST', FALSE, FALSE, 'LT-002/003 use literature bands; local calibration bumps confidence from 0.72 to ~0.85.'),
 ('D14-OI-05', 14, 'Register with Copernicus Data Space and confirm quota fits a 10-cluster pilot', 'operations', 'EST', FALSE, FALSE, 'Free tier is expected to fit; verify before scale.'),
 ('D14-OI-06', 14, 'Assess FASAL / CHAMAN horticulture products for ginger coverage', 'kb_author', 'EST', FALSE, FALSE, 'May give a regional baseline for free; if it does, replaces the Phase-1 author-estimate model.'),
 ('D14-OI-07', 14, 'Verify DPDP consent covers satellite-derived plot advisory display', 'legal', 'EST', TRUE, FALSE, 'DP-001 already blocks third-party display without consent; onboarding consent language must match.'),
 ('D14-OI-08', 14, 'Coordinate with VNMKV Parbhani for phenology validation', 'kb_author', 'EST', FALSE, FALSE, 'PH-001/002 curve fitting uses published parameters; VNMKV local phenology sharpens them.'),
 ('D14-OI-09', 14, 'Season 1 falsifiable test on satellite lead time for rhizome rot', 'field trial', 'EST', FALSE, FALSE, 'RAW MASTER §5.6 test. Result decides whether any D14 rule can ever be strengthened for rot detection or whether the blind spot is fundamental.'),
 ('D14-OI-10', 14, 'Reconcile satellite-derived rainfall (GPM IMERG) with D07 rainfall', 'kb_author', 'EST', FALSE, FALSE, 'Sits between D07 and D14; assign owner and homing before adding IMERG rules.')
ON CONFLICT DO NOTHING;

-- D07 total_rules counter after VPD retrofit (was 35, now 38)
UPDATE kb_domains SET total_rules = 38 WHERE domain_id = 7 AND total_rules = 35;
