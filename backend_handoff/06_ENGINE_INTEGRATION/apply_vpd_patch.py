"""
Apply VPD retrofit patch to Ginger KB.

Scope — only additions, never edits:
  Domain 7 gains:
    - _schema.additions.rule_categories_domain_7["VP"]
    - _schema.additions.new_farm_brain_fields["vpd_kpa", "vpd_night_mean_kpa"]
    - _schema.additions.constants (VPD thresholds)
    - reference_data["vpd_context"]
    - 3 new rules: D07-VP-001, D07-VP-002, D07-VP-003
    - 1 new open_item: D07-OI-09
    - summary counters bumped to reflect additions
    - metadata.total_rules bumped, review_log entry appended
    - next_steps: VPD calibration entry appended

  Domain 11 (precedence home) gains:
    - 1 new precedence graph entry: D07-VP-002 BUNDLES with D07-HS-004

Not touched anywhere: any existing rule, trigger expression, golden test,
delivery class, precedence entry, immutable rule, or field declaration.
"""

import json
from copy import deepcopy

D7_PATH = "Domain7_Rules_Ginger.json"
D11_PATH = "Domain11_Rules_Ginger.json"

# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------
with open(D7_PATH, encoding="utf-8") as f:
    d7 = json.load(f)
with open(D11_PATH, encoding="utf-8") as f:
    d11 = json.load(f)

# Snapshot original state so we can assert we didn't touch existing rules
orig_d7_rules = deepcopy(d7["rules"])
orig_d7_rule_ids = [r["rule_id"] for r in orig_d7_rules]
orig_d11_graph = deepcopy(d11["_schema"]["additions"]["precedence"]["graph"])
orig_d11_graph_keys = {(g["subject"], g["relation"], g["object"]) for g in orig_d11_graph}

# ---------------------------------------------------------------------------
# 1. Domain 7 — _schema.additions
# ---------------------------------------------------------------------------
sch = d7["_schema"]["additions"]

# 1a. Rule category
assert "VP" not in sch["rule_categories_domain_7"], "VP category already exists!"
sch["rule_categories_domain_7"]["VP"] = "vapour pressure deficit — transpiration and spray-efficacy driver derived from air temperature and relative humidity"

# 1b. Farm-brain fields (must be declared or DSL parser rejects them)
assert "vpd_kpa" not in sch["new_farm_brain_fields"]
sch["new_farm_brain_fields"]["vpd_kpa"] = "number — vapour pressure deficit in kilopascals; derived from air_temp_max_c and rh_pct via Tetens' equation; 0.8–1.5 kPa is the plant-friendly band"
sch["new_farm_brain_fields"]["vpd_night_mean_kpa"] = "number — mean nighttime VPD (2200–0600 local) in kilopascals; below 0.3 signals almost certain dew and leaf wetness"
sch["new_farm_brain_fields"]["spray_scheduled_today"] = "boolean — true when a foliar spray of any kind is queued for the current day; used by SILENT_GUARD rules to check safety before the recommendation leaves the engine"

# 1c. Constants (author estimates; open_item flags for validation)
sch["constants"]["vpd_spray_low_kpa"] = 0.4
sch["constants"]["vpd_spray_high_kpa"] = 2.0
sch["constants"]["vpd_optimum_low_kpa"] = 0.8
sch["constants"]["vpd_optimum_high_kpa"] = 1.5
sch["constants"]["vpd_dew_probable_kpa"] = 0.3

