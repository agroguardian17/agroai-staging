"""Use case: drive one alert through the advisory state machine.

Round 13. The subscriber (``app/jobs/advisory_subscriber.py``) calls this for
every ``alert.created`` event *and* for every due ``pending`` row found by the
reconciliation sweep. Both paths funnel here, and the atomic **claim** makes
that safe: only one of them proceeds per alert.

State machine (advisory_status on ``alerts_notifications``):

    pending → in_flight → composed            (compose returned a suggestion)
                        → skipped              (compose returned a skip reason)
                        → failed_permanent     (ChatModelError transient=False)
                        → pending (backoff)    (transient failure, attempts left)
                        → failed_transient     (transient failure, attempts exhausted)

Retry policy (transient = timeout / 5xx / rate-limit):
* attempts is incremented; ``next_retry_at = now + backoff[attempts-1]`` (or the
  rate-limit ``Retry-After`` when the adapter surfaced one).
* once attempts exceeds the backoff schedule length, the row is ``failed_transient``.

PURE w.r.t. imports: stdlib + ports + domain + application only. No infra.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application import compose_advisory
from app.application.compose_advisory import ComposeAdvisoryDeps
from app.application.ports.ai_suggestion_repo import AiSuggestion
from app.application.ports.alert_repo import AlertRepo
from app.application.ports.chat_model import ChatModelError
from app.application.ports.event_bus import EVENT_SUGGESTION_GENERATED, EventBus

# Exponential backoff before each retry, indexed by attempt number. A transient
# failure that pushes ``attempts`` past the end of this schedule becomes
# ``failed_transient``. 30s → 2m → 8m → 30m → 2h, i.e. up to 6 compose attempts
# (1 initial + 5 retries).
DEFAULT_BACKOFF_SECONDS: tuple[int, ...] = (30, 120, 480, 1800, 7200)


@dataclass(frozen=True, slots=True)
class DispatchAdvisoryDeps:
    alert_repo: AlertRepo
    compose_deps: ComposeAdvisoryDeps
    event_bus: EventBus
    backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS


@dataclass(frozen=True, slots=True)
class DispatchAdvisoryResult:
    # composed | skipped | failed_permanent | failed_transient | transient_retry
    # | already_handled
    outcome: str
    skip_reason: str | None = None
    suggestion: AiSuggestion | None = None
    attempts: int = 0


async def execute(
    *,
    alert_id: int,
    deps: DispatchAdvisoryDeps,
    now: datetime,
) -> DispatchAdvisoryResult:
    """Claim the alert, compose its advisory, and record the outcome."""
    attempts = await deps.alert_repo.claim_for_advisory(alert_id, now)
    if attempts is None:
        # Another worker (or an earlier tick) already claimed/handled it, or it
        # is not yet due. Nothing to do — never touch a row we didn't claim.
        return DispatchAdvisoryResult(outcome="already_handled")

    try:
        result = await compose_advisory.execute(alert_id=alert_id, deps=deps.compose_deps, now=now)
    except ChatModelError as exc:
        if exc.transient:
            return await _handle_transient(alert_id, attempts, exc, deps, now)
        await deps.alert_repo.set_advisory_outcome(
            alert_id, status="failed_permanent", attempts=attempts, last_error=str(exc)
        )
        return DispatchAdvisoryResult(outcome="failed_permanent", attempts=attempts)
    except Exception as exc:  # unexpected — treat as retryable, capped by backoff
        return await _handle_transient(alert_id, attempts, exc, deps, now)

    if result.suggestion is None:
        reason = result.skip_reason or "unknown"
        await deps.alert_repo.set_advisory_outcome(
            alert_id, status="skipped", attempts=attempts, last_error=f"skip:{reason}"
        )
        return DispatchAdvisoryResult(outcome="skipped", skip_reason=reason, attempts=attempts)

    await deps.alert_repo.set_advisory_outcome(alert_id, status="composed", attempts=attempts)
    await deps.event_bus.publish(
        EVENT_SUGGESTION_GENERATED,
        {
            "suggestion_id": str(result.suggestion.suggestion_id),
            "plot_id": result.suggestion.plot_id,
            "farmer_id": str(result.suggestion.farmer_id),
            # Not scored yet — Round 18's confidence work fills this in.
            "confidence_band": None,
            "advisory_status": "composed",
        },
    )
    return DispatchAdvisoryResult(
        outcome="composed", suggestion=result.suggestion, attempts=attempts
    )


async def _handle_transient(
    alert_id: int,
    attempts: int,
    exc: Exception,
    deps: DispatchAdvisoryDeps,
    now: datetime,
) -> DispatchAdvisoryResult:
    new_attempts = attempts + 1
    schedule = deps.backoff_seconds
    if new_attempts > len(schedule):
        await deps.alert_repo.set_advisory_outcome(
            alert_id,
            status="failed_transient",
            attempts=new_attempts,
            last_error=str(exc),
        )
        return DispatchAdvisoryResult(outcome="failed_transient", attempts=new_attempts)

    retry_after = getattr(exc, "retry_after_seconds", None)
    delay = retry_after if retry_after is not None else schedule[new_attempts - 1]
    next_retry_at = now + timedelta(seconds=float(delay))
    await deps.alert_repo.set_advisory_outcome(
        alert_id,
        status="pending",
        attempts=new_attempts,
        next_retry_at=next_retry_at,
        last_error=str(exc),
    )
    return DispatchAdvisoryResult(outcome="transient_retry", attempts=new_attempts)


__all__ = [
    "DEFAULT_BACKOFF_SECONDS",
    "DispatchAdvisoryDeps",
    "DispatchAdvisoryResult",
    "execute",
]
