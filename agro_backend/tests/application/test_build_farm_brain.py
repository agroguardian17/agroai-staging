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
from app.domain.weather_station_reading import WeatherStationReading

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
    def __init__(self, plot=None) -> None:
        self._plot = plot

    async def find(self, plot_id):
        return self._plot

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


def _sample_weather() -> WeatherStationReading:
    return WeatherStationReading(
        tenant_id=_TENANT,
        master_node_id="AGR-MN-0001",
        farm_id=_FARM,
        recorded_at=datetime(2026, 8, 3, 14, 0, tzinfo=UTC),
        humidity_pct=Decimal("55"),
        air_temp_max_c=Decimal("32"),
        air_temp_min_c=Decimal("21"),
        dew_point_c=Decimal("18"),
    )


class _FakeWeatherRepo:
    def __init__(self, weather: WeatherStationReading | None) -> None:
        self._w = weather
        self.asked_for: uuid.UUID | None = None

    async def most_recent_for_farm(self, farm_id):
        self.asked_for = farm_id
        return self._w

    # unused by the builder but required by the Protocol
    async def save(self, reading):  # pragma: no cover
        return 1

    async def latest_for_node(self, master_node_id, limit):  # pragma: no cover
        return []

    async def most_recent(self, master_node_id):  # pragma: no cover
        return None


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


def _sample_plot():
    from app.domain.plot import Plot

    return Plot(
        plot_id="PLOT_PILOT_001",
        tenant_id=_TENANT,
        farm_id=_FARM,
        plot_number=1,
        area_acre=Decimal("1.0"),
        gps_lat=20.10,
        gps_lng=75.20,
        irrigation_valve_id="V1",
        data_tier="full",
        plot_status="active",
        gps_boundary_geojson={
            "type": "Polygon",
            "coordinates": [[[75.20, 20.10], [75.21, 20.10], [75.21, 20.11], [75.20, 20.10]]],
        },
    )


class _FakeSatelliteRepo:
    def __init__(self, optical, sar) -> None:
        self._optical = optical
        self._sar = sar

    async def recent(self, plot_id, satellite_source, limit):
        from app.application.ports.satellite_reading_repo import SOURCE_OPTICAL

        return self._optical if satellite_source == SOURCE_OPTICAL else self._sar

    async def save(self, **kwargs):  # pragma: no cover
        return None


@pytest.mark.asyncio
async def test_fills_satellite_indices_deltas_and_polygon() -> None:
    from datetime import timedelta

    from app.application.ports.satellite_reading_repo import (
        SOURCE_OPTICAL,
        SOURCE_SAR,
        SatelliteScene,
    )

    today = date(2026, 8, 3)  # dap = 63 for the sample season
    opt_latest = SatelliteScene(
        image_date=today - timedelta(days=3),
        satellite_source=SOURCE_OPTICAL,
        ndvi_mean=Decimal("0.50"),
        ndmi_mean=Decimal("0.40"),
        nbr_value=Decimal("0.30"),
        ndre_mean=Decimal("0.35"),
        valid_pixel_pct=Decimal("72"),
        cloud_cover_pct=Decimal("8"),
        pipeline_version="cdse-1.0",
    )
    opt_prev = SatelliteScene(
        image_date=today - timedelta(days=13),
        satellite_source=SOURCE_OPTICAL,
        ndvi_mean=Decimal("0.62"),
        ndmi_mean=Decimal("0.50"),
        nbr_value=Decimal("0.35"),
        ndre_mean=Decimal("0.40"),
    )
    sar_latest = SatelliteScene(
        image_date=today - timedelta(days=4),
        satellite_source=SOURCE_SAR,
        sar_vv_db=Decimal("-9"),
        sar_vh_db=Decimal("-15"),
    )
    declared = frozenset(
        {
            "dap",
            "ndvi_mean",
            "scene_valid_pixel_pct",
            "ndvi_freshness_days",
            "sat_advisory_confidence",
            "ndvi_delta_10d",
            "plot_ndvi_baseline_regional",
            "plot_ndvi_gap_regional",
            "plot_polygon_wkt",
            "plot_area_ha",
            "sar_vv_db",
            "sar_rvi",
            "sar_gap_days",
        }
    )
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(_sample_plot()),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        satellite_reading_repo=_FakeSatelliteRepo([opt_latest, opt_prev], [sar_latest]),
        declared_fields=declared,
    )
    state = (await build_farm_brain(plot_id="PLOT_PILOT_001", today=today, deps=deps)).state
    assert state["ndvi_mean"] == Decimal("0.50")
    assert state["scene_valid_pixel_pct"] == Decimal("72")
    assert state["ndvi_freshness_days"] == 3
    assert state["sat_advisory_confidence"] == Decimal("1")  # fresh scene
    assert state["ndvi_delta_10d"] == Decimal("-0.12")  # 0.50 - 0.62
    assert state["plot_ndvi_baseline_regional"] is not None  # DAP 63 -> ~0.45
    assert state["plot_ndvi_gap_regional"] is not None
    assert state["plot_polygon_wkt"] is not None and state["plot_polygon_wkt"].startswith("POLYGON")
    assert state["plot_area_ha"] == Decimal("0.4047")
    assert state["sar_vv_db"] == Decimal("-9")
    assert state["sar_rvi"] is not None  # computed from VV/VH
    assert state["sar_gap_days"] == 4


