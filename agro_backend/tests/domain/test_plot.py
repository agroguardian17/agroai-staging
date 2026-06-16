"""Tests for ``app.domain.plot``.


Verifies dataclass behavior, enum/schema parity, and routing helpers.
"""

from __future__ import annotations

import dataclasses
import uuid
from decimal import Decimal

import pytest

from app.domain.plot import DataTier, Plot, PlotStatus

_TENANT = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
_FARM = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")


def _make(
    *,
    data_tier: DataTier = DataTier.SUB_NODE,
    status: PlotStatus = PlotStatus.ACTIVE,
    node_id: str | None = "AGR-MH-0001",
) -> Plot:
    return Plot(
        plot_id="PLOT_AUR_001_Z1",
        tenant_id=_TENANT,
        farm_id=_FARM,
        plot_number=1,
        area_acre=Decimal("2.5"),
        gps_lat=19.876543,
        gps_lng=75.342110,
        irrigation_valve_id="VALVE_AUR_001_Z1",
        data_tier=data_tier,
        plot_status=status,
        node_id=node_id,
    )


def test_plot_constructs_with_required_fields() -> None:
    p = _make()
    assert p.plot_id == "PLOT_AUR_001_Z1"
    assert p.area_acre == Decimal("2.5")
    assert p.gps_boundary_geojson is None


def test_plot_is_frozen() -> None:
    p = _make()
    with pytest.raises(dataclasses.FrozenInstanceError):
        p.area_acre = Decimal("3.0")  # type: ignore[misc]


def test_has_sensor_true_for_sub_node_tier() -> None:
    assert _make(data_tier=DataTier.SUB_NODE).has_sensor() is True


def test_has_sensor_false_for_satellite_only() -> None:
    assert _make(data_tier=DataTier.SATELLITE_ONLY, node_id=None).has_sensor() is False


def test_is_active_routes_on_status() -> None:
    assert _make(status=PlotStatus.ACTIVE).is_active() is True
    assert _make(status=PlotStatus.FALLOW).is_active() is False
    assert _make(status=PlotStatus.RETIRED).is_active() is False


def test_data_tier_values_match_schema() -> None:
    # Must match the CHECK in migration 0004 EXACTLY.
    expected = {"sub_node", "satellite_only"}
    assert {t.value for t in DataTier} == expected


def test_plot_status_values_match_schema() -> None:
    # Default in 0001: 'active'. Other documented states: fallow, retired.
    # If the schema CHECK ever differs from this set, the migration is the
    # source of truth and this assertion needs updating.
    expected = {"active", "fallow", "retired"}
    assert {s.value for s in PlotStatus} == expected


def test_gps_boundary_geojson_is_plain_dict() -> None:
    # Domain layer must NOT import shapely; GeoJSON stays as a dict here.
    poly = {
        "type": "Polygon",
        "coordinates": [[[75.0, 19.8], [75.1, 19.8], [75.1, 19.9], [75.0, 19.9], [75.0, 19.8]]],
    }
    p = dataclasses.replace(_make(), gps_boundary_geojson=poly)
    assert p.gps_boundary_geojson is poly  # by reference; no copy required
    assert isinstance(p.gps_boundary_geojson, dict)
