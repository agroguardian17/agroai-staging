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
from decimal import Decimal
from typing import Any

from app.application.ports.alert_repo import AlertRepo
from app.application.ports.event_bus import EVENT_ALERT_CREATED, EventBus
from app.domain.alert import AlertCandidate
from app.domain.metrics import MetricsContext, compute
from app.domain.rule_definitions import PILOT_RULESET
from app.domain.rules import Rule, RuleHit, RuleSet, evaluate_all
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
class RuleEvaluationRecord:
    """Per-rule outcome for one reading — the Reading Journey's rule step.

    Observability only (Round-3 R3.1). Carries JSON-friendly scalars so the
    broker can drop it straight into a ``pipeline_trace`` stage without
    re-touching the domain objects. ``alert_id`` is set only when the rule
    fired AND wasn't cooldown-suppressed AND a row was created.
    """

    rule_id: str
    alert_type: str
    severity: str
    fired: bool
    cooldown_suppressed: bool
    alert_id: int | None
    value: str | None
    threshold: str | None


@dataclass(frozen=True, slots=True)
class EvaluateRulesResult:
    """Counts surfaced as Prometheus deltas by the caller.

    ``evaluations`` is the per-rule journey (one record per rule in ruleset
    order), added for R3.1. It is additive and defaults empty, so the
    calibration-mode short-circuit and existing callers are unaffected.
    """

    hits: int
    created: int
    cooldown_suppressed: int
    evaluations: list[RuleEvaluationRecord] = field(default_factory=list)


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
    evaluations = evaluate_all(reading, metrics, deps.ruleset)

    hits = 0
    created = 0
    suppressed = 0
    records: list[RuleEvaluationRecord] = []
    for ev in evaluations:
        if not ev.fired:
            records.append(_record(ev.rule, fired=False, cooldown=False, alert_id=None, hit=None))
            continue

        hits += 1
        hit = ev.as_hit()
        if await _is_in_cooldown(hit.rule, reading.plot_id, now, deps.alert_repo):
            suppressed += 1
            records.append(_record(hit.rule, fired=True, cooldown=True, alert_id=None, hit=hit))
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
        records.append(_record(hit.rule, fired=True, cooldown=False, alert_id=alert_id, hit=hit))

    return EvaluateRulesResult(
        hits=hits,
        created=created,
        cooldown_suppressed=suppressed,
        evaluations=records,
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


def _record(
    rule: Rule,
    *,
    fired: bool,
    cooldown: bool,
    alert_id: int | None,
    hit: RuleHit | None,
) -> RuleEvaluationRecord:
    """Build one per-rule journey record (JSON-friendly scalars)."""
    value = _str_or_none(hit.substitutions.get("value")) if hit is not None else None
    threshold = _str_or_none(hit.substitutions.get("threshold")) if hit is not None else None
    return RuleEvaluationRecord(
        rule_id=rule.rule_id,
        alert_type=rule.alert_type.value,
        severity=rule.severity.value,
        fired=fired,
        cooldown_suppressed=cooldown,
        alert_id=alert_id,
        value=value,
        threshold=threshold,
    )


def _str_or_none(v: object) -> str | None:
    return None if v is None else str(v)


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


def _decimal_or_none(v: object) -> Decimal | None:
    """Wrapper around the same helper used by rules.evaluate."""
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    if isinstance(v, int | str):
        try:
            return Decimal(str(v))
        except Exception:
            return None
    if isinstance(v, float):
        return Decimal(str(v))
    return None


__all__ = [
    "EvaluateRulesDeps",
    "EvaluateRulesResult",
    "RuleEvaluationRecord",
    "execute",
]
