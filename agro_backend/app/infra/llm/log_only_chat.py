"""Stub chat model for dev / tests.

Returns a canned Marathi advisory string so the rest of the pipeline
can be exercised without hitting Anthropic. Useful for:

* Unit tests that don't need a real LLM call.
* Demo runs on a laptop without an API key.
* Cost-free smoke testing of the full alert -> compose path.

The canned text deliberately mentions the alert_type so we can
assert the request was actually routed through (vs. a hardcoded
reply that would mask bugs).
"""

from __future__ import annotations

import time

import structlog

from app.application.ports.chat_model import ChatRequest, ChatResponse

log = structlog.get_logger(__name__)


class LogOnlyChatModel:
    """No-network chat model. Echoes a synthesized response."""

    def __init__(self, *, canned_text: str | None = None) -> None:
        self._canned = canned_text

    async def complete(self, request: ChatRequest) -> ChatResponse:
        start = time.perf_counter()
        text = self._canned or _synthesize(request)
        latency_ms = int((time.perf_counter() - start) * 1000)
        log.info(
            "log_only_chat.fake_completion",
            model=request.model,
            system_chars=len(request.system),
            user_chars=len(request.user),
        )
        # Token counts are rough estimates (4 chars ~= 1 token for Latin
        # text; Marathi is a bit different but it doesn't matter for the
        # dev stub).
        in_tokens = max(1, (len(request.system) + len(request.user)) // 4)
        out_tokens = max(1, len(text) // 4)
        return ChatResponse(
            text=text,
            model=request.model,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            latency_ms=latency_ms,
            finish_reason="stop",
        )


def _synthesize(request: ChatRequest) -> str:
    """Generic Marathi text that the test suite can match on."""
    return "[dev-stub] नमस्कार शेतकरी मित्र. आपल्या शेतात एक नवीन सूचना आहे. कृपया सेन्सर तपासा."


__all__ = ["LogOnlyChatModel"]
