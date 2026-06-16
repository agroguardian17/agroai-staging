"""Liveness and readiness contract tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_returns_200_with_contract(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert "commit" in body
    assert "env" in body
    assert body["env"] in {"development", "staging", "production", "test"}


@pytest.mark.asyncio
async def test_ready_returns_200_with_check_list(client: AsyncClient) -> None:
    response = await client.get("/api/v1/ready")
    assert response.status_code == 200

    body = response.json()
    assert "ready" in body
    assert "checks" in body
    assert isinstance(body["checks"], list)
    expected_components = {"postgres", "mosquitto", "chroma"}
    assert {c["name"] for c in body["checks"]} == expected_components


@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_format(client: AsyncClient) -> None:
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    body = response.text
    assert "agro_http_requests_total" in body or "agro_" in body


@pytest.mark.asyncio
async def test_openapi_schema_documents_health(client: AsyncClient) -> None:
    response = await client.get("/api/v1/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "/api/v1/health" in schema["paths"]
    assert "/api/v1/ready" in schema["paths"]
