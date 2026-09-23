"""Postgres adapter for
:class:`~app.application.ports.cluster_repo.ClusterRepo`.

The cluster aggregate is derived state: after any membership change,
:meth:`persist_assignment` recomputes ``plot_count``, the centroid (member
mean), ``planting_week_median`` (``percentile_disc`` — an actual member week),
and ``baseline_active`` (>= ``min_plots_per_cluster``) from the ``plot_cluster``
rows, so ``clusters`` never drifts from its members. All writes for one
assignment share a single transaction.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncSession, async_sessionmaker

from app.domain.clustering import ClusterCandidate, PlotForClustering

_CONFIG_SQL = text("SELECT key, value FROM cluster_config")

_ACTIVE_SQL = text(
    """
    SELECT cluster_id, variety, planting_week_median, centroid_lat, centroid_lng, plot_count
    FROM clusters
    WHERE tenant_id = :tenant_id
    ORDER BY cluster_id
    """
)

_FOR_PLOT_SQL = text("SELECT cluster_id FROM plot_cluster WHERE plot_id = :plot_id")

_DETACH_SQL = text("DELETE FROM plot_cluster WHERE plot_id = :plot_id RETURNING cluster_id")

_SPAWN_SQL = text(
    """
    INSERT INTO clusters (
        cluster_id, tenant_id, variety, planting_week_median, centroid_lat, centroid_lng
    ) VALUES (
        :cluster_id, :tenant_id, :variety, :planting_week, :centroid_lat, :centroid_lng
    )
    """
)

_UPSERT_MEMBER_SQL = text(
    """
    INSERT INTO plot_cluster (
        plot_id, cluster_id, tenant_id, variety, planting_week,
        centroid_lat, centroid_lng, distance_km, fit_score, informational_only, assigned_at
    ) VALUES (
        :plot_id, :cluster_id, :tenant_id, :variety, :planting_week,
        :centroid_lat, :centroid_lng, :distance_km, :fit_score, :informational_only, now()
    )
    ON CONFLICT (plot_id) DO UPDATE SET
        cluster_id = EXCLUDED.cluster_id,
        tenant_id = EXCLUDED.tenant_id,
        variety = EXCLUDED.variety,
        planting_week = EXCLUDED.planting_week,
        centroid_lat = EXCLUDED.centroid_lat,
        centroid_lng = EXCLUDED.centroid_lng,
        distance_km = EXCLUDED.distance_km,
        fit_score = EXCLUDED.fit_score,
        informational_only = EXCLUDED.informational_only,
        assigned_at = now()
    """
)

# Recompute one cluster from its members; delete it when it has none left.
_RECOMPUTE_SQL = text(
    """
    UPDATE clusters c SET
        plot_count = m.n,
        centroid_lat = m.lat,
        centroid_lng = m.lng,
        planting_week_median = m.wk,
        baseline_active = (m.n >= :min_plots),
        updated_at = now()
    FROM (
        SELECT count(*) AS n,
               avg(centroid_lat) AS lat,
               avg(centroid_lng) AS lng,
               percentile_disc(0.5) WITHIN GROUP (ORDER BY planting_week) AS wk
        FROM plot_cluster WHERE cluster_id = :cluster_id
    ) m
    WHERE c.cluster_id = :cluster_id
    """
)

# Drop a cluster with no members left (checked against plot_cluster, not the
# possibly-stale plot_count). Must run BEFORE recompute: avg/percentile over an
# empty member set are NULL and would violate the NOT NULL centroid columns.
_DELETE_EMPTY_SQL = text(
    """
    DELETE FROM clusters c
    WHERE c.cluster_id = :cluster_id
      AND NOT EXISTS (SELECT 1 FROM plot_cluster p WHERE p.cluster_id = :cluster_id)
    """
)


def _mint_cluster_id() -> str:
    return f"CL-{uuid.uuid4().hex[:10]}"


class PgClusterRepo:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker

    async def load_config(self) -> dict[str, str]:
        async with self._sm() as session:
            res = await session.execute(_CONFIG_SQL)
            rows = res.all()
        return {r.key: r.value for r in rows}

    async def load_active(self, tenant_id: uuid.UUID) -> list[ClusterCandidate]:
        async with self._sm() as session:
            res = await session.execute(_ACTIVE_SQL, {"tenant_id": tenant_id})
            rows = res.all()
        out: list[ClusterCandidate] = []
        for r in rows:
            rr: Any = r
            out.append(
                ClusterCandidate(
                    cluster_id=rr.cluster_id,
                    variety=rr.variety,
                    planting_week_median=rr.planting_week_median,
                    centroid_lat=float(rr.centroid_lat),
                    centroid_lng=float(rr.centroid_lng),
                    plot_count=int(rr.plot_count),
                )
            )
        return out

    async def cluster_id_for_plot(self, plot_id: str) -> str | None:
        async with self._sm() as session:
            res = await session.execute(_FOR_PLOT_SQL, {"plot_id": plot_id})
            row = res.first()
        return row.cluster_id if row is not None else None

    async def persist_assignment(
        self,
        *,
        tenant_id: uuid.UUID,
        plot_id: str,
        plot: PlotForClustering,
        chosen_cluster_id: str | None,
        distance_km: float | None,
        fit_score: float,
        informational_only: bool,
    ) -> str:
        async with self._sm() as session, session.begin():
            conn = await session.connection()
            config = await self._min_plots(conn)

            # Detach any prior membership (re-run / variety change).
            detached = await conn.execute(_DETACH_SQL, {"plot_id": plot_id})
            prior = detached.scalar_one_or_none()

            if chosen_cluster_id is None:
                final_id = _mint_cluster_id()
                await conn.execute(
                    _SPAWN_SQL,
                    {
                        "cluster_id": final_id,
                        "tenant_id": tenant_id,
                        "variety": plot.variety,
                        "planting_week": plot.planting_week,
                        "centroid_lat": plot.centroid_lat,
                        "centroid_lng": plot.centroid_lng,
                    },
                )
            else:
                final_id = chosen_cluster_id

            await conn.execute(
                _UPSERT_MEMBER_SQL,
                {
                    "plot_id": plot_id,
                    "cluster_id": final_id,
                    "tenant_id": tenant_id,
                    "variety": plot.variety,
                    "planting_week": plot.planting_week,
                    "centroid_lat": plot.centroid_lat,
                    "centroid_lng": plot.centroid_lng,
                    "distance_km": distance_km,
                    "fit_score": fit_score,
                    "informational_only": informational_only,
                },
            )

            # Recompute the target cluster, and the old one if the plot moved.
            # Delete-empty runs first so an emptied prior cluster is dropped
            # rather than recomputed to NULL centroids.
            affected = {final_id}
            if prior is not None and prior != final_id:
                affected.add(prior)
            for cid in affected:
                await conn.execute(_DELETE_EMPTY_SQL, {"cluster_id": cid})
                await conn.execute(_RECOMPUTE_SQL, {"cluster_id": cid, "min_plots": config})

        return final_id

    async def _min_plots(self, conn: AsyncConnection) -> int:
        res = await conn.execute(_CONFIG_SQL)
        cfg = {r.key: r.value for r in res.all()}
        try:
            return int(cfg.get("min_plots_per_cluster", "8"))
        except ValueError:
            return 8


__all__ = ["PgClusterRepo"]
