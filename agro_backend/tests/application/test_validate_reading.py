"""Tests for ``app.application.validate_reading.execute``.


Drives the orchestrator with a fake :class:`ReadingRepo` that returns
predictable history snapshots. Asserts:


* A clean reading passes through unchanged.
* Each gate independently sets the right ``sensor_health_json`` flag.
* The gate-skipping logic prevents duplicate flags on the same field.
* Multiple gates fire together when they cover disjoint fields.
* The returned Reading is a new instance (input was frozen).
"""


from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.application import validate_reading
from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import LOW_BATTERY_THRESHOLD_V, Reading, TransmissionType
from app.domain.validation_gates import ValidationFlag


def _r(**over: object) -> Reading:
    base: dict[str, object] = {
        "tenant_id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "farmer_id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "farm_id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "plot_id": "P1",
        "node_id": "N1",
        "recorded_at": datetime(2026, 5, 1, 12, 0, tzinfo=UTC),
        "received_at_master": datetime(2026, 5, 1, 12, 0, 5, tzinfo=UTC),
        "transmission_type": TransmissionType.LORA,
    }
    base.update(over)
    return Reading(**base)  # type: ignore[arg-type]




class _StubRepo:
    """Fake ReadingRepo that returns canned history per (node_id, field).


    Construct with maps from field-name to the list the gate expects.
    The other ReadingRepo methods raise - the orchestrator should never
    touch them.
    """


    def __init__(
        self,
        stuck: dict[str, Sequence[Decimal | None]] | None = None,
        mad: dict[str, list[Decimal]] | None = None,
    ) -> None:
        self._stuck = stuck or {}
        self._mad = mad or {}


    async def save(self, reading: Reading) -> int | None:  # pragma: no cover
        raise AssertionError("orchestrator must not call save()")


    async def latest_for_plot(self, plot_id: str, limit: int) -> list[Reading]:  # pragma: no cover
        raise AssertionError("orchestrator must not call latest_for_plot()")


    async def recent_for_node(
        self, node_id: str, since: datetime
    ) -> list[Reading]:  # pragma: no cover
        raise AssertionError("orchestrator must not call recent_for_node()")


    async def history_for_stuck_check(
        self, node_id: str, field: str, minutes: int
    ) -> list[Decimal | None]:
        return list(self._stuck.get(field, ()))


    async def history_for_mad_check(self, node_id: str, field: str, hours: int) -> list[Decimal]:
        return self._mad.get(field, [])




def _assert_runtime_protocol(stub: object) -> None:
    """Sanity: the stub really does satisfy the ReadingRepo Protocol."""
    assert isinstance(stub, ReadingRepo)




# ===========================================================================
# Happy path
# ===========================================================================
async def test_clean_reading_returns_unchanged() -> None:
    repo = _StubRepo()
    _assert_runtime_protocol(repo)
    reading = _r(
        soil_moisture_1_pct=Decimal("30"),
        soil_moisture_2_pct=Decimal("31"),
        battery_voltage_v=Decimal("3.7"),
    )
    out = await validate_reading.execute(reading, repo)
    assert out is reading
    assert out.validation_warn is False
    assert out.sensor_health_json == {}




# ===========================================================================
# Gate 1 - range fail
# ===========================================================================
async def test_range_fail_sets_warn_and_flag() -> None:
    repo = _StubRepo()
    reading = _r(soil_ph=Decimal("15"))  # outside [0, 14]
    out = await validate_reading.execute(reading, repo)
    assert out.validation_warn is True
    assert out.sensor_health_json["soil_ph"] == ValidationFlag.RANGE_FAIL.value




async def test_range_fail_returns_new_instance() -> None:
    repo = _StubRepo()
    reading = _r(soil_ph=Decimal("15"))
    out = await validate_reading.execute(reading, repo)
    assert out is not reading




async def test_two_range_fails_both_flagged() -> None:
    repo = _StubRepo()
    reading = _r(soil_ph=Decimal("15"), soil_moisture_1_pct=Decimal("-5"))
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["soil_ph"] == ValidationFlag.RANGE_FAIL.value
    assert out.sensor_health_json["soil_moisture_1_pct"] == ValidationFlag.RANGE_FAIL.value




# ===========================================================================
# Gate 2 - stuck
# ===========================================================================
async def test_stuck_fires_when_history_repeats() -> None:
    stuck_history = [Decimal("31.5")] * 5
    repo = _StubRepo(stuck={"soil_moisture_1_pct": stuck_history})
    reading = _r(soil_moisture_1_pct=Decimal("31.5"))
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["soil_moisture_1_pct"] == ValidationFlag.STUCK.value




