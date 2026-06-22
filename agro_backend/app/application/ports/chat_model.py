"""Port: async chat completion.

Round-11 use cases (compose_advisory) call ``ChatModel.complete()`` with
a system prompt + user prompt; the adapter (Claude / log-only / future
OpenAI) returns the text + bookkeeping.

The port deliberately avoids exposing the underlying SDK's message
shape. If we later want to swap Anthropic for another provider, only
the adapter changes; use cases keep the same Protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """One call to a chat model. Frozen so accidental mutation doesn't
    desync a retry from the original payload.

    ``system`` and ``user`` are plain strings; the adapter shapes them
    into the provider's native message envelope. ``model`` is the
    explicit model name (e.g. ``claude-sonnet-4-5``) — the use case
    decides which tier to pay for, not the adapter.
    """

    system: str
    user: str
    model: str
    max_tokens: int = 800
    temperature: float = 0.2  # advisory generation wants deterministic-ish output


@dataclass(frozen=True, slots=True)
class ChatResponse:
    """Outcome of one chat call.

    ``input_tokens`` + ``output_tokens`` come from the provider's
    usage block; we sum them when computing cost.
    """

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int
    finish_reason: str = "stop"


class ChatModelError(Exception):
    """Raised by the adapter when the provider rejects the call.

    The adapter MUST NOT raise on retryable network errors without
    classification — it should distinguish transient (timeout, 5xx)
    from permanent (4xx, content_policy) so the use case can act.
    """

    def __init__(self, message: str, *, transient: bool = False) -> None:
        super().__init__(message)
        self.transient = transient


@runtime_checkable
class ChatModel(Protocol):
    """Single async method. No streaming for Round 11."""

    async def complete(self, request: ChatRequest) -> ChatResponse: ...


__all__ = ["ChatModel", "ChatModelError", "ChatRequest", "ChatResponse"]
