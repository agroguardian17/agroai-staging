"""Pure water-budget math for the D03-WB engine.

Turns a single-pipe drip flow reading plus plot geometry and per-variety stage
water targets into the derived fields the D03-WB / D03-ST-001 knowledge-base
rules evaluate against. The rules cannot do arithmetic in the trigger DSL, so
this module produces the *ratios* and *classifications* they compare to
constants (e.g. ``stage_water_deficit_ratio > 0.25``).

Pure: stdlib + ``Decimal`` only (no framework imports), per the domain-purity
gate. Every function returns ``None`` when an input it needs is missing, so a
partially-known plot yields a partially-populated budget and the dependent
rules simply stay UNKNOWN (three-valued logic) rather than misfiring.

Design notes / provenance:
- Plant count uses the plot's own ``plants_per_acre x area_acre`` when both are
  known (the geometry-derived estimate the farmer app will later refine).
- VWC status maps the latest volumetric water content against the season's own
  saturation / stress thresholds (probe-first — the KB's cardinal
  ``VWC > water-budget`` precedence relies on this).
- Deficit ratio is ``1 - min(1, cumulative / stage_target)`` — the FAO-56-style
  fraction of the stage's per-plant target still owed, clamped to [0, 1].
- Cumulative-vs-lifecycle ratio compares season-to-date per-plant water against
  the variety's lifecycle high-end (the >1.20 over-irrigation flag).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_ZERO = Decimal("0")
_ONE = Decimal("1")

# VWC status enum values (must match the KB `vwc_status` field enum).
VWC_SATURATED = "saturated"
VWC_LOW = "low"
VWC_OK = "ok"


@dataclass(frozen=True)
class VarietyStageTargets:
    """Per-variety, per-stage water targets (a row of ``variety_stage_water_target``)."""

    stage: str | None = None
    dap_start: int | None = None
    dap_end: int | None = None
    stage_target_l_low: Decimal | None = None
    stage_target_l_high: Decimal | None = None
    per_event_l_low: Decimal | None = None
    per_event_l_high: Decimal | None = None
    max_l_per_event: Decimal | None = None
    lifecycle_target_high: Decimal | None = None


@dataclass(frozen=True)
class WaterBudget:
    """The derived water-budget fields the D03-WB rules read.

    Any field may be ``None`` (the mapper leaves the corresponding farm-brain
    key UNKNOWN and the rule does not fire).
    """

    plot_plants_estimated: int | None = None
    vwc_status: str | None = None
    variety_min_per_event_l: Decimal | None = None
    variety_max_per_event_l: Decimal | None = None
    per_plant_water_stage_cumulative_l: Decimal | None = None
    stage_water_deficit_ratio: Decimal | None = None
    per_plant_cumulative_vs_lifecycle_ratio: Decimal | None = None
    per_plant_dose_l_last_event: Decimal | None = None
    days_since_last_flow_reading: int | None = None
    flow_telemetry_field_exists: bool = False
    planting_geometry_incomplete: bool = True


def estimate_plants(area_acre: Decimal | None, plants_per_acre: int | None) -> int | None:
    """Whole-plot plant estimate from ``plants_per_acre x area_acre``.

    Returns ``None`` if either input is missing or non-positive.
    """
    if area_acre is None or plants_per_acre is None:
        return None
    if area_acre <= _ZERO or plants_per_acre <= 0:
        return None
    return int((Decimal(plants_per_acre) * area_acre).to_integral_value(rounding="ROUND_HALF_UP"))


def classify_vwc(
    vwc_pct: Decimal | None,
    saturation: Decimal | None,
    stress_threshold: Decimal | None,
) -> str | None:
    """Classify volumetric water content against the season's own thresholds.

    ``>= saturation`` -> ``saturated`` (irrigation veto), ``<= stress`` ->
    ``low`` (needs water), otherwise ``ok``. Returns ``None`` when the reading
    is absent so the KB rule stays UNKNOWN rather than assuming a state.
    """
    if vwc_pct is None:
        return None
    if saturation is not None and vwc_pct >= saturation:
        return VWC_SATURATED
    if stress_threshold is not None and vwc_pct <= stress_threshold:
        return VWC_LOW
    return VWC_OK


def per_plant_cumulative(total_flow_litres: Decimal | None, plants: int | None) -> Decimal | None:
    """Season/stage cumulative water delivered per plant."""
    if total_flow_litres is None or plants is None or plants <= 0:
        return None
    return (total_flow_litres / Decimal(plants)).quantize(Decimal("0.01"))


def deficit_ratio(
    cumulative_per_plant: Decimal | None, stage_target: Decimal | None
) -> Decimal | None:
    """Fraction of the stage's per-plant water target still owed, clamped [0, 1].

    ``1 - min(1, cumulative / target)``. Returns ``None`` if the target is
    missing or non-positive.
    """
    if cumulative_per_plant is None or stage_target is None or stage_target <= _ZERO:
        return None
    ratio = cumulative_per_plant / stage_target
    if ratio > _ONE:
        ratio = _ONE
    if ratio < _ZERO:
        ratio = _ZERO
    return (_ONE - ratio).quantize(Decimal("0.01"))


def cumulative_vs_lifecycle_ratio(
    cumulative_per_plant: Decimal | None, lifecycle_target_high: Decimal | None
) -> Decimal | None:
    """Season-to-date per-plant water as a fraction of the variety lifecycle high-end."""
    if (
        cumulative_per_plant is None
        or lifecycle_target_high is None
        or lifecycle_target_high <= _ZERO
    ):
        return None
    return (cumulative_per_plant / lifecycle_target_high).quantize(Decimal("0.001"))


def geometry_incomplete(
    *,
    planting_method: str | None,
    dripper_spacing_cm: Decimal | None,
    drippers_per_acre: int | None,
    rows_per_bed: int | None,
    plants_per_acre: int | None,
) -> bool:
    """True while any geometry input the water-budget engine needs is missing.

    Drives the pre-planting blocking gate D03-WB-008. ``planting_method`` and a
    dripper count are the fields the farmer app still has to capture; the bed
    fields come from the season plan.
    """
    return (
        planting_method is None
        or dripper_spacing_cm is None
        or drippers_per_acre is None
        or rows_per_bed is None
        or plants_per_acre is None
    )
