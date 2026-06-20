"""Postgres adapter for :class:`~app.application.ports.plot_repo.PlotRepo`.


Reads and writes against the ``plots`` table. The application-facing
:class:`~app.domain.plot.Plot` is a *projection* of that table (Round 3
SCHEMA_DECISIONS): we only carry the fields the application reasons about,
not every column the schema stores.


``update_data_tier`` writes the ``node_id`` column - never ``data_tier``
directly. The BEFORE trigger ``plots_set_data_tier`` (migration 0004) keeps
``data_tier`` in lock-step with ``node_id``. The application calls this
method; the trigger is the source of truth for the enum.
"""


from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.plot import DataTier, Plot, PlotStatus

_SELECT_COLUMNS = (
    "plot_id, tenant_id, farm_id, plot_number, area_acre, gps_lat, gps_lng, "
    "gps_boundary_geojson, node_id, soil_type_override, crop_current_season_id, "
    "drip_line_count, plot_status, plot_name, data_tier"
)




def _row_to_plot(row: Any) -> Plot:
    return Plot(
        plot_id=row.plot_id,
        tenant_id=row.tenant_id,
        farm_id=row.farm_id,
        plot_number=row.plot_number,
        area_acre=Decimal(str(row.area_acre)),
        gps_lat=float(row.gps_lat),
        gps_lng=float(row.gps_lng),
        irrigation_valve_id=_resolve_valve_id(row),
        data_tier=DataTier(row.data_tier),
        plot_status=PlotStatus(row.plot_status),
        plot_name=row.plot_name,
        node_id=row.node_id,
        soil_type_override=row.soil_type_override,
        crop_current_season_id=row.crop_current_season_id,
        drip_line_count=row.drip_line_count,
        gps_boundary_geojson=dict(row.gps_boundary_geojson) if row.gps_boundary_geojson else None,
    )




def _resolve_valve_id(row: Any) -> str:
    """``irrigation_valve_id`` is non-null in the schema but Plot dataclass
    requires it. If a future seed leaves it null somehow, default to empty
    string - the domain treats empty as "unassigned" without crashing.
    Selecting it explicitly when present:
    """
    return getattr(row, "irrigation_valve_id", None) or ""




class PgPlotRepo:
    """Concrete :class:`PlotRepo` against Postgres."""


    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sm = sessionmaker


    # ------------------------------------------------------------------
    async def find(self, plot_id: str) -> Plot | None:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS}, irrigation_valve_id FROM plots WHERE plot_id = :plot_id"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"plot_id": plot_id})
            row = res.first()
        return None if row is None else _row_to_plot(row)


    # ------------------------------------------------------------------
    async def for_farmer(self, farmer_id: uuid.UUID) -> list[Plot]:
        # Plots don't carry farmer_id directly; we resolve via the farm
        # to which they belong (farms.farmer_id is the owner).
        # Filter out retired plots per the Protocol docstring.
        stmt = text(
            "SELECT p.plot_id, p.tenant_id, p.farm_id, p.plot_number, p.area_acre, "
            "p.gps_lat, p.gps_lng, p.gps_boundary_geojson, p.node_id, "
            "p.soil_type_override, p.crop_current_season_id, p.drip_line_count, "
            "p.plot_status, p.plot_name, p.data_tier, p.irrigation_valve_id "
            "FROM plots p "
            "JOIN farms f ON f.farm_id = p.farm_id "
            "WHERE f.farmer_id = :farmer_id AND p.plot_status != 'retired' "
            "ORDER BY p.plot_number ASC"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"farmer_id": farmer_id})
            return [_row_to_plot(r) for r in res.all()]


    # ------------------------------------------------------------------
    async def for_tenant(self, tenant_id: uuid.UUID) -> list[Plot]:
        stmt = text(
            f"SELECT {_SELECT_COLUMNS}, irrigation_valve_id FROM plots "
            "WHERE tenant_id = :tenant_id "
            "ORDER BY plot_id ASC"
        )
        async with self._sm() as session:
            res = await session.execute(stmt, {"tenant_id": tenant_id})
            return [_row_to_plot(r) for r in res.all()]


    # ------------------------------------------------------------------
    async def update_data_tier(self, plot_id: str, tier: DataTier) -> None:
        # The trigger plots_set_data_tier (0004) derives data_tier from
        # node_id. We never write data_tier directly here. Moving to
        # SUB_NODE requires a registered node_id, which the application
        # layer is responsible for resolving BEFORE calling this method
        # (see PlotRepo.update_data_tier docstring in Round 4).
        #
        # For SATELLITE_ONLY -> NULL the node_id, and the trigger sets
        # data_tier='satellite_only'. For SUB_NODE we'd need an actual
        # device_id; for now we only support the satellite_only path
        # here and raise on the sub_node path so a future caller can't
        # accidentally clear data without context. Round 9 wires the
        # full SUB_NODE registration flow.
        if tier is DataTier.SUB_NODE:
            raise NotImplementedError(
                "update_data_tier -> SUB_NODE requires a node_id argument; "
                "wire the technician-install flow in Round 9"
            )
        stmt = text("UPDATE plots SET node_id = NULL WHERE plot_id = :plot_id")
        async with self._sm() as session:
            await session.execute(stmt, {"plot_id": plot_id})
            await session.commit()




__all__ = ["PgPlotRepo"]
