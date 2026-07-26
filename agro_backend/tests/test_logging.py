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
