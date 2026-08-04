"""Farm Brain builder coverage tests.

The engine's DSL parser rejects any expression that references a field name
not present in ``kb_farm_brain_fields``. Our builder MUST return a dict whose
keys are exactly the declared set plus the synthetic helpers. This test locks
that contract with a fake repo triad; the real DB coverage happens in the
integration suite.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.application.build_farm_brain import (
    SYNTHETIC_FIELDS,
    FarmBrainDeps,
    build_farm_brain,
)
from app.application.ports.crop_season_repo import CropSeasonView
from app.domain.sensor import Reading, TransmissionType

_TENANT = uuid.UUID("11111111-1111-1111-1111-111111111111")
_FARMER = uuid.UUID("aaaaaaaa-1111-1111-1111-111111111111")
_FARM = uuid.UUID("bbbbbbbb-2222-2222-2222-222222222222")
_SEASON = uuid.UUID("cccccccc-3333-3333-3333-000000000001")


def _sample_reading() -> Reading:
    return Reading(
        tenant_id=_TENANT,
        farmer_id=_FARMER,
        farm_id=_FARM,
        plot_id="PLOT_PILOT_001",
        node_id="AGR-SN-0001",
        recorded_at=datetime(2026, 8, 3, 6, 0, tzinfo=UTC),
        received_at_master=datetime(2026, 8, 3, 6, 0, tzinfo=UTC),
        transmission_type=TransmissionType.LORA,
        signal_rssi_dbm=-72,
        battery_voltage_v=Decimal("3.62"),
        battery_percent=Decimal("58"),
        solar_charging=True,
        low_battery_flag=False,
        soil_moisture_1_pct=Decimal("41.9"),
        soil_moisture_2_pct=Decimal("42.4"),
        soil_moisture_avg_pct=Decimal("42.15"),
        soil_temp_c=None,
        soil_temp_rootzone_c=Decimal("24.7"),
        soil_ph=Decimal("6.9"),
        soil_ec_ms_cm=Decimal("0.42"),
        soil_n_mg_kg=Decimal("95"),
        soil_p_mg_kg=Decimal("48"),
        soil_k_mg_kg=Decimal("82"),
        soil_n_bucket=None,
        soil_p_bucket=None,
        soil_k_bucket=None,
        npk_sensor_raw_hex=None,
        tamper_detected=False,
        enclosure_temp_c=Decimal("31.2"),
        fault_flags=None,
        sensor_health_json={},
        firmware_version="sub-node-1.0.0",
        uptime_seconds=864230,
        cadence_mode=None,
        backlog_pending=False,
        validation_warn=False,
    )


def _sample_season() -> CropSeasonView:
    return CropSeasonView(
        season_id=_SEASON,
        tenant_id=_TENANT,
        farm_id=_FARM,
        plot_id="PLOT_PILOT_001",
        crop_name_english="Ginger",
        crop_name_marathi="आले",
        crop_category="cash_crop",
        crop_variety="Mahima",
        sowing_date=date(2026, 6, 1),
        expected_harvest_date=date(2027, 2, 1),
        current_growth_stage="vegetative",
        crop_age_days_today=63,
    )


class _FakeReadingRepo:
    def __init__(self, reading: Reading | None) -> None:
        self._r = reading

    async def latest_for_plot(self, plot_id: str, limit: int = 1) -> list[Reading]:
        return [self._r] if self._r else []

    # unused by the builder but required by the Protocol
    async def save(self, reading: Reading) -> int | None:  # pragma: no cover
        return 1

    async def recent_for_node(self, node_id, since):  # pragma: no cover
        return []

    async def history_for_stuck_check(self, node_id, field, minutes):  # pragma: no cover
        return []

    async def history_for_mad_check(self, node_id, field, hours):  # pragma: no cover
        return []


class _FakePlotRepo:
    async def find(self, plot_id):  # pragma: no cover — not read today
        return None

    async def for_farmer(self, farmer_id):  # pragma: no cover
        return []

    async def for_tenant(self, tenant_id):  # pragma: no cover
        return []

    async def update_data_tier(self, plot_id, tier):  # pragma: no cover
        return None


class _FakeSeasonRepo:
    def __init__(self, season: CropSeasonView | None) -> None:
        self._s = season

    async def find_active_for_plot(self, plot_id):
        return self._s

    async def list_active_by_crop(self, crop):  # pragma: no cover
        return [self._s] if self._s else []


@pytest.mark.asyncio
async def test_every_declared_field_is_a_dict_key() -> None:
    """The engine's DSL parser rejects unknown fields; every declared field
    must appear as a key in the built state (value may be None).
    """
    declared = frozenset({"dap", "current_stage", "soil_moisture_avg_pct", "custom_x"})
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        declared_fields=declared,
    )
    state = await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    for f in declared:
        assert f in state.state, f"declared field {f!r} missing from Farm Brain dict"


@pytest.mark.asyncio
async def test_fills_from_reading_and_season() -> None:
    """Known-good inputs populate the expected fields."""
    declared = frozenset(
        {
            "soil_moisture_avg_pct",
            "soil_ph",
            "battery_voltage_v",
            "dap",
            "current_stage",
            "days_to_harvest",
        }
    )
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        declared_fields=declared,
    )
    state = await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    assert state.state["soil_moisture_avg_pct"] == Decimal("42.15")
    assert state.state["soil_ph"] == Decimal("6.9")
    assert state.state["battery_voltage_v"] == Decimal("3.62")
    assert state.state["dap"] == 63  # (2026-08-03 - 2026-06-01)
    assert state.state["current_stage"] == "vegetative"
    # 2027-02-01 - 2026-08-03 = 182 days
    assert state.state["days_to_harvest"] == 182


@pytest.mark.asyncio
async def test_missing_reading_yields_unknowns() -> None:
    """No latest reading → every sensor field stays None."""
    declared = frozenset({"soil_moisture_avg_pct", "battery_voltage_v", "dap"})
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(None),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        declared_fields=declared,
    )
    state = await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    assert state.state["soil_moisture_avg_pct"] is None
    assert state.state["battery_voltage_v"] is None
    # DAP comes from season, still populated
    assert state.state["dap"] == 63


def test_synthetic_fields_constant() -> None:
    """SYNTHETIC_FIELDS is what the engine expects to always exist."""
    assert "current_month" in SYNTHETIC_FIELDS
    assert "days_to_planting" in SYNTHETIC_FIELDS
    assert "days_to_harvest" in SYNTHETIC_FIELDS
    # Guardrail proposals (used by immutable capability-claim rules)
    assert "capability_claim_proposed" in SYNTHETIC_FIELDS
    assert "profit_guarantee_proposed" in SYNTHETIC_FIELDS
