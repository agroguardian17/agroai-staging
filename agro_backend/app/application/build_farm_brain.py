"""Assemble a Farm Brain state dict for the ginger engine.

The teammate's engine expects a per-plot per-day dict keyed on the names
declared in ``kb_farm_brain_fields`` - 306 fields covering sensors, weather,
crop stage, plot facts, operational records, derived durations, and synthetic
helpers.

Our current data sources fill roughly one-third of those fields (latest
Reading, Plot, CropSeason, computed DAP + month). The rest come back as
``None`` and the engine's three-valued logic reports
``"insufficient data: <field>"`` for any rule that references them. This is
the intended behaviour - see ``ginger/engine/ARCHITECTURE.md`` §3.

This module is pure application-layer code: it depends only on repository
Protocols (``ReadingRepo``, ``PlotRepo``, ``CropSeasonRepo``) and stdlib.
Purity is enforced by the AST scan under ``tests/application/``.

Field coverage today:

* **Sensor** (~25 of ~30): populated from the latest ``node_sensor_readings``
  row per plot. Missing when no reading exists yet.
* **Battery** (~8 of ~10): same source.
* **Crop stage** (~5 of ~5): computed from ``crop_seasons`` + today's date.
* **Plot facts** (~5 of ~20): from ``plots``. Most plot facts (soil type,
  water source specifics, irrigation valve counts, etc.) need explicit
  farm-config data that has no ingestion path yet.
* **Weather station**, **operational records**, **satellite/NDVI**: 0 of
  the ~45 fields. These require adapters we have not built yet.
* **Synthetic** (~15 of ~15): ``current_month``, ``days_to_planting``,
  ``days_to_harvest``, product-policy proposals - all deterministic from
  the date and rule context.
* **Duration fields** (``<field>__duration``): computed only for
  ``soil_moisture_avg_pct`` (via a 24-h history window) as a placeholder;
  extending this to more fields is a follow-up.

Any field name declared in ``kb_farm_brain_fields`` that we do not populate
must still appear as a dict key with value ``None``. The
``test_build_farm_brain`` coverage test fails the build if a declared field
is missing entirely, because the DSL parser raises on unknown field names.
"""

from __future__ import annotations

import calendar
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.application.ports.advisory_metrics_repo import AdvisoryMetricsRepo
from app.application.ports.crop_scouting_repo import CropScoutingRepo, CropScoutingView
from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.farm_repo import FarmFacts, FarmRepo
from app.application.ports.farmer_consent_repo import FarmerConsentRepo
from app.application.ports.farmer_repo import FarmerLocation, FarmerRepo
from app.application.ports.farmer_schemes_repo import FarmerSchemesRepo
from app.application.ports.lab_soil_test_repo import LabSoilTestRepo, LabSoilTestView
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.application.ports.satellite_reading_repo import (
    SOURCE_OPTICAL,
    SOURCE_SAR,
    SOURCE_THERMAL,
    SatelliteReadingRepo,
    SatelliteScene,
)
from app.application.ports.season_economics_repo import SeasonEconomicsRepo
from app.application.ports.season_operations_repo import SeasonOperationsRepo
from app.application.ports.weather_forecast_repo import ForecastRow, WeatherForecastRepo
from app.application.ports.weather_station_reading_repo import WeatherStationReadingRepo
from app.application.ports.yield_model_repo import YieldModelRepo, YieldPredictionLog
from app.domain.plot import Plot
from app.domain.satellite_metrics import (
    acre_to_hectare,
    advisory_confidence_from_freshness,
    baseline_gap,
    index_delta,
    ndvi_regional_baseline,
    sar_rvi,
)
from app.domain.sensor import Reading
from app.domain.vpd import vpd_kpa
from app.domain.weather_station_reading import WeatherStationReading
from app.domain.yield_model import UValue, ceiling_basis_for_layout, predict_yield

if TYPE_CHECKING:
    # Kept to declare unused ports if future rounds add extra data sources.
    pass


# Synthetic fields that the ginger engine always adds to the field vocabulary
# regardless of what the database declares. Kept here as a constant so tests
# can assert we know about all of them.
# Minimum cluster peers before a peer NDVI baseline is meaningful (KB spec).
_MIN_PEERS = 3

# Domain 12 compliance window: an advisory is "on time" when the farmer's
# first following action is recorded no later than this many days after it was
# issued (D12-AL-001 flags an action not recorded within 3 days of its deadline).
_ADVISORY_ON_TIME_DAYS = 3

SYNTHETIC_FIELDS: frozenset[str] = frozenset(
    {
        "current_month",
        "days_to_planting",
        "days_to_harvest",
        "brand_name_proposed",
        "capability_claim_proposed",
        "profit_guarantee_proposed",
        "price_forecast_proposed",
    }
)


@dataclass(frozen=True, slots=True)
class FarmBrainDeps:
    """Repository ports the builder needs. Constructed once per job run."""

    reading_repo: ReadingRepo
    plot_repo: PlotRepo
    crop_season_repo: CropSeasonRepo
    # Optional weather source. When present, the builder fills the cluster
    # weather-station fields (air temperature, humidity) and the derived
    # ``vpd_kpa`` used by the Domain 7 VPD rules. None keeps weather UNKNOWN.
    weather_station_reading_repo: WeatherStationReadingRepo | None = None
    # Optional weather-forecast source (Open-Meteo, past+future window). Feeds
    # the KB's D07 rain-window / evaporation / radiation fields. None keeps them
    # UNKNOWN.
    weather_forecast_repo: WeatherForecastRepo | None = None
    # Optional satellite source. When present (and the plot has a boundary),
    # the builder fills the Domain 14 optical/SAR index fields, deltas,
    # freshness/confidence, baseline gap and plot polygon. None keeps them
    # UNKNOWN so every D14 rule reports UNKNOWN (never fires).
    satellite_reading_repo: SatelliteReadingRepo | None = None
    # Optional farm + farmer sources. When present the builder fills the
    # plot/farm/farmer facts the KB reads (soil, water source, irrigation,
    # district/taluka). None keeps them UNKNOWN.
    farm_repo: FarmRepo | None = None
    farmer_repo: FarmerRepo | None = None
    # Optional soil-lab source. When present the builder fills the KB's soil
    # chemistry fields (organic carbon, EC, free lime, micronutrients) from
    # the latest test, and sets soil_test_available. None keeps them UNKNOWN.
    lab_soil_test_repo: LabSoilTestRepo | None = None
    # Optional crop-scouting source. When present the builder fills the KB's
    # D05/D06 pest & disease observation fields from the latest scouting row.
    crop_scouting_repo: CropScoutingRepo | None = None
    # Optional per-season economics / operations + per-farmer schemes (Phase 2.4).
    season_economics_repo: SeasonEconomicsRepo | None = None
    season_operations_repo: SeasonOperationsRepo | None = None
    farmer_schemes_repo: FarmerSchemesRepo | None = None
    farmer_consent_repo: FarmerConsentRepo | None = None
    # Optional advisory-performance source (Domain 12 evaluation counters).
    # Derived from the engine's own ai_suggestions + farmer_actions history;
    # fills advisory_issued/completed/on_time counts and action_compliance_rate.
    # None keeps them UNKNOWN.
    advisory_metrics_repo: AdvisoryMetricsRepo | None = None
    # Optional Domain 11 yield-model source. When present the builder runs the
    # process-baseline predictor and fills the D11 prediction/attribution fields,
    # logging each prediction. None keeps them UNKNOWN.
    yield_model_repo: YieldModelRepo | None = None
    # The full ``kb_farm_brain_fields`` set. Injected so tests can pin a
    # subset; the daily job reads it from the database at startup.
    declared_fields: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True, slots=True)
