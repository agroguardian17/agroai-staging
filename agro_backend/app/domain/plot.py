"""Plot domain model.


PURE module: stdlib only. No framework imports - enforced by the domain
purity test. Mirrors a small, application-relevant projection of the
``plots`` table.


Why a domain :class:`Plot` distinct from ``app.infra.persistence.models.farms.Plot``:


* The ORM model carries every column (15+ fields including storage-only
  bookkeeping like ``created_at``, ``crop_current_season_id`` FK, JSONB
  geometry). The application layer reasons about ~5 fields per plot.
* The ORM model imports SQLAlchemy. The domain :class:`Plot` does not.
  Application use cases that take a Plot parameter remain framework-free.
* The :class:`DataTier` discriminator drives routing in Phase 5
  (sensor-derived advisory vs. satellite-only fallback) - it is *the*
  domain concept; the trigger ``plots_set_data_tier`` (0004) is the
  storage-level enforcement.


When the repository (Phase 2 stage 2.5) loads a row from ``plots``, it
returns a domain :class:`Plot`; the ORM model never escapes the infra layer.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any


class DataTier(StrEnum):
    """Whether a plot has on-prem sensors or relies on satellite-only data.


    Value matches the CHECK constraint added by migration 0004 (and seeded
    by the ``plots_set_data_tier`` trigger that watches the ``node_id``
    column). The application layer reads this as the primary routing
    discriminator - never inspects ``node_id`` directly.
    """

    SUB_NODE = "sub_node"  # has a registered Sub Node (node_id is not null)
    SATELLITE_ONLY = "satellite_only"  # no node; depends on satellite imagery + Main Node weather


class PlotStatus(StrEnum):
    """Lifecycle state for a plot (``plots.plot_status``).


    Fallow plots still receive satellite-based health updates so we don't
    lose history across seasons; retired plots are read-only.
    """

    ACTIVE = "active"
    FALLOW = "fallow"
    RETIRED = "retired"


@dataclass(frozen=True, slots=True)
class Plot:
    """Application view of a row in the ``plots`` table.


    Carries the fields the application layer actually uses, including the
    GPS boundary GeoJSON (kept as a plain ``dict`` so the domain doesn't
    need shapely; geometry parsing happens at the infra boundary in Phase 6
    when satellite ingest needs ST_GeomFromGeoJSON).


    The ``node_id`` is preserved alongside ``data_tier`` because some
    diagnostic flows (Phase 12 calibration) need it; routing logic must
    still pivot on ``data_tier`` for forward-compatibility.
    """

    plot_id: str
    tenant_id: uuid.UUID
    farm_id: uuid.UUID
    plot_number: int
    area_acre: Decimal
    gps_lat: float
    gps_lng: float

    irrigation_valve_id: str
    data_tier: DataTier
    plot_status: PlotStatus

    plot_name: str | None = None
    node_id: str | None = None
    soil_type_override: str | None = None
    crop_current_season_id: uuid.UUID | None = None
    drip_line_count: int | None = None
    gps_boundary_geojson: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    def has_sensor(self) -> bool:
        """``True`` iff the plot has a registered Sub Node.


        Equivalent to ``data_tier == DataTier.SUB_NODE``; lives as a method
        so application code reads clearly: ``if plot.has_sensor(): ...``.
        """
        return self.data_tier is DataTier.SUB_NODE

    def is_active(self) -> bool:
        """``True`` for plots currently running a crop season."""
        return self.plot_status is PlotStatus.ACTIVE


__all__ = ["DataTier", "Plot", "PlotStatus"]
