"""Plot repository port.


Read/update operations against the ``plots`` table that the application
layer needs. Concrete implementation in Round 6
(``app.infra.persistence.pg_plot_repo.PgPlotRepo``).


The ``update_data_tier`` method exists for the technician-install flow
(Round 9), which transitions a plot from ``satellite_only`` to ``sub_node``
once a Sub Node is provisioned. The actual write happens via the
``node_id`` column - the BEFORE trigger ``plots_set_data_tier`` (migration
0004) keeps ``data_tier`` in sync. The application calls this method,
not the trigger directly.
"""


from __future__ import annotations

import uuid
from typing import Protocol, runtime_checkable

from app.domain.plot import DataTier, Plot


@runtime_checkable
class PlotRepo(Protocol):
    """Operations the read API + crop-change wizard + technician flows need."""


    async def find(self, plot_id: str) -> Plot | None:
        """Look up one plot by its TEXT primary key. ``None`` if not found.


        Used by every endpoint that takes a ``plot_id`` path parameter
        and by the ingest pipeline when it needs to attach ``tenant_id``
        for RLS session context.
        """
        ...


    async def for_farmer(self, farmer_id: uuid.UUID) -> list[Plot]:
        """All active+fallow plots a farmer owns, ordered by ``plot_number``.


        Retired plots are filtered out (the dashboard shows them via a
        separate query when explicitly requested).
        """
        ...


    async def for_tenant(self, tenant_id: uuid.UUID) -> list[Plot]:
        """Every plot for a tenant (admin/agronomist scope).


        Returns ALL statuses including retired - the dashboard's
        "Operations" view shows them and filters client-side.
        """
        ...


    async def update_data_tier(self, plot_id: str, tier: DataTier) -> None:
        """Transition a plot's data tier.


        The implementation MUST update ``node_id`` (the trigger keeps
        ``data_tier`` in sync) rather than writing ``data_tier``
        directly - the column has a server default and the trigger is
        authoritative. Going ``satellite_only -> sub_node`` requires a
        ``node_id`` argument; the application layer is responsible for
        looking up the right device before calling this. (We do not
        re-shape this port until that flow lands in Round 9.)
        """
        ...




__all__ = ["PlotRepo"]
