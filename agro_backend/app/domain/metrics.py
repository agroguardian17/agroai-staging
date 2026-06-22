"""Pure derived metrics over a single Reading.


This module is the input layer for the rule engine. A :class:`DerivedMetrics`
instance is computed from one :class:`~app.domain.sensor.Reading` plus a
thin :class:`MetricsContext` (target moisture from crop config etc.) and
contains the *interpreted* fields that rules check against - things like
"is the battery critical?", "is moisture below target?", "do the pump
signals look like a dry-run signature?".


PURE module: stdlib only. No framework imports. No IO. The
``tests/domain/test_domain_purity.py`` AST scan enforces this.


Why this layer exists at all:


* Rules want to ask "is moisture below the stage target?" - not
  "is the raw pct below 30?". Without derived metrics every rule has
  to embed the same threshold math, and crop-stage variation makes
  the rule list explode combinatorially.
* Derived metrics centralise the threshold definitions so the rule
  engine (and the dashboard, in Round 12) can render them.
* Tests for these computations are sub-millisecond and require no
  fixtures - they're the cheapest place to catch bugs in our
  understanding of the physics.


Constants live at the top of the module. Any change to one of them is
a deliberate calibration event and should be code-reviewed; the unit
tests intentionally pin the constants so a drift is visible in the
diff.
"""


from __future__ import annotations


from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


from app.domain.sensor import Reading


# ---------------------------------------------------------------------------
# Calibration constants - any change is a deliberate event.
# ---------------------------------------------------------------------------


# Battery (LiFePO4 single cell, nominal 3.30 V resting):
BATTERY_HEALTHY_V: Decimal = Decimal("3.40")
BATTERY_LOW_V: Decimal = Decimal("3.30")  # matches LOW_BATTERY_THRESHOLD_V
BATTERY_CRITICAL_V: Decimal = Decimal("3.10")
BATTERY_DEAD_V: Decimal = Decimal("2.90")
BATTERY_HEALTHY_PCT: Decimal = Decimal("40")
BATTERY_LOW_PCT: Decimal = Decimal("20")
BATTERY_CRITICAL_PCT: Decimal = Decimal("10")


# Frost risk: soil at the root zone below this is a frost-injury threshold
# (a domain-specific value; for Aurangabad's cotton/tur it's conservative).
FROST_SOIL_TEMP_C: Decimal = Decimal("4.0")


# Dry-run signature: pump is "running" (per the relay flag) but current
# and flow are both below these floors. A real dry well shows ~0 current
# draw because the impeller has no resistance to push against.
DRY_RUN_PUMP_CURRENT_A_MAX: Decimal = Decimal("0.5")
DRY_RUN_FLOW_LPM_MAX: Decimal = Decimal("0.2")


# Moisture: per-crop targets land in Phase 5. Pilot default is the
# generic "field capacity floor" for black-soil cotton.
DEFAULT_TARGET_MOISTURE_PCT: Decimal = Decimal("28.0")




# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------




class BatteryState(StrEnum):
    """Coarse health bucket for the battery."""


    HEALTHY = "healthy"
    LOW = "low"
    CRITICAL = "critical"
    DEAD = "dead"
    UNKNOWN = "unknown"  # no battery telemetry on this reading




@dataclass(frozen=True, slots=True)
class MetricsContext:
    """Inputs the metric computations need that aren't on the Reading itself.


    For the pilot this is just the target soil moisture. Phase 5 will
    expand this with crop_stage, GDD accumulation, last-irrigation-time,
    etc.; rules and metrics then read from the richer context without
    reshaping their function signatures.
    """


    target_moisture_pct: Decimal = DEFAULT_TARGET_MOISTURE_PCT




@dataclass(frozen=True, slots=True)
class DerivedMetrics:
    """The interpreted view of one reading. Rules consume this."""


    # Moisture
    moisture_deficit_pct: Decimal | None  # positive => below target (too dry)
    moisture_below_target: bool


    # Battery
    battery_state: BatteryState


    # Environmental risk
    frost_risk: bool


    # Pump / irrigation
    dry_run_signature: bool


    # Sensor health
    sensor_health_warn: bool




# ---------------------------------------------------------------------------
# Pure helper functions - each is unit-testable in isolation.
# ---------------------------------------------------------------------------




def moisture_deficit(actual_pct: Decimal | None, target_pct: Decimal) -> Decimal | None:
    """Return target - actual. Positive => below target (too dry).


    None when we have no actual reading (sensor dead or both probes
    sentinel-out).
    """
    if actual_pct is None:
        return None
    return target_pct - actual_pct




