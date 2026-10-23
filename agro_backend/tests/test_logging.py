"""Tests for sensitive-field redaction."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import AppEnv
from app.lib import logging as app_logging


@pytest.mark.parametrize(
    ("app_env", "expected"),
    [
        (AppEnv.DEVELOPMENT, "123456"),
        (AppEnv.PRODUCTION, "***REDACTED***"),
    ],
)
def test_otp_code_is_visible_only_in_development(
    monkeypatch: pytest.MonkeyPatch, app_env: AppEnv, expected: str
) -> None:
    monkeypatch.setattr(app_logging, "get_settings", lambda: SimpleNamespace(APP_ENV=app_env))

    event = app_logging._redact_sensitive(None, "warning", {"otp_code": "123456"})

    assert event["otp_code"] == expected


def test_prod_tracebacks_keep_stack_but_drop_frame_locals() -> None:
    """A4: the production exception renderer keeps the traceback but never dumps
    frame locals (which previously included the whole Settings repr)."""
    import sys

    transformer = app_logging._exception_transformer()
    secret_local = "DO-NOT-LEAK-THIS"
    assert secret_local  # keep it a live local in the frame that raises
    try:
        raise ValueError("kaboom")
    except ValueError:
        rendered = transformer(sys.exc_info())

    blob = str(rendered)
    assert "kaboom" in blob and "ValueError" in blob  # the stack/exception is preserved
    assert "DO-NOT-LEAK-THIS" not in blob  # frame locals are NOT dumped
    for exc in rendered:
        for frame in exc.get("frames", []):
            assert not frame.get("locals")
