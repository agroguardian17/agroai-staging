"""Tests for app.application.process_reading.execute.


Validates the "fresh-insert gate" + the ingest -> rules composition.
"""


from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from app.application import evaluate_rules, ingest_telemetry
from app.application.process_reading import (
    ProcessReadingDeps,
    ProcessReadingResult,
    execute,
)
from app.domain.alert import AlertCandidate, AlertType, Severity
from app.domain.rules import Rule, RuleSet
from app.domain.sensor import Reading, TransmissionType

NOW = datetime(2026, 6, 20, 12, 0, tzinfo=UTC)
TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")




def _reading(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": TENANT,
        "farmer_id": uuid.uuid4(),
        "farm_id": uuid.uuid4(),
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
class _StubReadingRepo:
    def __init__(self, save_return: int | None) -> None:
        self._save = save_return
        self.saved: list[Reading] = []


    async def save(self, r):
        self.saved.append(r)
        return self._save


    async def latest_for_plot(self, plot_id, limit):
        return []


    async def recent_for_node(self, node_id, since):
        return []


    async def history_for_stuck_check(self, node_id, field, minutes):
        return []


    async def history_for_mad_check(self, node_id, field, hours):
        return []




class _StubEventBus:
    def __init__(self) -> None:
        self.published: list[tuple[str, dict[str, Any]]] = []


    async def publish(self, name: str, payload: dict[str, Any]) -> None:
        self.published.append((name, payload))




class _StubAlertRepo:
    def __init__(self) -> None:
        self.created: list[AlertCandidate] = []
        self._id = 1


    async def create(self, c):
        self.created.append(c)
        out = self._id
        self._id += 1
        return out


    async def last_triggered_at(self, plot_id, alert_type):
        return None


    async def resolve(self, alert_id, notes=None):
        pass


    async def list_for_plot(self, plot_id, limit=50):
        return []




def _always_fire_ruleset() -> RuleSet:
    return RuleSet(
        rules=(
            Rule(
                rule_id="fire",
                alert_type=AlertType.LOW_BATTERY,
                severity=Severity.WARNING,
                message_template_marathi="अलर्ट",
                predicate=lambda _r, _m: True,
            ),
        ),
    )




def _silent_ruleset() -> RuleSet:
    return RuleSet(rules=())




def _deps(
    *,
    save_return: int | None = 42,
    ruleset: RuleSet | None = None,
) -> tuple[ProcessReadingDeps, _StubReadingRepo, _StubAlertRepo, _StubEventBus]:
    rr = _StubReadingRepo(save_return)
    bus = _StubEventBus()
    ar = _StubAlertRepo()
    return (
        ProcessReadingDeps(
            ingest_deps=ingest_telemetry.IngestDeps(reading_repo=rr, event_bus=bus),
            evaluate_deps=evaluate_rules.EvaluateRulesDeps(
                alert_repo=ar, event_bus=bus, ruleset=ruleset or _always_fire_ruleset()
            ),
        ),
        rr,
        ar,
        bus,
    )




# ===========================================================================
# Fresh insert -> rules ran
# ===========================================================================
async def test_fresh_insert_invokes_rule_evaluation() -> None:
    deps, _, alert_repo, bus = _deps(save_return=100)
    out = await execute(_reading(), deps, now=NOW)
    assert isinstance(out, ProcessReadingResult)
    assert out.ingest.reading_id == 100
    assert out.rules is not None
    assert out.rules.hits == 1
    assert out.rules.created == 1
    assert len(alert_repo.created) == 1
    # Two events: telemetry.ingested + alert.created.
    names = {n for n, _ in bus.published}
    assert "telemetry.ingested" in names
    assert "alert.created" in names




# ===========================================================================
# Duplicate -> rules skipped
# ===========================================================================
async def test_duplicate_row_skips_rule_evaluation() -> None:
    deps, _, alert_repo, bus = _deps(save_return=None)
    out = await execute(_reading(), deps, now=NOW)
    assert out.ingest.reading_id is None
    assert out.rules is None
    assert alert_repo.created == []
    # No telemetry.ingested event either (ingest_telemetry suppresses it).
    assert bus.published == []




# ===========================================================================
# Silent ruleset -> ingest still ran
# ===========================================================================
async def test_silent_ruleset_runs_ingest_with_no_alerts() -> None:
    deps, reading_repo, alert_repo, _ = _deps(save_return=7, ruleset=_silent_ruleset())
    out = await execute(_reading(), deps, now=NOW)
    assert out.ingest.reading_id == 7
    assert out.rules is not None
    assert out.rules.hits == 0
    assert out.rules.created == 0
    assert len(reading_repo.saved) == 1
    assert alert_repo.created == []




# ===========================================================================
# Default now=None uses wall clock (smoke)
# ===========================================================================
async def test_default_now_does_not_crash() -> None:
    deps, _, _, _ = _deps()
    out = await execute(_reading(), deps)  # no now arg
    assert out.rules is not None
    assert out.rules.created == 1