class FarmBrainState:
    """The assembled dict plus a coverage-diagnostic breakdown.

    The engine only reads ``.state``; ``.filled`` and ``.unknown`` are for
    metrics + logging so we can watch coverage improve as adapters land.
    """

    state: dict[str, Any]
    filled: frozenset[str]
    unknown: frozenset[str]


async def build_farm_brain(
    *,
    plot_id: str,
    today: date,
    deps: FarmBrainDeps,
) -> FarmBrainState:
    """Build one plot's Farm Brain state for ``today``.

    Missing sources translate to ``None`` values, never to raised exceptions.
    A plot with zero readings and no active crop season still produces a
    valid state dict - the engine's three-valued logic will report every
    dependent rule as ``UNKNOWN``.
    """
    state: dict[str, Any] = {}

    # Every declared field defaults to None. We fill in what we can below.
    for f in deps.declared_fields:
        state[f] = None
        # Duration companion field, if the DSL declares one.
        # (Only ``soil_moisture_avg_pct__duration`` is filled today; the
        # rest stay None to satisfy parse-time field declaration.)
        # No-op here; the loop already sets the __duration variant to None
        # if it was declared.

    # ---- Latest reading ------------------------------------------------
    latest = await deps.reading_repo.latest_for_plot(plot_id, limit=1)
    reading: Reading | None = latest[0] if latest else None
    if reading is not None:
        _populate_from_reading(state, reading)

    # ---- Plot facts (area, id, soil override) --------------------------
    # Fetched unconditionally (the satellite branch reuses this row).
    plot = await deps.plot_repo.find(plot_id)
    if plot is not None:
        _populate_from_plot(state, plot)

    # ---- Crop season (stage + DAP + synthetic dates) -------------------
    season = await deps.crop_season_repo.find_active_for_plot(plot_id)
    _populate_from_season(state, season, today)

    # ---- Farm facts (soil, water source, irrigation) ------------------
    # Farm-level; resolve from the active season's farm.
    if deps.farm_repo is not None and season is not None:
        facts = await deps.farm_repo.find_facts(season.farm_id)
        if facts is not None:
            _populate_from_farm(state, facts)

    # ---- Soil lab test (KB nutrient chemistry) ------------------------
    # Overrides the farm-level soil_oc_pct fallback set above when a test
    # exists, and fills the micronutrient / EC / free-lime fields.
    if deps.lab_soil_test_repo is not None and season is not None:
        lab = await deps.lab_soil_test_repo.latest_for_farm(season.farm_id)
        if lab is not None:
            _populate_from_lab_soil(state, lab)

    # ---- Crop scouting (D05/D06 pest & disease observations) ----------
    if deps.crop_scouting_repo is not None:
        scouting = await deps.crop_scouting_repo.latest_for_plot(plot_id)
        if scouting is not None:
            _populate_from_scouting(state, scouting)

    # ---- Season economics + operations (D13 / D03-D08), 1:1 per season -
    if season is not None and deps.season_economics_repo is not None:
        econ = await deps.season_economics_repo.for_season(season.season_id)
        if econ is not None:
            for _f in _ECON_FIELDS:
                _set(state, _f, getattr(econ, _f))
    if season is not None and deps.season_operations_repo is not None:
        ops = await deps.season_operations_repo.for_season(season.season_id)
        if ops is not None:
            for _f in _OPS_FIELDS:
                _set(state, _f, getattr(ops, _f))

    # ---- Advisory performance (D12 evaluation counters) ---------------
    # History-derived: what the engine issued (ai_suggestions) vs what the
    # farmer did (farmer_actions), aggregated over the active season.
    if season is not None and deps.advisory_metrics_repo is not None:
        perf = await deps.advisory_metrics_repo.performance_for_season(
            season.season_id, on_time_days=_ADVISORY_ON_TIME_DAYS
        )
        _set(state, "advisory_issued_count", perf.advisory_issued_count)
        _set(state, "advisory_completed_count", perf.advisory_completed_count)
        _set(
            state,
            "advisory_completed_on_time_count",
            perf.advisory_completed_on_time_count,
        )
        _set(state, "action_compliance_rate", perf.action_compliance_rate)

    # ---- Farmer location (district / taluka) --------------------------
    if deps.farmer_repo is not None and season is not None:
        owner = await deps.farmer_repo.owner_of_farm(season.farm_id)
        if owner is not None:
            _set(state, "farmer_id", str(owner))
            loc = await deps.farmer_repo.find_location(owner)
            if loc is not None:
                _populate_from_farmer(state, loc)
            if deps.farmer_schemes_repo is not None:
                sch = await deps.farmer_schemes_repo.for_farmer(owner)
                if sch is not None:
                    for _f in _SCHEMES_FIELDS:
                        _set(state, _f, getattr(sch, _f))
            if deps.farmer_consent_repo is not None:
                con = await deps.farmer_consent_repo.for_farmer(owner)
                if con is not None:
                    for _f in _CONSENT_FIELDS:
                        _set(state, _f, getattr(con, _f))

    # ---- Weather station (air temp + humidity + derived VPD) -----------
    # Weather is farm-level; resolve it from the active season's farm. The
    # cluster station's temperature and humidity feed the Domain 7 VPD rules
    # via the computed ``vpd_kpa``.
    if deps.weather_station_reading_repo is not None and season is not None:
        weather = await deps.weather_station_reading_repo.most_recent_for_farm(season.farm_id)
        if weather is not None:
            _populate_from_weather(state, weather)

    # ---- Weather forecast (Open-Meteo past+future window, D07) ---------
    # Farm-level; a ~3-week past window + short forecast lets us derive the
    # KB's rain-gap / dry-spell / effective-rainfall / evaporation / radiation
    # fields without the (not-yet-installed) Main Node weather station.
    if deps.weather_forecast_repo is not None and season is not None:
        rows = await deps.weather_forecast_repo.window_for_farm(
            season.farm_id, today - timedelta(days=92), today + timedelta(days=7)
        )
        if rows:
            _populate_from_forecast(state, rows, today, season.sowing_date)

    # ---- Satellite (Domain 14 optical + SAR indices) -------------------
    # Reads the recent scenes per source, plus the plot boundary for the
    # polygon/area gates. Computes deltas, freshness, confidence and the
    # baseline gap from the pure satellite-metrics helpers.
    if deps.satellite_reading_repo is not None:
        optical = await deps.satellite_reading_repo.recent(plot_id, SOURCE_OPTICAL, limit=6)
        sar = await deps.satellite_reading_repo.recent(plot_id, SOURCE_SAR, limit=6)
        _populate_from_satellite(state, optical, sar, plot, today)
        # Landsat thermal (LST) — the latest scene feeds cwsi (derived below).
        thermal = await deps.satellite_reading_repo.recent(plot_id, SOURCE_THERMAL, limit=1)
        if thermal:
            _set(state, "lst_c", thermal[0].lst_c)
        # Peer NDVI/NDRE baseline across the cluster's other plots at the same
        # growth stage (KB: available once >= 3 plots are enrolled).
        dap = state.get("dap")
        if optical and season is not None and isinstance(dap, int):
            peer = await deps.satellite_reading_repo.peer_baseline_at_dap(
                tenant_id=season.tenant_id,
                crop_name_english=season.crop_name_english,
                dap=dap,
                today=today,
                exclude_plot_id=plot_id,
            )
            if peer.peer_count >= _MIN_PEERS:
                o0 = optical[0]
                _set(state, "plot_ndvi_baseline_peer", peer.ndvi_mean)
                _set(state, "plot_ndvi_gap_peer", baseline_gap(o0.ndvi_mean, peer.ndvi_mean))
                _set(state, "plot_ndre_baseline_regional", peer.ndre_mean)
                _set(state, "plot_ndre_gap_regional", baseline_gap(o0.ndre_mean, peer.ndre_mean))

    # ---- Composite derivations (from fields filled above) --------------
    _derive_composite(state, today)

    # ---- Domain 11 yield model (process baseline) ----------------------
    # Runs after the composite step so prediction_stage / signal fields are set.
    if season is not None and deps.yield_model_repo is not None:
        await _populate_yield_prediction(state, deps.yield_model_repo, season, today)

    # ---- Synthetic ------------------------------------------------------
    state["current_month"] = today.month
    # brand/capability/profit/price proposals are engine-side attempts,
    # set at attempt time - not from data. Default to None; the immutable
    # guardrail rules read them only when an attempt is being made.

    # ---- Derived durations ------
    # The engine's ``DURATION(...)`` DSL reads ``<field>__duration``. Every
    # declared duration field is currently None (unknown). Populating them
    # requires a generic ``history(plot_id, field, from_ts)`` on ReadingRepo,
    # which is a follow-up round. The engine's three-valued logic reports
    # UNKNOWN for rules that reference an unavailable duration; that is the
    # intended behaviour.

    filled = frozenset(k for k, v in state.items() if v is not None)
    unknown = frozenset(deps.declared_fields) - filled
    return FarmBrainState(state=state, filled=filled, unknown=unknown)


