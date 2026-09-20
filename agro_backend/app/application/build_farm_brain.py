"""Assemble a Farm Brain state dict for the ginger engine.

The teammate's engine expects a per-plot per-day dict keyed on the names
declared in ``kb_farm_brain_fields`` — 306 fields covering sensors, weather,
crop stage, plot facts, operational records, derived durations, and synthetic
helpers.

Our current data sources fill roughly one-third of those fields (latest
Reading, Plot, CropSeason, computed DAP + month). The rest come back as
``None`` and the engine's three-valued logic reports
``"insufficient data: <field>"`` for any rule that references them. This is
the intended behaviour — see ``ginger/engine/ARCHITECTURE.md`` §3.

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
  ``days_to_harvest``, product-policy proposals — all deterministic from
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

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.farm_repo import FarmFacts, FarmRepo
from app.application.ports.farmer_repo import FarmerLocation, FarmerRepo
from app.application.ports.lab_soil_test_repo import LabSoilTestRepo, LabSoilTestView
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.application.ports.satellite_reading_repo import (
    SOURCE_OPTICAL,
    SOURCE_SAR,
    SatelliteReadingRepo,
    SatelliteScene,
)
from app.application.ports.weather_station_reading_repo import WeatherStationReadingRepo
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

if TYPE_CHECKING:
    # Kept to declare unused ports if future rounds add extra data sources.
    pass


# Synthetic fields that the ginger engine always adds to the field vocabulary
# regardless of what the database declares. Kept here as a constant so tests
# can assert we know about all of them.
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
    valid state dict — the engine's three-valued logic will report every
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

    # ---- Farmer location (district / taluka) --------------------------
    if deps.farmer_repo is not None and season is not None:
        owner = await deps.farmer_repo.owner_of_farm(season.farm_id)
        if owner is not None:
            _set(state, "farmer_id", str(owner))
            loc = await deps.farmer_repo.find_location(owner)
            if loc is not None:
                _populate_from_farmer(state, loc)

    # ---- Weather station (air temp + humidity + derived VPD) -----------
    # Weather is farm-level; resolve it from the active season's farm. The
    # cluster station's temperature and humidity feed the Domain 7 VPD rules
    # via the computed ``vpd_kpa``.
    if deps.weather_station_reading_repo is not None and season is not None:
        weather = await deps.weather_station_reading_repo.most_recent_for_farm(season.farm_id)
        if weather is not None:
            _populate_from_weather(state, weather)

    # ---- Satellite (Domain 14 optical + SAR indices) -------------------
    # Reads the recent scenes per source, plus the plot boundary for the
    # polygon/area gates. Computes deltas, freshness, confidence and the
    # baseline gap from the pure satellite-metrics helpers.
    if deps.satellite_reading_repo is not None:
        optical = await deps.satellite_reading_repo.recent(plot_id, SOURCE_OPTICAL, limit=6)
        sar = await deps.satellite_reading_repo.recent(plot_id, SOURCE_SAR, limit=6)
        _populate_from_satellite(state, optical, sar, plot, today)

    # ---- Synthetic ------------------------------------------------------
    state["current_month"] = today.month
    # brand/capability/profit/price proposals are engine-side attempts,
    # set at attempt time — not from data. Default to None; the immutable
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


def _populate_from_season(
    state: dict[str, Any], season: CropSeasonView | None, today: date
) -> None:
    """Fill crop stage, DAP, and season-derived synthetic fields."""
    if season is None:
        return
    dap = (today - season.sowing_date).days if season.sowing_date else None
    _set(state, "dap", dap)
    _set(state, "current_stage", season.current_growth_stage)
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


def _populate_from_farmer(state: dict[str, Any], loc: FarmerLocation) -> None:
    """Fill farmer administrative location (D10 scheme rules)."""
    _set(state, "district", loc.district)
    _set(state, "taluka", loc.taluka)


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