async def test_stuck_skipped_when_range_fail_on_same_field() -> None:
    # 99% moisture is range-valid (RANGES says 0-100). Force a real out-of-range
    # to exercise the skip path.
    stuck_history = [Decimal("999")] * 5
    repo = _StubRepo(stuck={"soil_moisture_1_pct": stuck_history})
    reading = _r(soil_moisture_1_pct=Decimal("999"))  # range-fails first
    out = await validate_reading.execute(reading, repo)
    # Should be range_fail, NOT stuck (range gate runs first and short-circuits).
    assert out.sensor_health_json["soil_moisture_1_pct"] == ValidationFlag.RANGE_FAIL.value




# ===========================================================================
# Gate 3 - MAD outlier
# ===========================================================================
async def test_mad_outlier_fires_for_clear_deviation() -> None:
    # 20-sample window clustered near 30; reading is 200.
    window = [Decimal("30") + Decimal(i) / Decimal("10") for i in range(-10, 10)]
    repo = _StubRepo(mad={"soil_moisture_1_pct": window})
    reading = _r(soil_moisture_1_pct=Decimal("200"))
    out = await validate_reading.execute(reading, repo)
    # 200 is out-of-range too (100 is the upper bound), so range_fail wins.
    # Use an in-range outlier instead:
    reading = _r(soil_moisture_1_pct=Decimal("95"))
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["soil_moisture_1_pct"] == ValidationFlag.OUTLIER.value




async def test_mad_skipped_when_window_too_small() -> None:
    # Only 5 samples (below MAD_MIN_WINDOW = 12) -> no opinion.
    window = [Decimal("30")] * 5
    repo = _StubRepo(mad={"soil_moisture_1_pct": window})
    reading = _r(soil_moisture_1_pct=Decimal("95"))
    out = await validate_reading.execute(reading, repo)
    assert "soil_moisture_1_pct" not in out.sensor_health_json




# ===========================================================================
# Gate 4 - cross-sensor
# ===========================================================================
async def test_cross_sensor_moisture_disagreement_sets_flag() -> None:
    repo = _StubRepo()
    reading = _r(
        soil_moisture_1_pct=Decimal("20"),
        soil_moisture_2_pct=Decimal("80"),
    )
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["soil_moisture_avg_pct"] == ValidationFlag.CROSS_SENSOR.value




async def test_cross_sensor_low_battery_inconsistency() -> None:
    repo = _StubRepo()
    reading = _r(
        battery_voltage_v=LOW_BATTERY_THRESHOLD_V - Decimal("0.5"),
        low_battery_flag=False,
    )
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["low_battery_flag"] == ValidationFlag.CROSS_SENSOR.value




# ===========================================================================
# Combinations
# ===========================================================================
async def test_multiple_disjoint_flags_all_recorded() -> None:
    stuck_history = [Decimal("31.5")] * 5
    repo = _StubRepo(stuck={"soil_temp_rootzone_c": stuck_history})
    reading = _r(
        soil_ph=Decimal("15"),  # range fail
        soil_temp_rootzone_c=Decimal("31.5"),  # stuck via history
        soil_moisture_1_pct=Decimal("20"),  # disagree
        soil_moisture_2_pct=Decimal("80"),  # disagree
    )
    out = await validate_reading.execute(reading, repo)
    assert out.validation_warn is True
    assert out.sensor_health_json["soil_ph"] == ValidationFlag.RANGE_FAIL.value
    assert out.sensor_health_json["soil_temp_rootzone_c"] == ValidationFlag.STUCK.value
    assert out.sensor_health_json["soil_moisture_avg_pct"] == ValidationFlag.CROSS_SENSOR.value




async def test_existing_sensor_health_is_preserved() -> None:
    # Firmware may have populated sensor_health_json before the cloud gate runs.
    # The orchestrator must merge, not overwrite.
    repo = _StubRepo()
    reading = _r(
        soil_ph=Decimal("15"),
        sensor_health_json={"npk_probe": "modbus_timeout"},
    )
    out = await validate_reading.execute(reading, repo)
    assert out.sensor_health_json["npk_probe"] == "modbus_timeout"
    assert out.sensor_health_json["soil_ph"] == ValidationFlag.RANGE_FAIL.value




# ===========================================================================
# Type-safety guard
# ===========================================================================
async def test_orchestrator_raises_on_schema_drift() -> None:
    # Simulate someone adding a non-Decimal field to RANGES. We can't
    # actually mutate RANGES (frozenset of (Decimal,Decimal)), but we can
    # verify the helper is type-strict by trying to coerce a non-Decimal
    # Reading attribute - this is more of a contract test for the
    # ``_decimal_field`` helper than a runtime path.
    from app.application.validate_reading import _decimal_field


    reading = _r(plot_id="P1")
    with pytest.raises(TypeError):
        # plot_id is str, not Decimal - if a future PR adds "plot_id" to
        # RANGES, this helper catches it loudly.
        _decimal_field(reading, "plot_id")