@pytest.mark.asyncio
async def test_no_satellite_repo_leaves_d14_unknown() -> None:
    declared = frozenset({"ndvi_mean", "plot_polygon_wkt", "sat_advisory_confidence", "dap"})
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        declared_fields=declared,
    )
    state = (
        await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    ).state
    assert state["ndvi_mean"] is None
    assert state["plot_polygon_wkt"] is None
    assert state["sat_advisory_confidence"] is None
    assert state["dap"] == 63


@pytest.mark.asyncio
async def test_fills_weather_and_computes_vpd() -> None:
    """When a weather repo is present, air temp/humidity and derived VPD fill."""
    declared = frozenset({"air_temp_max_c", "air_temp_min_c", "rh_pct", "dew_point_c", "vpd_kpa"})
    wrepo = _FakeWeatherRepo(_sample_weather())
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        weather_station_reading_repo=wrepo,
        declared_fields=declared,
    )
    state = await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    assert wrepo.asked_for == _FARM  # resolved via the active season's farm
    assert state.state["air_temp_max_c"] == Decimal("32")
    assert state.state["rh_pct"] == Decimal("55")  # aliased from humidity_pct
    assert state.state["dew_point_c"] == Decimal("18")
    # vpd at 32 C / 55% RH ~ 2.14 kPa (above the 2.0 spray ceiling)
    assert state.state["vpd_kpa"] is not None
    assert Decimal("2.0") < state.state["vpd_kpa"] < Decimal("2.3")


@pytest.mark.asyncio
async def test_no_weather_repo_leaves_vpd_unknown() -> None:
    """Without a weather repo, weather + VPD fields stay None (UNKNOWN)."""
    declared = frozenset({"air_temp_max_c", "rh_pct", "vpd_kpa", "dap"})
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(_sample_reading()),
        plot_repo=_FakePlotRepo(),
        crop_season_repo=_FakeSeasonRepo(_sample_season()),
        declared_fields=declared,
    )
    state = await build_farm_brain(plot_id="PLOT_PILOT_001", today=date(2026, 8, 3), deps=deps)
    assert state.state["air_temp_max_c"] is None
    assert state.state["rh_pct"] is None
    assert state.state["vpd_kpa"] is None
    assert state.state["dap"] == 63  # unaffected


