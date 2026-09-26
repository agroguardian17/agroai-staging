"""Validate the registered_herbicide_registry seed (migration 0053)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine

from .conftest import DB_SKIP_REASON, db_available

pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)

_HARD_BLOCK_TIERS = {
    "L1_crop_damage_block",
    "L1_nonselective_block",
    "L1_not_for_ginger_block",
}


def test_registry_seeded_with_13_entries(sync_engine: Engine) -> None:
    with sync_engine.begin() as conn:
        count = conn.execute(
            text("SELECT count(*) FROM registered_herbicide_registry")
        ).scalar_one()
    assert count == 13


def test_compliance_tiers_present(sync_engine: Engine) -> None:
    with sync_engine.begin() as conn:
        tiers = {
            r.compliance_tier
            for r in conn.execute(
                text("SELECT DISTINCT compliance_tier FROM registered_herbicide_registry")
            ).all()
        }
    # All six tiers from the D08-WD-001 taxonomy are represented.
    assert {
        "L1_recommended_practice",
        "L1_crop_damage_block",
        "L1_nonselective_block",
        "L1_not_for_ginger_block",
        "L3_off_label_icar_recommended",
        "L4_off_label_needs_verification",
    } <= tiers


def test_key_products_classified_correctly(sync_engine: Engine) -> None:
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT product_name, compliance_tier, dose_per_acre_low, dose_per_acre_high "
                "FROM registered_herbicide_registry"
            )
        ).all()
    by_name = {r.product_name: r for r in rows}
    # Non-selective knockdowns hard-blocked.
    assert by_name["Roundup"].compliance_tier == "L1_nonselective_block"
    assert by_name["Gramoxone"].compliance_tier == "L1_nonselective_block"
    # The comma-bearing product name round-trips as a single key.
    assert by_name["2,4-D"].compliance_tier == "L1_crop_damage_block"
    # Season 1 default recommended practice.
    assert by_name["Manual/Mechanical"].compliance_tier == "L1_recommended_practice"
    # Off-label ICAR products carry their label doses.
    assert float(by_name["Goal"].dose_per_acre_low) == 180.0
    assert float(by_name["Goal"].dose_per_acre_high) == 200.0
    assert by_name["Goal"].compliance_tier == "L3_off_label_icar_recommended"


def test_hard_block_products_have_no_dose(sync_engine: Engine) -> None:
    # Hard-blocked products carry no recommendable dose.
    with sync_engine.begin() as conn:
        rows = conn.execute(
            text(
                "SELECT product_name, dose_per_acre_low, dose_per_acre_high "
                "FROM registered_herbicide_registry WHERE compliance_tier = ANY(:tiers)"
            ),
            {"tiers": list(_HARD_BLOCK_TIERS)},
        ).all()
    assert rows
    for r in rows:
        assert r.dose_per_acre_low is None, r.product_name
        assert r.dose_per_acre_high is None, r.product_name
