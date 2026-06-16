"""Settings validation tests."""

from __future__ import annotations

import importlib

import pytest


def test_settings_load_with_test_env() -> None:
    from app.config import AppEnv, get_settings

    get_settings.cache_clear()
    s = get_settings()
    assert s.APP_ENV is AppEnv.TEST
    assert s.cors_origins, "CORS origins must parse to a non-empty list"


def test_secret_str_is_redacted_in_repr() -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    rendered = repr(s)
    # SecretStr always renders as '**********' in repr.
    secret_value = s.AUTH_JWT_SECRET.get_secret_value()
    assert secret_value not in rendered, "SecretStr values must never appear in repr"


def test_production_refuses_default_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """Refuse to boot in production when secrets look like the dev defaults."""
    from app import config as cfg

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_JWT_SECRET", "CHANGE_ME_dev_only_32_byte_secret")
    monkeypatch.setenv("POSTGRES_PASSWORD", "agro")
    monkeypatch.setenv("MQTT_BROKER_PASSWORD", "CHANGE_ME")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")

    importlib.reload(cfg)
    cfg.get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="Refusing to start in production"):
        cfg.get_settings()

    # Reset for other tests.
    monkeypatch.setenv("APP_ENV", "test")
    importlib.reload(cfg)
    cfg.get_settings.cache_clear()


def test_cors_origins_parser() -> None:
    from app.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    s = s.model_copy(update={"CORS_ALLOWED_ORIGINS": "https://a.example, https://b.example"})
    assert s.cors_origins == ["https://a.example", "https://b.example"]


def test_trailing_slashes_stripped_from_urls() -> None:
    from app.config import Settings

    s = Settings(
        OPEN_METEO_BASE_URL="https://api.open-meteo.com/v1/",
        IMD_BASE_URL="https://mausam.imd.gov.in/api/",
    )
    assert s.OPEN_METEO_BASE_URL == "https://api.open-meteo.com/v1"
    assert s.IMD_BASE_URL == "https://mausam.imd.gov.in/api"
