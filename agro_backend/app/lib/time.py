"""IST timezone helpers. Roadmap Part 9 failure point #11: never subtract 5h30m by hand."""

from __future__ import annotations

from datetime import UTC, datetime, tzinfo
from zoneinfo import ZoneInfo

IST: tzinfo = ZoneInfo("Asia/Kolkata")


def now_utc() -> datetime:
    """Return the current time as a timezone-aware UTC datetime."""
    return datetime.now(UTC)


def now_ist() -> datetime:
    """Return the current time as a timezone-aware IST datetime."""
    return datetime.now(IST)


def to_ist(dt: datetime) -> datetime:
    """Convert any aware datetime to IST. Naive datetimes raise.

    All persistence is UTC; only convert to IST at presentation boundaries
    (cron schedules, dashboard rendering, Marathi advisory text).
    """
    if dt.tzinfo is None:
        raise ValueError("Cannot convert a naive datetime to IST")
    return dt.astimezone(IST)


def ensure_aware(dt: datetime, default: tzinfo = UTC) -> datetime:
    """Return ``dt`` unchanged if aware, else attach ``default`` tzinfo."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=default)


__all__ = ["IST", "ensure_aware", "now_ist", "now_utc", "to_ist"]
