"""Unit test: the diagnostics scheduler no-ops when disabled (no DB needed)."""

from __future__ import annotations

from types import SimpleNamespace

from app.jobs.diagnostics_scheduler import build_and_start_diagnostics_scheduler


async def test_disabled_returns_none() -> None:
    settings = SimpleNamespace(DIAGNOSTICS_ENABLED=False)
    assert await build_and_start_diagnostics_scheduler(settings) is None  # type: ignore[arg-type]
