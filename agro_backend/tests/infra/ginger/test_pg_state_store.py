"""Shape tests for PgStateStore.

Full DB round-trip lives in the integration suite (needs migration 0010
applied). These tests exercise the sync interface + JSON payload shape with
a stub psycopg2 connection so they run in unit CI.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch


def test_pg_state_store_load_returns_empty_when_row_missing() -> None:
    from app.infra.ginger.pg_state_store import PgStateStore

    fake_cur = MagicMock()
    fake_cur.__enter__.return_value = fake_cur
    fake_cur.fetchone.return_value = None
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.cursor.return_value = fake_cur

    with patch("app.infra.ginger.pg_state_store.psycopg2.connect", return_value=fake_conn):
        store = PgStateStore("postgresql://x")
        assert store.load("PLOT_MISSING") == {}


def test_pg_state_store_load_returns_reset_reason_on_version_mismatch() -> None:
    from app.infra.ginger.pg_state_store import PgStateStore

    fake_cur = MagicMock()
    fake_cur.__enter__.return_value = fake_cur
    fake_cur.fetchone.return_value = {"version": -999, "payload": "{}"}
    fake_conn = MagicMock()
    fake_conn.__enter__.return_value = fake_conn
    fake_conn.cursor.return_value = fake_cur

    with patch("app.infra.ginger.pg_state_store.psycopg2.connect", return_value=fake_conn):
        store = PgStateStore("postgresql://x")
        out = store.load("PLOT_PILOT_001")
        assert "_reset_reason" in out
        assert "-999" in out["_reset_reason"]


def test_pg_state_store_log_advisory_noop_on_empty_list() -> None:
    """An empty messages list must NOT open a connection or issue SQL."""
    from app.infra.ginger.pg_state_store import PgStateStore

    with patch(
        "app.infra.ginger.pg_state_store.psycopg2.connect"
    ) as mock_connect:
        store = PgStateStore("postgresql://x")
        store.log_advisory("PLOT_PILOT_001", date(2026, 8, 3), [])
        mock_connect.assert_not_called()