# ---------------------------------------------------------------------------
# 2. Domain 7 — reference_data.vpd_context
# ---------------------------------------------------------------------------
d7["reference_data"]["vpd_context"] = {
    "what_it_is": "Vapour Pressure Deficit is the gap between how much moisture the air is holding and how much it could hold at the current temperature. It is the true driver of plant transpiration and of the drying-versus-evaporating fate of a spray droplet. Relative humidity alone does not carry this information: 80 percent RH at 20 C and 80 percent RH at 35 C are the same number and very different agronomic situations.",
    "formula": {
        "saturation_vapour_pressure_kpa": "e_s(T) = 0.6108 * exp( 17.27 * T / (T + 237.3) )",
        "vpd_kpa": "e_s(T) * (1 - RH/100)",
        "reference": "FAO-56 Penman–Monteith, chapter 3; Tetens 1930 formulation."
    },
    "bands_for_ginger": {
        "below_0_4_kpa": "Saturating air. Droplets do not dry. Fungal spore germination window. Spraying now is worse than not spraying. Also a strong dew and leaf-wetness signal.",
        "0_4_to_0_8_kpa": "Humid. Slow drying. Cover spray acceptable but efficacy reduced.",
        "0_8_to_1_5_kpa": "Plant-friendly band. Best window for foliar operations. Normal transpiration.",
        "1_5_to_2_0_kpa": "Dry. Droplets evaporate before uptake. Adjuvant helps; timing shift is cheaper.",
        "above_2_0_kpa": "Water-stress territory. Transpiration exceeds root supply. Do not spray. Do not add fertigation load without checking soil moisture."
    },
    "why_it_is_not_a_disease_predictor_by_itself": "VPD refines existing humidity, leaf wetness and spray rules. It does not replace them. The soft-rot rule D07-HU-001 stays as the primary trigger. VPD is added as a confidence and safety layer, not as a competing alarm.",
    "why_it_is_not_used_for_irrigation_here": "The Domain 3 water requirement is already driven by pan_evaporation_mm_day, which is itself a function of temperature, humidity, wind and radiation. VPD is one term inside that computation. Adding a second VPD-based irrigation rule would double-count the same physical signal — see architecture section 4 on count-once enforcement.",
    "why_it_is_valuable_here": "Two decisions in the current knowledge base still turn on humidity alone. The spray-safety guard D07-HS-004 covers temperature and rain but not the two spray-failing humidity extremes. The winter foliar disease rule D07-HU-002 leans on an estimated leaf_wetness_hours field, and direct measurement is a logged capability gap (D07-OI-05). VPD closes both without moving the existing rules.",
    "honest_limits": [
        "Thresholds below are agronomic consensus for foliar crops, not ginger-specific. Season one field data revises them.",
        "The computation is only as good as the temperature and humidity sensors. Above 24 hours of stale station data, D07-WS-004 already downgrades all weather-dependent advisory; VPD-derived rules inherit that downgrade.",
        "Nighttime VPD requires a nighttime humidity reading. Sub-node sampling frequency at G2/G5 is four-hourly (see architecture section 14); at those stages the nighttime-mean field is a wider estimate and its rule confidence drops accordingly."
    ],
    "primary_sources": [
        "FAO-56 Irrigation and Drainage Paper, chapter 3 (reference evapotranspiration)",
        "Grantz 1990, Plant, Cell & Environment — VPD and stomatal conductance",
        "Ministry of Agriculture, Government of India — Foliar spray timing guidelines"
    ]
}

# ---------------------------------------------------------------------------
# 3. Domain 7 — three new rules
# ---------------------------------------------------------------------------

