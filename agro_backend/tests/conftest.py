"""Shared pytest fixtures.

Phase 0 deliverables:
- ``settings`` fixture overrides cached Settings to APP_ENV=test
- ``app`` fixture builds a fresh FastAPI app per test session
- ``client`` fixture is an httpx AsyncClient bound to the in-process app
  via ASGI transport - no socket binding, no port collisions.

Phase 1+ adds postgres + mosquitto testcontainer fixtures here.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

# Force test environment BEFORE app modules import their settings.
os.environ["APP_ENV"] = "test"
os.environ["AUTH_JWT_SECRET"] = "test-jwt-secret-32-bytes-of-noise!!"
os.environ["POSTGRES_PASSWORD"] = "test-pw"
os.environ["MQTT_BROKER_PASSWORD"] = "test-pw"


@pytest.fixture(scope="session")
def settings() -> Iterator[object]:
    """Provide a fresh Settings instance bound to the test environment."""
    from app.config import get_settings

    get_settings.cache_clear()
    s = get_settings()
    yield s
    get_settings.cache_clear()


@pytest.fixture(scope="session")
def app(settings: object) -> Iterator[FastAPI]:
    """Build the FastAPI app exactly once per test session."""
    from app.main import create_app

    application = create_app()
    yield application


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """In-process httpx client - lifespan events run end-to-end."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
