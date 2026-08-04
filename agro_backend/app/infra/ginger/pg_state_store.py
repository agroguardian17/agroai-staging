"""Postgres implementation of the ginger engine's state store interface.

The teammate's ``ginger.engine.persistence`` ships two backends:

* ``FileStateStore`` — one JSON document per plot on the filesystem.
* ``SqliteStateStore`` — a SQLite file, transactional, safe for concurrent runs.

Their arch doc §15 explicitly calls out that a **PostgreSQL adapter is a known
gap**: *"File and SQLite implementations exist; the interface is identical."*
This module fills that gap.

Interface expected by ``PersistentRunner`` (from their ``persistence.py``):

* ``load(plot_id) -> dict`` — return the persisted state, or ``{}`` if none.
  On schema version mismatch return ``{'_reset_reason': str}`` and let the
  runner start clean.
* ``save(plot_id, notifier, overrides, answered, last_run)`` — atomic upsert.
* ``log_advisory(plot_id, day, messages)`` — optional; called only if the
  ``PersistentRunner`` sees this attribute.
* ``history(plot_id, limit=30)`` — optional; for the dashboard.

The tables (``engine_state`` and ``advisory_log``) are created by Alembic
migration 0010 as part of the ginger knowledge base SQL. This adapter reads
and writes them via **psycopg2** (sync) because the teammate's calling code
is synchronous. The daily job wraps runs in ``asyncio.to_thread`` so the sync
DB access does not block the asyncio loop.

State-format compatibility with SqliteStateStore is deliberate: the payload
column stores the same JSON blob shape the SQLite backend uses. This means
their existing tests can run against Postgres by swapping only the store, and
a future migration between SQLite and Postgres is a plain ``COPY`` of the
``engine_state`` and ``advisory_log`` tables.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

import psycopg2
from persistence import (  # type: ignore[import-not-found] # flat via sys.path shim
    STATE_VERSION,
    dump_notifier,
    dump_overrides,
)
from psycopg2.extras import RealDictCursor

# Runtime import order: activate the flat-import shim in ``ginger`` BEFORE
# reaching into their engine modules for the serializers + STATE_VERSION.
import ginger  # noqa: F401 - side-effect: sys.path shim

if TYPE_CHECKING:
    from expert_override import OverrideStore  # type: ignore[import-not-found]
    from notification_policy import Notifier  # type: ignore[import-not-found]


def _iso(x: object) -> str | None:
    """Their persistence uses date.isoformat(); mirror that at the boundary."""
    if x is None:
        return None
    if isinstance(x, date):
        return x.isoformat()
    return str(x)


class PgStateStore:
    """Persist ginger engine state in the same Postgres the rest of the app uses.

    Parameters
    ----------
    dsn:
        A libpq-style connection string, e.g.
        ``"postgresql://agro:pw@localhost:5432/agro"``. This is the SYNC
        DSN (``DATABASE_URL_SYNC`` in settings), NOT the asyncpg one.

    The class opens a short-lived connection per method call — matching the
    ``SqliteStateStore`` pattern. A future optimisation could pool
    connections; the daily job iterates ~4 plots in the pilot so pooling is
    not worth the complexity today.
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    # ------------------------------------------------------------------
    # Contract methods called by PersistentRunner
    # ------------------------------------------------------------------
    def load(self, plot_id: str) -> dict[str, Any]:
        """Return the persisted state or a reset marker.

        Matches ``SqliteStateStore.load``: on version mismatch we return
        ``{'_reset_reason': ...}`` and the caller starts fresh rather than
        half-restoring.
        """
        with psycopg2.connect(self._dsn) as conn, conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:
            cur.execute(
                "SELECT version, payload FROM engine_state WHERE plot_id = %s",
                (plot_id,),
            )
            row = cur.fetchone()
        if row is None:
            return {}
        version = row["version"]
        payload = row["payload"]
        if version != STATE_VERSION:
            return {
                "_reset_reason": (
                    f"state version {version} != {STATE_VERSION}; starting clean"
                )
            }
        # ``payload`` is stored as JSON text in the SQL migration; JSONB would
        # also work. Guard both by decoding only if it is a string.
        if isinstance(payload, str):
            return json.loads(payload)
        return dict(payload)

    def save(
        self,
        plot_id: str,
        notifier: Notifier,
        overrides: OverrideStore,
        answered: set[str],
        last_run: date,
    ) -> None:
        """Upsert one plot's engine state atomically.

        Called at the end of ``run_day`` and after ``create_override``.
        """
        payload = json.dumps(
            {
                "version": STATE_VERSION,
                "plot_id": plot_id,
                "last_run": _iso(last_run),
                "notifier": dump_notifier(notifier),
                "overrides": dump_overrides(overrides),
                "answered": sorted(answered),
            },
            ensure_ascii=False,
        )
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO engine_state (plot_id, version, last_run, saved_at, payload)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (plot_id) DO UPDATE SET
                    version = EXCLUDED.version,
                    last_run = EXCLUDED.last_run,
                    saved_at = EXCLUDED.saved_at,
                    payload = EXCLUDED.payload
                """,
                (
                    plot_id,
                    STATE_VERSION,
                    _iso(last_run),
                    datetime.utcnow().isoformat(timespec="seconds"),
                    payload,
                ),
            )
            conn.commit()

    def log_advisory(self, plot_id: str, day: date, messages: list[Any]) -> None:
        """Insert one row per delivered advisory. Idempotent on (plot, day, rule).

        ``messages`` is a list of their ``runner.Message`` instances with
        ``.rule_id``, ``.severity``, and ``.render() -> str``.
        """
        if not messages:
            return
        rows = [
            (plot_id, _iso(day), m.rule_id, m.severity, m.render()) for m in messages
        ]
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO advisory_log (plot_id, day, rule_id, severity, message)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                rows,
            )
            conn.commit()

    def history(
        self, plot_id: str, limit: int = 30
    ) -> list[tuple[str, str, str]]:
        """Recent (day, rule_id, severity) tuples. Newest first.

        Kept for parity with ``SqliteStateStore.history``. The main read
        surface is the FastAPI endpoint, not this method.
        """
        with psycopg2.connect(self._dsn) as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT day::text, rule_id, severity FROM advisory_log
                WHERE plot_id = %s ORDER BY day DESC LIMIT %s
                """,
                (plot_id, limit),
            )
            return list(cur.fetchall())


__all__ = ["PgStateStore"]