# ---------------------------------------------------------------------------
# Section fillers
# ---------------------------------------------------------------------------


def _populate_from_reading(state: dict[str, Any], r: Reading) -> None:
    """Copy every scalar sensor value we have."""
    # Sensor + battery
    _set(state, "soil_moisture_1_pct", r.soil_moisture_1_pct)
    _set(state, "soil_moisture_2_pct", r.soil_moisture_2_pct)
    _set(state, "soil_moisture_avg_pct", r.soil_moisture_avg_pct)
    _set(state, "soil_moisture_vwc", r.soil_moisture_avg_pct)  # alias
    _set(state, "soil_temp_c", r.soil_temp_c)
    _set(state, "soil_temp_rootzone_c", r.soil_temp_rootzone_c)
    _set(state, "soil_ph", r.soil_ph)
    _set(state, "soil_ec_ms_cm", r.soil_ec_ms_cm)
    _set(state, "ec_current", r.soil_ec_ms_cm)  # alias
    _set(state, "soil_n_mg_kg", r.soil_n_mg_kg)
    _set(state, "soil_p_mg_kg", r.soil_p_mg_kg)
    _set(state, "soil_k_mg_kg", r.soil_k_mg_kg)
    _set(state, "battery_voltage_v", r.battery_voltage_v)
    _set(state, "battery_percent", r.battery_percent)
    _set(state, "solar_charging", r.solar_charging)
    _set(state, "low_battery_flag", r.low_battery_flag)
    _set(state, "tamper_detected", r.tamper_detected)
    _set(state, "enclosure_temp_c", r.enclosure_temp_c)
    _set(state, "firmware_version", r.firmware_version)
    _set(state, "signal_rssi_dbm", r.signal_rssi_dbm)


# crop_seasons agronomy-plan columns (migration 0022) whose KB field name is
# identical to the CropSeasonView attribute name - copied by name in the mapper.
_SEASON_PLAN_FIELDS: tuple[str, ...] = (
    "deep_ploughing_done",
    "solarization_done",
    "solarization_weeks",
    "planting_layout",
    "bed_height_cm",
    "bed_width_cm",
    "furrow_width_cm",
    "plants_per_acre",
    "planting_depth_cm",
    "earthing_up_date",
    "earthing_up_2_date",
    "mulch_stage_1_done",
    "mulch_stage_2_done",
    "mulch_stage_3_done",
    "n_target_kg_per_acre",
    "p_target_kg_per_acre",
    "k_target_kg_per_acre",
    "n_applied_kg_per_acre",
    "p_applied_kg_per_acre",
    "k_applied_kg_per_acre",
    "n_split_1_date",
    "n_split_2_date",
    "k_late_split_1_date",
    "k_late_split_2_date",
    "fym_t_per_acre",
    "fym_fully_decomposed",
    "trichoderma_kg_per_acre",
    "neem_cake_basal_kg_per_acre",
    "neem_cake_earthing_kg_per_acre",
    "micronutrient_basal_done",
    "micronutrient_spray_1_done",
    "micronutrient_spray_2_done",
    "hot_water_treatment_done",
    "biofumigation_done",
    "azospirillum_psb_done",
    "marigold_planted",
    "target_product",
    "k_source",
    # part 2 (migration 0024)
    "affected_plants_removed",
    "bed_former_arranged",
    "bud_orientation_instructed",
    "calibration_date",
    "calibration_done",
    "crop_coefficient_kc",
    "drainage_levels_present",
    "drainage_outlet_present",
    "drip_efficiency_measured",
    "drip_flow_lph_per_acre",
    "drip_lateral_spacing_ft",
    "drip_shifts_per_day",
    "dripper_spacing_cm",
    "drippers_per_acre",
    "dry_recovery_pct_actual",
    "drying_method",
    "drying_space_ready",
    "field_history_rot",
    "field_history_wilt",
    "gap_filling_done",
    "harvest_route",
    "intercrop_selected",
    "limiting_nutrient",
    "main_drain_connected",
    "moisture_probe_depth_cm",
    "pan_coefficient_kp",
    "perennial_weeds_removed",
    "ppe_available",
    "processing_trained_operator",
    "produce_washed",
    "rows_per_bed",
    "season_water_plan_basis",
    "seasonal_water_requirement_litres",
    "seed_at_planting_kg",
    "seed_buds_per_piece",
    "seed_piece_weight_g",
    "seed_storage_loss_pct",
    "seed_storage_method",
    "seed_stored_kg",
    "shade_pct",
    "so2_treatment_used",
    "storage_loss_monthly_pct",
    "vwc_field_capacity",
    "vwc_saturation",
    "vwc_stress_threshold",
    "water_available_oct_feb_litres",
    "water_stress_after_earthing_done",
    "water_withdrawal_pct",
    "water_withdrawal_start_date",
    "water_withdrawal_started",
)


