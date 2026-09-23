"""Domain 11 yield model v1 - the D11_YIELD_MODEL_v1 spec math (pure).

The 0.1 scaffold in ``yield_model.py`` used a layout-based ceiling (94/113) and a
fixed +/- interval. This module implements the spec's richer model as pure,
deterministic functions the application layer composes (§3-§5):

    Y_potential = Y_var x SI                       (variety ceiling x site index)
    Y_process   = Y_potential x PROD(1 - u_i I_i)  (over interdependence-reduced factors)
    Y_final     = Y_process + epsilon_ml           (epsilon_ml = 0 in Season 1)
    (low, point, high) = bootstrap_ci(...)          (1000 Monte-Carlo draws, §4)

Interdependence groups (§3.3) overlap - factor 2 is in {1,2,11} and {2,14} - so
"apply the group's max, not the sum" is generalised to **connected components**:
factors sharing any group name form one cluster, and only the cluster's
max-loss (u_i x I_i) member enters the survival product. That avoids
double-counting a linked causal chain without dropping a factor twice.

Attribution follows §5 step 11: each factor's marginal loss is Y_potential x u_i
x I_i (uncompounded); explained = sum capped at the gap; the remainder is
unexplained. Pure: stdlib only (``random`` seeded for reproducible CIs).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

# Per-dimension fallback multipliers when a plot's key is not in site_index_config
# (mirrors the spec's 'other' / 'outside_marathwada' catch-alls).
SITE_INDEX_DEFAULTS: dict[str, float] = {"soil": 0.65, "water": 0.65, "climate": 0.75}

# Bootstrap parameters (§4).
_U_CV = 0.4  # 40% coefficient of variation on EST u_i
_I_SD = 0.1  # +/-0.1 measurement noise on I_i
_DRAWS = 1000


@dataclass(frozen=True, slots=True)
class YieldFactor:
    """One factor at its measured intensity this season."""

    factor_id: int
    factor_key: str
    u_value: float
    intensity: float  # I_i in [0, 1]
    groups: tuple[str, ...] = ()  # interdependence-group memberships
    rule_id: str | None = None


@dataclass(frozen=True, slots=True)
class FactorLoss:
    factor_id: int
    factor_key: str
    loss_quintal: float  # marginal Y_potential * u_i * I_i
    u_value: float
    intensity: float
    in_survival_product: bool  # False when subsumed by its cluster's representative


@dataclass(frozen=True, slots=True)
class YieldForecast:
    y_potential: float
    y_process: float
    epsilon_ml: float
    y_point: float
    y_low_90: float
    y_high_90: float
    attribution: list[FactorLoss] = field(default_factory=list)
    unexplained_quintal: float = 0.0
    unexplained_pct: float = 0.0
    missing_factors: list[int] = field(default_factory=list)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def resolve_site_index(
    config: Mapping[tuple[str, str], float],
    *,
    soil_key: str,
    water_key: str,
    climate_key: str,
) -> float:
    """SI = SI_soil x SI_water x SI_climate from site_index_config (§3.2).

    A key absent from the config falls back to that dimension's catch-all.
    """
    si_soil = config.get(("soil", soil_key), SITE_INDEX_DEFAULTS["soil"])
    si_water = config.get(("water", water_key), SITE_INDEX_DEFAULTS["water"])
    si_climate = config.get(("climate", climate_key), SITE_INDEX_DEFAULTS["climate"])
    return si_soil * si_water * si_climate


def _components(factors: Sequence[YieldFactor]) -> list[list[int]]:
    """Connected components of factor indices linked by a shared group name."""
    parent = list(range(len(factors)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    # Link every pair of factors that share at least one group name.
    by_group: dict[str, list[int]] = {}
    for i, f in enumerate(factors):
        for g in f.groups:
            by_group.setdefault(g, []).append(i)
    for members in by_group.values():
        for i in members[1:]:
            union(members[0], i)

    comps: dict[int, list[int]] = {}
    for i in range(len(factors)):
        comps.setdefault(find(i), []).append(i)
    return list(comps.values())


def survival_factors(factors: Sequence[YieldFactor]) -> list[YieldFactor]:
    """Factors that enter PROD(1 - u_i I_i): one representative (max u_i*I_i) per
    connected interdependence cluster; every ungrouped factor as itself."""
    reps: list[YieldFactor] = []
    for comp in _components(factors):
        rep = max((factors[i] for i in comp), key=lambda f: f.u_value * f.intensity)
        reps.append(rep)
    return reps


def bootstrap_ci(
    y_potential: float,
    factors: Sequence[YieldFactor],
    *,
    draws: int = _DRAWS,
    seed: int = 0,
) -> tuple[float, float, float]:
    """(y_low_90, y_point, y_high_90) by Monte-Carlo over u_i / I_i uncertainty (§4).

    Deterministic for a given seed so predictions are reproducible and testable.
    ``factors`` should already be interdependence-reduced (survival_factors).
    """
    if not factors:
        return (y_potential, y_potential, y_potential)
    rng = random.Random(seed)
    draws_out: list[float] = []
    for _ in range(draws):
        surviving = 1.0
        for f in factors:
            u_draw = _clamp01(rng.gauss(f.u_value, f.u_value * _U_CV))
            i_draw = _clamp01(rng.gauss(f.intensity, _I_SD))
            surviving *= 1.0 - u_draw * i_draw
        draws_out.append(y_potential * surviving)
    draws_out.sort()
    lo = draws_out[int(0.05 * (draws - 1))]
    hi = draws_out[int(0.95 * (draws - 1))]
    mid = draws_out[draws // 2]
    return (round(lo, 1), round(mid, 1), round(hi, 1))


def predict_yield_full(
    *,
    y_potential: float,
    factors: Sequence[YieldFactor],
    missing_factors: Sequence[int] = (),
    epsilon_ml: float = 0.0,
    draws: int = _DRAWS,
    seed: int = 0,
) -> YieldForecast:
    """Compose the spec pipeline (§5) into a forecast. Pure and deterministic.

    ``factors`` are the factors with a measured intensity > 0; ``missing_factors``
    are factor_ids whose intensity could not be measured (flagged, not applied).
    """
    reduced = survival_factors(factors)
    surviving = 1.0
    for f in reduced:
        surviving *= 1.0 - f.u_value * f.intensity
    y_process = y_potential * surviving
    y_point_base = y_process + epsilon_ml

    lo, mid, hi = bootstrap_ci(y_potential, reduced, draws=draws, seed=seed)
    # Recentre the bootstrap band on the point estimate (bootstrap median tracks
    # y_process; epsilon_ml shifts the point in Season 2+).
    shift = y_point_base - mid
    y_low = round(lo + shift, 1)
    y_high = round(hi + shift, 1)

    gap = y_potential - y_process
    reps = {id(f) for f in reduced}
    attribution: list[FactorLoss] = [
        FactorLoss(
            factor_id=f.factor_id,
            factor_key=f.factor_key,
            loss_quintal=round(y_potential * f.u_value * f.intensity, 2),
            u_value=f.u_value,
            intensity=round(f.intensity, 3),
            in_survival_product=id(f) in reps,
        )
        for f in factors
    ]
    explained = min(sum(a.loss_quintal for a in attribution), gap) if gap > 1e-9 else 0.0
    unexplained = max(0.0, gap - explained)
    unexplained_pct = round(unexplained / gap * 100.0, 1) if gap > 1e-9 else 0.0

    return YieldForecast(
        y_potential=round(y_potential, 2),
        y_process=round(y_process, 2),
        epsilon_ml=round(epsilon_ml, 2),
        y_point=round(y_point_base, 1),
        y_low_90=y_low,
        y_high_90=y_high,
        attribution=attribution,
        unexplained_quintal=round(unexplained, 2),
        unexplained_pct=unexplained_pct,
        missing_factors=list(missing_factors),
    )


__all__ = [
    "SITE_INDEX_DEFAULTS",
    "FactorLoss",
    "YieldFactor",
    "YieldForecast",
    "bootstrap_ci",
    "predict_yield_full",
    "resolve_site_index",
    "survival_factors",
]
