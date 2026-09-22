"""Unit tests for the pure Domain 11 yield model."""

from __future__ import annotations

from app.domain.yield_model import (
    CEILING_QTL_PER_ACRE,
    UValue,
    ceiling_basis_for_layout,
    predict_yield,
)

_ROT = UValue(
    factor_key="soft_rot",
    u_value=0.60,
    signal_field="rot_incidence_pct",
    representative_rule_id="D06-ROT-001",
    rank=1,
)
_WILT = UValue(
    factor_key="bacterial_wilt",
    u_value=0.50,
    signal_field="wilt_incidence_pct",
    representative_rule_id="D06-WILT-001",
    rank=3,
)


def test_no_signals_predicts_the_ceiling_with_no_loss() -> None:
    p = predict_yield(
        ceiling_basis="variety_only_94",
        factors=[_ROT, _WILT],
        signals={},
        prediction_stage="G2",
    )
    assert p.ceiling_quintal_per_acre == 94.0
    assert p.predicted_yield_quintal_per_acre == 94.0
    assert p.cumulative_loss_pct == 0.0
    # No gap -> attribution undefined (UNKNOWN), not a fabricated 0.
    assert p.gap_attributed_pct is None
    assert p.gap_unexplained_pct is None
    assert p.u_values_applied == []
    assert p.prediction_interval_pct == 20.0  # G2
    assert p.data_quality == 0.0  # neither signal present


def test_rot_signal_applies_its_u_value() -> None:
    p = predict_yield(
        ceiling_basis="variety_only_94",
        factors=[_ROT, _WILT],
        signals={"rot_incidence_pct": 50.0},
        prediction_stage="G1",
    )
    # intensity 0.5, u 0.60 -> surviving 0.70 -> 65.8 qtl/acre
    assert p.predicted_yield_quintal_per_acre == 65.8
    assert p.cumulative_loss_pct == 30.0
    assert "D06-ROT-001" in p.u_values_applied
    assert p.gap_attributed_pct is not None
    assert p.prediction_interval_pct == 22.0  # G1
    assert 0 < p.data_quality <= 1.0


def test_broad_ridge_layout_raises_the_ceiling() -> None:
    assert ceiling_basis_for_layout("broad ridge") == "variety_plus_broad_ridge_113"
    assert ceiling_basis_for_layout("flat") == "variety_only_94"
    assert ceiling_basis_for_layout(None) == "unverified"
    p = predict_yield(
        ceiling_basis="variety_plus_broad_ridge_113",
        factors=[_ROT],
        signals={},
        prediction_stage="G0",
    )
    assert p.ceiling_quintal_per_acre == CEILING_QTL_PER_ACRE["variety_plus_broad_ridge_113"]
    assert p.prediction_interval_pct == 25.0  # G0


def test_ceiling_override_wins_for_arithmetic() -> None:
    p = predict_yield(
        ceiling_basis="variety_only_94",
        factors=[_ROT],
        signals={"rot_incidence_pct": 100.0},
        prediction_stage="G2",
        ceiling_override=100.0,
    )
    # full rot intensity, u 0.60 -> surviving 0.40 -> 40.0
    assert p.ceiling_quintal_per_acre == 100.0
    assert p.predicted_yield_quintal_per_acre == 40.0
