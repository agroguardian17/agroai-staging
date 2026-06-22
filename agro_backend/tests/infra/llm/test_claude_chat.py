"""Tests for ClaudeChatModel. Uses respx to mock the Anthropic HTTP layer.

Anthropic's SDK uses httpx under the hood, so respx intercepts the call
without needing to mock the SDK itself.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from app.application.ports.chat_model import ChatModelError, ChatRequest
from app.infra.llm.claude_chat import ClaudeChatModel, ClaudeSettings

API_URL = "https://api.anthropic.com/v1/messages"


def _settings() -> ClaudeSettings:
    return ClaudeSettings(api_key="sk-test-key")


def _request() -> ChatRequest:
    return ChatRequest(
        system="You are an MSCI-pilot agronomist.",
        user="Battery dropped below 3.30V. What should the farmer do?",
        model="claude-sonnet-4-5",
        max_tokens=200,
        temperature=0.2,
    )


def _ok_payload(text: str = "बॅटरी बदला.") -> dict:
    return {
        "id": "msg_01",
        "type": "message",
        "role": "assistant",
        "model": "claude-sonnet-4-5",
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "content": [{"type": "text", "text": text}],
        "usage": {"input_tokens": 42, "output_tokens": 17},
    }


@pytest.mark.asyncio
@respx.mock
async def test_complete_returns_text_and_usage() -> None:
    respx.post(API_URL).mock(return_value=httpx.Response(200, json=_ok_payload()))
    model = ClaudeChatModel(_settings())
    try:
        out = await model.complete(_request())
    finally:
        await model.aclose()
    assert out.text == "बॅटरी बदला."
    assert out.input_tokens == 42
    assert out.output_tokens == 17
    assert out.model == "claude-sonnet-4-5"
    assert out.finish_reason == "end_turn"
    assert out.latency_ms >= 0


@pytest.mark.asyncio
@respx.mock
async def test_complete_concatenates_multiple_text_blocks() -> None:
    body = _ok_payload()
    body["content"] = [
        {"type": "text", "text": "पहिली ओळ."},
        {"type": "text", "text": "दुसरी ओळ."},
    ]
    respx.post(API_URL).mock(return_value=httpx.Response(200, json=body))
    model = ClaudeChatModel(_settings())
    try:
        out = await model.complete(_request())
    finally:
        await model.aclose()
    assert "पहिली ओळ." in out.text
    assert "दुसरी ओळ." in out.text


@pytest.mark.asyncio
@respx.mock
async def test_5xx_marks_transient() -> None:
    respx.post(API_URL).mock(return_value=httpx.Response(503, json={"error": {"message": "down"}}))
    model = ClaudeChatModel(_settings())
    try:
        with pytest.raises(ChatModelError) as exc_info:
            await model.complete(_request())
    finally:
        await model.aclose()
    assert exc_info.value.transient is True


@pytest.mark.asyncio
@respx.mock
async def test_4xx_marks_permanent() -> None:
    respx.post(API_URL).mock(
        return_value=httpx.Response(
            400, json={"error": {"type": "invalid_request_error", "message": "bad"}}
        )
    )
    model = ClaudeChatModel(_settings())
    try:
        with pytest.raises(ChatModelError) as exc_info:
            await model.complete(_request())
    finally:
        await model.aclose()
    assert exc_info.value.transient is False


@pytest.mark.asyncio
@respx.mock
async def test_429_marks_transient() -> None:
    respx.post(API_URL).mock(
        return_value=httpx.Response(429, json={"error": {"type": "rate_limit_error"}})
    )
    model = ClaudeChatModel(_settings())
    try:
        with pytest.raises(ChatModelError) as exc_info:
            await model.complete(_request())
    finally:
        await model.aclose()
    assert exc_info.value.transient is True


@pytest.mark.asyncio
@respx.mock
async def test_no_text_blocks_returns_empty_string() -> None:
    body = _ok_payload()
    body["content"] = []
    respx.post(API_URL).mock(return_value=httpx.Response(200, json=body))
    model = ClaudeChatModel(_settings())
    try:
        out = await model.complete(_request())
    finally:
        await model.aclose()
    assert out.text == ""