VP_001 = {
    "rule_id": "D07-VP-001",
    "category": "VP",
    "priority": 4,
    "severity": "info",
    "stage": "ALL",
    "trigger": {
        "english": "A daily station reading is received AND both air_temp_max_c and rh_pct are present",
        "marathi": "दिवसाची हवामान केंद्राची नोंद आली आणि कमाल तापमान व सापेक्ष आर्द्रता दोन्ही उपलब्ध आहेत",
        "expr": "air_temp_max_c IS NOT NULL AND rh_pct IS NOT NULL",
        "expr_version": "dsl-1.0",
        "expr_note": "Computation trigger. Produces vpd_kpa; consumed by D07-VP-002, D07-VP-003 and any downstream rule that reads the field. Nothing is emitted to the farmer.",
        "golden_tests": [
            {
                "context": {"air_temp_max_c": 30, "rh_pct": 60},
                "expect": "TRUE",
                "label": "compute vpd for a normal reading"
            },
            {
                "context": {"air_temp_max_c": 30, "rh_pct": None},
                "expect": "UNKNOWN",
                "label": "missing rh must not fire and must not read as false"
            },
            {
                "context": {"air_temp_max_c": None, "rh_pct": 60},
                "expect": "UNKNOWN",
                "label": "missing temperature must not fire and must not read as false"
            }
        ]
    },
    "action": {
        "english": "Compute vpd_kpa = 0.6108 * exp(17.27 * air_temp_max_c / (air_temp_max_c + 237.3)) * (1 - rh_pct/100) and store it on the daily record. Also update vpd_night_mean_kpa from the nighttime hourly readings where available. Emit nothing to the farmer.",
        "marathi": "vpd_kpa या नोंदीची गणना करा — Tetens समीकरणाने. रात्रीच्या तासांतील सरासरी vpd_night_mean_kpa सुद्धा नोंदवा. शेतकऱ्याला कोणतीही सूचना पाठवू नका — ही केवळ आतील गणना आहे."
    },
    "reasoning": {
        "agronomic_basis": "Relative humidity conflates two very different agronomic situations at different temperatures. VPD is the temperature-corrected form and is what plants and spray droplets actually respond to. Storing it once per day lets every downstream rule read the same value and lets the count-once check succeed.",
        "yield_impact": "None directly. Enables D07-VP-002 (spray safety) and D07-VP-003 (leaf wetness confidence).",
        "confidence_score": 0.85,
        "source_tier": "A",
        "references": [
            "FAO-56 chapter 3, Penman–Monteith reference evapotranspiration",
            "Tetens 1930, saturation vapour pressure equation"
        ]
    },
    "cross_domain_dependencies": {
        "feeds_into": ["domain_3_water", "domain_5_pest", "domain_6_disease", "domain_8_operations"],
        "depends_on": []
    },
    "farm_brain_schema": [
        "air_temp_max_c",
        "rh_pct",
        "vpd_kpa",
        "vpd_night_mean_kpa",
        "station_data_age_hours"
    ],
    "u_value": None,
    "recoverability": "none",
    "source_class": "DERIVED",
    "kannad_note": "The cluster weather station already logs temperature and humidity, so VPD is arithmetic on the master unit and needs no new hardware. This closes a real gap without any capital cost.",
    "decision_type": "AUTO_DECISION",
    "automation": "automatic",
    "status": "AUTHOR_DRAFT",
    "immutable": False,
    "delivery": "SILENT_GUARD"
}

