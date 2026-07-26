"""Structured logging setup. JSON in production, pretty in development.

structlog is the only logger we use anywhere. ``print()`` is banned by
.cursorrules rule #9. Loggers are bound by module via
``log = structlog.get_logger(__name__)``.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.config import AppEnv, get_settings

_REDACT_KEYS: frozenset[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "authorization",
        "api_key",
        "anthropic_api_key",
        "meta_whatsapp_token",
        "otp",
        "code",
        "code_hash",
        "refresh_token",
        "access_token",
        "jwt",
    }
)


def _redact_sensitive(_logger: object, _name: str, event_dict: EventDict) -> EventDict:
    """Best-effort redaction of obviously sensitive fields.

    This is defense-in-depth - the OtpDeliveryClient already declines to
    pass codes to the logger, but if anyone slips up, this catches it.
    """
    for key in list(event_dict.keys()):
        lk = key.lower()
        if lk == "otp_code" and get_settings().APP_ENV is AppEnv.DEVELOPMENT:
            continue
        if any(sensitive in lk for sensitive in _REDACT_KEYS):
            event_dict[key] = "***REDACTED***"
    return event_dict


def _phone_last4(_logger: object, _name: str, event_dict: EventDict) -> EventDict:
    """If callers pass ``phone_e164``, log only the last 4 digits.

    Required by .cursorrules rule #24.
    """
    if "phone_e164" in event_dict:
        phone = str(event_dict["phone_e164"])
        event_dict["phone_e164"] = f"***{phone[-4:]}" if len(phone) >= 4 else "***"
    return event_dict


def _add_logger_name(logger: object, _name: str, event_dict: EventDict) -> EventDict:
    logger_name = getattr(logger, "name", None)
    if logger_name:
        event_dict["logger"] = logger_name
    return event_dict


def configure_logging() -> None:
    """Configure structlog + stdlib logging once at process startup."""
    settings = get_settings()

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        _add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _redact_sensitive,
        _phone_last4,
    ]

    if settings.APP_ENV is AppEnv.DEVELOPMENT:
        renderer: Processor = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.LOG_LEVEL)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Bridge stdlib logging (uvicorn, sqlalchemy, httpx, anthropic SDK) into structlog.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )
    for noisy in ("uvicorn.access", "httpx", "httpcore", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> Any:
    """Convenience wrapper - prefer ``log = structlog.get_logger(__name__)`` directly."""
    return structlog.get_logger(name)


__all__ = ["configure_logging", "get_logger"]
