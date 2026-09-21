"""Domain 11 yield model - pure process baseline (Phase 1 scaffold).

Implements the AGRONOMY_SIGNOFF / VJH-V1.0 §2 method:

    Y_predicted = Y_ceiling * prod(1 - u_i * I_i)

- ``u_i`` is a factor's U-value (fraction of yield lost if fully expressed).
- ``I_i`` is its intensity this season (0..1), derived from a wired farm-brain
  signal where one exists, else 0 (no evidence -> assume not expressed).

Phase 1 is process-baseline only; the ML residual layer is zero until Season 2
paired (predicted, actual) data exists. Every prediction carries a
stage-dependent interval, per-factor attribution, and a data-quality figure so
the caller can be honest about confidence. Pure: stdlib only, no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Prediction interval (± percent) by prediction_stage - the CURRENT KB enum
# (D11-PR-001). When the G0-G5 stage model lands in the KB, remap here.
PREDICTION_INTERVAL_PCT: dict[str, float] = {
    "pre_season": 25.0,
    "g1_end": 22.0,
    "mid_season": 20.0,
    "pre_harvest_observation": 12.0,
    "pre_harvest_sampled": 8.0,
}
_DEFAULT_INTERVAL_PCT = 25.0

# Ceiling (quintal/acre) by basis - the KB ceiling_basis enum.
CEILING_QTL_PER_ACRE: dict[str, float] = {
    "variety_only_94": 94.0,
    "variety_plus_broad_ridge_113": 113.0,
    "unverified": 94.0,  # conservative fallback
}

MODEL_VERSION = "ginger-yield/v0.1-scaffold"

# Confidence rises as the season progresses and the crop is observable.
_CONFIDENCE_BY_STAGE: dict[str, float] = {
    "pre_season": 0.30,
    "g1_end": 0.45,
    "mid_season": 0.60,
    "pre_harvest_observation": 0.75,
    "pre_harvest_sampled": 0.90,
}


@dataclass(frozen=True, slots=True)
class UValue:
    """One row of the U-value register (from ``yield_u_values``)."""

    factor_key: str
    u_value: float
    signal_field: str | None
    representative_rule_id: str | None
    rank: int = 0


@dataclass(frozen=True, slots=True)
class FactorContribution:
    factor_key: str
    u_value: float
    intensity: float
    loss_pct: float  # u_i * I_i * 100
    rule_id: str | None


@dataclass(frozen=True, slots=True)
class YieldPrediction:
    ceiling_quintal_per_acre: float
    ceiling_basis: str
    predicted_yield_quintal_per_acre: float
    ci_low_quintal_per_acre: float
    ci_high_quintal_per_acre: float
    prediction_interval_pct: float
    cumulative_loss_pct: float
    gap_attributed_pct: float | None
    gap_unexplained_pct: float | None
    u_values_applied: list[str] = field(default_factory=list)
    attribution: list[FactorContribution] = field(default_factory=list)
    u_value_source_class: str = "EST"
    data_quality: float = 0.0
    confidence: float = 0.0
    model_version: str = MODEL_VERSION


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _intensity(signal_field: str | None, signals: dict[str, object]) -> tuple[float, bool]:
    """Map a wired signal to intensity in [0,1]. Returns (intensity, had_signal).

    Transparent Phase 1 transforms; refined per D11_YIELD_MODEL_v1.md (15 Oct).
    """
    if signal_field is None:
        return 0.0, False
    v = signals.get(signal_field)
    if v is None:
        return 0.0, False
    if signal_field == "nematode_suspected":
        return (0.5 if bool(v) else 0.0), True
    try:
        val = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0, False
    if signal_field == "establishment_pct":
        # Poor establishment = high intensity (80% = healthy baseline).
        return _clamp01((80.0 - val) / 80.0), True
    if signal_field == "standing_water_hours_observed":
        return _clamp01(val / 48.0), True  # 48h waterlogging = fully expressed
    if signal_field == "dry_spell_days":
        return _clamp01(val / 21.0), True
    if signal_field == "heat_stress_days_count":
        return _clamp01(val / 30.0), True
    if signal_field.endswith("_pct"):
        return _clamp01(val / 100.0), True
    return 0.0, False


def predict_yield(
    *,
    ceiling_basis: str,
    factors: list[UValue],
    signals: dict[str, object],
    prediction_stage: str | None,
    ceiling_override: float | None = None,
) -> YieldPrediction:
    """Run the process baseline for one plot at its current stage.

    ``ceiling_override`` (an entered ceiling_quintal_per_acre) wins over the
    basis default for the arithmetic; ``ceiling_basis`` still records the basis.
    """
    ceiling = (
        ceiling_override
        if ceiling_override is not None
        else CEILING_QTL_PER_ACRE.get(ceiling_basis, CEILING_QTL_PER_ACRE["unverified"])
    )

    surviving = 1.0
    contributions: list[FactorContribution] = []
    applied: list[str] = []
    signalled = 0
    for f in factors:
        intensity, had = _intensity(f.signal_field, signals)
        if had:
            signalled += 1
        if intensity > 0.0:
            surviving *= 1.0 - f.u_value * intensity
            contributions.append(
                FactorContribution(
                    factor_key=f.factor_key,
                    u_value=f.u_value,
                    intensity=round(intensity, 3),
                    loss_pct=round(f.u_value * intensity * 100.0, 2),
                    rule_id=f.representative_rule_id,
                )
            )
            if f.representative_rule_id:
                applied.append(f.representative_rule_id)

    predicted = ceiling * surviving
    cumulative_loss_pct = round((1.0 - surviving) * 100.0, 2)
    gap = ceiling - predicted

    # Explained gap = sum of individual losses for materially-expressed factors
    # (intensity > 0.2, per VJH §2). Clamp against the (product-based) gap.
    explained = sum(
        c.u_value * c.intensity * ceiling for c in contributions if c.intensity > 0.2
    )
    if gap > 1e-9:
        attributed = min(explained, gap)
        gap_attributed_pct: float | None = round(attributed / gap * 100.0, 1)
        gap_unexplained_pct: float | None = round((gap - attributed) / gap * 100.0, 1)
    else:
        gap_attributed_pct = None
        gap_unexplained_pct = None

    interval = PREDICTION_INTERVAL_PCT.get(prediction_stage or "", _DEFAULT_INTERVAL_PCT)
    ci_low = round(predicted * (1.0 - interval / 100.0), 1)
    ci_high = round(predicted * (1.0 + interval / 100.0), 1)

    data_quality = round(signalled / len(factors), 2) if factors else 0.0
    confidence = _CONFIDENCE_BY_STAGE.get(prediction_stage or "", 0.30)

    return YieldPrediction(
        ceiling_quintal_per_acre=round(ceiling, 1),
        ceiling_basis=ceiling_basis,
        predicted_yield_quintal_per_acre=round(predicted, 1),
        ci_low_quintal_per_acre=ci_low,
        ci_high_quintal_per_acre=ci_high,
        prediction_interval_pct=interval,
        cumulative_loss_pct=cumulative_loss_pct,
        gap_attributed_pct=gap_attributed_pct,
        gap_unexplained_pct=gap_unexplained_pct,
        u_values_applied=applied,
        attribution=contributions,
        u_value_source_class="EST",
        data_quality=data_quality,
        confidence=confidence,
    )


def ceiling_basis_for_layout(planting_layout: object) -> str:
    """Derive the KB ceiling_basis enum from the plot's planting layout."""
    if planting_layout is None:
        return "unverified"
    s = str(planting_layout).strip().lower()
    if any(k in s for k in ("broad", "ridge", "bed", "raised")):
        return "variety_plus_broad_ridge_113"
    return "variety_only_94"


__all__ = [
    "CEILING_QTL_PER_ACRE",
    "MODEL_VERSION",
    "PREDICTION_INTERVAL_PCT",
    "FactorContribution",
    "UValue",
    "YieldPrediction",
    "ceiling_basis_for_layout",
    "predict_yield",
]
