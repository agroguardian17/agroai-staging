"""Centralized typed settings loaded from environment variables.

Every setting is declared once here. Code reads ``settings.X`` rather than
``os.environ[...]``, so missing variables are surfaced at startup with a
clear pydantic validation error instead of an opaque KeyError mid-request.

Provider portability charter (roadmap Part 0.5) lives in this file too:
endpoint URLs are env-configurable; no AWS-specific hosts hardcoded.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnv(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


class OtpTransport(StrEnum):
    WHATSAPP = "whatsapp"
    SMS = "sms"  # only after Phase 13 wires MSG91 adapter


class Settings(BaseSettings):
    """Single source of truth for runtime configuration.

    Validation rules:
    - Production environments must have non-default secrets.
    - URLs are stripped of trailing slashes for predictable joining.
    - Anything that looks like a credential is wrapped in SecretStr so it
      never leaks into ``repr()``, structlog renderers or Sentry breadcrumbs.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- App ----------------------------------------------------------------
    APP_ENV: AppEnv = AppEnv.DEVELOPMENT
    APP_VERSION: str = "0.0.1"
    APP_GIT_SHA: str = "dev"
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # ---- Database -----------------------------------------------------------
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://agro:agro@localhost:5432/agro",
        description="Async DSN for SQLAlchemy 2.0 / asyncpg.",
    )
    DATABASE_URL_SYNC: str = Field(
        default="postgresql://agro:agro@localhost:5432/agro",
        description="Sync DSN for Alembic migrations.",
    )
    POSTGRES_USER: str = "agro"
    POSTGRES_DB: str = "agro"
    POSTGRES_PASSWORD: SecretStr = SecretStr("agro")
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT_S: int = 30

    # ---- Auth ---------------------------------------------------------------
    AUTH_JWT_SECRET: SecretStr = SecretStr("CHANGE_ME_dev_only_32_byte_secret")
    AUTH_JWT_ACCESS_TTL_SECONDS: int = 900
    AUTH_JWT_REFRESH_TTL_SECONDS: int = 2_592_000
    AUTH_JWT_ISSUER: str = "agroguardian"
    AUTH_JWT_AUDIENCE: str = "agroguardian-app"
    AUTH_JWT_ALGORITHM: Literal["HS256"] = "HS256"
    OTP_TRANSPORT: OtpTransport = OtpTransport.WHATSAPP
    OTP_CODE_TTL_SECONDS: int = 300
    OTP_MAX_ATTEMPTS: int = 5
    OTP_LOCKOUT_MINUTES: int = 30

    # ---- MQTT ---------------------------------------------------------------
    MQTT_BROKER_HOST: str = "localhost"
    MQTT_BROKER_PORT: int = 1883
    MQTT_BROKER_USER: str = "service"
    MQTT_BROKER_PASSWORD: SecretStr = SecretStr("CHANGE_ME")
    MQTT_TLS_CA_PATH: str = "/etc/ssl/certs/ca-certificates.crt"
    MQTT_USE_TLS: bool = False
    MQTT_QUEUE_MAXSIZE: int = 5000

    # ---- ChromaDB -----------------------------------------------------------
    CHROMA_HOST: str = "localhost"
    CHROMA_PORT: int = 8001
    CHROMA_PERSIST_PATH: str = "/data/chroma"
    CHROMA_EMBEDDING_MODEL: str = "paraphrase-multilingual-mpnet-base-v2"

    # ---- Anthropic ----------------------------------------------------------
    ANTHROPIC_API_KEY: SecretStr = SecretStr("")
    ANTHROPIC_MODEL_SONNET: str = "claude-sonnet-4-5"
    ANTHROPIC_MODEL_HAIKU: str = "claude-haiku-4-5"
    USD_INR_RATE: float = 83.0
    LLM_MAX_TOOL_ITER: int = 5

    # ---- WhatsApp / Meta Cloud API ------------------------------------------
    META_WHATSAPP_PHONE_NUMBER_ID: str = ""
    META_WHATSAPP_BUSINESS_ACCOUNT_ID: str = ""
    META_WHATSAPP_TOKEN: SecretStr = SecretStr("")
    META_WHATSAPP_VERIFY_TOKEN: SecretStr = SecretStr("")
    META_WHATSAPP_OTP_TEMPLATE_NAME: str = "agroguardian_otp_v1"
    META_WHATSAPP_ADVISORY_TEMPLATE_NAME: str = "agroguardian_advisory_v1"
    META_WHATSAPP_GRAPH_VERSION: str = "v20.0"

    # ---- FCM ----------------------------------------------------------------
    FCM_SERVICE_ACCOUNT_JSON_PATH: str = "/secrets/fcm-sa.json"
    FCM_PROJECT_ID: str = ""

    # ---- Satellite ----------------------------------------------------------
    COPERNICUS_CLIENT_ID: str = ""
    COPERNICUS_CLIENT_SECRET: SecretStr = SecretStr("")
    COPERNICUS_BASE_URL: str = "https://sh.dataspace.copernicus.eu"
    COPERNICUS_TOKEN_URL: str = (
        "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    )
    NASA_EARTHDATA_USERNAME: str = ""
    NASA_EARTHDATA_PASSWORD: SecretStr = SecretStr("")

    # ---- Forecast -----------------------------------------------------------
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1"
    IMD_BASE_URL: str = "https://mausam.imd.gov.in/api"

    # ---- Object storage (S3-compatible only; never AWS) ---------------------
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: SecretStr = SecretStr("")
    R2_ENDPOINT_URL: str = ""
    R2_BUCKET_RASTERS: str = "agro-rasters"
    R2_BUCKET_PHOTOS: str = "agro-photos"
    R2_BUCKET_FIRMWARE: str = "agro-firmware"

    B2_KEY_ID: str = ""
    B2_APPLICATION_KEY: SecretStr = SecretStr("")
    B2_ENDPOINT_URL: str = ""
    B2_BUCKET_BACKUPS: str = "agro-backups"

    # ---- Monitoring ---------------------------------------------------------
    SENTRY_DSN: str = ""
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1
    SENTRY_PROFILES_SAMPLE_RATE: float = 0.1
    BETTER_STACK_TOKEN: SecretStr = SecretStr("")
    BETTER_STACK_INGEST_HOST: str = "in.logs.betterstack.com"

    # ---- HTTP / CORS --------------------------------------------------------
    CORS_ALLOWED_ORIGINS: str = "http://localhost:8000,http://localhost:8501"
    TRUSTED_HOSTS: str = "*"

    # ---- OTA (Phase 8) ------------------------------------------------------
    OTA_SIGNING_PRIVATE_KEY_PEM: SecretStr = SecretStr("")
    OTA_SIGNING_PUBLIC_KEY_PEM: str = ""

    # ---- Project paths (resolved at runtime) --------------------------------
    PROJECT_ROOT: Path = Field(default_factory=lambda: Path(__file__).resolve().parent.parent)

    # ------------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------------
    @field_validator(
        "COPERNICUS_BASE_URL",
        "COPERNICUS_TOKEN_URL",
        "OPEN_METEO_BASE_URL",
        "IMD_BASE_URL",
        "R2_ENDPOINT_URL",
        "B2_ENDPOINT_URL",
        "BETTER_STACK_INGEST_HOST",
    )
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @field_validator("CORS_ALLOWED_ORIGINS")
    @classmethod
    def _cors_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("CORS_ALLOWED_ORIGINS must list at least one origin")
        return v

    @field_validator("APP_ENV", mode="after")
    @classmethod
    def _enforce_production_secrets(cls, v: AppEnv, info: object) -> AppEnv:
        # Note: cross-field validation runs in model_validator below.
        return v

    # ------------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------------
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [h.strip() for h in self.TRUSTED_HOSTS.split(",") if h.strip()]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV is AppEnv.PRODUCTION

    @property
    def is_test(self) -> bool:
        return self.APP_ENV is AppEnv.TEST

    @property
    def sentry_enabled(self) -> bool:
        return bool(self.SENTRY_DSN.strip()) and self.APP_ENV is not AppEnv.TEST


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached factory. Tests can override by calling ``get_settings.cache_clear()``."""
    settings = Settings()
    if settings.is_production:
        _assert_production_safe(settings)
    return settings


def _assert_production_safe(s: Settings) -> None:
    """Refuse to start in production with obvious dev defaults."""
    fatal: list[str] = []
    if s.AUTH_JWT_SECRET.get_secret_value().startswith("CHANGE_ME"):
        fatal.append("AUTH_JWT_SECRET")
    if s.POSTGRES_PASSWORD.get_secret_value() in {"agro", "CHANGE_ME"}:
        fatal.append("POSTGRES_PASSWORD")
    if s.MQTT_BROKER_PASSWORD.get_secret_value() == "CHANGE_ME":
        fatal.append("MQTT_BROKER_PASSWORD")
    if not s.ANTHROPIC_API_KEY.get_secret_value():
        fatal.append("ANTHROPIC_API_KEY")
    if fatal:
        raise RuntimeError(
            "Refusing to start in production with default/empty secrets: " + ", ".join(fatal)
        )


__all__ = ["AppEnv", "OtpTransport", "Settings", "get_settings"]
