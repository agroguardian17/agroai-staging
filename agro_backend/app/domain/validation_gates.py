"""Pure validation gates for incoming sensor readings.


PURE module: stdlib only (Decimal, statistics, enum, dataclasses). Enforced
by ``tests/domain/test_domain_purity.py``.


The hexagon places *pure validation math* in the domain layer and the
*orchestration* (which fetches history from the database, runs gates in
order, builds the augmented Reading) in the application layer
(``app.application.validate_reading``). This file is only the math.


Four gates per Roadmap §1.10 / Phase 2.3:


1. **Range check** — each numeric value falls within a physically-sensible
   bound. Pure: takes a field name + value, returns a flag or None.
2. **Stuck check** — last-N consecutive readings of the same sensor are
   identical (sensor frozen / cable cut). Pure math: takes the pre-fetched
   history snapshot and decides.
3. **MAD outlier check** — single reading falls > k·MAD from the trailing
   24-h median. Pure math: takes the pre-fetched window + value.
4. **Cross-sensor consistency** — within one Reading, do the two moisture
   probes agree? Is the NPK probe self-consistent? Pure: inspects the
   Reading.


The application orchestrator wires these together. The repo port supplies
the historical windows. Validation is observable: every gate that fires
adds an entry to ``sensor_health_json`` (keyed by field name).
"""


from __future__ import annotations

import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from app.domain.sensor import LOW_BATTERY_THRESHOLD_V, Reading


class ValidationFlag(StrEnum):
    """Per-field validation outcomes recorded in ``sensor_health_json``.


    A single field can collect at most one flag per validation run; the
    application orchestrator picks the *first* gate to fire in the
    canonical gate order: range -> stuck -> outlier -> cross_sensor.
    """


    RANGE_FAIL = "range_fail"
    STUCK = "stuck"
    OUTLIER = "outlier"
    CROSS_SENSOR = "cross_sensor"




@dataclass(frozen=True, slots=True)
class GateResult:
    """One gate firing against one field.


    Returned by the pure gate functions; consumed by the application
    orchestrator which translates the (field, flag) pairs into the
    ``sensor_health_json`` map written to ``node_sensor_readings``.
    """


    field: str
    flag: ValidationFlag
    detail: str  # human-readable for logs / dashboards; never a PII vector




# ---------------------------------------------------------------------------
# Gate 1 — Range check
# ---------------------------------------------------------------------------
# Physical bounds, inclusive. Anything outside -> RANGE_FAIL.
#
# Sources:
#   * NPK probe spec sheets (JXBS-3001 / JXBS-3001-NPK)
#   * Roadmap §1.10 sample ranges
#   * Capacitive moisture sensor calibration window
#
# These are PHYSICAL bounds, not crop-relevant thresholds. A reading of
# 95% moisture is unusual for a Maharashtra plot but physically possible;
# the rule engine (Phase 4) decides what to do with it. The range gate
# only catches "this number cannot come from a working sensor".
RANGES: dict[str, tuple[Decimal, Decimal]] = {
    "soil_moisture_1_pct": (Decimal("0"), Decimal("100")),
    "soil_moisture_2_pct": (Decimal("0"), Decimal("100")),
    "soil_moisture_avg_pct": (Decimal("0"), Decimal("100")),
    "soil_temp_c": (Decimal("-10"), Decimal("80")),
    "soil_temp_rootzone_c": (Decimal("-10"), Decimal("80")),
    "soil_ph": (Decimal("0"), Decimal("14")),
    "soil_ec_ms_cm": (Decimal("0"), Decimal("20")),
    "soil_n_mg_kg": (Decimal("0"), Decimal("2000")),
    "soil_p_mg_kg": (Decimal("0"), Decimal("2000")),
    "soil_k_mg_kg": (Decimal("0"), Decimal("2000")),
    "battery_voltage_v": (Decimal("0"), Decimal("9")),
    "battery_percent": (Decimal("0"), Decimal("100")),
}




def check_range(field: str, value: Decimal | None) -> GateResult | None:
    """Return a RANGE_FAIL if value is outside the physical bound, else None.


    ``None`` value or unknown field returns ``None`` (no opinion). The
    application orchestrator iterates over ``RANGES.keys()`` rather than
    ``dir(reading)`` so an unknown field is a no-op here, not an error.
    """
    if value is None or field not in RANGES:
        return None
    lo, hi = RANGES[field]
    if value < lo or value > hi:
        return GateResult(
            field=field,
            flag=ValidationFlag.RANGE_FAIL,
            detail=f"value {value} outside [{lo}, {hi}]",
        )
    return None




# ---------------------------------------------------------------------------
# Gate 2 — Stuck check
# ---------------------------------------------------------------------------
STUCK_MIN_IDENTICAL: int = 4
"""Number of identical non-null values (within the window) that triggers
the STUCK flag. With ``history_for_stuck_check`` returning up to ~6 rows,
4 identical means "more than half the trailing window stuck on one
value" - that's the firmware / probe failure mode we want to catch."""




def is_stuck(history: Sequence[Decimal | None], latest: Decimal | None) -> bool:
    """``True`` iff at least :data:`STUCK_MIN_IDENTICAL` non-null values
    (including ``latest`` if non-null) are identical.


    ``history`` arrives oldest -> newest from the repo. ``latest`` is the
    just-incoming Reading's value for the same field; the orchestrator
    appends it conceptually but we pass it explicitly so this function
    stays pure. ``None`` values are skipped (a missing reading is not
    evidence of stuckness).


    A brand-new node with only one recorded value -> returns False
    (insufficient evidence).
    """
    if latest is None:
        return False
    non_null = [v for v in history if v is not None]
    non_null.append(latest)
    if len(non_null) < STUCK_MIN_IDENTICAL:
        return False
    same = sum(1 for v in non_null if v == latest)
    return same >= STUCK_MIN_IDENTICAL




