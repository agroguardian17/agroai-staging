"""IMD rainfall-normals loader (reference.imd_normals)."""

from __future__ import annotations

import pytest

from app.application.reference.imd_normals import (
    STATION_RAINFALL_NORMAL,
    load_normals,
    station_key,
)

# The confirmed Chikalthana anchor (AG-V2.0 §4); must be reproduced exactly.
_CHIKALTHANA_MONTHLY = [2.6, 2.2, 11.4, 6.0, 17.4, 155.6, 178.0, 171.5, 172.4, 68.2, 17.5, 8.9]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Aurangabad (Chikalthana)", "chikalthana"),
        ("Jalna", "jalna"),
        ("Ahmadnagar", "ahmadnagar"),
    ],
)
def test_station_key_slug(name: str, expected: str) -> None:
    assert station_key(name) == expected


def test_load_normals_has_all_stations_with_metadata() -> None:
    normals = load_normals()
    assert len(normals) == 11  # Chikalthana + 10 Marathwada/expansion stations
    for key, entry in normals.items():
        assert len(entry["monthly_mm"]) == 12, key
        assert entry["annual_mm"] > 0, key
        # Provenance must never be stripped.
        assert entry["source_institution"], key
        assert entry["verification_status"], key


def test_chikalthana_anchor_matches_confirmed_values() -> None:
    normals = load_normals()
    anchor = normals["chikalthana"]
    assert anchor["monthly_mm"] == _CHIKALTHANA_MONTHLY
    assert anchor["annual_mm"] == 811.7
    assert "CONFIRMED" in anchor["verification_status"]


def test_module_level_table_loaded() -> None:
    assert "chikalthana" in STATION_RAINFALL_NORMAL
    assert STATION_RAINFALL_NORMAL["chikalthana"]["annual_mm"] == 811.7
