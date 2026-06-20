"""Validation orchestrator.


Wires the four pure gates from :mod:`app.domain.validation_gates` together,
fetching the historical windows the stuck/MAD gates need via the
:class:`~app.application.ports.reading_repo.ReadingRepo` port.


Per ``.cursorrules`` #13 the application layer imports domain + ports +
stdlib + typing. NO infra/, NO frameworks. This file's only side effect is
the two ``await repo.history_for_*`` calls; if the repo is faked in tests
the whole orchestrator runs synchronously without I/O.


The output is a *new* :class:`~app.domain.sensor.Reading` (the input is
frozen). When any gate fires:


* ``validation_warn`` is set to True
* ``sensor_health_json`` accumulates ``{field: flag.value}`` entries


The orchestrator does NOT decide what to do with the warning - that's the
ingest use case (Round 7), which may persist, drop, or alert based on the
flags. Round 5 stops at "produce the validated Reading".
"""


from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.application.ports.reading_repo import ReadingRepo
from app.domain.sensor import Reading
from app.domain.validation_gates import (
    MAD_K,
    RANGES,
    ValidationFlag,
    check_cross_sensor,
    check_range,
    is_mad_outlier,
    is_stuck,
)

# Window sizes for the database-backed gates. The roadmap docs cite these
# as "Phase 2.3 defaults"; the values match the JXBS sampling cadence and
# the dashboard's refresh budget.
STUCK_WINDOW_MINUTES: int = 90
MAD_WINDOW_HOURS: int = 24




# The gates ONLY check fields in this list. Fields not here (e.g. flags
# like ``low_battery_flag``, identity columns, JSONB) get no range/stuck/MAD
# treatment. Cross-sensor is handled separately and inspects the Reading
# as a whole, so its field set is implicit.
_NUMERIC_FIELDS_TO_CHECK: tuple[str, ...] = tuple(RANGES.keys())




async def execute(reading: Reading, repo: ReadingRepo) -> Reading:
    """Run all four validation gates against ``reading``.


    Returns the same Reading if no gate fired, or a new Reading with
    ``validation_warn=True`` and ``sensor_health_json`` augmented.


    Gate order (deterministic):


    1. Range check (pure, per field)
    2. Stuck check (DB-backed, per field; skipped if range_fail fired)
    3. MAD outlier (DB-backed, per field; skipped if range_fail or stuck fired)
    4. Cross-sensor consistency (pure, on the Reading as a whole)


    Skipping later gates when an earlier one fired keeps
    ``sensor_health_json`` keyed at "one flag per field" - downstream
    consumers (rule engine, dashboard) don't have to choose between
    contradicting flags.
    """
    flags: dict[str, str] = {}


    # ----- Gate 1: range -----
    for field in _NUMERIC_FIELDS_TO_CHECK:
        value = _decimal_field(reading, field)
        result = check_range(field, value)
        if result is not None:
            flags[field] = result.flag.value


    # ----- Gate 2: stuck (skip fields already flagged) -----
    for field in _NUMERIC_FIELDS_TO_CHECK:
        if field in flags:
            continue
        value = _decimal_field(reading, field)
        if value is None:
            continue
        history = await repo.history_for_stuck_check(reading.node_id, field, STUCK_WINDOW_MINUTES)
        if is_stuck(history, value):
            flags[field] = ValidationFlag.STUCK.value


    # ----- Gate 3: MAD outlier (skip fields already flagged) -----
    for field in _NUMERIC_FIELDS_TO_CHECK:
        if field in flags:
            continue
        value = _decimal_field(reading, field)
        if value is None:
            continue
        window = await repo.history_for_mad_check(reading.node_id, field, MAD_WINDOW_HOURS)
        if is_mad_outlier(window, value, MAD_K):
            flags[field] = ValidationFlag.OUTLIER.value


    # ----- Gate 4: cross-sensor (pure, last so it can observe earlier flags) -----
    for result in check_cross_sensor(reading):
        # Cross-sensor doesn't override an earlier per-field flag - the
        # range fail is more actionable than the cross-sensor disagreement
        # that it likely caused.
        flags.setdefault(result.field, result.flag.value)


    if not flags:
        return reading


    # Merge new flags with anything already in sensor_health_json (the
    # firmware may have already populated it from its on-device checks).
    merged: dict[str, Any] = {**reading.sensor_health_json, **flags}
    return reading.with_(validation_warn=True, sensor_health_json=merged)




def _decimal_field(reading: Reading, field: str) -> Decimal | None:
    """Type-narrowing accessor.


    ``getattr(reading, field)`` returns ``Any`` from mypy's perspective.
    This helper narrows to ``Decimal | None`` for the gate signatures and
    raises ``AttributeError`` if the Reading dataclass ever loses a field
    the orchestrator expects (which would be a programming error, not a
    runtime input error).
    """
    val = getattr(reading, field)
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    # Schema drift: a Reading field appeared in RANGES but is not a Decimal.
    # Fail loudly rather than silently skip - this is a wiring bug.
    raise TypeError(
        f"Reading.{field} is {type(val).__name__}, not Decimal | None - "
        f"validation_gates.RANGES drifted from Reading dataclass"
    )




__all__ = ["MAD_WINDOW_HOURS", "STUCK_WINDOW_MINUTES", "execute"]
