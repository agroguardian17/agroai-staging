"""End-to-end Reading processor: ingest → rule evaluation.


This is the use case the MQTT broker now calls (in place of
``ingest_telemetry.execute`` directly). It composes two existing
use cases:


1. ``ingest_telemetry.execute`` — validate + save + publish
   ``telemetry.ingested``. Returns an IngestResult; ``reading_id`` is
   None when the row was a duplicate.
2. ``evaluate_rules.execute`` — only invoked when ``reading_id is not
   None`` (i.e. on a fresh insert). On a duplicate we skip rule
   evaluation so re-ingest doesn't double-create alerts.


The split between this composer and the two use cases is deliberate:


* Each underlying use case stays single-purpose and is testable in
  isolation.
* The composer's only responsibility is the "fresh-insert gate" — a
  one-line decision that doesn't belong inside either child.
* If Phase 4.5 wants to move rule evaluation to an async subscriber
  on ``telemetry.ingested``, we delete this composer; the children
  don't change.
"""


from __future__ import annotations


from dataclasses import dataclass
from datetime import UTC, datetime


from app.application import evaluate_rules, ingest_telemetry
from app.domain.sensor import Reading




@dataclass(frozen=True, slots=True)
class ProcessReadingDeps:
    ingest_deps: ingest_telemetry.IngestDeps
    evaluate_deps: evaluate_rules.EvaluateRulesDeps




@dataclass(frozen=True, slots=True)
class ProcessReadingResult:
    ingest: ingest_telemetry.IngestResult
    # ``rules`` is None when rules were skipped (duplicate row).
    rules: evaluate_rules.EvaluateRulesResult | None


    @property
    def reading_id(self) -> int | None:
        """Pass-through for the MQTT broker's drain-loop duplicate check.


        Keeps the broker working with either an IngestResult-shaped
        return (Round 7 wiring) or a ProcessReadingResult (Round 10).
        """
        return self.ingest.reading_id




async def execute(
    reading: Reading,
    deps: ProcessReadingDeps,
    *,
    now: datetime | None = None,
) -> ProcessReadingResult:
    """Run the full Reading pipeline.


    ``now`` is the timestamp used as the rules' triggered_at. Defaults
    to wall-clock UTC; tests pass a fixed value. We don't use the
    Reading's recorded_at because cooldown windows must be measured
    against ingest time, not packet time (a backlog flush replaying
    old packets shouldn't re-trigger every alert).
    """
    ingest_result = await ingest_telemetry.execute(reading, deps.ingest_deps)
    if ingest_result.reading_id is None:
        # Duplicate row — the alerts were emitted when it was first
        # ingested. Skip to avoid duplicate alert rows.
        return ProcessReadingResult(ingest=ingest_result, rules=None)


    eval_now = now or datetime.now(UTC)
    rules_result = await evaluate_rules.execute(reading, deps.evaluate_deps, now=eval_now)
    return ProcessReadingResult(ingest=ingest_result, rules=rules_result)




__all__ = ["ProcessReadingDeps", "ProcessReadingResult", "execute"]
