"""Port: Domain 11 yield-model persistence.

Reads the U-value register (``yield_u_values``), the variety ceilings
(``variety_potential``) and the site-index heuristic (``site_index_config``) that
the v1 yield model runs on, and appends each prediction to
``yield_prediction_log`` for later model-vs-actual evaluation.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class UValueRow:
    factor_key: str
    rank: int
    u_value: float
    signal_field: str | None
    representative_rule_id: str | None
    factor_id: int | None = None
    interdependence_group: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class VarietyPotential:
    variety: str
    y_var_q_per_acre: float
    verification_status: str


@dataclass(frozen=True, slots=True)
class YieldPredictionLog:
    tenant_id: uuid.UUID
    season_id: uuid.UUID
    plot_id: str | None
    prediction_date: date
    dap: int | None
    prediction_stage: str | None
    ceiling_quintal_per_acre: float | None
    ceiling_basis: str | None
    predicted_yield_quintal_per_acre: float | None
    ci_low_quintal_per_acre: float | None
    ci_high_quintal_per_acre: float | None
    prediction_interval_pct: float | None
    cumulative_loss_pct: float | None
    gap_attributed_pct: float | None
    gap_unexplained_pct: float | None
    u_values_applied: list[str]
    attribution: list[dict[str, Any]]
    u_value_source_class: str
    model_version: str
    data_quality: float | None
    confidence: float | None
    # v1 model columns (migration 0040).
    y_potential: float | None = None
    y_process: float | None = None
    epsilon_ml: float | None = None
    y_point: float | None = None
    y_low_90: float | None = None
    y_high_90: float | None = None
    unexplained_pct: float | None = None
    missing_factors: list[int] = field(default_factory=list)
    as_of_date: date | None = None


@runtime_checkable
class YieldModelRepo(Protocol):
    async def list_u_values(self, crop: str = "Ginger") -> list[UValueRow]:
        """Active U-value register rows for the crop, ordered by rank."""
        ...

    async def get_variety_potential(self, variety: str) -> VarietyPotential | None:
        """The variety ceiling (Y_var) row, matched loosely on the variety name."""
        ...

    async def list_site_index_config(self) -> dict[tuple[str, str], float]:
        """The whole site-index heuristic as {(dimension, key): multiplier}."""
        ...

    async def log_prediction(self, row: YieldPredictionLog) -> None:
        """Append one prediction to the log."""
        ...


__all__ = ["UValueRow", "VarietyPotential", "YieldModelRepo", "YieldPredictionLog"]
