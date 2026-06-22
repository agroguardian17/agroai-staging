"""Integration tests for PgFarmerRepo."""


from __future__ import annotations


import uuid
from collections.abc import Iterator


import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


from app.application.ports.farmer_repo import FarmerRepo
from app.infra.persistence.pg_farmer_repo import PgFarmerRepo


from .conftest import DB_SKIP_REASON, PILOT_TENANT, db_available


pytestmark = pytest.mark.skipif(not db_available(), reason=DB_SKIP_REASON)




@pytest.fixture
def seed_farmer(sync_engine: Engine) -> Iterator[tuple[uuid.UUID, str]]:
    farmer_id = uuid.uuid4()
    phone = f"+919001{uuid.uuid4().hex[:6]}"
    with sync_engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO farmers (
                    farmer_id, tenant_id, full_name, marathi_name, phone_primary,
                    whatsapp_number, language_preference, village, taluka, district,
                    state, subscription_tier, subscription_start, subscription_end,
                    payment_status
                ) VALUES (
                    :fid, :tenant, 'Ramesh', 'रमेश', :phone, :phone,
                    'marathi', 'v', 't', 'd', 'Maharashtra', 'basic',
                    '2025-06-01', '2026-06-01', 'paid'
                )
                """
            ),
            {"fid": farmer_id, "tenant": PILOT_TENANT, "phone": phone},
        )
    yield farmer_id, phone
    with sync_engine.begin() as conn:
        conn.execute(text("DELETE FROM farmers WHERE farmer_id = :f"), {"f": farmer_id})




async def test_pg_farmer_repo_satisfies_protocol(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    assert isinstance(PgFarmerRepo(sessionmaker), FarmerRepo)




async def test_find_by_phone_returns_identity(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: tuple[uuid.UUID, str],
) -> None:
    farmer_id, phone = seed_farmer
    repo = PgFarmerRepo(sessionmaker)
    out = await repo.find_by_phone(phone)
    assert out is not None
    assert out.farmer_id == farmer_id
    assert out.full_name == "Ramesh"
    assert out.language_preference == "marathi"
    assert out.account_status == "active"




async def test_find_by_phone_unknown_returns_none(
    sessionmaker: async_sessionmaker[AsyncSession],
) -> None:
    repo = PgFarmerRepo(sessionmaker)
    assert await repo.find_by_phone("+91999999999") is None




async def test_find_by_id_returns_identity(
    sessionmaker: async_sessionmaker[AsyncSession],
    seed_farmer: tuple[uuid.UUID, str],
) -> None:
    farmer_id, _ = seed_farmer
    repo = PgFarmerRepo(sessionmaker)
    out = await repo.find_by_id(farmer_id)
    assert out is not None
    assert out.farmer_id == farmer_id
