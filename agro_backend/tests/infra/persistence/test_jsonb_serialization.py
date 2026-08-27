"""Unit tests for JSONB parameter encoding at the Postgres boundary."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from app.infra.persistence.pg_reading_repo import _jsonb_param


def test_jsonb_param_serializes_nested_decimal_datetime_and_uuid() -> None:
    payload = {
        "master_readings": {
            "bme280_temp_c": Decimal("32.4"),
            "lora_snr_db": Decimal("8.5"),
        },
        "recorded_at": datetime(2026, 8, 27, 3, 55, tzinfo=UTC),
        "tenant_id": UUID("11111111-1111-1111-1111-111111111111"),
    }

    encoded = _jsonb_param(payload)
    decoded = json.loads(encoded)

    assert decoded["master_readings"]["bme280_temp_c"] == "32.4"
    assert decoded["master_readings"]["lora_snr_db"] == "8.5"
    assert decoded["recorded_at"] == "2026-08-27T03:55:00+00:00"
    assert decoded["tenant_id"] == "11111111-1111-1111-1111-111111111111"
