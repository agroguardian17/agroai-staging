"""Pipeline self-test — run canned raw payloads through the real calibrate +
validate chain and assert the per-stage checklist.

A one-command "is the ingest pipeline healthy?" check for ops and CI. It exercises
the *actual* ``TelemetryInRaw.to_domain(calibration)`` math and the same validators
the live tracer uses (via ``build_ingest_trace``), with golden cases whose expected
outcome (ok / warn / fail) is known. No database, no broker, no network.

Run it:  ``python -m app.infra.pipeline_selftest``  (exit 0 = all pass)
Lives in the infra layer because it builds the infra wire model; reuses the pure
domain validators + the application assembler.
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any

from app.application.build_pipeline_trace import build_ingest_trace
from app.domain.device_calibration import DeviceCalibration
from app.domain.sensor import TransmissionType
from app.infra.mqtt.schemas import MasterReadings, RawReadings, TelemetryInRaw

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _calibration(**overrides: Any) -> DeviceCalibration:
    base: dict[str, Any] = {
        "tenant_id": str(_TENANT),
        "device_id": "AGR-SN-0001",
        "soil_dry_adc": 1019,
        "soil_wet_adc": 340,
        "battery_vref_v": Decimal("3.3"),
        "battery_divider_ratio": Decimal("2.0"),
        "pressure_offset_v": Decimal("0.5"),
        "pressure_scale_bar_per_v": Decimal("2.5"),
        "flow_pulses_per_litre": Decimal("450"),
        "flow_window_seconds": Decimal("16"),
        "npk_temp_divisor": Decimal("10"),
        "npk_moisture_divisor": Decimal("10"),
        "npk_ph_divisor": Decimal("100"),
        "calibration_version": 1,
    }
    base.update(overrides)
    return DeviceCalibration(**base)


def _raw(**overrides: Any) -> RawReadings:
    base: dict[str, Any] = {
        "soil_adc": 600,
        "battery_adc": 620,
        "pressure_adc": 300,
        "flow_pulses_window": 100,
        "flow_pulses_total": 1000,
        "window_s": 300,
        "npk_ok": True,
        "npk_temp_raw": 270,
        "npk_moisture_raw": 400,
        "npk_ec_us_cm": 1200,
        "npk_ph_raw": 640,
        "npk_nitrogen_mg_kg": 50,
        "npk_phosphorus_mg_kg": 40,
        "npk_potassium_mg_kg": 120,
        "sub_node_fw": "viraai-sn-1.0.0-raw",
    }
    base.update(overrides)
    return RawReadings(**base)


def make_model(raw: RawReadings) -> TelemetryInRaw:
    """Build a valid v2-raw wire model around a raw_readings block."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "$schema": "agro-guardian/telemetry/v2-raw",
        "tenant_id": _TENANT,
        "farmer_id": uuid.uuid4(),
        "farm_id": uuid.uuid4(),
        "plot_id": "PLOT_PILOT_001",
        "node_id": "AGR-SN-0001",
        "recorded_at": now,
        "received_at_master": now,
        "transmission_type": TransmissionType.LORA,
        "raw_readings": raw,
        "master_readings": MasterReadings(lora_rssi_dbm=-80),
    }
    return TelemetryInRaw.model_validate(payload)


@dataclass(frozen=True)
class _Case:
    name: str
    raw: dict[str, Any] = field(default_factory=dict)
    cal: dict[str, Any] = field(default_factory=dict)
    expect: str = "ok"


# Golden cases — each drives the real to_domain + validators to a known outcome.
_CASES: tuple[_Case, ...] = (
    _Case("healthy clean reading", expect="ok"),
    _Case("first-cycle window_s=0 (flow uncomputable)", raw={"window_s": 0}, expect="warn"),
    _Case("NPK read failed", raw={"npk_ok": False}, expect="warn"),
    _Case(
        "implausible calibration → battery > 20V",
        cal={"battery_divider_ratio": Decimal("20")},
        expect="fail",
    ),
)


@dataclass
class SelfTestCaseResult:
    name: str
    passed: bool
    overall: str
    expected: str
    calibrated: dict[str, Any]
    findings: list[dict[str, Any]]


@dataclass
class SelfTestReport:
    passed: bool
    cases: list[SelfTestCaseResult]


def run_self_test() -> SelfTestReport:
    results: list[SelfTestCaseResult] = []
    for case in _CASES:
        cal = _calibration(**case.cal)
        model = make_model(_raw(**case.raw))
        reading = model.to_domain(cal)
        trace = build_ingest_trace(
            topic="selftest",
            model=model,
            reading=reading,
            result=SimpleNamespace(reading_id=1, rules=None),
            calibration=cal,
        )
        results.append(
            SelfTestCaseResult(
                name=case.name,
                passed=trace.overall == case.expect,
                overall=trace.overall,
                expected=case.expect,
                calibrated=trace.calibrated,
                findings=trace.validations,
            )
        )
    return SelfTestReport(passed=all(r.passed for r in results), cases=results)


def _main() -> int:
    report = run_self_test()
    for r in report.cases:
        mark = "PASS" if r.passed else "FAIL"
        print(f"[{mark}] {r.name}: overall={r.overall} (expected {r.expected})")
        for f in r.findings:
            print(f"        - {f.get('level')} {f.get('field')}: {f.get('msg')}")
    print(
        f"\n{'ALL PASS' if report.passed else 'FAILURES PRESENT'} "
        f"({sum(c.passed for c in report.cases)}/{len(report.cases)})"
    )
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(_main())