def _populate_from_season(
    state: dict[str, Any], season: CropSeasonView | None, today: date
) -> None:
    """Fill crop stage, DAP, and season-derived synthetic fields."""
    if season is None:
        return
    dap = (today - season.sowing_date).days if season.sowing_date else None
    _set(state, "dap", dap)
    _set(state, "current_stage", season.current_growth_stage)
    # We stage by calendar (DAP), so declare the provenance the KB reads.
    _set(state, "stage_source", "calendar")
    _set(state, "crop_name_english", season.crop_name_english)
    _set(state, "crop_name_marathi", season.crop_name_marathi)
    _set(state, "crop_variety", season.crop_variety)
    _set(state, "sowing_date", season.sowing_date)
    _set(state, "expected_harvest_date", season.expected_harvest_date)
    # KB-named counterparts (the engine reads these names, not the raw
    # column names above): variety, planting_date, harvest_date, yields, cost.
    _set(state, "variety", season.crop_variety)
    _set(state, "planting_date", season.sowing_date)
    _set(state, "harvest_date", season.actual_harvest_date)
    _set(state, "seed_cost_per_kg", season.seed_cost_per_kg)
    _set(state, "yield_target_quintal_per_acre", season.target_yield_qtl_per_acre)
    _set(state, "yield_quintal_per_acre_actual", season.actual_yield_qtl_per_acre)
    # Agronomy-plan facts (migration 0022): the KB field name equals the
    # CropSeasonView attribute name, so copy them by name.
    for f in _SEASON_PLAN_FIELDS:
        _set(state, f, getattr(season, f))
    if season.sowing_date:
        state["days_to_planting"] = (season.sowing_date - today).days
    if season.expected_harvest_date:
        state["days_to_harvest"] = (season.expected_harvest_date - today).days


def _populate_from_weather(state: dict[str, Any], w: WeatherStationReading) -> None:
    """Fill cluster weather-station fields and the derived VPD.

    ``rh_pct`` is the KB's name for relative humidity (aliased from the
    reading's ``humidity_pct``). ``vpd_kpa`` is computed from the daytime max
    temperature and humidity via the Tetens equation; it is what the Domain 7
    VPD rules read. ``vpd_night_mean_kpa`` needs nighttime hourly aggregates we
    do not yet store, so it stays UNKNOWN (tracked as a follow-up).
    """
    _set(state, "air_temp_max_c", w.air_temp_max_c)
    _set(state, "air_temp_min_c", w.air_temp_min_c)
    _set(state, "rh_pct", w.humidity_pct)
    _set(state, "humidity_pct", w.humidity_pct)
    _set(state, "dew_point_c", w.dew_point_c)
    _set(state, "vpd_kpa", vpd_kpa(w.air_temp_max_c, w.humidity_pct))
    # KB reads wind in m/s; the station stores km/h.
    if w.wind_speed_kmh is not None:
        _set(state, "wind_speed_ms", w.wind_speed_kmh / Decimal("3.6"))


# A day with >= this much rain counts as a "rain day" for gap/dry-spell logic.
_RAIN_DAY_MM = 2.5
_HEAT_STRESS_TMAX_C = 37.0


def _rain_gap_days(rows: list[ForecastRow], today: date) -> int | None:
    """Days since the last rain day at or before ``today`` (0 = rained today).

    None when the window holds no past rows to judge from.
    """
    past = [r for r in rows if r.forecast_for_date <= today]
    if not past:
        return None
    for r in sorted(past, key=lambda x: x.forecast_for_date, reverse=True):
        if (r.rain_mm_expected or 0.0) >= _RAIN_DAY_MM:
            return (today - r.forecast_for_date).days
    return (today - min(r.forecast_for_date for r in past)).days


def _dry_spell_days(rows: list[ForecastRow], today: date) -> int | None:
    """Consecutive dry days ending at ``today`` (walking backwards)."""
    by_date = {r.forecast_for_date: (r.rain_mm_expected or 0.0) for r in rows}
    if today not in by_date:
        return None
    n = 0
    d = today
    while d in by_date and by_date[d] < _RAIN_DAY_MM:
        n += 1
        d = d - timedelta(days=1)
    return n


def _effective_rainfall_mm(rows: list[ForecastRow], today: date, window: int = 7) -> float | None:
    """Sum of rain over the last ``window`` days, each day capped at 50 mm."""
    start = today - timedelta(days=window - 1)
    vals = [
        min(r.rain_mm_expected or 0.0, 50.0) for r in rows if start <= r.forecast_for_date <= today
    ]
    return round(sum(vals), 2) if vals else None


def _heat_stress_days(rows: list[ForecastRow], today: date, window: int = 30) -> int | None:
    """Count of past days (within ``window``) with tmax >= the heat threshold."""
    start = today - timedelta(days=window - 1)
    past = [r for r in rows if start <= r.forecast_for_date <= today]
    if not past:
        return None
    return sum(1 for r in past if (r.temp_max_c or 0.0) >= _HEAT_STRESS_TMAX_C)


def _forecast_rain_48h_mm(rows: list[ForecastRow], today: date) -> float | None:
    """Sum of expected rain over the next two days (today+1, today+2)."""
    fut = [
        r.rain_mm_expected or 0.0
        for r in rows
        if today < r.forecast_for_date <= today + timedelta(days=2)
    ]
    return round(sum(fut), 2) if fut else None


def _rain_last_48h_mm(rows: list[ForecastRow], today: date) -> float | None:
    """Cumulative rain over the last 48 h (today-1 .. today)."""
    past = [
        r.rain_mm_expected or 0.0
        for r in rows
        if today - timedelta(days=1) <= r.forecast_for_date <= today
    ]
    return round(sum(past), 2) if past else None


# Cyclone proxy thresholds: an extreme wind + heavy rain day in the next 3 days.
_CYCLONE_WIND_KMH = 60.0
_CYCLONE_RAIN_MM = 50.0


def _cyclone_alert(rows: list[ForecastRow], today: date) -> bool | None:
    """Proxy cyclone/severe-weather flag from the forecast window (NOT an
    official IMD warning): any day in the next 3 with gale wind AND heavy rain.
    """
    fut = [r for r in rows if today <= r.forecast_for_date <= today + timedelta(days=3)]
    if not fut:
        return None
    return any(
        (r.wind_speed_kmh or 0.0) >= _CYCLONE_WIND_KMH
        and (r.rain_mm_expected or 0.0) >= _CYCLONE_RAIN_MM
        for r in fut
    )


def _fog_days_consecutive(rows: list[ForecastRow], today: date) -> int | None:
    """Consecutive foggy days ending at ``today`` (walking backwards)."""
    by_date = {r.forecast_for_date: r.fog_observed for r in rows}
    if by_date.get(today) is None:
        return None
    n = 0
    d = today
    while by_date.get(d) is True:
        n += 1
        d = d - timedelta(days=1)
    return n


# The engine build/version tag the KB's D11/D12 provenance rules read.
_MODEL_VERSION = "ginger-engine/v1.0"

GINGER_CROP_KEY = "Ginger"

