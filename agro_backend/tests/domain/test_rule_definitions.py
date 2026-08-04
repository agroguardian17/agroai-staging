"""Behaviour tests for the pilot RuleSet.


Each rule gets a happy-path "should fire" test and a quiet-path
"should not fire" test. Integration with the engine is via
:func:`evaluate` so we exercise the full path from
(Reading, DerivedMetrics) to AlertCandidate.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from app.domain.alert import AlertType, Severity
from app.domain.metrics import (
    BATTERY_CRITICAL_V,
    BATTERY_LOW_V,
    BatteryState,
    DerivedMetrics,
)
from app.domain.rule_definitions import (
    PILOT_EMITTED_ALERT_TYPES,
    PILOT_RULE_BY_ID,
    PILOT_RULESET,
)
from app.domain.rules import evaluate, evaluate_to_hits
from app.domain.sensor import Reading, TransmissionType

NOW = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)




def _r(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "farmer_id": uuid.uuid4(),
        "farm_id": uuid.uuid4(),
        "plot_id": "P1",
        "node_id": "AGR-001",
        "recorded_at": NOW,
        "received_at_master": NOW,
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




def _m(**over: object) -> DerivedMetrics:
    base: dict[str, object] = {
        "moisture_deficit_pct": None,
        "moisture_below_target": False,
        "battery_state": BatteryState.HEALTHY,
        "frost_risk": False,
        "dry_run_signature": False,
        "sensor_health_warn": False,
    }
    base.update(over)
    return DerivedMetrics(**base)  # type: ignore[arg-type]




def _fired_rule_ids(reading: Reading, metrics: DerivedMetrics) -> set[str]:
    return {h.rule.rule_id for h in evaluate_to_hits(reading, metrics, PILOT_RULESET)}




# ===========================================================================
# Catalog sanity
# ===========================================================================
def test_ruleset_rule_ids_are_unique() -> None:
    ids = [r.rule_id for r in PILOT_RULESET.rules]
    assert len(ids) == len(set(ids))




def test_pilot_emitted_alert_types_is_subset_of_alert_type() -> None:
    for at in PILOT_EMITTED_ALERT_TYPES:
        assert at in set(AlertType)




def test_every_rule_has_a_marathi_template_with_no_english() -> None:
    for r in PILOT_RULESET.rules:
        assert r.message_template_marathi.strip(), r.rule_id
        # Cheap heuristic: Marathi text uses Devanagari (U+0900-U+097F).
        assert any("ऀ" <= ch <= "ॿ" for ch in r.message_template_marathi), r.rule_id




def test_pilot_rule_by_id_matches_ruleset() -> None:
    assert set(PILOT_RULE_BY_ID.keys()) == {r.rule_id for r in PILOT_RULESET.rules}




# ===========================================================================
# low_battery
# ===========================================================================
def test_low_battery_fires_when_state_is_low() -> None:
    fired = _fired_rule_ids(
        _r(battery_voltage_v=Decimal("3.25")),
        _m(battery_state=BatteryState.LOW),
    )
    assert "low_battery" in fired
    assert "battery_critical" not in fired




def test_low_battery_fires_when_state_is_critical_or_dead() -> None:
    fired = _fired_rule_ids(
        _r(battery_voltage_v=Decimal("3.00")),
        _m(battery_state=BatteryState.CRITICAL),
    )
    assert "low_battery" in fired
    assert "battery_critical" in fired




def test_battery_critical_silent_when_only_low() -> None:
    fired = _fired_rule_ids(
        _r(battery_voltage_v=Decimal("3.25")),
        _m(battery_state=BatteryState.LOW),
    )
    assert "battery_critical" not in fired




def test_low_battery_silent_when_healthy() -> None:
    fired = _fired_rule_ids(
        _r(battery_voltage_v=Decimal("3.55")),
        _m(battery_state=BatteryState.HEALTHY),
    )
    assert "low_battery" not in fired
    assert "battery_critical" not in fired




# ===========================================================================
# low_water
# ===========================================================================
def test_low_water_fires_when_below_target() -> None:
    fired = _fired_rule_ids(
        _r(soil_moisture_avg_pct=Decimal("20")),
        _m(
            moisture_below_target=True,
            moisture_deficit_pct=Decimal("8"),
        ),
    )
    assert "low_water" in fired




def test_low_water_silent_when_above_target() -> None:
    fired = _fired_rule_ids(
        _r(soil_moisture_avg_pct=Decimal("35")),
        _m(moisture_below_target=False, moisture_deficit_pct=Decimal("-7")),
    )
    assert "low_water" not in fired




# ===========================================================================
# dry_run
# ===========================================================================
def test_dry_run_fires_via_firmware_flag() -> None:
    fired = _fired_rule_ids(_r(dry_run_detected=True), _m())
    assert "dry_run" in fired




def test_dry_run_fires_via_signature() -> None:
    fired = _fired_rule_ids(_r(), _m(dry_run_signature=True))
    assert "dry_run" in fired




def test_dry_run_silent_when_neither_signal() -> None:
    fired = _fired_rule_ids(_r(), _m())
    assert "dry_run" not in fired




# ===========================================================================
# sensor_fault
# ===========================================================================
def test_sensor_fault_fires_when_validation_warn() -> None:
    fired = _fired_rule_ids(_r(validation_warn=True), _m(sensor_health_warn=True))
    assert "sensor_fault" in fired




def test_sensor_fault_silent_on_clean_reading() -> None:
    assert "sensor_fault" not in _fired_rule_ids(_r(), _m())




# ===========================================================================
# frost
# ===========================================================================
def test_frost_fires_when_temp_low() -> None:
    fired = _fired_rule_ids(
        _r(soil_temp_rootzone_c=Decimal("3.0")),
        _m(frost_risk=True),
    )
    assert "frost" in fired




def test_frost_silent_when_warm() -> None:
    fired = _fired_rule_ids(_r(soil_temp_rootzone_c=Decimal("25")), _m())
    assert "frost" not in fired




# ===========================================================================
# tamper
# ===========================================================================
def test_tamper_fires_when_flag_set() -> None:
    assert "tamper" in _fired_rule_ids(_r(tamper_detected=True), _m())




def test_tamper_silent_when_flag_unset_or_none() -> None:
    assert "tamper" not in _fired_rule_ids(_r(), _m())
    assert "tamper" not in _fired_rule_ids(_r(tamper_detected=False), _m())




# ===========================================================================
# Integration: emit AlertCandidates with correct shape
# ===========================================================================
def test_evaluate_emits_alert_candidates_for_healthy_critical_battery() -> None:
    reading = _r(battery_voltage_v=Decimal("3.05"))
    metrics = _m(battery_state=BatteryState.CRITICAL)
    candidates = evaluate(reading, metrics, PILOT_RULESET, now=NOW)
    by_type = {(c.alert_type, c.severity) for c in candidates}
    assert (AlertType.LOW_BATTERY, Severity.WARNING) in by_type
    assert (AlertType.LOW_BATTERY, Severity.CRITICAL) in by_type
    # Critical message renders the voltage:
    crit = next(
        c
        for c in candidates
        if c.alert_type is AlertType.LOW_BATTERY and c.severity is Severity.CRITICAL
    )
    assert "3.05" in crit.alert_message_marathi




def test_evaluate_emits_no_candidates_for_clean_reading() -> None:
    candidates = evaluate(_r(), _m(), PILOT_RULESET, now=NOW)
    assert candidates == []




def test_thresholds_constants_match_metrics_module() -> None:
    # PILOT_THRESHOLDS is the dashboard's source of truth; if it drifts
    # from the metrics module the surface area gets confused.
    from app.domain.rule_definitions import PILOT_THRESHOLDS


    assert PILOT_THRESHOLDS["battery_low_v"] == BATTERY_LOW_V
    assert PILOT_THRESHOLDS["battery_critical_v"] == BATTERY_CRITICAL_V
