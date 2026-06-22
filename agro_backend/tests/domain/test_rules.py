"""Tests for the rule engine in app.domain.rules."""


from __future__ import annotations


import uuid
from datetime import UTC, datetime
from decimal import Decimal


import pytest


from app.domain.alert import AlertCandidate, AlertType, Severity
from app.domain.metrics import BatteryState, DerivedMetrics
from app.domain.rules import (
    Rule,
    RuleSet,
    alert_id_for,
    evaluate,
    evaluate_to_hits,
)
from app.domain.sensor import Reading, TransmissionType


NOW = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
FARMER = uuid.UUID("22222222-2222-2222-2222-222222222222")
FARM = uuid.UUID("33333333-3333-3333-3333-333333333333")




def _reading(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": TENANT,
        "farmer_id": FARMER,
        "farm_id": FARM,
        "plot_id": "P1",
        "node_id": "AGR-001",
        "recorded_at": NOW,
        "received_at_master": NOW,
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




def _metrics(**over: object) -> DerivedMetrics:
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




def _always_true_rule(rid: str = "always") -> Rule:
    return Rule(
        rule_id=rid,
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.INFO,
        message_template_marathi="अलर्ट",
        predicate=lambda _r, _m: True,
    )




# ===========================================================================
# Rule + RuleSet construction
# ===========================================================================
def test_ruleset_rejects_duplicate_rule_ids() -> None:
    r1 = _always_true_rule("dup")
    r2 = _always_true_rule("dup")
    with pytest.raises(ValueError, match="Duplicate"):
        RuleSet(rules=(r1, r2))




def test_ruleset_holds_rules_in_declaration_order() -> None:
    a = _always_true_rule("a")
    b = _always_true_rule("b")
    rs = RuleSet(rules=(a, b))
    assert rs.rules == (a, b)




# ===========================================================================
# evaluate_to_hits - the engine's pure step
# ===========================================================================
def test_evaluate_to_hits_returns_hit_when_predicate_true() -> None:
    rs = RuleSet(rules=(_always_true_rule(),))
    hits = evaluate_to_hits(_reading(), _metrics(), rs)
    assert len(hits) == 1
    assert hits[0].rule.rule_id == "always"




def test_evaluate_to_hits_skips_false_predicate() -> None:
    never = Rule(
        rule_id="never",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.INFO,
        message_template_marathi="x",
        predicate=lambda _r, _m: False,
    )
    hits = evaluate_to_hits(_reading(), _metrics(), RuleSet(rules=(never,)))
    assert hits == []




def test_evaluate_to_hits_treats_dict_result_as_truthy_with_substitutions() -> None:
    rule = Rule(
        rule_id="bat",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.WARNING,
        message_template_marathi="व्होल्टेज {voltage} पडले",
        predicate=lambda _r, _m: {"voltage": "3.10"},
    )
    hits = evaluate_to_hits(_reading(), _metrics(), RuleSet(rules=(rule,)))
    assert len(hits) == 1
    assert hits[0].render_message() == "व्होल्टेज 3.10 पडले"




def test_evaluate_to_hits_renders_template_with_missing_keys_safely() -> None:
    # If a predicate forgets a key, the engine falls back to the
    # unrendered template rather than crashing the whole evaluation.
    rule = Rule(
        rule_id="bat",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.INFO,
        message_template_marathi="{missing_key}",
        predicate=lambda _r, _m: {},
    )
    hits = evaluate_to_hits(_reading(), _metrics(), RuleSet(rules=(rule,)))
    assert hits[0].render_message() == "{missing_key}"




# ===========================================================================
# evaluate - full path to AlertCandidate
# ===========================================================================
def test_evaluate_builds_alert_candidate_with_reading_identity() -> None:
    rs = RuleSet(rules=(_always_true_rule(),))
    candidates = evaluate(_reading(), _metrics(), rs, now=NOW)
    assert len(candidates) == 1
    c = candidates[0]
    assert isinstance(c, AlertCandidate)
    assert c.tenant_id == TENANT
    assert c.farm_id == FARM
    assert c.farmer_id == FARMER
    assert c.device_id == "AGR-001"
    assert c.triggered_at == NOW




def test_evaluate_carries_value_and_threshold_when_supplied() -> None:
    rule = Rule(
        rule_id="bat",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.WARNING,
        message_template_marathi="{voltage}V (खाली {threshold}V)",
        predicate=lambda _r, _m: {
            "voltage": Decimal("3.10"),
            "value": Decimal("3.10"),
            "threshold": Decimal("3.30"),
        },
        emits_value=True,
    )
    candidates = evaluate(_reading(), _metrics(), RuleSet(rules=(rule,)), now=NOW)
    assert candidates[0].alert_value == Decimal("3.10")
    assert candidates[0].alert_threshold == Decimal("3.30")




def test_evaluate_multiple_rules_emit_multiple_candidates() -> None:
    a = _always_true_rule("a")
    b = Rule(
        rule_id="b",
        alert_type=AlertType.FROST,
        severity=Severity.WARNING,
        message_template_marathi="frost",
        predicate=lambda _r, _m: True,
    )
    out = evaluate(_reading(), _metrics(), RuleSet(rules=(a, b)), now=NOW)
    assert {c.alert_type for c in out} == {AlertType.LOW_BATTERY, AlertType.FROST}




def test_evaluate_empty_ruleset_returns_empty_list() -> None:
    assert evaluate(_reading(), _metrics(), RuleSet(rules=()), now=NOW) == []




def test_evaluate_handles_non_bool_non_dict_predicate_result_as_no_hit() -> None:
    # Defensive: a buggy predicate returning e.g. an int 0 shouldn't crash;
    # treat anything other than True / dict as "no hit".
    rule = Rule(
        rule_id="weird",
        alert_type=AlertType.LOW_BATTERY,
        severity=Severity.INFO,
        message_template_marathi="x",
        predicate=lambda _r, _m: 0,  # type: ignore[return-value]
    )
    assert evaluate(_reading(), _metrics(), RuleSet(rules=(rule,)), now=NOW) == []




# ===========================================================================
# alert_id_for
# ===========================================================================
def test_alert_id_for_is_deterministic() -> None:
    r = _reading()
    a = alert_id_for(r, "low_battery")
    b = alert_id_for(r, "low_battery")
    assert a == b




def test_alert_id_for_differs_by_rule() -> None:
    r = _reading()
    a = alert_id_for(r, "low_battery")
    b = alert_id_for(r, "frost")
    assert a != b
