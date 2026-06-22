"""Tests for the LogOnlyChatModel stub."""

from __future__ import annotations

from app.application.ports.chat_model import ChatModel, ChatRequest
from app.infra.llm.log_only_chat import LogOnlyChatModel


def _request() -> ChatRequest:
    return ChatRequest(
        system="You are an agronomist.",
        user="Battery is low. Advise.",
        model="claude-sonnet-4-5",
    )


async def test_log_only_returns_marathi_response() -> None:
    out = await LogOnlyChatModel().complete(_request())
    assert out.text
    # Devanagari heuristic - the canned text must include Marathi.
    assert any("ऀ" <= ch <= "ॿ" for ch in out.text)
    assert out.finish_reason == "stop"


async def test_log_only_satisfies_chat_model_protocol() -> None:
    assert isinstance(LogOnlyChatModel(), ChatModel)


async def test_log_only_can_override_canned_text() -> None:
    out = await LogOnlyChatModel(canned_text="कस्टम मेसेज").complete(_request())
    assert out.text == "कस्टम मेसेज"


async def test_log_only_returns_positive_token_counts() -> None:
    out = await LogOnlyChatModel().complete(_request())
    assert out.input_tokens >= 1
    assert out.output_tokens >= 1
    assert out.model == "claude-sonnet-4-5"
