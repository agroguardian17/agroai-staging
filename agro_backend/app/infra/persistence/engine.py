"""Async SQLAlchemy engine + sessionmaker factory.


Single place that knows how to build the async machinery our repositories
need. Use cases get a ``sessionmaker`` from here (typically via FastAPI
dependency injection later) and pass it to the concrete repo
constructors. The repos open one session per method call inside an
``async with`` block - lightweight, predictable, no leaked connections.


Why this lives in infra and not application:


* The async engine is a concrete SQLAlchemy + asyncpg object - a
  framework concern (.cursorrules #13 - application stays framework-free).
* The application layer only ever sees ``ReadingRepo`` etc. as Protocols
  (Round 4); the concrete machinery is wired through ``deps.py`` at the
  FastAPI seam (next round).


Provider portability (.cursorrules #25-26): we use ``postgresql+asyncpg``
URLs - vanilla Postgres, no AWS-specific driver. The URL itself comes
from Settings (``DATABASE_URL``); the schema string is portable.
"""


from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def make_async_engine(
    url: str,
    *,
    echo: bool = False,
    pool_size: int = 10,
    max_overflow: int = 5,
) -> AsyncEngine:
    """Build the async SQLAlchemy engine.


    Defaults:


    * ``pool_size=10`` - enough headroom for the ingest worker + a handful
      of API requests at pilot scale. Increase when read traffic outgrows it.
    * ``max_overflow=5`` - temporary burst capacity above pool_size.
    * ``pool_pre_ping=True`` - cheap ``SELECT 1`` before reusing a connection;
      catches stale connections after a Lightsail snapshot pause or a
      transient network blip without surfacing the error to the caller.
    * ``echo=False`` - SQL logging is INSANELY chatty under structlog; flip
      to True only for ad-hoc debugging.
    """
    return create_async_engine(
        url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=True,
        future=True,
    )




def make_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Build the async sessionmaker bound to an engine.


    * ``expire_on_commit=False`` - by default SQLAlchemy expires attributes
      after commit. That's correct for ORM-heavy apps where the same
      object survives across transactions. Our repos return *new* domain
      dataclasses constructed from query results, so expiry is irrelevant
      and the default just adds an extra fetch on every commit.
    * ``class_=AsyncSession`` - explicit so a future SQLAlchemy default
      change doesn't silently break us.
    """
    return async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )




__all__ = [
    "AsyncEngine",
    "AsyncSession",
    "async_sessionmaker",
    "make_async_engine",
    "make_sessionmaker",
]
