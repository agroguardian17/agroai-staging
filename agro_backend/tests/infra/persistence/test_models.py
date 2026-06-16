"""Model-layer tests that need no database (run on Windows + CI).

These assert the ORM mapping matches the migrations: all 35 tables present,
tenant_id on tenant-scoped tables, partition metadata + idempotency constraints
on the time-series tables, and the key v3 columns.
"""

from __future__ import annotations

import pytest
from sqlalchemy import UniqueConstraint

from app.infra.persistence.models import Base

EXPECTED_TABLES = {
    # 21 source tables
    "farmers",
    "farms",
    "plots",
    "crop_seasons",
    "node_sensor_readings",
    "weather_station_readings",
    "satellite_data",
    "weather_forecasts",
    "electricity_schedule_log",
    "irrigation_events",
    "water_source_status",
    "ai_suggestions",
    "farmer_actions",
    "ai_learning_log",
    "device_registry",
    "component_inventory",
    "technician_installations",
    "service_maintenance",
    "alerts_notifications",
    "subscriptions_billing",
    "product_performance_bi",
    # 14 v3 tables
    "tenants",
    "users",
    "otp_codes",
    "refresh_tokens",
    "audit_log",
    "notification_dispatch_log",
    "notification_dlq",
    "ingest_unmatched",
    "event_outbox",
    "feature_flags",
    "system_config",
    "chat_messages",
    "calibration_history",
    "wa_inbound_log",
}

# Every tenant-scoped table must carry tenant_id.
TENANT_SCOPED = EXPECTED_TABLES - {
    "tenants",
    "users",
    "audit_log",
    "system_config",
}


def test_all_35_tables_registered() -> None:
    actual = set(Base.metadata.tables.keys())
    assert actual == EXPECTED_TABLES
    assert len(actual) == 35


@pytest.mark.parametrize("table", sorted(TENANT_SCOPED))
def test_tenant_scoped_tables_have_tenant_id(table: str) -> None:
    cols = Base.metadata.tables[table].c
    assert "tenant_id" in cols, f"{table} missing tenant_id"


def test_node_sensor_readings_is_partitioned_with_idempotency() -> None:
    t = Base.metadata.tables["node_sensor_readings"]
    assert t.dialect_options["postgresql"]["partition_by"] == "RANGE (recorded_at)"
    # composite PK includes the partition key
    pk_cols = {c.name for c in t.primary_key.columns}
    assert pk_cols == {"reading_id", "recorded_at"}
    # idempotency unique constraint
    uniques = {
        tuple(sorted(c.name for c in con.columns))
        for con in t.constraints
        if isinstance(con, UniqueConstraint)
    }
    assert ("node_id", "recorded_at") in uniques


def test_weather_forecasts_partitioned_by_fetched_at() -> None:
    t = Base.metadata.tables["weather_forecasts"]
    assert t.dialect_options["postgresql"]["partition_by"] == "RANGE (fetched_at)"
    assert {c.name for c in t.primary_key.columns} == {"forecast_id", "fetched_at"}


def test_node_reading_v3_columns_present() -> None:
    cols = Base.metadata.tables["node_sensor_readings"].c
    for col in (
        "soil_temp_rootzone_c",
        "soil_n_bucket",
        "soil_p_bucket",
        "soil_k_bucket",
        "cadence_mode",
        "backlog_pending",
        "validation_warn",
        "low_battery_flag",
    ):
        assert col in cols, f"missing {col}"


def test_plots_data_tier_and_nullable_node() -> None:
    cols = Base.metadata.tables["plots"].c
    assert "data_tier" in cols
    assert cols["node_id"].nullable is True


def test_ai_suggestions_review_columns() -> None:
    cols = Base.metadata.tables["ai_suggestions"].c
    for col in (
        "review_status",
        "reviewed_by",
        "reviewed_at",
        "review_notes",
        "prompt_template_version",
        "llm_cost_inr",
        "confidence_score",
        "confidence_band",
    ):
        assert col in cols, f"missing {col}"


def test_farmers_phone_privacy_columns() -> None:
    cols = Base.metadata.tables["farmers"].c
    assert "phone_hash" in cols
    assert "phone_encrypted" in cols
