"""Postgres adapter for
:class:`~app.application.ports.yield_model_repo.YieldModelRepo`."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.application.ports.yield_model_repo import (
    UValueRow,
    VarietyPotential,
    YieldPredictionLog,
)

_LIST_SQL = text(
    """
    SELECT factor_key, rank, u_value, signal_field, representative_rule_id,
           factor_id, interdependence_group
    FROM yield_u_values
    WHERE crop = :crop AND active IS TRUE
    ORDER BY rank ASC
    """
)

# Loose variety match: the season stores e.g. "Mahima" while the register keys
# read "IISR Mahima"; match on either containing the other, shortest name first.
_VARIETY_SQL = text(
    """
    SELECT variety, y_var_q_per_acre, verification_status
    FROM variety_potential
    WHERE variety ILIKE ('%' || :variety || '%') OR :variety ILIKE ('%' || variety || '%')
    ORDER BY length(variety) ASC
    LIMIT 1
    """
)

_SITE_INDEX_SQL = text("SELECT dimension, key, value FROM site_index_config")

_INSERT_SQL = text(
    """
    INSERT INTO yield_prediction_log (
        tenant_id, season_id, plot_id, prediction_date, dap, prediction_stage,
        ceiling_quintal_per_acre, ceiling_basis, predicted_yield_quintal_per_acre,
        ci_low_quintal_per_acre, ci_high_quintal_per_acre, prediction_interval_pct,
        cumulative_loss_pct, gap_attributed_pct, gap_unexplained_pct,
        u_values_applied, attribution, u_value_source_class, model_version,
        data_quality, confidence,
        y_potential, y_process, epsilon_ml, y_point, y_low_90, y_high_90,
        unexplained_pct, missing_factors, as_of_date
    ) VALUES (
        :tenant_id, :season_id, :plot_id, :prediction_date, :dap, :prediction_stage,
        :ceiling, :ceiling_basis, :predicted,
        :ci_low, :ci_high, :interval_pct,
        :cumulative_loss_pct, :gap_attributed_pct, :gap_unexplained_pct,
        CAST(:u_values_applied AS JSONB), CAST(:attribution AS JSONB),
        :u_value_source_class, :model_version, :data_quality, :confidence,
        :y_potential, :y_process, :epsilon_ml, :y_point, :y_low_90, :y_high_90,
        :unexplained_pct, :missing_factors, :as_of_date
    )
    """
)


class PgYieldModelRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def list_u_values(self, crop: str = "Ginger") -> list[UValueRow]:
        async with self._sm() as session:
            res = await session.execute(_LIST_SQL, {"crop": crop})
            rows = res.all()
        out: list[UValueRow] = []
        for r in rows:
            rr: Any = r
            out.append(
                UValueRow(
                    factor_key=rr.factor_key,
                    rank=int(rr.rank),
                    u_value=float(rr.u_value),
                    signal_field=rr.signal_field,
                    representative_rule_id=rr.representative_rule_id,
                    factor_id=int(rr.factor_id) if rr.factor_id is not None else None,
                    interdependence_group=tuple(rr.interdependence_group or ()),
                )
            )
        return out

    async def get_variety_potential(self, variety: str) -> VarietyPotential | None:
        async with self._sm() as session:
            res = await session.execute(_VARIETY_SQL, {"variety": variety})
            row = res.first()
        if row is None:
            return None
        rr: Any = row
        return VarietyPotential(
            variety=rr.variety,
            y_var_q_per_acre=float(rr.y_var_q_per_acre),
            verification_status=rr.verification_status,
        )

    async def list_site_index_config(self) -> dict[tuple[str, str], float]:
        async with self._sm() as session:
            res = await session.execute(_SITE_INDEX_SQL)
            rows = res.all()
        out: dict[tuple[str, str], float] = {}
        for r in rows:
            rr: Any = r
            out[(rr.dimension, rr.key)] = float(rr.value)
        return out

    async def log_prediction(self, row: YieldPredictionLog) -> None:
        params = {
            "tenant_id": row.tenant_id,
            "season_id": row.season_id,
            "plot_id": row.plot_id,
            "prediction_date": row.prediction_date,
            "dap": row.dap,
            "prediction_stage": row.prediction_stage,
            "ceiling": row.ceiling_quintal_per_acre,
            "ceiling_basis": row.ceiling_basis,
            "predicted": row.predicted_yield_quintal_per_acre,
            "ci_low": row.ci_low_quintal_per_acre,
            "ci_high": row.ci_high_quintal_per_acre,
            "interval_pct": row.prediction_interval_pct,
            "cumulative_loss_pct": row.cumulative_loss_pct,
            "gap_attributed_pct": row.gap_attributed_pct,
            "gap_unexplained_pct": row.gap_unexplained_pct,
            "u_values_applied": json.dumps(row.u_values_applied),
            "attribution": json.dumps(row.attribution),
            "u_value_source_class": row.u_value_source_class,
            "model_version": row.model_version,
            "data_quality": row.data_quality,
            "confidence": row.confidence,
            "y_potential": row.y_potential,
            "y_process": row.y_process,
            "epsilon_ml": row.epsilon_ml,
            "y_point": row.y_point,
            "y_low_90": row.y_low_90,
            "y_high_90": row.y_high_90,
            "unexplained_pct": row.unexplained_pct,
            "missing_factors": row.missing_factors,
            "as_of_date": row.as_of_date,
        }
        async with self._sm() as session:
            await session.execute(_INSERT_SQL, params)
            await session.commit()


__all__ = ["PgYieldModelRepo"]
