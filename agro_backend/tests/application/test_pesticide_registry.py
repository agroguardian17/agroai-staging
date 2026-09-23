"""Pesticide registry loader + the mapper blocklist gate it feeds."""

from __future__ import annotations

import datetime

import pytest

from app.application.build_farm_brain import (
    _blocklisted_spray_inputs,
    _phi_days_remaining,
)
from app.application.reference.pesticide_registry import (
    CROP_INPUT_BLOCKLIST,
    PHI_DAYS_BY_GROUP,
    load_registry,
    parse_phi_days,
)

# The 9 molecules that must refuse a PHI and surface a block (registry v1.1).
_BLOCKED = {
    "streptocycline",
    "chlorpyriphos",
    "monocrotophos",
    "phorate",
    "endosulfan",
    "bhc_lindane",
    "carbofuran",
    "methyl_parathion",
    "glyphosate_post_emergence_ginger",
}


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("15-21", 21),
        ("30-40", 40),
        ("30+ (pre-plant only)", 30),
        ("15", 15),
        ("0", 0),
        ("", None),
        (None, None),
        ("N/A — BANNED", None),
    ],
)
def test_parse_phi_days_takes_largest_integer(raw: str | None, expected: int | None) -> None:
    assert parse_phi_days(raw) == expected


def test_registry_loads_all_blocklist_molecules() -> None:
    _, blocklist = load_registry()
    assert _BLOCKED.issubset(blocklist.keys())
    # Every blocklist entry carries a reason + a source_ref for the farmer alert.
    for group in _BLOCKED:
        assert blocklist[group]["reason"]
        assert blocklist[group]["source_ref"]


def test_registry_phi_values_are_vnmkv_corrected() -> None:
    phi, blocklist = load_registry()
    # VNMKV-corrected upper bounds (registry v1.1).
    assert phi["mancozeb"] == 21
    assert phi["copper_oxychloride"] == 15
    assert phi["metalaxyl_m"] == 30
    assert phi["imidacloprid"] == 40
    # Biologicals carry a zero PHI, not the conservative default.
    assert phi["trichoderma_harzianum"] == 0
    # Blocklisted molecules never appear in the PHI table.
    assert _BLOCKED.isdisjoint(phi.keys())


def test_module_level_maps_are_populated() -> None:
    assert "streptocycline" in CROP_INPUT_BLOCKLIST
    assert "chlorpyriphos" in CROP_INPUT_BLOCKLIST
    assert PHI_DAYS_BY_GROUP.get("mancozeb") == 21


def test_mapper_blocklist_gate_flags_streptocycline() -> None:
    # The 2024 streptocycline ban must now be caught by the gate (case-insensitive).
    hits = _blocklisted_spray_inputs({"last_insecticide_group": "Streptocycline"})
    assert "streptocycline" in hits
    assert hits["streptocycline"]["reason"]


def test_phi_remaining_skips_blocklisted_and_defaults_unknown() -> None:
    today = datetime.date(2026, 9, 1)
    # A blocklisted spray yields no PHI number (handled by the block gate instead).
    only_blocked = {
        "last_insecticide_group": "streptocycline",
        "last_insecticide_date": datetime.date(2026, 8, 30),
    }
    assert _phi_days_remaining(only_blocked, today) is None
    # An unknown group falls through to the conservative 21-day default.
    unknown = {
        "last_fungicide_group": "some_unlisted_group",
        "last_fungicide_date": datetime.date(2026, 8, 30),
    }
    assert _phi_days_remaining(unknown, today) == 21 - 2