VP_002 = {
    "rule_id": "D07-VP-002",
    "category": "VP",
    "priority": 4,
    "severity": "info",
    "stage": "ALL",
    "trigger": {
        "english": "A foliar spray is scheduled AND vpd_kpa is either below 0.4 or above 2.0",
        "marathi": "फवारणी नियोजित आहे आणि vpd_kpa एकतर ०.४ पेक्षा कमी किंवा २.० पेक्षा जास्त आहे",
        "expr": "spray_scheduled_today IS TRUE AND (vpd_kpa < 0.4 OR vpd_kpa > 2.0)",
        "expr_version": "dsl-1.0",
        "expr_note": "SILENT_GUARD — the rule only speaks when the spray recommendation is actually being sent. It bundles with D07-HS-004; one message, both reasons.",
        "golden_tests": [
            {
                "context": {"spray_scheduled_today": True, "vpd_kpa": 0.25},
                "expect": "TRUE",
                "label": "very humid — droplets will not dry, spray amplifies disease"
            },
            {
                "context": {"spray_scheduled_today": True, "vpd_kpa": 2.4},
                "expect": "TRUE",
                "label": "very dry — droplets evaporate before uptake"
            },
            {
                "context": {"spray_scheduled_today": True, "vpd_kpa": 1.1},
                "expect": "FALSE",
                "label": "plant-friendly band — no block"
            },
            {
                "context": {"spray_scheduled_today": False, "vpd_kpa": 0.25},
                "expect": "FALSE",
                "label": "no spray attempted — silent guard stays silent"
            },
            {
                "context": {"spray_scheduled_today": True, "vpd_kpa": None},
                "expect": "UNKNOWN",
                "label": "missing vpd — do not silently pass; report gap"
            }
        ]
    },
    "action": {
        "english": "Delay the spray to the next window inside VPD 0.8 to 1.5 kPa, typically 2 to 4 hours later or the following morning. Below 0.4 kPa the droplets do not dry and disease pressure is amplified rather than reduced. Above 2.0 kPa evaporation is faster than uptake and effective dose collapses. If D07-HS-004 also fires, present one combined message: temperature or rain plus VPD, one recommended new window.",
        "marathi": "फवारणी VPD ०.८ ते १.५ kPa च्या पट्ट्यात होईल अशा वेळेवर पुढे ढकला — बहुतेक वेळा २–४ तासांनी किंवा दुसऱ्या दिवशी सकाळी. VPD ०.४ पेक्षा कमी असेल तर थेंब वाळत नाहीत आणि रोगदाब कमी होण्याऐवजी वाढतो. VPD २.० च्या वर असेल तर पानांवर बसण्यापूर्वीच बाष्पीभवन होते आणि प्रभावी मात्रा खूप कमी होते. D07-HS-004 देखील लागू होत असल्यास एकच एकत्रित संदेश द्या — तापमान/पाऊस आणि VPD, एकच पुढील वेळ."
    },
    "reasoning": {
        "agronomic_basis": "Spray efficacy is a function of droplet residence on the leaf, which in turn tracks VPD, not temperature or rainfall alone. D07-HS-004 catches high temperature and imminent rain but is blind to the two humidity extremes. This rule adds only that missing discrimination, without changing D07-HS-004's behaviour.",
        "yield_impact": "Grouped under the existing spray-timing duplication group. Not counted separately; see v_u_values_deduplicated.",
        "confidence_score": 0.78,
        "source_tier": "B",
        "references": [
            "Foliar spray drift and efficacy studies, ICAR-CPCRI 2019",
            "FAO-56 chapter 3",
            "Ministry of Agriculture, Government of India — spray timing guidelines"
        ]
    },
    "cross_domain_dependencies": {
        "feeds_into": ["domain_4_nutrient", "domain_5_pest", "domain_6_disease", "domain_8_operations"],
        "depends_on": ["domain_7_weather"]
    },
    "farm_brain_schema": [
        "spray_scheduled_today",
        "vpd_kpa",
        "air_temp_max_c",
        "forecast_rain_48h_mm"
    ],
    "u_value": None,
    "recoverability": "same_season",
    "source_class": "DERIVED",
    "kannad_note": "Marathwada's May pre-monsoon and December–February fog months hit both VPD extremes within the same season. Kannad's daytime maxima of 40+ C push VPD past 3.0 kPa, while pre-dawn winter fog drops it below 0.2 kPa. The two spray-failure windows are not exotic; they are the normal spring afternoon and the normal winter morning here.",
    "decision_type": "SENSOR_ALERT",
    "automation": "assisted",
    "status": "AUTHOR_DRAFT",
    "immutable": False,
    "delivery": "SILENT_GUARD"
}