# ---------------------------------------------------------------------------
# Gate 3 — MAD outlier check
# ---------------------------------------------------------------------------
MAD_K: Decimal = Decimal("3.5")
"""Multiplier applied to the MAD to define the outlier threshold. 3.5x is
the Hampel-identifier standard - tighter than 4.5 (which catches only
extreme spikes) and looser than 2.5 (which flags normal sensor noise
during dawn/dusk transitions)."""


MAD_MIN_WINDOW: int = 12
"""Minimum sample count below which MAD is too noisy to trust.
~12 samples over a 24-h window means at least one reading every 2 hours,
which matches the rapid-cadence Sub Node defaults."""




def is_mad_outlier(window: list[Decimal], value: Decimal, k: Decimal = MAD_K) -> bool:
    """``True`` iff ``value`` lies more than ``k * MAD`` from the window median.


    Hampel-identifier style. MAD = median(|x_i - median|). With ``k=3.5``
    this approximates the 3-sigma test for normally distributed data
    (MAD * 1.4826 ~= sigma for a normal distribution), but is robust to
    real outliers in the window itself - one bad reading doesn't poison
    the threshold.


    Returns ``False`` when the window has fewer than :data:`MAD_MIN_WINDOW`
    samples (brand-new node; let the reading through).
    """
    if len(window) < MAD_MIN_WINDOW:
        return False
    median = Decimal(statistics.median(window))
    deviations = [abs(x - median) for x in window]
    mad = Decimal(statistics.median(deviations))
    if mad == 0:
        # Degenerate case: every value identical. Treat anything different
        # as an outlier (the stuck gate also fires here, which is fine -
        # downstream code dedupes by field, not by gate).
        return value != median
    return abs(value - median) > k * mad




# ---------------------------------------------------------------------------
# Gate 4 — Cross-sensor consistency
# ---------------------------------------------------------------------------
MOISTURE_DISAGREE_PCT: Decimal = Decimal("15")
"""Percentage-point delta between the two capacitive moisture probes that
triggers a cross-sensor flag. 15 is the value the ADT Baramati pilot used
empirically; tighter than 10 (false positives from one probe being closer
to a drip emitter) and looser than 25 (misses real probe drift)."""




def check_cross_sensor(reading: Reading) -> list[GateResult]:
    """Inspect one Reading for internal contradictions.


    Currently checks:


    * The two capacitive moisture probes agree within
      :data:`MOISTURE_DISAGREE_PCT` percentage points.
    * The firmware's ``low_battery_flag`` agrees with
      :data:`LOW_BATTERY_THRESHOLD_V` and ``battery_voltage_v``.
    * NPK probe self-consistency: if N/P/K are present, EC must also be
      present (the JXBS-3001 emits them as one Modbus frame; missing EC
      means partial probe failure).


    Returns the list of GateResults that fired (possibly empty).
    """
    results: list[GateResult] = []


    # Moisture probe disagreement
    m1, m2 = reading.soil_moisture_1_pct, reading.soil_moisture_2_pct
    if m1 is not None and m2 is not None and abs(m1 - m2) > MOISTURE_DISAGREE_PCT:
        # Flag the avg field - that's what downstream consumers read.
        results.append(
            GateResult(
                field="soil_moisture_avg_pct",
                flag=ValidationFlag.CROSS_SENSOR,
                detail=(
                    f"moisture probes disagree: probe1={m1}, probe2={m2}, "
                    f"|delta|>{MOISTURE_DISAGREE_PCT}pp"
                ),
            )
        )


    # Low-battery-flag consistency
    bv = reading.battery_voltage_v
    if bv is not None and bv < LOW_BATTERY_THRESHOLD_V and not reading.low_battery_flag:
        results.append(
            GateResult(
                field="low_battery_flag",
                flag=ValidationFlag.CROSS_SENSOR,
                detail=(
                    f"battery_voltage_v={bv} below threshold {LOW_BATTERY_THRESHOLD_V} "
                    "but firmware did not set low_battery_flag"
                ),
            )
        )


    # NPK partial-failure detection
    n, p, k = reading.soil_n_mg_kg, reading.soil_p_mg_kg, reading.soil_k_mg_kg
    ec = reading.soil_ec_ms_cm
    npk_count = sum(v is not None for v in (n, p, k))
    if 0 < npk_count < 3:
        # One or two of N/P/K present but not all three: probe partial failure.
        results.append(
            GateResult(
                field="npk_sensor_raw_hex",
                flag=ValidationFlag.CROSS_SENSOR,
                detail=f"partial NPK frame: n={n}, p={p}, k={k}",
            )
        )
    elif npk_count == 3 and ec is None:
        # All three NPK present but EC missing: same probe should have emitted
        # both. Either firmware filtered EC or the frame parser failed.
        results.append(
            GateResult(
                field="soil_ec_ms_cm",
                flag=ValidationFlag.CROSS_SENSOR,
                detail="NPK present without EC; JXBS probe emits them together",
            )
        )


    return results




__all__ = [
    "MAD_K",
    "MAD_MIN_WINDOW",
    "MOISTURE_DISAGREE_PCT",
    "RANGES",
    "STUCK_MIN_IDENTICAL",
    "GateResult",
    "ValidationFlag",
    "check_cross_sensor",
    "check_range",
    "is_mad_outlier",
    "is_stuck",
]
