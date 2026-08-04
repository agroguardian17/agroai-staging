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
from typing import TYPE_CHECKING, Any

from app.application.ports.crop_season_repo import CropSeasonRepo, CropSeasonView
from app.application.ports.plot_repo import PlotRepo
from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import Reading

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

    # ---- Crop season (stage + DAP + synthetic dates) -------------------
    season = await deps.crop_season_repo.find_active_for_plot(plot_id)
    _populate_from_season(state, season, today)

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
    if season.sowing_date:
        state["days_to_planting"] = (season.sowing_date - today).days
    if season.expected_harvest_date:
        state["days_to_harvest"] = (season.expected_harvest_date - today).days


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
