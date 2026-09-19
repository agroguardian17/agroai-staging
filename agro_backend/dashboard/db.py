"""Read-only Postgres access for the internal ops dashboard.

The dashboard is a team-internal tool: it reads **directly** from Postgres
(cross-tenant, no RLS session vars) rather than through the farmer-facing API,
so it can surface every table, the whole advisory pipeline, and live events
without an endpoint per view.

Every connection is opened ``default_transaction_read_only=on`` — a hard guard
that makes any accidental write raise at the server. The connection string is
``DASHBOARD_DATABASE_URL`` (SQLAlchemy/psycopg form), or it is assembled from
the standard ``POSTGRES_*`` / ``PG*`` env the compose stack already sets.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import Engine, create_engine, text


def _url() -> str:
    explicit = os.environ.get("DASHBOARD_DATABASE_URL", "").strip()
    if explicit:
        # Normalise a plain postgres:// or asyncpg URL to the psycopg driver.
        return (
            explicit.replace("postgresql+asyncpg://", "postgresql+psycopg://")
            .replace("postgres://", "postgresql+psycopg://")
            .replace("postgresql://", "postgresql+psycopg://")
            if "+psycopg" not in explicit
            else explicit
        )
    user = os.environ.get("POSTGRES_USER", "agro")
    pw = os.environ.get("POSTGRES_PASSWORD", "agro")
    host = os.environ.get("PGHOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PGPORT", "5432")
    db = os.environ.get("POSTGRES_DB", "agro")
    return f"postgresql+psycopg://{user}:{pw}@{host}:{port}/{db}"


@lru_cache(maxsize=1)
def engine() -> Engine:
    return create_engine(
        _url(),
        pool_pre_ping=True,
        pool_size=3,
        max_overflow=2,
        # Hard read-only guard: every transaction on this engine rejects writes.
        connect_args={"options": "-c default_transaction_read_only=on"},
    )


@st.cache_data(ttl=15)
def df(sql: str, params: dict[str, Any] | None = None) -> pd.DataFrame:
    """Run a read query and return a DataFrame. Cached 15s to spare the DB."""
    with engine().connect() as conn:
        return pd.read_sql(text(sql), conn, params=params or {})


@st.cache_data(ttl=15)
def scalar(sql: str, params: dict[str, Any] | None = None) -> Any:
    with engine().connect() as conn:
        return conn.execute(text(sql), params or {}).scalar()


@st.cache_data(ttl=30)
def relations() -> pd.DataFrame:
    """Every table/partition in `public` with an approximate live-row count."""
    return df(
        """
        SELECT c.relname AS table,
               CASE c.relkind WHEN 'p' THEN 'partitioned' WHEN 'r' THEN 'table' END AS kind,
               COALESCE(s.n_live_tup, 0) AS approx_rows
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
        WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p')
        ORDER BY c.relname
        """
    )


@st.cache_data(ttl=30)
def columns(table: str) -> list[str]:
    rows = df(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = :t
        ORDER BY ordinal_position
        """,
        {"t": table},
    )
    return rows["column_name"].tolist() if not rows.empty else []


def migration_head() -> str:
    try:
        return scalar("SELECT version_num FROM alembic_version") or "unknown"
    except Exception:
        return "unknown"


def healthy() -> tuple[bool, str]:
    """Cheap connectivity probe for the landing page."""
    try:
        scalar("SELECT 1")
    except Exception as exc:  # pragma: no cover - surfaced in the UI
        return False, str(exc)[:200]
    return True, "connected"


# ---------------------------------------------------------------------------
# Write path — used ONLY by the Data Entry page.
#
# The engine above is hard read-only. The Data Entry page needs to persist the
# pilot intake fields, so it uses this separate, write-capable engine. It is
# deliberately NOT the default: every other page keeps the read-only guard.
# ---------------------------------------------------------------------------


@lru_cache(maxsize=1)
def write_engine() -> Engine:
    return create_engine(_url(), pool_pre_ping=True, pool_size=2, max_overflow=1)


def fetch_row(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """One row as a dict (read via the write engine, so it sees uncommitted-free
    fresh state and is never served from the 15 s read cache)."""
    with write_engine().connect() as conn:
        row = conn.execute(text(sql), params or {}).mappings().first()
    return dict(row) if row is not None else None


def execute_write(sql: str, params: dict[str, Any] | None = None) -> int:
    """Run one parameterized write in its own transaction. Returns rowcount."""
    with write_engine().begin() as conn:
        return conn.execute(text(sql), params or {}).rowcount
