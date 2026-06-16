"""Tests for app.lib.time helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from app.lib.time import IST, ensure_aware, now_ist, now_utc, to_ist


def test_now_utc_is_aware_utc() -> None:
    dt = now_utc()
    assert dt.tzinfo is not None
    offset = dt.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 0


def test_now_ist_is_aware_ist() -> None:
    dt = now_ist()
    assert dt.tzinfo is not None
    offset = dt.utcoffset()
    assert offset is not None
    assert offset.total_seconds() == 5.5 * 3600


def test_to_ist_converts_aware_datetime() -> None:
    src = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    out = to_ist(src)
    assert out.tzinfo == IST
    assert out.hour == 17 and out.minute == 30


def test_to_ist_rejects_naive() -> None:
    with pytest.raises(ValueError, match="naive"):
        to_ist(datetime(2026, 1, 1, 12, 0))


def test_ensure_aware_attaches_default_when_naive() -> None:
    naive = datetime(2026, 1, 1, 12, 0)
    aware = ensure_aware(naive)
    assert aware.tzinfo == UTC


def test_ensure_aware_passes_through_when_already_aware() -> None:
    src = datetime(2026, 1, 1, 12, 0, tzinfo=ZoneInfo("America/New_York"))
    out = ensure_aware(src)
    assert out is src