VP_003 = {
    "rule_id": "D07-VP-003",
    "category": "VP",
    "priority": 3,
    "severity": "info",
    "stage": "G4",
    "trigger": {
        "english": "vpd_night_mean_kpa is below 0.3 AND fog is not observed AND month is December, January or February",
        "marathi": "रात्रीचा सरासरी VPD ०.३ पेक्षा कमी, धुके नोंदवलेले नाही, आणि महिना डिसेंबर–जानेवारी–फेब्रुवारी आहे",
        "expr": "vpd_night_mean_kpa < 0.3 AND fog_observed IS FALSE AND MONTH IN [DEC, JAN, FEB]",
        "expr_version": "dsl-1.0",
        "expr_note": "SILENT_GUARD — no farmer message. Tags the nightly leaf_wetness_hours estimate with high dew-probability confidence. Directly addresses the open capability gap D07-OI-05 without replacing the humidity-based rule D07-HU-002.",
        "golden_tests": [
            {
                "context": {"vpd_night_mean_kpa": 0.2, "fog_observed": False, "current_month": "JAN"},
                "expect": "TRUE",
                "label": "cold clear night — dew almost certain even without fog observation"
            },
            {
                "context": {"vpd_night_mean_kpa": 0.2, "fog_observed": True, "current_month": "JAN"},
                "expect": "FALSE",
                "label": "fog already recorded — D07-HU-002 has the signal, no tag needed"
            },
            {
                "context": {"vpd_night_mean_kpa": 0.6, "fog_observed": False, "current_month": "JAN"},
                "expect": "FALSE",
                "label": "dry night — dew unlikely"
            },
            {
                "context": {"vpd_night_mean_kpa": 0.2, "fog_observed": False, "current_month": "JUL"},
                "expect": "FALSE",
                "label": "monsoon — different disease season, driven by saturation not by dew"
            }
        ]
    },
    "action": {
        "english": "Tag tonight's estimated leaf_wetness_hours with a high dew-probability confidence flag and log the reason (very low nighttime VPD with clear sky). Do not raise a new disease alert. If D07-HU-002 fires overnight or the next morning, the confidence flag travels with it. This is the interim substitute for the missing leaf wetness sensor logged as D07-OI-05.",
        "marathi": "आजच्या रात्रीच्या अंदाजित leaf_wetness_hours नोंदीवर उच्च-दव-संभाव्यता ध्वज लावा आणि कारण नोंदवा (रात्रीचा VPD अत्यंत कमी, आकाश निरभ्र). नवीन रोग सूचना देऊ नका. रात्रभर किंवा सकाळी D07-HU-002 सुरू झाल्यास हा ध्वज त्याच्यासोबत जातो. हा पानावरील ओलावा सेन्सर बसेपर्यंतचा (D07-OI-05) तात्पुरता पर्याय आहे."
    },
    "reasoning": {
        "agronomic_basis": "Dew formation on ginger leaves requires the leaf surface to reach the dew point of the surrounding air. Low nighttime VPD means the air is already close to saturation and radiative cooling of the leaf will cross that threshold. Fog observations catch part of this signal; low VPD catches the other part, especially on cold clear nights when fog does not form but dew still soaks the canopy.",
        "yield_impact": "None directly. Improves the reliability of D07-HU-002 and future disease-forecast rules that depend on it.",
        "confidence_score": 0.75,
        "source_tier": "B",
        "references": [
            "Grantz 1990, Plant, Cell & Environment",
            "IMD Marathwada winter humidity records",
            "Domain 6 leaf wetness estimation notes"
        ]
    },
    "cross_domain_dependencies": {
        "feeds_into": ["domain_6_disease", "domain_7_weather"],
        "depends_on": ["domain_7_weather"]
    },
    "farm_brain_schema": [
        "vpd_night_mean_kpa",
        "fog_observed",
        "leaf_wetness_hours",
        "current_stage"
    ],
    "u_value": None,
    "recoverability": "same_season",
    "source_class": "DERIVED",
    "kannad_note": "Marathwada winter mornings are the local advantage for rhizome bulking mentioned in D07 key_innovations, but they are also when the second foliar disease season starts. VPD makes the dew half of that pattern measurable without waiting for a leaf wetness sensor purchase.",
    "decision_type": "AUTO_DECISION",
    "automation": "automatic",
    "status": "AUTHOR_DRAFT",
    "immutable": False,
    "delivery": "SILENT_GUARD"
}

# Append (never insert before existing entries)
d7["rules"].extend([VP_001, VP_002, VP_003])

# ---------------------------------------------------------------------------
# 4. Domain 7 — open_items, summary, metadata, next_steps
# ---------------------------------------------------------------------------

