"""Pure rule engine.


A :class:`Rule` is a (predicate, message-template, alert spec) triple.
The :func:`evaluate` function applies a :class:`RuleSet` to a
(Reading, DerivedMetrics) pair and returns a list of
:class:`~app.domain.alert.AlertCandidate` objects ready for the
notification dispatcher (Round 10) to consider.


PURE module: stdlib only. No framework imports. No IO. No clock - the
caller passes ``now`` so tests can pin it.


Why a Python-predicate model rather than a JSON DSL:


* Pilot ruleset is small (~7 rules); the cost of inventing a DSL is
  larger than the cost of writing 7 lambdas.
* The predicate has the full type system available: it works on
  :class:`Reading` and :class:`DerivedMetrics`, not on stringly-typed
  field paths.
* Tests can construct ad-hoc rules in a single expression instead of
  building JSON blobs.


If Phase 7 needs config-driven rules (so agronomists can author them
without a deploy), we'll add a second loader that reads YAML/JSON and
materialises Rule objects on top of this engine. The engine itself
doesn't change.


Cooldown handling: the engine emits one AlertCandidate per matching
rule per call. It does NOT consult cooldown state - that lookup
requires a repo (``AlertRepo.last_triggered_at``) and lives in the
application layer (Round 10's hot-rule pipeline). Each rule declares
its ``cooldown_minutes`` here so the application layer knows the
intended quiet period without re-encoding it.
"""


from __future__ import annotations

import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.alert import AlertCandidate, AlertType, Severity
from app.domain.metrics import DerivedMetrics
from app.domain.sensor import Reading

# A predicate sees the reading + the derived metrics and returns either:
# * False  -> rule didn't fire
# * True   -> rule fired; engine uses .message_template_marathi as-is
# * dict   -> rule fired AND the dict supplies values for .format() on
#             the template (e.g. {"voltage": "3.10"})
PredicateResult = bool | dict[str, object]
RulePredicate = Callable[[Reading, DerivedMetrics], PredicateResult]




@dataclass(frozen=True, slots=True)
class Rule:
    """One rule definition.


    The ``rule_id`` is a stable string identifier used in metrics and
    test diagnostics. It MUST be unique within a RuleSet.
    """


    rule_id: str
    alert_type: AlertType
    severity: Severity
    message_template_marathi: str
    predicate: RulePredicate
    cooldown_minutes: int = 60  # default quiet period after firing
    # Optional: when True the rule may carry numeric value + threshold
    # in the AlertCandidate (Roadmap §4.4 - the dispatcher uses these
    # for the alert card's "actual / expected" row).
    emits_value: bool = False




@dataclass(frozen=True, slots=True)
class RuleSet:
    """Collection of rules evaluated together. Frozen + ordered for
    deterministic test output and metric label stability.
    """


    rules: tuple[Rule, ...]


    def __post_init__(self) -> None:
        seen: set[str] = set()
        for r in self.rules:
            if r.rule_id in seen:
                raise ValueError(f"Duplicate rule_id in RuleSet: {r.rule_id}")
            seen.add(r.rule_id)




@dataclass(frozen=True, slots=True)
class RuleHit:
    """Internal record: a rule that fired plus the template substitutions.


    Returned by :func:`evaluate_to_hits` for callers that want metric
    labels or want to apply additional filtering before building
    AlertCandidates. :func:`evaluate` is the convenience wrapper that
    materialises AlertCandidates directly.
    """


    rule: Rule
    substitutions: dict[str, object] = field(default_factory=dict)


    def render_message(self) -> str:
        if not self.substitutions:
            return self.rule.message_template_marathi
        try:
            return self.rule.message_template_marathi.format(**self.substitutions)
        except (KeyError, IndexError):
            # Defensive: if a template expects {voltage} but the predicate
            # forgot to supply it, fall back to the unrendered template
            # so the farmer still gets *something* readable.
            return self.rule.message_template_marathi




# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------




def evaluate_to_hits(
    reading: Reading,
    metrics: DerivedMetrics,
    ruleset: RuleSet,
) -> list[RuleHit]:
    """Run the ruleset, return the rules that fired (no AlertCandidates yet)."""
    hits: list[RuleHit] = []
    for rule in ruleset.rules:
        result = rule.predicate(reading, metrics)
        if result is False or result is None:
            continue
        substitutions: dict[str, object]
        if isinstance(result, dict):
            substitutions = result
        elif result is True:
            substitutions = {}
        else:
            continue
        hits.append(RuleHit(rule=rule, substitutions=substitutions))
    return hits




def evaluate(
    reading: Reading,
    metrics: DerivedMetrics,
    ruleset: RuleSet,
    *,
    now: datetime,
) -> list[AlertCandidate]:
    """Run the ruleset; return AlertCandidates ready for the dispatcher.


    ``now`` is injected so the engine stays pure (no ``datetime.now()``).
    All emitted candidates carry ``triggered_at=now``.
    """
    hits = evaluate_to_hits(reading, metrics, ruleset)
    candidates: list[AlertCandidate] = []
    for hit in hits:
        candidates.append(
            AlertCandidate(
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
        )
    return candidates




def _decimal_or_none(v: object) -> Decimal | None:
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
        # Should be rare; convert via string to dodge float-precision artefacts.
        return Decimal(str(v))
    return None




# ---------------------------------------------------------------------------
# Helpers for rule authors (used by app.domain.rule_definitions)
# ---------------------------------------------------------------------------




def alert_id_for(reading: Reading, rule_id: str) -> str:
    """Stable opaque id for a (reading, rule) pair.


    Useful for deterministic test assertions: ``alert_id_for(r, "low_battery")``
    is the same string for the same inputs. Not stored in the DB; the
    DB row gets a serial alert_id from Postgres.
    """
    return f"{reading.node_id}:{rule_id}:{reading.recorded_at.isoformat()}"




def _uuid_namespace() -> uuid.UUID:
    """Stable namespace UUID for hashing rule_ids if any caller wants UUIDv5.
    Not used by the engine itself; exposed for downstream tooling.
    """
    return uuid.UUID("11111111-2222-3333-4444-555555555555")



__all__ = [
    "PredicateResult",
    "Rule",
    "RuleHit",
    "RulePredicate",
    "RuleSet",
    "alert_id_for",
    "evaluate",
    "evaluate_to_hits",
]