# Inputs the KB has an immutable "no" on for a crop (food safety / Seed Act).
# When a blocklisted input is recorded, a pre-harvest-interval number would
# contradict the block, so PHI is forced to UNKNOWN and the trace fields below
# are set for the D05 'blocklisted_input_detected' branch. Seeded from
# AGRONOMY_SIGNOFF (2026-09-21): chlorpyriphos is on the D05-CH-001 blocklist
# for ginger. Replaced/extended by ginger_pesticide_registry.csv when it lands.
# Keys are matched case-insensitively against the entered pesticide group/name.
_CROP_INPUT_BLOCKLIST: dict[str, dict[str, dict[str, str]]] = {
    GINGER_CROP_KEY: {
        "chlorpyriphos": {
            "reason": "Not registered on ginger; blocked by D05-CH-001.",
            "source_ref": "CIB&RC label / FSSAI MRL; AGRONOMY_SIGNOFF 2026-09-21",
        },
    },
}

# Pre-harvest interval (days) by pesticide FRAC/IRAC group or common name.
# AGRONOMIST TO CONFIRM the full table (ginger_pesticide_registry.csv, ETA
# 2026-09-30); conservative default for anything unlisted. Getting this wrong is
# a food-safety risk, so the default errs long (restrictive). chlorpyriphos is
# intentionally absent - it is blocklisted (see _CROP_INPUT_BLOCKLIST), never
# assigned a PHI.
_PHI_DAYS_DEFAULT = 21
_PHI_DAYS_BY_GROUP: dict[str, int] = {
    "M03": 7,
    "mancozeb": 7,
    "M01": 7,
    "copper": 5,
    "3": 7,
    "quinalphos": 21,
    "4A": 7,
    "imidacloprid": 40,
    "28": 3,
    "chlorantraniliprole": 5,
}

# IMD 1991-2020 monthly rainfall normals (mm) by station, with provenance
# (AGRONOMY_SIGNOFF / VJH-V1.0 §6). Ch. Sambhajinagar plots key to Chikalthana.
# Additional Marathwada + expansion stations arrive as
# imd_district_normals_1991_2020.csv (ETA 2026-09-25); add rows here.
_STATION_RAINFALL_NORMAL: dict[str, dict[str, Any]] = {
    "chikalthana": {
        # Jan..Dec
        "monthly_mm": [2.6, 2.2, 11.4, 6.0, 17.4, 155.6, 178.0, 171.5, 172.4, 68.2, 17.5, 8.9],
        "annual_mm": 811.7,
        "source_institution": "IMD",
        "station_name": "Aurangabad (Chikalthana)",
        "normal_period": "1991-2020",
        "geographical_scope": "station",
    },
}
# Interim agro-zone -> IMD station, until per-plot station codes are entered.
_ZONE_TO_STATION = {
    "marathwada_central": "chikalthana",
}
_SEASON_LEN_DAYS = 240  # ginger


def _expected_rain_to_date_mm(monthly_mm: list[float], sowing_date: date, today: date) -> float:
    """Season-to-date expected rainfall by summing the IMD monthly normals from
    sowing to today, prorating the first and current partial months by day."""
    if today < sowing_date:
        return 0.0
    total = 0.0
    y, m = sowing_date.year, sowing_date.month
    while (y, m) <= (today.year, today.month):
        dim = calendar.monthrange(y, m)[1]
        start = max(date(y, m, 1), sowing_date)
        end = min(date(y, m, dim), today)
        total += monthly_mm[m - 1] * ((end - start).days + 1) / dim
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return total


