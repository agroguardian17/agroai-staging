"""The pilot RuleSet.


Each rule here is one decision Phase 4's hot-rule evaluator emits.
The Marathi message templates are deliberately short (WhatsApp shows
~3 lines) and use only ``{key}`` placeholders the predicate supplies.


To add a rule in a future round:


1. Pick the right :class:`~app.domain.alert.AlertType` (extending the
   CHECK constraint in the schema if needed).
2. Write a predicate over ``(Reading, DerivedMetrics) -> bool | dict``.
3. Author the Marathi template (and English back-translation in the
   docstring for the agronomist review).
4. Append to :data:`PILOT_RULESET` and write a focused test in
   ``tests/domain/test_rule_definitions.py``.


PURE module: stdlib only.
"""


from __future__ import annotations

from decimal import Decimal

from app.domain.alert import AlertType, Severity
from app.domain.metrics import (
    BATTERY_CRITICAL_V,
    BATTERY_LOW_V,
    BatteryState,
    DerivedMetrics,
)
from app.domain.rules import Rule, RuleSet
from app.domain.sensor import Reading

# ---------------------------------------------------------------------------
# Individual rule predicates
# ---------------------------------------------------------------------------




def _predicate_low_battery(r: Reading, m: DerivedMetrics) -> bool | dict[str, object]:
    """Fire on BatteryState.LOW (severity INFO) or worse.


    The severity in the Rule itself is fixed (rule list authors picked
    WARNING for LOW); a future tier could split this into two rules
    if the dispatch path wants different cooldowns per severity.
    """
    if m.battery_state is BatteryState.HEALTHY or m.battery_state is BatteryState.UNKNOWN:
        return False
    voltage = r.battery_voltage_v
    return {
        "voltage": str(voltage) if voltage is not None else "?",
        "value": voltage,
        "threshold": BATTERY_LOW_V,
        "state": m.battery_state.value,
    }




def _predicate_battery_critical(r: Reading, m: DerivedMetrics) -> bool | dict[str, object]:
    """Separate rule for CRITICAL/DEAD so the message + severity match."""
    if m.battery_state not in (BatteryState.CRITICAL, BatteryState.DEAD):
        return False
    return {
        "voltage": str(r.battery_voltage_v) if r.battery_voltage_v is not None else "?",
        "value": r.battery_voltage_v,
        "threshold": BATTERY_CRITICAL_V,
    }




def _predicate_low_water(_r: Reading, m: DerivedMetrics) -> bool | dict[str, object]:
    if not m.moisture_below_target or m.moisture_deficit_pct is None:
        return False
    return {
        "deficit": str(m.moisture_deficit_pct),
        "value": m.moisture_deficit_pct,
    }




def _predicate_dry_run(r: Reading, m: DerivedMetrics) -> bool:
    # Prefer the firmware's own flag if present; otherwise use our
    # signature.
    if r.dry_run_detected:
        return True
    return m.dry_run_signature




def _predicate_sensor_fault(_r: Reading, m: DerivedMetrics) -> bool:
    return m.sensor_health_warn




def _predicate_frost(r: Reading, m: DerivedMetrics) -> bool | dict[str, object]:
    if not m.frost_risk:
        return False
    temp = r.soil_temp_rootzone_c
    return {
        "temp": str(temp) if temp is not None else "?",
        "value": temp,
    }




def _predicate_tamper(r: Reading, _m: DerivedMetrics) -> bool:
    return bool(r.tamper_detected)




# ---------------------------------------------------------------------------
# The pilot ruleset itself
# ---------------------------------------------------------------------------




PILOT_RULESET: RuleSet = RuleSet(
    rules=(
        # Battery low: warns the farmer to swap / charge. Cooldown long
        # so we don't spam them with one alert per reading.
        Rule(
            rule_id="low_battery",
            alert_type=AlertType.LOW_BATTERY,
            severity=Severity.WARNING,
            # English back-translation: "Sensor battery is low ({voltage}V).
            # Please charge soon."
            message_template_marathi="सेन्सर बॅटरी कमी आहे ({voltage}V). लवकर चार्ज करा.",
            predicate=_predicate_low_battery,
            cooldown_minutes=12 * 60,
            emits_value=True,
        ),
        # Battery critical: more urgent. Same alert_type but the
        # dispatcher can detect the severity bump and re-prioritise.
        Rule(
            rule_id="battery_critical",
            alert_type=AlertType.LOW_BATTERY,
            severity=Severity.CRITICAL,
            message_template_marathi=("बॅटरी अत्यंत कमी आहे ({voltage}V). सेन्सर बंद होऊ शकतो."),
            predicate=_predicate_battery_critical,
            cooldown_minutes=2 * 60,
            emits_value=True,
        ),
        # Low water: soil moisture below the target. The "deficit" in
        # the message is positive when too dry.
        Rule(
            rule_id="low_water",
            alert_type=AlertType.LOW_WATER,
            severity=Severity.WARNING,
            message_template_marathi="मातीतील ओलावा कमी आहे (कमी {deficit}%).",
            predicate=_predicate_low_water,
            cooldown_minutes=4 * 60,
            emits_value=True,
        ),
        # Dry-run: pump on but no water. Critical - protect the pump.
        Rule(
            rule_id="dry_run",
            alert_type=AlertType.DRY_RUN,
            severity=Severity.CRITICAL,
            message_template_marathi="पंप चालू पण पाणी नाही. लगेच बंद करा.",
            predicate=_predicate_dry_run,
            cooldown_minutes=30,
        ),
        # Sensor fault: validation gate fired or freeform fault flags.
        Rule(
            rule_id="sensor_fault",
            alert_type=AlertType.SENSOR_FAULT,
            severity=Severity.INFO,
            message_template_marathi="सेन्सर डेटा तपासणी अयशस्वी झाली.",
            predicate=_predicate_sensor_fault,
            cooldown_minutes=6 * 60,
        ),
        # Frost: soil at root zone below frost threshold.
        Rule(
            rule_id="frost",
            alert_type=AlertType.FROST,
            severity=Severity.WARNING,
            message_template_marathi="मातीचे तापमान {temp}°C - थंडीचा धोका.",
            predicate=_predicate_frost,
            cooldown_minutes=4 * 60,
            emits_value=True,
        ),
        # Tamper: physical interference detected.
        Rule(
            rule_id="tamper",
            alert_type=AlertType.TAMPER,
            severity=Severity.CRITICAL,
            message_template_marathi="उपकरणाशी छेडछाड झाली असण्याची शक्यता.",
            predicate=_predicate_tamper,
            cooldown_minutes=60,
        ),
    ),
)




# Convenience for tests + the dispatcher: rule_id -> Rule lookup.
PILOT_RULE_BY_ID: dict[str, Rule] = {r.rule_id: r for r in PILOT_RULESET.rules}




# Re-exported alert types so the dashboard / dispatcher can enumerate
# which AlertTypes the pilot can actually emit (subset of the full enum).
PILOT_EMITTED_ALERT_TYPES: frozenset[AlertType] = frozenset(
    r.alert_type for r in PILOT_RULESET.rules
)




# Threshold constants exposed for the dashboard (Round 12) so it can
# render the same numbers the rules use without hard-coding them twice.
PILOT_THRESHOLDS: dict[str, Decimal] = {
    "battery_low_v": BATTERY_LOW_V,
    "battery_critical_v": BATTERY_CRITICAL_V,
}




__all__ = [
    "PILOT_EMITTED_ALERT_TYPES",
    "PILOT_RULESET",
    "PILOT_RULE_BY_ID",
    "PILOT_THRESHOLDS",
]
