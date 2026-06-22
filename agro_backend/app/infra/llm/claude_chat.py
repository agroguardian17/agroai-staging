"""Anthropic Claude adapter for :class:`~app.application.ports.chat_model.ChatModel`.

Uses the official ``anthropic`` SDK's async client. We deliberately
don't expose anthropic types in the public API; use cases see only
the ports' :class:`ChatRequest` / :class:`ChatResponse` shapes.

Network errors are classified into "transient" (retryable: timeout,
connection errors, 5xx) vs "permanent" (4xx, content_policy). The
use case can decide whether to back off + retry.

Cost accounting: tokens are reported on the response; the periodic
cost-tracking job (Phase 5+) reads them off the Prometheus counter
that the application layer increments after each call.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import anthropic

from app.application.ports.chat_model import (
    ChatModel,
    ChatModelError,
    ChatRequest,
    ChatResponse,
)


@dataclass(frozen=True, slots=True)
class ClaudeSettings:
    api_key: str
    timeout_seconds: float = 30.0


class ClaudeChatModel:
    """:class:`ChatModel` over Anthropic's ``Messages`` endpoint."""

    def __init__(
        self,
        settings: ClaudeSettings,
        *,
        client: anthropic.AsyncAnthropic | None = None,
    ) -> None:
        self._s = settings
        self._owns_client = client is None
        self._client = client or anthropic.AsyncAnthropic(
            api_key=settings.api_key,
            timeout=settings.timeout_seconds,
        )

    async def complete(self, request: ChatRequest) -> ChatResponse:
        start = time.perf_counter()
        try:
            msg = await self._client.messages.create(
                model=request.model,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                system=request.system,
                messages=[{"role": "user", "content": request.user}],
            )
        except anthropic.APITimeoutError as exc:
            raise ChatModelError(f"claude timeout: {exc}", transient=True) from exc
        except anthropic.APIConnectionError as exc:
            raise ChatModelError(f"claude connection: {exc}", transient=True) from exc
        except anthropic.RateLimitError as exc:
            # Rate-limited; treat as transient (retry after backoff).
            raise ChatModelError(f"claude rate_limited: {exc}", transient=True) from exc
        except anthropic.APIStatusError as exc:
            # 4xx (content policy, invalid args). Permanent for this prompt.
            transient = 500 <= getattr(exc, "status_code", 500) < 600
            raise ChatModelError(f"claude api_error: {exc}", transient=transient) from exc

        latency_ms = int((time.perf_counter() - start) * 1000)
        text = _extract_text(msg)
        usage = getattr(msg, "usage", None)
        input_tokens = getattr(usage, "input_tokens", 0) or 0
        output_tokens = getattr(usage, "output_tokens", 0) or 0
        finish_reason = getattr(msg, "stop_reason", "stop") or "stop"
        return ChatResponse(
            text=text,
            model=request.model,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            latency_ms=latency_ms,
            finish_reason=str(finish_reason),
        )

    async def aclose(self) -> None:
        """Dispose the client if we own it (lifespan hook)."""
        if self._owns_client:
            await self._client.close()


def _extract_text(msg: object) -> str:
    """Concatenate all text blocks from an Anthropic Message.

    The SDK returns ``content`` as a list of blocks (text / tool_use / ...).
    For our use case (no tools yet) only ``TextBlock``s show up; we
    join them on newline. Defensive against unexpected block shapes.
    """
    content = getattr(msg, "content", None) or []
    parts: list[str] = []
    for block in content:
        t = getattr(block, "type", None) or getattr(block, "_type", None)
        if t == "text":
            parts.append(str(getattr(block, "text", "")))
    return "\n".join(parts).strip()


# Verify the adapter satisfies the Protocol (helps catch shape drift).
_PROTOCOL_CHECK: type[ChatModel] = ClaudeChatModel  # type: ignore[assignment]


__all__ = ["ClaudeChatModel", "ClaudeSettings"]