def _blocklisted_spray_inputs(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Blocklisted pesticide groups/names among the recorded sprays, if any.

    Maps the offending (lower-cased) group -> its {reason, source_ref}. Empty
    when nothing recorded is on the crop blocklist.
    """
    bl = _CROP_INPUT_BLOCKLIST.get(GINGER_CROP_KEY, {})
    hits: dict[str, dict[str, str]] = {}
    for group_field in ("last_fungicide_group", "last_insecticide_group"):
        g = state.get(group_field)
        if g is None:
            continue
        entry = bl.get(str(g).strip().lower())
        if entry is not None:
            hits[str(g).strip().lower()] = entry
    return hits


def _phi_days_remaining(state: dict[str, Any], today: date) -> int | None:
    """Days until the pre-harvest interval clears after the most recent spray.

    Reads the last fungicide/insecticide date + group from season_operations
    fields; PHI comes from ``_PHI_DAYS_BY_GROUP`` (conservative default). Returns
    the most restrictive (largest) remaining across the two sprays; 0 = cleared.

    Blocklisted inputs are skipped: they carry no valid PHI (a number would
    contradict the immutable block), and are surfaced via the blocklist gate.
    """
    bl = _CROP_INPUT_BLOCKLIST.get(GINGER_CROP_KEY, {})
    best: int | None = None
    for date_field, group_field in (
        ("last_fungicide_date", "last_fungicide_group"),
        ("last_insecticide_date", "last_insecticide_group"),
    ):
        d = state.get(date_field)
        if not isinstance(d, date):
            continue
        group = state.get(group_field)
        if str(group).strip().lower() in bl:
            continue
        phi = _PHI_DAYS_BY_GROUP.get(str(group), _PHI_DAYS_DEFAULT)
        remaining = max(0, phi - (today - d).days)
        best = remaining if best is None else max(best, remaining)
    return best


def _rainfall_deviation_pct(
    ytd_mm: object, zone: object, sowing_date: date | None, today: date
) -> float | None:
    """(season-to-date rain - expected) / expected * 100.

    Expected = the plot's IMD station monthly normals summed from sowing to
    today. The station is resolved from the agro-zone until per-plot station
    codes are entered (VJH-V1.0 §6)."""
    if ytd_mm is None or not isinstance(sowing_date, date):
        return None
    station_key = _ZONE_TO_STATION.get(str(zone))
    station = _STATION_RAINFALL_NORMAL.get(station_key) if station_key else None
    if station is None:
        return None
    expected = _expected_rain_to_date_mm(station["monthly_mm"], sowing_date, today)
    if expected <= 0:
        return None
    return round((float(ytd_mm) - expected) / expected * 100.0, 1)


def _prediction_stage(dap: int) -> str:
    """Coarse yield-prediction stage from days-after-planting (ginger ~240 d).

    AGRONOMIST TO CONFIRM the DAP cut-points.
    """
    if dap < 0:
        return "pre_season"
    if dap < 90:
        return "g1_end"
    if dap < 200:
        return "mid_season"
    return "pre_harvest_observation"


def _cwsi(lst_c: object, air_temp_max_c: object) -> float | None:
    """Crop Water Stress Index proxy in [0,1] from canopy (LST) minus air temp.

    A simple normalisation of the LST-Tair difference: 0 well-watered, 1 fully
    stressed. Only computed when a Landsat LST value is present (see satellite
    ``lst_c``); the fetch of LST itself is a pending external adapter.
    """
    if lst_c is None or air_temp_max_c is None:
        return None
    diff = float(lst_c) - float(air_temp_max_c)
    # -2 °C (cooler canopy = unstressed) .. +8 °C (hot canopy = stressed).
    return round(max(0.0, min(1.0, (diff + 2.0) / 10.0)), 3)


def _derive_composite(state: dict[str, Any], today: date) -> None:
    """Fields derived from other already-populated fields (no new source).

    ``vafsa_state`` (too_wet/workable/too_dry) is read off the soil-moisture VWC
    against the season's own field-capacity / stress thresholds - so it uses no
    hardcoded agronomy, only values the agronomist entered.
    """
    vwc = state.get("soil_moisture_vwc")
    sat = state.get("vwc_saturation")
    stress = state.get("vwc_stress_threshold")
    if vwc is not None and sat is not None and stress is not None:
        vafsa = "too_wet" if vwc >= sat else ("too_dry" if vwc <= stress else "workable")
        _set(state, "vafsa_state", vafsa)

    # Engine-side constants / stage classification (D11/D12).
    _set(state, "model_version", _MODEL_VERSION)
    dap = state.get("dap")
    if isinstance(dap, int):
        _set(state, "prediction_stage", _prediction_stage(dap))
    cwsi = _cwsi(state.get("lst_c"), state.get("air_temp_max_c"))
    if cwsi is not None:
        _set(state, "cwsi", cwsi)

    # Food-safety blocklist gate (runs BEFORE the PHI number is trusted). A
    # blocklisted input has no valid PHI - forcing it UNKNOWN and raising the
    # D05 'blocklisted_input_detected' branch instead of a misleading number.
    # (The trace fields surface once the KB declares them; harmless until then.)
    blocked = _blocklisted_spray_inputs(state)
    if blocked:
        entry = next(iter(blocked.values()))
        _set(state, "phi_blocklist_hit", True)
        _set(state, "blocklist_reason", entry["reason"])
        _set(state, "blocklist_source_ref", entry["source_ref"])
        _set(state, "farmer_alert_type", "blocklisted_input_detected")
    # PHI remaining after the most recent non-blocklisted spray (food safety).
    phi = _phi_days_remaining(state, today)
    if phi is not None:
        _set(state, "phi_days_remaining", phi)

    # Rainfall deviation vs the plot's IMD station normals (season-to-date).
    if isinstance(dap, int) and dap > 0:
        dev = _rainfall_deviation_pct(
            state.get("rainfall_ytd_mm"),
            state.get("agro_climatic_zone"),
            today - timedelta(days=dap),
            today,
        )
        if dev is not None:
            _set(state, "rainfall_deviation_pct", dev)


async def _populate_yield_prediction(
    state: dict[str, Any],
    repo: YieldModelRepo,
    season: CropSeasonView,
    today: date,
) -> None:
    """Run the Domain 11 process-baseline predictor and fill the D11 fields.

    ``interdependence_group`` stays UNKNOWN in this scaffold (needs the KB
    duplication-group mapping); everything else the model outputs is set, and
    the prediction is appended to yield_prediction_log (non-fatal)."""
    rows = await repo.list_u_values(season.crop_name_english)
    if not rows:
        return
    factors = [
        UValue(
            factor_key=r.factor_key,
            u_value=r.u_value,
            signal_field=r.signal_field,
            representative_rule_id=r.representative_rule_id,
            rank=r.rank,
        )
        for r in rows
    ]
    override = state.get("ceiling_quintal_per_acre")
    pred = predict_yield(
        ceiling_basis=ceiling_basis_for_layout(state.get("planting_layout")),
        factors=factors,
        signals=state,
        prediction_stage=state.get("prediction_stage"),
        ceiling_override=float(override) if override is not None else None,
    )

    _set(state, "predicted_yield_quintal_per_acre", pred.predicted_yield_quintal_per_acre)
    _set(state, "prediction_interval_pct", pred.prediction_interval_pct)
    _set(state, "yield_prediction_interval_pct", pred.prediction_interval_pct)
    _set(state, "cumulative_loss_pct", pred.cumulative_loss_pct)
    _set(state, "gap_attributed_pct", pred.gap_attributed_pct)
    _set(state, "gap_unexplained_pct", pred.gap_unexplained_pct)
    _set(state, "ceiling_basis", pred.ceiling_basis)
    _set(state, "u_values_applied", pred.u_values_applied)
    _set(state, "u_value_source_class", pred.u_value_source_class)
    if state.get("ceiling_quintal_per_acre") is None:
        _set(state, "ceiling_quintal_per_acre", pred.ceiling_quintal_per_acre)
    _set(
        state,
        "season_record_complete",
        state.get("harvest_date") is not None
        and state.get("yield_quintal_per_acre_actual") is not None,
    )

    dap = state.get("dap")
    log = YieldPredictionLog(
        tenant_id=season.tenant_id,
        season_id=season.season_id,
        plot_id=season.plot_id,
        prediction_date=today,
        dap=dap if isinstance(dap, int) else None,
        prediction_stage=state.get("prediction_stage"),
        ceiling_quintal_per_acre=pred.ceiling_quintal_per_acre,
        ceiling_basis=pred.ceiling_basis,
        predicted_yield_quintal_per_acre=pred.predicted_yield_quintal_per_acre,
        ci_low_quintal_per_acre=pred.ci_low_quintal_per_acre,
        ci_high_quintal_per_acre=pred.ci_high_quintal_per_acre,
        prediction_interval_pct=pred.prediction_interval_pct,
        cumulative_loss_pct=pred.cumulative_loss_pct,
        gap_attributed_pct=pred.gap_attributed_pct,
        gap_unexplained_pct=pred.gap_unexplained_pct,
        u_values_applied=pred.u_values_applied,
        attribution=[
            {
                "factor_key": c.factor_key,
                "u_value": c.u_value,
                "intensity": c.intensity,
                "loss_pct": c.loss_pct,
                "rule_id": c.rule_id,
            }
            for c in pred.attribution
        ],
        u_value_source_class=pred.u_value_source_class,
        model_version=pred.model_version,
        data_quality=pred.data_quality,
        confidence=pred.confidence,
    )
    # A log-write hiccup must never suppress the plot's advisory.
    with suppress(Exception):
        await repo.log_prediction(log)


def _populate_from_forecast(
    state: dict[str, Any], rows: list[ForecastRow], today: date, sowing_date: date | None = None
) -> None:
    """Fill the KB's D07 rain-window / evaporation / radiation fields from the
    Open-Meteo past+future window. Station-only fields (station_id, gauge age,
    forecast bias vs station) stay UNKNOWN until the Main Node is installed."""
    _set(state, "forecast_source", rows[0].source_api if rows else None)
    _set(state, "forecast_rain_48h_mm", _forecast_rain_48h_mm(rows, today))
    _set(state, "rainfall_last_48h_mm", _rain_last_48h_mm(rows, today))
    _set(state, "cyclone_alert_active", _cyclone_alert(rows, today))
    _set(state, "rain_gap_days", _rain_gap_days(rows, today))
    _set(state, "dry_spell_days", _dry_spell_days(rows, today))
    _set(state, "effective_rainfall_mm", _effective_rainfall_mm(rows, today))
    _set(state, "heat_stress_days_count", _heat_stress_days(rows, today))
    _set(state, "fog_days_consecutive", _fog_days_consecutive(rows, today))
    # Season-to-date rain (bounded by the fetched window, ~92 days back).
    if sowing_date is not None:
        ytd = [
            r.rain_mm_expected or 0.0 for r in rows if sowing_date <= r.forecast_for_date <= today
        ]
        if ytd:
            _set(state, "rainfall_ytd_mm", round(sum(ytd), 1))
    today_row = next((r for r in rows if r.forecast_for_date == today), None)
    if today_row is not None:
        _set(state, "rainfall_mm", today_row.rain_mm_expected)
        _set(state, "pan_evaporation_mm_day", today_row.et0_mm)
        _set(state, "solar_radiation_mj_m2", today_row.solar_radiation_mj_m2)
        _set(state, "vpd_night_mean_kpa", today_row.vpd_night_mean_kpa)
        if today_row.fog_observed is not None:
            _set(state, "fog_observed", today_row.fog_observed)


# DB ``farms.soil_type`` domain (black/red/sandy/loamy/mixed) → the KB's
# ``soil_type`` enum (vertisol/loam/sandy_loam/laterite/other). Anything not
# listed maps to ``other``. AGRONOMIST TO CONFIRM red→laterite (many "red"
# soils are red loams, not true laterite).
_SOIL_TYPE_MAP = {
    "black": "vertisol",
    "loamy": "loam",
    "sandy": "sandy_loam",
    "red": "laterite",
    "mixed": "other",
}

# KB ``soil_texture_class`` (light/medium/heavy) DERIVED from the constrained
# ``farms.soil_type`` column, NOT from the free-text ``farms.soil_texture``
# (which has no controlled vocabulary). Standard texture-by-feel classing;
# unknown soil types fall back to ``medium``. When a soil lab result lands
# (sand/silt/clay %), compute this from the USDA triangle instead.
_SOIL_TEXTURE_CLASS_MAP = {
    "black": "heavy",
    "loamy": "medium",
    "sandy": "light",
    "red": "medium",
    "mixed": "medium",
}


def _populate_from_plot(state: dict[str, Any], p: Plot) -> None:
    """Fill plot-level facts the KB reads."""
    _set(state, "area_acre", p.area_acre)
    _set(state, "plot_id", p.plot_id)


def _populate_from_farm(state: dict[str, Any], f: FarmFacts) -> None:
    """Fill farm-level facts the KB reads (soil, water source, irrigation)."""
    if f.soil_type is not None:
        _set(state, "soil_type", _SOIL_TYPE_MAP.get(f.soil_type, "other"))
        _set(state, "soil_texture_class", _SOIL_TEXTURE_CLASS_MAP.get(f.soil_type, "medium"))
    _set(state, "soil_depth_cm", f.soil_depth_cm)
    # Farm-level organic carbon is a coarse fallback for the KB's soil_oc_pct;
    # a real lab test (populated later) overrides it.
    _set(state, "soil_oc_pct", f.soil_organic_carbon_pct)
    _set(state, "water_source_type", f.water_source_primary)
    _set(state, "dripper_lph", f.drip_emitter_lph)
    if f.irrigation_type is not None:
        _set(state, "has_drip", f.irrigation_type == "drip")
    if isinstance(f.previous_crops_json, list):
        _set(state, "previous_crops_3yr", f.previous_crops_json)


# District → Marathwada agro-climatic zone (D07/D10). AGRONOMIST TO CONFIRM /
# EXTEND; unlisted districts fall back to 'unknown'.
_AGRO_ZONE = {
    "Chhatrapati Sambhajinagar": "marathwada_central",
    "Aurangabad": "marathwada_central",
    "Jalna": "marathwada_central",
    "Beed": "marathwada_central",
    "Dharashiv": "marathwada_western",
    "Osmanabad": "marathwada_western",
    "Latur": "marathwada_eastern",
    "Nanded": "marathwada_eastern",
    "Parbhani": "marathwada_eastern",
    "Hingoli": "marathwada_eastern",
}


def _populate_from_farmer(state: dict[str, Any], loc: FarmerLocation) -> None:
    """Fill farmer administrative location (D10 scheme rules)."""
    _set(state, "district", loc.district)
    _set(state, "taluka", loc.taluka)
    if loc.district is not None:
        _set(state, "agro_climatic_zone", _AGRO_ZONE.get(loc.district, "unknown"))
    if loc.language_preference is not None:
        _set(state, "advisory_language", "mr" if loc.language_preference == "marathi" else "en")


# crop_scouting observation columns (migration 0023) whose KB field name equals
# the CropScoutingView attribute name - copied by name.
_SCOUTING_FIELDS: tuple[str, ...] = (
    "emergence_started",
    "establishment_pct",
    "tillers_per_plant",
    "flowering_observed",
    "central_shoot_dead",
    "seed_sprouts_visible",
    "shoot_borer_incidence_pct",
    "leaf_roller_incidence_pct",
    "rhizome_fly_incidence_pct",
    "white_grub_suspected",
    "nematode_suspected",
    "leaf_caterpillar_observed",
    "light_trap_installed",
    "light_trap_count_nightly",
    "straight_line_holes_in_whorl",
    "stem_hole_with_webbing",
    "exposed_rhizomes_observed",
    "rot_incidence_pct",
    "wilt_incidence_pct",
    "leaf_spot_incidence_pct",
    "wilt_while_green",
    "leaf_spot_rings_visible",
    "ooze_test_result",
    "rhizome_texture",
    "rhizome_smell",
    "stem_cut_colour",
    "stem_ooze_type",
    "soft_rhizome_found",
    "plant_pulls_easily",
    "shoot_pulls_out_easily",
    "leaf_yellowing_pattern",
    "skin_scrape_result",
    "sample_dig_120_done",
    "sample_dig_180_done",
    "standing_water_hours_observed",
    "harvest_injury_observed",
    "moisture_pct_final",
)


_ECON_FIELDS: tuple[str, ...] = (
    "breakeven_price_per_quintal",
    "breakeven_yield_quintal",
    "cash_flow_gap_months",
    "cash_outflow_to_date",
    "ceiling_quintal_per_acre",
    "cost_drainage",
    "cost_earthing_labour",
    "cost_harvest_transport",
    "cost_micronutrients",
    "cost_mulch",
    "cost_seed",
    "cost_seed_treatment_planting",
    "crop_loan_taken",
    "drip_annual_share",
    "drip_capital_cost",
    "drip_life_years",
    "grade_a_pct",
    "grade_b_pct",
    "grade_c_pct",
    "graded_separately",
    "intercrop_revenue",
    "interest_cost",
    "land_rent_or_opportunity",
    "mulch_material_price_per_tonne",
    "mulch_quantity_t_per_acre",
    "net_return_per_acre",
    "sale_market",
    "sale_price_per_quintal",
    "seed_opportunity_cost",
    "seed_retained_or_purchased",
    "total_cost_per_acre",
    "transport_cost_per_quintal",
)


_OPS_FIELDS: tuple[str, ...] = (
    "basal_k_kg_per_acre",
    "basal_p_kg_per_acre",
    "castor_bait_prepared_date",
    "castor_bait_units_per_acre",
    "drip_runtime_min",
    "ethephon_spray_count",
    "fertigation_active",
    "fertigation_last_ec_response",
    "herbicide_post_emergent_date",
    "herbicide_pre_emergent_date",
    "irrigation_applied_litres_today",
    "kulav_passes",
    "last_fungicide_date",
    "last_fungicide_group",
    "last_insecticide_date",
    "last_insecticide_group",
    "metarhizium_kg_per_acre",
    "naa_spray_count",
    "weeding_count",
    "labour_arranged_date",
)


_SCHEMES_FIELDS: tuple[str, ...] = (
    "cgwb_block_category",
    "cibrc_list_checked_date",
    "data_review_due",
    "drip_subsidy_pct_applicable",
    "drought_prone_listed",
    "farm_pond_planned",
    "farmer_category",
    "geo_tagging_done",
    "kvk_contacted",
    "pmfby_notified_for_ginger",
    "pre_sanction_date",
    "pre_sanction_received",
    "priority_category",
    "research_centre_contacted",
    "scale_of_finance_per_acre",
    "seed_supplier_identified",
    "soil_lab_selected",
    "subsidy_applied_date",
    "subsidy_documents_ready",
    "subsidy_lottery_result",
    "subsidy_scheme_applied",
)

_CONSENT_FIELDS: tuple[str, ...] = (
    "consent_advisory",
    "consent_research",
    "consent_date",
    "third_party_share_consent_given",
    "data_retention_until",
    "deletion_requested",
    "cluster_anonymised",
    "sat_attribution_shown",
    "sat_public_display_context",
)


def _populate_from_scouting(state: dict[str, Any], s: CropScoutingView) -> None:
    """Fill the KB pest/disease/growth observations from the latest scouting row."""
    for f in _SCOUTING_FIELDS:
        _set(state, f, getattr(s, f))
    # pest_scouting_date is derived from the row's date, not a stored column.
    _set(state, "pest_scouting_date", s.scouting_date)


def _populate_from_lab_soil(state: dict[str, Any], lab: LabSoilTestView) -> None:
    """Fill the KB soil-chemistry fields from the latest lab test.

    A test existing at all sets ``soil_test_available``; the individual
    nutrient values are set only when the lab reported them.
    """
    _set(state, "soil_test_available", True)
    _set(state, "soil_oc_pct", lab.soil_oc_pct)  # overrides the farm fallback
    _set(state, "soil_ec", lab.soil_ec)
    _set(state, "soil_free_lime_pct", lab.soil_free_lime_pct)
    _set(state, "soil_zn_ppm", lab.soil_zn_ppm)
    _set(state, "soil_fe_ppm", lab.soil_fe_ppm)
    _set(state, "soil_ca_ppm", lab.soil_ca_ppm)
    _set(state, "soil_mg_ppm", lab.soil_mg_ppm)
    _set(state, "soil_s_ppm", lab.soil_s_ppm)


def _geojson_polygon_to_wkt(geojson: Any) -> str | None:
    """Convert a GeoJSON Polygon dict to a WKT string (pure, no shapely).

    D14-PL-001 only cares that ``plot_polygon_wkt`` is non-null when a boundary
    exists; the fetch adapter reads the raw GeoJSON separately. Returns ``None``
    for anything that is not a well-formed Polygon.
    """
    if not isinstance(geojson, dict) or geojson.get("type") != "Polygon":
        return None
    coords = geojson.get("coordinates")
    if not isinstance(coords, list) or not coords:
        return None
    rings: list[str] = []
    for ring in coords:
        pts = ", ".join(
            f"{pt[0]} {pt[1]}" for pt in ring if isinstance(pt, list | tuple) and len(pt) >= 2
        )
        if pts:
            rings.append(f"({pts})")
    return f"POLYGON({', '.join(rings)})" if rings else None


def _scene_before(
    scenes: list[SatelliteScene], latest_date: date, min_days: int
) -> SatelliteScene | None:
    """Most-recent scene at least ``min_days`` older than ``latest_date``.

    ``scenes`` is most-recent-first; used to pick the comparison scene for a
    day-over-day delta (scenes arrive ~5 days apart, so this approximates the
    rule's 10-day / 5-day windows).
    """
    for s in scenes:
        if (latest_date - s.image_date).days >= min_days:
            return s
    return None


def _populate_from_satellite(
    state: dict[str, Any],
    optical: list[SatelliteScene],
    sar: list[SatelliteScene],
    plot: Plot | None,
    today: date,
) -> None:
    """Fill the Domain 14 optical/SAR fields, deltas, freshness and baseline gap."""
    # Plot boundary gates (D14-PL-001 blocks all D14 output without these).
    if plot is not None:
        _set(state, "plot_polygon_wkt", _geojson_polygon_to_wkt(plot.gps_boundary_geojson))
        _set(state, "plot_area_ha", acre_to_hectare(plot.area_acre))

    if optical:
        o = optical[0]
        _set(state, "sat_source", o.satellite_source)
        _set(state, "ndvi_mean", o.ndvi_mean)
        _set(state, "ndvi_std", o.ndvi_std)
        _set(state, "ndre_mean", o.ndre_mean)
        _set(state, "ndmi_mean", o.ndmi_mean)
        _set(state, "evi_mean", o.evi_mean)
        _set(state, "savi_mean", o.savi_mean)
        _set(state, "nbr_mean", o.nbr_value)
        _set(state, "plot_cloud_pct", o.cloud_cover_pct)
        _set(state, "scene_valid_pixel_pct", o.valid_pixel_pct)
        _set(state, "sat_pipeline_version", o.pipeline_version)
        fresh = (today - o.image_date).days
        _set(state, "ndvi_freshness_days", fresh)
        _set(state, "optical_gap_days", fresh)
        _set(state, "sat_advisory_confidence", advisory_confidence_from_freshness(fresh))
        prev10 = _scene_before(optical, o.image_date, 7)
        if prev10 is not None:
            _set(state, "ndvi_delta_10d", index_delta(o.ndvi_mean, prev10.ndvi_mean))
            _set(state, "ndmi_delta_10d", index_delta(o.ndmi_mean, prev10.ndmi_mean))
            _set(state, "nbr_delta_10d", index_delta(o.nbr_value, prev10.nbr_value))
        prev5 = _scene_before(optical, o.image_date, 3)
        if prev5 is not None:
            d = index_delta(o.ndre_mean, prev5.ndre_mean)
            days = (o.image_date - prev5.image_date).days or 1
            if d is not None:
                _set(state, "ndre_slope_5d", d / Decimal(days))
        dap = state.get("dap")
        base = ndvi_regional_baseline(dap) if isinstance(dap, int) else None
        _set(state, "plot_ndvi_baseline_regional", base)
        _set(state, "plot_ndvi_gap_regional", baseline_gap(o.ndvi_mean, base))

    if sar:
        s = sar[0]
        _set(state, "sar_vv_db", s.sar_vv_db)
        _set(state, "sar_vh_db", s.sar_vh_db)
        rvi = s.sar_rvi if s.sar_rvi is not None else sar_rvi(s.sar_vv_db, s.sar_vh_db)
        _set(state, "sar_rvi", rvi)
        _set(state, "sar_coherence", s.sar_coherence)
        _set(state, "sar_gap_days", (today - s.image_date).days)
        prev_sar = _scene_before(sar, s.image_date, 1)
        if prev_sar is not None:
            _set(state, "sar_vv_delta_db", index_delta(s.sar_vv_db, prev_sar.sar_vv_db))


def _set(state: dict[str, Any], key: str, value: object) -> None:
    """Assign only if the key is declared and value is not None.

    We intentionally do not raise on undeclared field names; ingestion of
    a new sensor field is deliberate work. But we do not want to silently
    add a key the engine does not know about either. So: assign only if
    the key is already present (defaulted to None) in the dict.
    """
    if key in state and value is not None:
        state[key] = value


__all__ = ["SYNTHETIC_FIELDS", "FarmBrainDeps", "FarmBrainState", "build_farm_brain"]
