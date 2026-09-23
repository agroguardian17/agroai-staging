"""D11 yield model v1 — pure math (site index, interdependence, bootstrap CI)."""

from __future__ import annotations

from app.domain.yield_forecast import (
    YieldFactor,
    bootstrap_ci,
    predict_yield_full,
    resolve_site_index,
    survival_factors,
)


def _f(fid: int, u: float, i: float, groups: tuple[str, ...] = ()) -> YieldFactor:
    return YieldFactor(factor_id=fid, factor_key=f"f{fid}", u_value=u, intensity=i, groups=groups)


# --- site index -------------------------------------------------------------


def test_resolve_site_index_multiplies_three_dimensions() -> None:
    config = {
        ("soil", "black_vertisol_with_drip_flat"): 0.85,
        ("water", "assured_source_year_round"): 1.00,
        ("climate", "marathwada_east"): 0.95,
    }
    si = resolve_site_index(
        config,
        soil_key="black_vertisol_with_drip_flat",
        water_key="assured_source_year_round",
        climate_key="marathwada_east",
    )
    assert abs(si - 0.85 * 1.00 * 0.95) < 1e-9


def test_resolve_site_index_falls_back_on_unknown_key() -> None:
    si = resolve_site_index(config={}, soil_key="x", water_key="y", climate_key="z")
    assert abs(si - 0.65 * 0.65 * 0.75) < 1e-9  # per-dimension defaults


# --- interdependence reduction ---------------------------------------------


def test_survival_factors_keeps_max_within_a_group() -> None:
    # Two factors in one group -> only the higher u*I enters the product.
    reduced = survival_factors(
        [
            _f(1, 0.60, 1.0, ("soft_rot_cluster",)),  # u*I = 0.60
            _f(2, 0.35, 1.0, ("soft_rot_cluster",)),  # u*I = 0.35
        ]
    )
    assert [f.factor_id for f in reduced] == [1]


def test_survival_factors_merges_overlapping_groups_into_one_cluster() -> None:
    # factor 2 shares a group with both 1/11 and 14 -> one connected cluster
    # {1,2,11,14}; only its single max-loss member survives.
    factors = [
        _f(1, 0.60, 1.0, ("soft_rot_cluster",)),
        _f(2, 0.35, 1.0, ("soft_rot_cluster", "drip_drainage_cluster")),
        _f(11, 0.08, 1.0, ("soft_rot_cluster",)),
        _f(14, 0.15, 1.0, ("drip_drainage_cluster",)),
        _f(4, 0.20, 1.0, ("n_k_antagonism",)),
        _f(8, 0.08, 1.0, ("n_k_antagonism",)),
        _f(9, 0.10, 1.0),  # ungrouped
    ]
    reduced_ids = sorted(f.factor_id for f in survival_factors(factors))
    # cluster {1,2,11,14} -> 1 (max 0.60); cluster {4,8} -> 4 (max 0.20); 9 alone.
    assert reduced_ids == [1, 4, 9]


# --- bootstrap CI -----------------------------------------------------------


def test_bootstrap_ci_deterministic_and_ordered() -> None:
    factors = [_f(1, 0.30, 0.5), _f(2, 0.20, 0.4)]
    a = bootstrap_ci(90.0, factors, seed=7)
    b = bootstrap_ci(90.0, factors, seed=7)
    assert a == b  # reproducible for a fixed seed
    lo, mid, hi = a
    assert lo <= mid <= hi
    assert 0.0 < lo < 90.0


def test_bootstrap_ci_no_factors_is_a_point() -> None:
    assert bootstrap_ci(90.0, [], seed=1) == (90.0, 90.0, 90.0)


# --- full forecast ----------------------------------------------------------


def test_predict_yield_full_no_loss_returns_potential() -> None:
    fc = predict_yield_full(y_potential=90.0, factors=[])
    assert fc.y_process == 90.0
    assert fc.y_point == 90.0
    assert (fc.y_low_90, fc.y_high_90) == (90.0, 90.0)
    assert fc.unexplained_quintal == 0.0


def test_predict_yield_full_single_factor_attribution() -> None:
    fc = predict_yield_full(y_potential=90.0, factors=[_f(3, 0.50, 1.0)])
    assert fc.y_process == 45.0  # 90 * (1 - 0.5)
    assert len(fc.attribution) == 1
    assert fc.attribution[0].loss_quintal == 45.0
    assert fc.attribution[0].in_survival_product is True
    assert fc.unexplained_quintal == 0.0  # fully explained


def test_predict_yield_full_reduces_grouped_factors_in_product() -> None:
    grouped = [
        _f(1, 0.60, 1.0, ("soft_rot_cluster",)),
        _f(2, 0.35, 1.0, ("soft_rot_cluster",)),
    ]
    fc = predict_yield_full(y_potential=100.0, factors=grouped)
    # Only the max (0.60) enters the product -> 100 * 0.40 = 40, not 100*0.4*0.65=26.
    assert fc.y_process == 40.0
    # Both factors still appear in attribution; the subsumed one flagged.
    flags = {a.factor_id: a.in_survival_product for a in fc.attribution}
    assert flags == {1: True, 2: False}


def test_predict_yield_full_passes_missing_factors() -> None:
    fc = predict_yield_full(y_potential=90.0, factors=[_f(1, 0.5, 0.4)], missing_factors=[6, 12])
    assert fc.missing_factors == [6, 12]
