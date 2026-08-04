"""Tests for app.application.evaluate_rules.execute.


Pure unit tests with stub AlertRepo + EventBus. The pilot ruleset is
swapped for a minimal one in most tests so the assertions are precise.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

from app.application.evaluate_rules import (
    EvaluateRulesDeps,
    EvaluateRulesResult,
    execute,
)
from app.application.ports.event_bus import EVENT_ALERT_CREATED
from app.domain.alert import AlertCandidate, AlertType, Severity
from app.domain.rule_definitions import PILOT_RULESET
from app.domain.rules import Rule, RuleSet
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
        "plot_id": "PLOT_A",
        "node_id": "AGR-001",
        "recorded_at": NOW,
        "received_at_master": NOW,
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------
class _StubAlertRepo:
    def __init__(self, last_triggered: dict[tuple[str, AlertType], datetime] | None = None) -> None:
        self._last = last_triggered or {}
        self.created: list[AlertCandidate] = []
        self._next_id = 1


    async def create(self, candidate: AlertCandidate) -> int:
        self.created.append(candidate)
        out = self._next_id
        self._next_id += 1
        return out


    async def last_triggered_at(self, plot_id: str, alert_type: AlertType) -> datetime | None:
        return self._last.get((plot_id, alert_type))


    async def resolve(self, alert_id: int, notes: str | None = None) -> None:
        raise AssertionError("evaluate_rules must not call resolve()")


    async def list_for_plot(self, plot_id, limit=50):  # pragma: no cover - read-side
        raise AssertionError




class _StubEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []


    async def publish(self, event_name: str, payload: dict[str, Any]) -> None:
        self.published.append((event_name, payload))




def _deps(
    *,
    last_triggered: dict[tuple[str, AlertType], datetime] | None = None,
    ruleset: RuleSet | None = None,
) -> tuple[EvaluateRulesDeps, _StubAlertRepo, _StubEventBus]:
    repo = _StubAlertRepo(last_triggered)
    bus = _StubEventBus()
    deps = EvaluateRulesDeps(
        alert_repo=repo,
        event_bus=bus,
        ruleset=ruleset or PILOT_RULESET,
    )
    return deps, repo, bus




# A minimal "always fires once" ruleset for cooldown tests.
def _single_rule_set() -> RuleSet:
    return RuleSet(
        rules=(
            Rule(
                rule_id="always",
                alert_type=AlertType.LOW_BATTERY,
                severity=Severity.WARNING,
                message_template_marathi="अलर्ट",
                predicate=lambda _r, _m: True,
                cooldown_minutes=60,
            ),
        ),
    )




# ===========================================================================
# Happy path: low battery + frost on a single reading
# ===========================================================================
async def test_critical_battery_and_frost_emit_three_alerts_no_cooldown() -> None:
    """battery=3.05 + frost=2.0 -> low_battery + battery_critical + frost."""
    deps, repo, bus = _deps()
    result = await execute(
        _reading(
            battery_voltage_v=Decimal("3.05"),
            battery_percent=Decimal("5"),
            soil_temp_rootzone_c=Decimal("2.0"),
        ),
        deps,
        now=NOW,
    )
    assert isinstance(result, EvaluateRulesResult)
    assert result.hits == 3
    assert result.created == 3
    assert result.cooldown_suppressed == 0
    assert len(repo.created) == 3
    assert len(bus.published) == 3
    # Every published event is EVENT_ALERT_CREATED.
    for name, _ in bus.published:
        assert name == EVENT_ALERT_CREATED




async def test_persisted_candidate_carries_reading_identity() -> None:
    deps, repo, _ = _deps(ruleset=_single_rule_set())
    await execute(_reading(), deps, now=NOW)
    c = repo.created[0]
    assert c.tenant_id == TENANT
    assert c.farm_id == FARM
    assert c.farmer_id == FARMER
    assert c.device_id == "AGR-001"
    assert c.triggered_at == NOW




# ===========================================================================
# Empty-rule paths
# ===========================================================================
async def test_clean_reading_creates_no_alerts() -> None:
    """Healthy battery + warm soil + clean validation -> no rule fires."""
    deps, repo, bus = _deps()
    result = await execute(
        _reading(
            battery_voltage_v=Decimal("3.55"),
            soil_temp_rootzone_c=Decimal("25"),
            soil_moisture_avg_pct=Decimal("32"),  # above 28 default
        ),
        deps,
        now=NOW,
    )
    assert result == EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0)
    assert repo.created == []
    assert bus.published == []




# ===========================================================================
# Cooldown enforcement
# ===========================================================================
async def test_recent_alert_within_cooldown_is_suppressed() -> None:
    deps, repo, bus = _deps(
        last_triggered={("PLOT_A", AlertType.LOW_BATTERY): NOW - timedelta(minutes=10)},
        ruleset=_single_rule_set(),
    )
    result = await execute(_reading(), deps, now=NOW)
    # cooldown is 60 minutes; 10 min ago -> suppressed.
    assert result.cooldown_suppressed == 1
    assert result.created == 0
    assert repo.created == []
    assert bus.published == []




async def test_alert_outside_cooldown_window_fires_through() -> None:
    deps, repo, _bus = _deps(
        last_triggered={("PLOT_A", AlertType.LOW_BATTERY): NOW - timedelta(hours=2)},
        ruleset=_single_rule_set(),
    )
    result = await execute(_reading(), deps, now=NOW)
    assert result.created == 1
    assert result.cooldown_suppressed == 0
    assert len(repo.created) == 1




async def test_cooldown_is_per_alert_type_not_global() -> None:
    """A cooldown on LOW_BATTERY must not block FROST."""
    rules = RuleSet(
        rules=(
            Rule(
                rule_id="bat",
                alert_type=AlertType.LOW_BATTERY,
                severity=Severity.WARNING,
                message_template_marathi="bat",
                predicate=lambda _r, _m: True,
                cooldown_minutes=60,
            ),
            Rule(
                rule_id="frost",
                alert_type=AlertType.FROST,
                severity=Severity.WARNING,
                message_template_marathi="frost",
                predicate=lambda _r, _m: True,
                cooldown_minutes=60,
            ),
        ),
    )
    deps, repo, _ = _deps(
        last_triggered={("PLOT_A", AlertType.LOW_BATTERY): NOW - timedelta(minutes=5)},
        ruleset=rules,
    )
    result = await execute(_reading(), deps, now=NOW)
    assert result.created == 1
    assert result.cooldown_suppressed == 1
    # Only the FROST alert was persisted.
    assert repo.created[0].alert_type is AlertType.FROST




# ===========================================================================
# Event-bus payload shape
# ===========================================================================
async def test_published_payload_contains_alert_id_and_rule_id() -> None:
    deps, _, bus = _deps(ruleset=_single_rule_set())
    await execute(_reading(), deps, now=NOW)
    name, payload = bus.published[0]
    assert name == EVENT_ALERT_CREATED
    assert payload["alert_id"] == 1
    assert payload["rule_id"] == "always"
    assert payload["alert_type"] == AlertType.LOW_BATTERY.value
    assert payload["severity"] == Severity.WARNING.value
    assert payload["plot_id"] == "PLOT_A"
    assert payload["farmer_id"] == str(FARMER)




# ===========================================================================
# Error propagation (per .cursorrules #4 - no swallowing)
# ===========================================================================
class _BoomAlertRepo(_StubAlertRepo):
    async def create(self, c):
        raise RuntimeError("DB down")




class _BoomEventBus(_StubEventBus):
    async def publish(self, name, payload):
        raise RuntimeError("bus down")




async def test_repo_create_failure_propagates() -> None:
    deps = EvaluateRulesDeps(
        alert_repo=_BoomAlertRepo(),
        event_bus=_StubEventBus(),
        ruleset=_single_rule_set(),
    )
    with pytest.raises(RuntimeError, match="DB down"):
        await execute(_reading(), deps, now=NOW)




async def test_bus_publish_failure_propagates_after_persist() -> None:
    """If the row was persisted but the event fails, the exception
    surfaces (the drain loop's metric label distinguishes it).
    """
    repo = _StubAlertRepo()
    deps = EvaluateRulesDeps(
        alert_repo=repo,
        event_bus=_BoomEventBus(),
        ruleset=_single_rule_set(),
    )
    with pytest.raises(RuntimeError, match="bus down"):
        await execute(_reading(), deps, now=NOW)
    # And the row WAS persisted before the failure.
    assert len(repo.created) == 1