def battery_state_from(voltage: Decimal | None, percent: Decimal | None) -> BatteryState:
    """Pick the worst-case bucket across voltage and percent telemetry.


    LiFePO4 cells have a fairly flat discharge curve; percent (from a
    fuel gauge / coulomb counter) is more reliable below ~3.3V than
    voltage alone. We take the more pessimistic of the two so a single
    sensor lying healthy doesn't mask a real low.
    """
    if voltage is None and percent is None:
        return BatteryState.UNKNOWN


    states: list[BatteryState] = []


    if voltage is not None:
        if voltage <= BATTERY_DEAD_V:
            states.append(BatteryState.DEAD)
        elif voltage <= BATTERY_CRITICAL_V:
            states.append(BatteryState.CRITICAL)
        elif voltage < BATTERY_LOW_V:
            states.append(BatteryState.LOW)
        elif voltage >= BATTERY_HEALTHY_V:
            states.append(BatteryState.HEALTHY)
        else:
            # Between LOW and HEALTHY: still "low" until it climbs over.
            states.append(BatteryState.LOW)


    if percent is not None:
        if percent <= BATTERY_CRITICAL_PCT:
            states.append(BatteryState.CRITICAL)
        elif percent <= BATTERY_LOW_PCT:
            states.append(BatteryState.LOW)
        elif percent >= BATTERY_HEALTHY_PCT:
            states.append(BatteryState.HEALTHY)
        else:
            states.append(BatteryState.LOW)


    # Worst of the two by ordering (DEAD > CRITICAL > LOW > HEALTHY).
    return _worst(states)




_BATTERY_RANK: dict[BatteryState, int] = {
    BatteryState.HEALTHY: 0,
    BatteryState.LOW: 1,
    BatteryState.CRITICAL: 2,
    BatteryState.DEAD: 3,
    BatteryState.UNKNOWN: -1,  # never selected when any real state exists
}




def _worst(states: list[BatteryState]) -> BatteryState:
    return max(states, key=_BATTERY_RANK.__getitem__)




def is_frost_risk(soil_temp_c: Decimal | None) -> bool:
    if soil_temp_c is None:
        return False
    return soil_temp_c <= FROST_SOIL_TEMP_C




def is_dry_run_signature(
    *,
    pump_running: bool | None,
    pump_current_amps: Decimal | None,
    water_flow_lpm: Decimal | None,
) -> bool:
    """A dry well is a true case: pump on, no flow, almost no current draw."""
    if not pump_running:
        return False
    # Both current and flow must be present to make a confident call;
    # otherwise the firmware's own ``dry_run_detected`` flag is the
    # source of truth and the rule engine will key off that instead.
    if pump_current_amps is None or water_flow_lpm is None:
        return False
    return (
        pump_current_amps <= DRY_RUN_PUMP_CURRENT_A_MAX and water_flow_lpm <= DRY_RUN_FLOW_LPM_MAX
    )




def sensor_health_warn_from(reading: Reading) -> bool:
    """True if any validation gate fired or fault flags are present."""
    if reading.validation_warn:
        return True
    return bool(reading.fault_flags)




# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------




def compute(reading: Reading, ctx: MetricsContext | None = None) -> DerivedMetrics:
    """Compute the full DerivedMetrics from one Reading + context.


    Single entry point so the rule engine doesn't have to remember
    which helpers to call in which order.
    """
    context = ctx or MetricsContext()
    deficit = moisture_deficit(reading.soil_moisture_avg_pct, context.target_moisture_pct)
    return DerivedMetrics(
        moisture_deficit_pct=deficit,
        moisture_below_target=deficit is not None and deficit > Decimal("0"),
        battery_state=battery_state_from(reading.battery_voltage_v, reading.battery_percent),
        frost_risk=is_frost_risk(reading.soil_temp_rootzone_c),
        dry_run_signature=is_dry_run_signature(
            pump_running=reading.pump_running,
            pump_current_amps=reading.pump_current_amps,
            water_flow_lpm=reading.water_flow_lpm,
        ),
        sensor_health_warn=sensor_health_warn_from(reading),
    )




__all__ = [
    "BATTERY_CRITICAL_PCT",
    "BATTERY_CRITICAL_V",
    "BATTERY_DEAD_V",
    "BATTERY_HEALTHY_PCT",
    "BATTERY_HEALTHY_V",
    "BATTERY_LOW_PCT",
    "BATTERY_LOW_V",
    "DEFAULT_TARGET_MOISTURE_PCT",
    "DRY_RUN_FLOW_LPM_MAX",
    "DRY_RUN_PUMP_CURRENT_A_MAX",
    "FROST_SOIL_TEMP_C",
    "BatteryState",
    "DerivedMetrics",
    "MetricsContext",
    "battery_state_from",
    "compute",
    "is_dry_run_signature",
    "is_frost_risk",
    "moisture_deficit",
    "sensor_health_warn_from",
]
