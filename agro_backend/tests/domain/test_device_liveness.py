"""Unit tests for the pure device-liveness assessment (silence watchdog)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.alert import Severity
from app.domain.device_liveness import assess_liveness

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def _assess(recorded_at: datetime, *, online: bool = True, silence_ms: int = 0):
    return assess_liveness(
        recorded_at=recorded_at,
        sub_node_online=online,
        sub_node_silence_ms=silence_ms,
        now=NOW,
        warn_minutes=15,
        critical_minutes=60,
    )


def test_fresh_and_online_is_not_offline() -> None:
    v = _assess(NOW)
    assert not v.offline
    assert v.severity is Severity.INFO


def test_recent_heartbeat_within_warn_window_is_ok() -> None:
    v = _assess(NOW - timedelta(minutes=5))
    assert not v.offline


def test_sub_node_silent_warns() -> None:
    v = _assess(NOW, online=False, silence_ms=20 * 60_000)
    assert v.offline
    assert v.reason == "sub_node_silent"
    assert v.severity is Severity.WARNING
    assert v.silent_minutes == 20


def test_sub_node_silent_escalates_to_critical() -> None:
    v = _assess(NOW, online=False, silence_ms=90 * 60_000)
    assert v.offline
    assert v.severity is Severity.CRITICAL
    assert v.silent_minutes == 90


def test_main_node_stale_warns() -> None:
    v = _assess(NOW - timedelta(minutes=30))  # online, but heartbeat is old
    assert v.offline
    assert v.reason == "main_node_stale"
    assert v.severity is Severity.WARNING
    assert v.silent_minutes == 30


def test_main_node_stale_escalates_to_critical() -> None:
    v = _assess(NOW - timedelta(minutes=120))
    assert v.offline
    assert v.severity is Severity.CRITICAL
    assert v.silent_minutes == 120