def test_synthetic_fields_constant() -> None:
    """SYNTHETIC_FIELDS is what the engine expects to always exist."""
    assert "current_month" in SYNTHETIC_FIELDS
    assert "days_to_planting" in SYNTHETIC_FIELDS
    assert "days_to_harvest" in SYNTHETIC_FIELDS
    # Guardrail proposals (used by immutable capability-claim rules)
    assert "capability_claim_proposed" in SYNTHETIC_FIELDS
    assert "profit_guarantee_proposed" in SYNTHETIC_FIELDS


# ---------------------------------------------------------------------------
# Phase-1 field wiring: plot / farm / farmer facts under their KB names.
# ---------------------------------------------------------------------------


class _FakeFarmRepo:
    def __init__(self, facts=None) -> None:
        self._facts = facts

    async def find_facts(self, farm_id):
        return self._facts

    async def list_with_location(self):  # pragma: no cover
        return []


class _FakeFarmerRepo:
    def __init__(self, owner=None, location=None) -> None:
        self._owner = owner
        self._loc = location

    async def owner_of_farm(self, farm_id):
        return self._owner

    async def find_location(self, farmer_id):
        return self._loc

    async def find_by_phone(self, phone):  # pragma: no cover
        return None

    async def find_by_id(self, farmer_id):  # pragma: no cover
        return None


@pytest.mark.asyncio
async def test_fills_plot_farm_farmer_facts_under_kb_names() -> None:
    from app.application.ports.farm_repo import FarmFacts
    from app.application.ports.farmer_repo import FarmerLocation

    today = date(2026, 8, 3)
    season = CropSeasonView(
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
        actual_harvest_date=None,
        seed_cost_per_kg=Decimal("8000"),
        target_yield_qtl_per_acre=Decimal("300"),
        actual_yield_qtl_per_acre=None,
    )
    facts = FarmFacts(
        farm_id=_FARM,
        soil_type="black",
        soil_depth_cm=Decimal("30"),
        water_source_primary="well",
        irrigation_type="drip",
        drip_emitter_lph=Decimal("4"),
        previous_crops_json=["cotton", "soybean"],
    )
    loc = FarmerLocation(farmer_id=_FARMER, district="Chhatrapati Sambhajinagar", taluka="Kannad")
    declared = frozenset(
        {
            "variety",
            "planting_date",
            "harvest_date",
            "area_acre",
            "plot_id",
            "soil_type",
            "soil_depth_cm",
            "water_source_type",
            "has_drip",
            "dripper_lph",
            "previous_crops_3yr",
            "district",
            "taluka",
            "farmer_id",
            "yield_target_quintal_per_acre",
            "yield_quintal_per_acre_actual",
            "seed_cost_per_kg",
        }
    )
    deps = FarmBrainDeps(
        reading_repo=_FakeReadingRepo(None),
        plot_repo=_FakePlotRepo(_sample_plot()),
        crop_season_repo=_FakeSeasonRepo(season),
        farm_repo=_FakeFarmRepo(facts),
        farmer_repo=_FakeFarmerRepo(owner=_FARMER, location=loc),
        declared_fields=declared,
    )
    state = (await build_farm_brain(plot_id="PLOT_PILOT_001", today=today, deps=deps)).state
    assert state["variety"] == "Mahima"
    assert state["planting_date"] == date(2026, 6, 1)
    assert state["harvest_date"] is None
    assert state["area_acre"] == Decimal("1.0")
    assert state["plot_id"] == "PLOT_PILOT_001"
    assert state["soil_type"] == "vertisol"  # black -> vertisol value map
    assert state["soil_depth_cm"] == Decimal("30")
    assert state["water_source_type"] == "well"
    assert state["has_drip"] is True
    assert state["dripper_lph"] == Decimal("4")
    assert state["previous_crops_3yr"] == ["cotton", "soybean"]
    assert state["district"] == "Chhatrapati Sambhajinagar"
    assert state["taluka"] == "Kannad"
    assert state["farmer_id"] == str(_FARMER)
    assert state["yield_target_quintal_per_acre"] == Decimal("300")
    assert state["yield_quintal_per_acre_actual"] is None
    assert state["seed_cost_per_kg"] == Decimal("8000")
