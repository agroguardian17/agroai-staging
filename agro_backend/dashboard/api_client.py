"""Thin HTTP client over the AgroGuardian read API.

The dashboard never talks to Postgres directly — every screen pulls
through ``/api/v1/*``. Keeping the wire format in one module means
schema changes need one diff, not one per page.

The client uses the static JWT in ``ACCESS_TOKEN`` (see README).
Round 12.5 will swap the static-token mode for an OTP login screen.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
import streamlit as st


def _base_url() -> str:
    return os.environ.get("AGRO_API_BASE_URL", "http://localhost:8000").rstrip("/")


def _token() -> str:
    tok = os.environ.get("ACCESS_TOKEN", "").strip()
    if not tok:
        st.error(
            "ACCESS_TOKEN env var is missing. Mint one via "
            "`POST /api/v1/auth/verify_otp` and export it before launching "
            "the dashboard."
        )
        st.stop()
    return tok


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token()}", "Accept": "application/json"}


def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    url = f"{_base_url()}{path}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=_headers(), params=params or {})
    if resp.status_code >= 400:
        st.error(f"API {resp.status_code} from GET {path}: {resp.text[:300]}")
        st.stop()
    return resp.json()


def _post(path: str, json: dict[str, Any]) -> Any:
    url = f"{_base_url()}{path}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=_headers(), json=json)
    if resp.status_code >= 400:
        st.error(f"API {resp.status_code} from POST {path}: {resp.text[:300]}")
        st.stop()
    return resp.json()


# ---------------------------------------------------------------------------
# Read endpoints
# ---------------------------------------------------------------------------
def whoami() -> dict[str, Any]:
    return _get("/api/v1/me")


def list_plots() -> list[dict[str, Any]]:
    return _get("/api/v1/plots")


def get_plot(plot_id: str) -> dict[str, Any]:
    return _get(f"/api/v1/plots/{plot_id}")


def list_readings(plot_id: str, limit: int = 100) -> list[dict[str, Any]]:
    return _get(f"/api/v1/plots/{plot_id}/readings", params={"limit": limit})


def list_plot_alerts(plot_id: str, limit: int = 50) -> list[dict[str, Any]]:
    return _get(f"/api/v1/plots/{plot_id}/alerts", params={"limit": limit})


def list_plot_suggestions(plot_id: str, limit: int = 20) -> list[dict[str, Any]]:
    return _get(f"/api/v1/plots/{plot_id}/suggestions", params={"limit": limit})


def list_alerts(
    *, status_filter: str = "open", severity: str | None = None, limit: int = 100
) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"status": status_filter, "limit": limit}
    if severity:
        params["severity"] = severity
    return _get("/api/v1/alerts", params=params)


def resolve_alert(alert_id: int, notes: str | None = None) -> dict[str, Any]:
    return _post(f"/api/v1/alerts/{alert_id}/resolve", json={"notes": notes})