d7["open_items"].append({
    "id": "D07-OI-09",
    "item": "Local calibration of VPD spray-window thresholds (0.4 / 0.8 / 1.5 / 2.0 kPa) against season-one spray-outcome records",
    "owner": "field trial, season 1",
    "source_class": "EST",
    "blocking": False,
    "note": "Current thresholds are agronomic consensus for foliar crops in general. Ginger-specific and Kannad-specific values may shift by 0.1 to 0.2 kPa in either direction after one season of paired spray-and-outcome records."
})

# Summary counters
s = d7["summary"]
s["total_rules"] = s["total_rules"] + 3  # 35 -> 38
s["by_category"]["VP"] = 3
# priority: 2× priority 4 + 1× priority 3
s["by_priority"]["4"] = s["by_priority"].get("4", 0) + 2
s["by_priority"]["3"] = s["by_priority"].get("3", 0) + 1
# severity: 3× info
s["by_severity"]["info"] = s["by_severity"].get("info", 0) + 3
# source_tier: A (1) + B (2)
s["by_source_tier"]["A"] = s["by_source_tier"].get("A", 0) + 1
s["by_source_tier"]["B"] = s["by_source_tier"].get("B", 0) + 2
# source_class: all DERIVED
s["by_source_class"]["DERIVED"] = s["by_source_class"].get("DERIVED", 0) + 3
# decision_type: 2× AUTO_DECISION + 1× SENSOR_ALERT
s["by_decision_type"]["AUTO_DECISION"] = s["by_decision_type"].get("AUTO_DECISION", 0) + 2
s["by_decision_type"]["SENSOR_ALERT"] = s["by_decision_type"].get("SENSOR_ALERT", 0) + 1
# rules with trigger_expr and delivery_class both increase by 3
s["rules_with_trigger_expr"] = s.get("rules_with_trigger_expr", 0) + 3
s["rules_with_delivery_class"] = s.get("rules_with_delivery_class", 0) + 3
# confidence range recomputation over the three new rules (0.85, 0.78, 0.75)
new_confs = [0.85, 0.78, 0.75]
# The existing confidence_range covers 35 rules mean 0.787. Extend without inventing precision.
existing_mean = s["confidence_range"]["mean"]
existing_n = 35
new_mean = round(
    (existing_mean * existing_n + sum(new_confs)) / (existing_n + len(new_confs)),
    3
)
s["confidence_range"]["min"] = min(s["confidence_range"]["min"], min(new_confs))
s["confidence_range"]["max"] = max(s["confidence_range"]["max"], max(new_confs))
s["confidence_range"]["mean"] = new_mean

# Metadata bump
d7["metadata"]["total_rules"] = d7["metadata"]["total_rules"] + 3
d7["metadata"]["rule_count_note"] = (
    d7["metadata"].get("rule_count_note", "")
    + " | 2026-09-17: +3 rules (D07-VP-001/002/003) added under VP category — VPD retrofit, additive-only."
).strip(" |")
if "review_log" in d7["metadata"] and isinstance(d7["metadata"]["review_log"], dict):
    # Keep the existing tier-1 summary intact; only bump rules_total to match new count
    # and append a change_log list alongside for the additive edit.
    rl = d7["metadata"]["review_log"]
    rl["rules_total"] = d7["metadata"]["total_rules"]
    rl.setdefault("change_log", []).append({
        "date": "2026-09-17",
        "author": "kb_author",
        "change": "VPD retrofit — additive only",
        "detail": "Added VP category, 3 farm_brain fields (vpd_kpa, vpd_night_mean_kpa, spray_scheduled_today), 5 constants, vpd_context reference block, rules D07-VP-001/002/003, open_item D07-OI-09. Zero existing rules edited. Precedence: 1 BUNDLES entry added in Domain 11 (VP-002 with HS-004). Golden tests: 12 new."
    })

