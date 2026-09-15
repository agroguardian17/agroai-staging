"""Use case: deliver one composed advisory to the farmer over WhatsApp.

Round 14. The delivery subscriber (``app/jobs/delivery_subscriber.py``) calls
this for every ``suggestion.generated`` event *and* for every due ``pending``
row found by the reconciliation sweep. Both funnel here, and the atomic
**claim** makes that safe: only one proceeds per suggestion.

State machine (``delivery_status`` on ``ai_suggestions``):

    pending → in_flight → sent               (provider accepted the send)
                        → skipped             (nothing to send / no recipient)
                        → failed_permanent    (4xx: bad template, invalid number)
                        → pending (backoff)   (transient: rate-limit / 5xx / net)
                        → failed_transient    (transient, attempts exhausted)

A proactive (outside the 24h service window) WhatsApp message must be a
pre-approved template, so the Marathi advisory text goes out as the template's
body parameter.

PURE w.r.t. imports: stdlib + ports + domain + application only. No infra.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from app.application.ports.ai_suggestion_repo import AiSuggestionRepo
from app.application.ports.farmer_repo import FarmerRepo
from app.application.ports.whatsapp_sender import WhatsappSender, WhatsappSendResult

# Same shape/tempo as the compose backoff (dispatch_advisory): 30s → 2m → 8m →
# 30m → 2h, i.e. up to 6 send attempts (1 initial + 5 retries) before a
# transient failure becomes ``failed_transient``.
DEFAULT_BACKOFF_SECONDS: tuple[int, ...] = (30, 120, 480, 1800, 7200)

# Provider error_codes that are worth retrying. Everything else (a 4xx that is
# not rate-limiting — bad template, invalid recipient, revoked token) is
# permanent: retrying would just fail the same way.
_TRANSIENT_CODES = frozenset(
    {"network_error", "http_429", "meta_80008", "meta_130429", "sender_raised"}
)


def _is_transient(error_code: str | None) -> bool:
    if error_code is None:
        return True  # unknown → give it the benefit of a bounded retry
    if error_code in _TRANSIENT_CODES:
        return True
    # Any 5xx from Meta/Graph is a server-side blip.
    return error_code.startswith("http_5")


# farmers.language_preference stores a full word ('marathi'/'hindi'/'english',
# migration 0001), but a WhatsApp template's language must be the Meta/ISO code
# ('mr'/'hi'/'en'). Map it; unknown/blank falls back to the deps default.
_META_LANG = {"marathi": "mr", "hindi": "hi", "english": "en"}


def _meta_language(preference: str | None, default: str) -> str:
    return _META_LANG.get((preference or "").strip().lower(), default)


@dataclass(frozen=True, slots=True)
class DeliverAdvisoryDeps:
    ai_suggestion_repo: AiSuggestionRepo
    farmer_repo: FarmerRepo
    sender: WhatsappSender
    template_name: str
    default_language: str = "mr"
    require_review: bool = False
    backoff_seconds: tuple[int, ...] = DEFAULT_BACKOFF_SECONDS


@dataclass(frozen=True, slots=True)
class DeliverAdvisoryResult:
    # sent | skipped | failed_permanent | failed_transient | transient_retry
    # | already_handled
    outcome: str
    skip_reason: str | None = None
    provider_message_id: str | None = None
    attempts: int = 0


async def execute(
    *,
    suggestion_id: uuid.UUID,
    deps: DeliverAdvisoryDeps,
    now: datetime,
) -> DeliverAdvisoryResult:
    """Claim the suggestion, send it via WhatsApp, and record the outcome."""
    attempts = await deps.ai_suggestion_repo.claim_for_delivery(
        suggestion_id, now, require_review=deps.require_review
    )
    if attempts is None:
        # Another worker/tick already handled it, it is not yet due, or (with
        # require_review) not yet approved. Never touch a row we didn't claim.
        return DeliverAdvisoryResult(outcome="already_handled")

    suggestion = await deps.ai_suggestion_repo.find_by_id(suggestion_id)
    if suggestion is None or not (suggestion.full_message_marathi or "").strip():
        await deps.ai_suggestion_repo.set_delivery_outcome(
            suggestion_id, status="skipped", attempts=attempts, last_error="skip:empty_message"
        )
        return DeliverAdvisoryResult(
            outcome="skipped", skip_reason="empty_message", attempts=attempts
        )

    farmer = await deps.farmer_repo.find_by_id(suggestion.farmer_id)
    if farmer is None:
        # No recipient — retrying will not conjure one. Permanent.
        await deps.ai_suggestion_repo.set_delivery_outcome(
            suggestion_id,
            status="failed_permanent",
            attempts=attempts,
            last_error="unknown_farmer",
        )
        return DeliverAdvisoryResult(outcome="failed_permanent", attempts=attempts)

    language = _meta_language(farmer.language_preference, deps.default_language)
    try:
        result = await deps.sender.send_template(
            phone=farmer.phone,
            template_name=deps.template_name,
            language_code=language,
            body_params=[suggestion.full_message_marathi],
        )
    except Exception as exc:  # adapter contract says it shouldn't raise; be safe
        result = WhatsappSendResult(
            accepted=False,
            provider_message_id=None,
            error_code="sender_raised",
            error_detail=str(exc),
        )

    if result.accepted:
        await deps.ai_suggestion_repo.set_delivery_outcome(
            suggestion_id,
            status="sent",
            attempts=attempts,
            provider_message_id=result.provider_message_id,
            sent_at=now,
        )
        return DeliverAdvisoryResult(
            outcome="sent", provider_message_id=result.provider_message_id, attempts=attempts
        )

    if not _is_transient(result.error_code):
        await deps.ai_suggestion_repo.set_delivery_outcome(
            suggestion_id,
            status="failed_permanent",
            attempts=attempts,
            last_error=result.error_code or "rejected",
        )
        return DeliverAdvisoryResult(outcome="failed_permanent", attempts=attempts)

    return await _handle_transient(suggestion_id, attempts, result.error_code, deps, now)


async def _handle_transient(
    suggestion_id: uuid.UUID,
    attempts: int,
    error_code: str | None,
    deps: DeliverAdvisoryDeps,
    now: datetime,
) -> DeliverAdvisoryResult:
    new_attempts = attempts + 1
    schedule = deps.backoff_seconds
    if new_attempts > len(schedule):
        await deps.ai_suggestion_repo.set_delivery_outcome(
            suggestion_id,
            status="failed_transient",
            attempts=new_attempts,
            last_error=error_code or "transient",
        )
        return DeliverAdvisoryResult(outcome="failed_transient", attempts=new_attempts)

    delay = schedule[new_attempts - 1]
    next_retry_at = now + timedelta(seconds=float(delay))
    await deps.ai_suggestion_repo.set_delivery_outcome(
        suggestion_id,
        status="pending",
        attempts=new_attempts,
        next_retry_at=next_retry_at,
        last_error=error_code or "transient",
    )
    return DeliverAdvisoryResult(outcome="transient_retry", attempts=new_attempts)


__all__ = [
    "DEFAULT_BACKOFF_SECONDS",
    "DeliverAdvisoryDeps",
    "DeliverAdvisoryResult",
    "execute",
]
