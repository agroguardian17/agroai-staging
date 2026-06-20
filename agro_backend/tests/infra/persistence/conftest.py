"""Shared fixtures for the Postgres-backed repository tests.


These tests need a reachable Postgres with ``alembic upgrade head`` applied.
They auto-skip when no database is reachable - each test module declares
``pytestmark = pytest.mark.skipif(not db_available(), reason=...)`` because
pytest does NOT propagate module-level ``pytestmark`` from a conftest down
to other test modules.


The async engine + sessionmaker fixtures are session-scoped to avoid
opening a new pool on every test. The ``clean_telemetry`` fixture
truncates the working tables before each test so independence is
preserved.
"""


from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator

import pytest
import pytest_asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infra.persistence.engine import make_async_engine, make_sessionmaker

SYNC_URL = os.getenv("DATABASE_URL_SYNC", "postgresql://agro:agro@localhost:5433/agro")
ASYNC_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://agro:agro@localhost:5433/agro",
)


PILOT_TENANT = "11111111-1111-1111-1111-111111111111"




def db_available() -> bool:
    """Probe whether Postgres at SYNC_URL is reachable.


    Each test module's ``pytestmark`` calls this and skips on False.
    Module-level pytestmark in a conftest does NOT propagate to other
    test modules; this helper is the shared piece they import.
    """
    try:
        eng = create_engine(SYNC_URL)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        eng.dispose()
    except Exception:
        return False
    return True




DB_SKIP_REASON = "Postgres not reachable; run on the Mac dev stack after `alembic upgrade head`."




@pytest.fixture(scope="session")
def sync_engine() -> Iterator[Engine]:
    """Sync engine for seeding fixture rows (matches test_schema_db.py)."""
    eng = create_engine(SYNC_URL, future=True)
    yield eng
    eng.dispose()




@pytest_asyncio.fixture
async def async_engine() -> AsyncIterator[AsyncEngine]:
    """Function-scoped on purpose.


    pytest-asyncio creates a new event loop for each async test by
    default. A session-scoped AsyncEngine creates its connection pool
    on the FIRST test's loop; later tests then try to reuse those
    connections on a different loop and asyncpg raises
    ``RuntimeError: ... attached to a different loop`` (and on
    teardown, ``Event loop is closed``). Scoping the engine per-test
    sidesteps all of that for the cost of one short-lived pool per
    test (cheap; tests are local Postgres).
    """
    eng = make_async_engine(ASYNC_URL, pool_size=5, max_overflow=2)
    yield eng
    await eng.dispose()




@pytest_asyncio.fixture
async def sessionmaker(
    async_engine: AsyncEngine,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    yield make_sessionmaker(async_engine)




@pytest.fixture
def clean_telemetry(sync_engine: Engine) -> Iterator[None]:
    """Truncate the rapidly-changing tables before a test so assertions
    aren't polluted by other tests' data. Master tables (tenants, plots,
    farms, farmers, device_registry) are NOT truncated - they're seeded
    elsewhere and must survive.
    """
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                "TRUNCATE TABLE node_sensor_readings, alerts_notifications RESTART IDENTITY CASCADE"
            )
        )
    yield




__all__ = [
    "ASYNC_URL",
    "PILOT_TENANT",
    "SYNC_URL",
    "async_engine",
    "clean_telemetry",
    "sessionmaker",
    "sync_engine",
]