# Next steps — append, do not disturb existing order
d7["next_steps"].append(
    "6. Collect paired spray-attempt-and-outcome records in season 1 to calibrate the VPD thresholds in D07-VP-002 (currently EST); revise D07-OI-09"
)

# ---------------------------------------------------------------------------
# 5. Domain 11 — precedence graph gets ONE new BUNDLES entry
# ---------------------------------------------------------------------------
new_prec = {
    "subject": "D07-VP-002",
    "relation": "BUNDLES",
    "object": "D07-HS-004",
    "reason_en": "Both guards fire on the same scheduled foliar spray event. One field visit, one message: list temperature or rain, VPD, and the next recommended window together.",
    "reason_mr": "दोन्ही नियम एकाच फवारणी घटनेवर लागू होतात. एकाच शेतफेरीत एकच संदेश द्या — तापमान/पाऊस, VPD, आणि पुढील शिफारशीत वेळ एकत्र सांगा."
}
key = (new_prec["subject"], new_prec["relation"], new_prec["object"])
assert key not in orig_d11_graph_keys, "precedence entry already exists!"
d11["_schema"]["additions"]["precedence"]["graph"].append(new_prec)

# ---------------------------------------------------------------------------
# 6. Invariant checks — nothing existing was disturbed
# ---------------------------------------------------------------------------
# a. Every original D07 rule is present, byte-identical, in the same order
for i, orig_rule in enumerate(orig_d7_rules):
    assert d7["rules"][i] == orig_rule, f"existing rule {orig_rule['rule_id']} was modified!"
# b. Three new rules appended at the end
assert d7["rules"][-3]["rule_id"] == "D07-VP-001"
assert d7["rules"][-2]["rule_id"] == "D07-VP-002"
assert d7["rules"][-1]["rule_id"] == "D07-VP-003"
# c. Every original D11 precedence entry preserved
for i, orig_entry in enumerate(orig_d11_graph):
    assert d11["_schema"]["additions"]["precedence"]["graph"][i] == orig_entry
# d. Immutable rules list not affected (D07 has 0; still 0)
new_immutable_d7 = [r["rule_id"] for r in d7["rules"] if r.get("immutable")]
assert new_immutable_d7 == [], f"unexpected immutable in D07: {new_immutable_d7}"
# e. New rule IDs match the domain-id constraint (D07-...)
for rid in ["D07-VP-001", "D07-VP-002", "D07-VP-003"]:
    assert rid.startswith("D07-"), rid
# f. No duplicate rule_ids
all_ids = [r["rule_id"] for r in d7["rules"]]
assert len(all_ids) == len(set(all_ids)), "duplicate rule_id detected"

# ---------------------------------------------------------------------------
# 7. Write out
# ---------------------------------------------------------------------------
with open(D7_PATH, "w", encoding="utf-8") as f:
    json.dump(d7, f, ensure_ascii=False, indent=2)
    f.write("\n")
with open(D11_PATH, "w", encoding="utf-8") as f:
    json.dump(d11, f, ensure_ascii=False, indent=2)
    f.write("\n")

print("PATCH APPLIED")
print(f"  Domain 7: {len(orig_d7_rules)} rules -> {len(d7['rules'])} rules (+3)")
print(f"  Domain 7: total_rules metadata = {d7['metadata']['total_rules']}")
print(f"  Domain 7: summary.total_rules  = {d7['summary']['total_rules']}")
print(f"  Domain 7: summary.by_category  = {d7['summary']['by_category']}")
print(f"  Domain 11: precedence graph {len(orig_d11_graph)} -> {len(d11['_schema']['additions']['precedence']['graph'])} (+1)")
print(f"  New rule IDs: D07-VP-001, D07-VP-002, D07-VP-003")
print(f"  New precedence: D07-VP-002 BUNDLES D07-HS-004")
print(f"  New farm_brain fields: vpd_kpa, vpd_night_mean_kpa, spray_scheduled_today")
print(f"  New open_item: D07-OI-09")
print(f"  All invariant checks passed.")
