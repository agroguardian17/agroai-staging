"""Port: D12 peer-cluster persistence (D12_QA_WORKFLOW §4.6, §5.3).

The ``assign_cluster`` use-case reads the active clusters and the config knobs
through this port, runs the pure gating algorithm
(:func:`app.domain.clustering.assign_cluster`), then hands the outcome back to
:meth:`ClusterRepo.persist_assignment`, which writes ``plot_cluster`` and
recomputes the affected ``clusters`` aggregates atomically. The mapper reads a
plot's assigned cluster via :meth:`cluster_id_for_plot`.

Concrete implementation: :class:`app.infra.persistence.pg_cluster_repo.PgClusterRepo`.
"""

from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.domain.clustering import ClusterCandidate, PlotForClustering


@runtime_checkable
class ClusterRepo(Protocol):
    async def load_config(self) -> dict[str, str]:
        """The ``cluster_config`` key/value knobs (variety_gate, proximity, ...)."""
        ...

    async def load_active(self, tenant_id: uuid.UUID) -> list[ClusterCandidate]:
        """Active clusters for the tenant, as gating candidates."""
        ...

    async def cluster_id_for_plot(self, plot_id: str) -> str | None:
        """The plot's assigned cluster id, or ``None`` if unassigned."""
        ...

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
        """Persist one assignment and recompute aggregates; return the final id.

        ``chosen_cluster_id is None`` spawns a new cluster (the id is minted
        here). Any prior membership for the plot is detached first, and a
        cluster left with no members is deleted. Runs in a single transaction.
        """
        ...


__all__ = ["ClusterRepo"]
