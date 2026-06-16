"""Tests for ``app.domain.alert`` enums + AlertCandidate dataclass."""

from __future__ import annotations

import dataclasses
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.domain.alert import AlertCandidate, AlertType, DispatchStatus, Severity

_NOW = datetime(2026, 5, 1, 12, 0, 0, tzinfo=UTC)
_TENANT = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
_FARMER = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
_FARM = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")


def _candidate(**overrides: object) -> AlertCandidate:
    base: dict[str, object] = {
        "alert_type": AlertType.LOW_BATTERY,
        "severity": Severity.WARNING,
        "alert_message_marathi": "बॅटरी कमी आहे - तंत्रज्ञाला कळवा.",
        "tenant_id": _TENANT,
        "farm_id": _FARM,
        "farmer_id": _FARMER,
        "triggered_at": _NOW,
    }
    base.update(overrides)
    return AlertCandidate(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------
def test_alert_candidate_construction() -> None:
    a = _candidate()
    assert a.alert_type is AlertType.LOW_BATTERY
    assert a.severity is Severity.WARNING
    assert a.device_id is None
    assert a.alert_value is None


def test_alert_candidate_with_values_and_device() -> None:
    a = _candidate(
        device_id="AGR-MH-0001",
        alert_value=Decimal("3.10"),
        alert_threshold=Decimal("3.30"),
    )
    assert a.device_id == "AGR-MH-0001"
    assert a.alert_value == Decimal("3.10")
    assert a.alert_threshold == Decimal("3.30")


def test_alert_candidate_is_frozen() -> None:
    a = _candidate()
    with pytest.raises(dataclasses.FrozenInstanceError):
        a.severity = Severity.CRITICAL  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Enum / schema parity
# ---------------------------------------------------------------------------
def test_severity_values_match_schema() -> None:
    # alerts_notifications.severity CHECK ('info','warning','critical')
    expected = {"info", "warning", "critical"}
    assert {s.value for s in Severity} == expected


def test_alert_type_values_match_schema() -> None:
    # alerts_notifications.alert_type CHECK (...) from migration 0001 line 697.
    expected = {
        "dry_run",
        "low_water",
        "power_off",
        "pump_fault",
        "sensor_fault",
        "rain_heavy",
        "frost",
        "pest_risk",
        "disease_risk",
        "low_battery",
        "device_offline",
        "tamper",
    }
    assert {t.value for t in AlertType} == expected


def test_dispatch_status_values_match_schema() -> None:
    # alerts_notifications.dispatch_status added in 0002:
    # CHECK (dispatch_status IN ('pending','sent','failed','dlq'))
    expected = {"pending", "sent", "failed", "dlq"}
    assert {s.value for s in DispatchStatus} == expected


# ---------------------------------------------------------------------------
# Triggered-at must be timezone-aware
# ---------------------------------------------------------------------------
def test_triggered_at_carries_tzinfo() -> None:
    # The dataclass doesn't reject naive datetimes itself (that's a validation
    # gate's job at the boundary), but the canonical construction path must
    # always use aware datetimes - this test documents that contract.
    a = _candidate()
    assert a.triggered_at.tzinfo is not None
