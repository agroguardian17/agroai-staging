"""Use case: evaluate the pilot ruleset against one Reading and persist
the surviving alerts.


Steps:


1. ``metrics.compute(reading)`` builds the DerivedMetrics.
2. ``rules.evaluate_to_hits(reading, metrics, ruleset)`` runs the rules.
3. For each hit: query ``AlertRepo.last_triggered_at`` against the rule's
   ``cooldown_minutes``; suppress when the cooldown hasn't elapsed.
4. Persist surviving candidates via ``AlertRepo.create``.
5. Publish ``alert.created`` on the event bus for each persisted row.


The use case is the seam between the pure rule engine (Round 9) and
the persistence + event-bus side effects. The engine itself stays
pure; the cooldown lookup and write happens here.


CALIBRATION_MODE short-circuit
------------------------------
When ``deps.calibration_mode`` is ``True`` the use case returns a
zero-count result immediately without touching metrics, rules, repo, or
bus. This is the "hardware bench" flag: during initial sensor dial-in
the probes emit unrealistic values that would otherwise trigger every
rule on every reading and spam the dashboard/WhatsApp/push. Flip the
flag off (via the ``CALIBRATION_MODE`` env var) once the sensors are
producing sane values.


PURE w.r.t. imports: stdlib + ports + domain only. No infra imports.
The application-purity AST test enforces this.
"""


from __future__ import annotations


from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


from app.application.ports.alert_repo import AlertRepo
from app.application.ports.event_bus import EVENT_ALERT_CREATED, EventBus
from app.domain.alert import AlertCandidate
from app.domain.metrics import MetricsContext, compute
from app.domain.rule_definitions import PILOT_RULESET
from app.domain.rules import Rule, RuleHit, RuleSet, evaluate_to_hits
from app.domain.sensor import Reading




@dataclass(frozen=True, slots=True)
class EvaluateRulesDeps:
    """Ports + the active RuleSet + calibration flag.


    ``ruleset`` defaults to the pilot set; tests can pin a smaller set
    to keep their assertions focused. ``metrics_context`` likewise
    defaults to the standard MetricsContext; future per-plot crop-stage
    awareness will pass a richer one constructed from the CropSeason.


    ``calibration_mode`` short-circuits execute() when True. Wired from
    ``Settings.CALIBRATION_MODE`` in :mod:`app.jobs.ingest_startup`.
    """


    alert_repo: AlertRepo
    event_bus: EventBus
    ruleset: RuleSet = PILOT_RULESET
    metrics_context: MetricsContext = field(default_factory=MetricsContext)
    calibration_mode: bool = False




@dataclass(frozen=True, slots=True)
class EvaluateRulesResult:
    """Counts surfaced as Prometheus deltas by the caller."""


    hits: int
    created: int
    cooldown_suppressed: int




async def execute(
    reading: Reading,
    deps: EvaluateRulesDeps,
    *,
    now: datetime,
) -> EvaluateRulesResult:
    """Run the pipeline; return how many alerts were created vs suppressed."""
    if deps.calibration_mode:
        # Bench mode: rules are disabled. No metrics, no repo, no bus.
        # Ingest still persists the row (that's what we want to inspect).
        return EvaluateRulesResult(hits=0, created=0, cooldown_suppressed=0)

    metrics = compute(reading, deps.metrics_context)
    hits = evaluate_to_hits(reading, metrics, deps.ruleset)


    created = 0
    suppressed = 0
    for hit in hits:
        if await _is_in_cooldown(hit.rule, reading.plot_id, now, deps.alert_repo):
            suppressed += 1
            continue
        candidate = _build_candidate(hit, reading, now)
        alert_id = await deps.alert_repo.create(candidate)
        await _publish_alert_created(
            event_bus=deps.event_bus,
            alert_id=alert_id,
            hit=hit,
            reading=reading,
        )
        created += 1


    return EvaluateRulesResult(
        hits=len(hits),
        created=created,
        cooldown_suppressed=suppressed,
    )




# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------




async def _is_in_cooldown(
    rule: Rule,
    plot_id: str,
    now: datetime,
    alert_repo: AlertRepo,
) -> bool:
    """Has the same alert_type fired on this plot within rule.cooldown_minutes?


    AlertRepo.last_triggered_at is keyed by (plot_id, alert_type) not by
    rule_id; two rules that share an alert_type therefore share a
    cooldown. The pilot's only collision is low_battery + battery_critical
    (both AlertType.LOW_BATTERY). The cooldowns are set so battery_critical
    (2h) is shorter than low_battery (12h), so a critical drop after a
    routine low warn fires through.
    """
    last_at = await alert_repo.last_triggered_at(plot_id, rule.alert_type)
    if last_at is None:
        return False
    elapsed_minutes = (now - last_at).total_seconds() / 60.0
    return elapsed_minutes < rule.cooldown_minutes




def _build_candidate(hit: RuleHit, reading: Reading, now: datetime) -> AlertCandidate:
    return AlertCandidate(
        alert_type=hit.rule.alert_type,
        severity=hit.rule.severity,
        alert_message_marathi=hit.render_message(),
        tenant_id=reading.tenant_id,
        farm_id=reading.farm_id,
        farmer_id=reading.farmer_id,
        triggered_at=now,
        device_id=reading.node_id,
        alert_value=_decimal_or_none(hit.substitutions.get("value")),
        alert_threshold=_decimal_or_none(hit.substitutions.get("threshold")),
    )




async def _publish_alert_created(
    *,
    event_bus: EventBus,
    alert_id: int,
    hit: RuleHit,
    reading: Reading,
) -> None:
    """Publish IDs only (Roadmap 1.3 - never full domain objects).


    The dispatcher (Phase 7) will re-fetch the alert by id when it
    needs the full row.
    """
    payload: dict[str, Any] = {
        "alert_id": alert_id,
        "alert_type": hit.rule.alert_type.value,
        "severity": hit.rule.severity.value,
        "rule_id": hit.rule.rule_id,
        "plot_id": reading.plot_id,
        "farmer_id": str(reading.farmer_id),
    }
    await event_bus.publish(EVENT_ALERT_CREATED, payload)




def _decimal_or_none(v: object) -> object:
    """Wrapper around the same helper used by rules.evaluate."""
    from decimal import Decimal


    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, (int, str)):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    if isinstance(v, float):
        return Decimal(str(v))
    return None




__all__ = ["EvaluateRulesDeps", "EvaluateRulesResult", "execute"]
