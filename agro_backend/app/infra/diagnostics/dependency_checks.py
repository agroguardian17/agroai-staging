"""External-dependency self-tests (debug hardening, Round 2).

Lightweight, **side-effect-free** reachability/credential probes for the four
external integrations, returning domain ``CheckResult`` rows (category
``dependency``). They catch the "dead integration" class — a CDSE client that
stopped authenticating, an expired Meta token — that otherwise only shows up as
missing data days later.

Each probe:
* ``skip`` when the integration is unconfigured (blank creds) — never a false fail;
* ``ok`` on a successful auth/reachability response;
* ``fail`` (with the HTTP status / error) otherwise — and never raises.

Notes:
* Anthropic is a **config** check (key present + model ids set) — we do not spend
  a live API call nightly; a stale model id still surfaces via the advisory path.
* USGS ``login-token`` validates credentials only. The Landsat *download-access*
  403 (the pilot's actual failure) surfaces as the ``satellite_fresh`` / LST
  freshness check, not here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import structlog

from app.domain.diagnostics import CATEGORY_DEPENDENCY, CheckResult

if TYPE_CHECKING:
    from app.config import Settings

log = structlog.get_logger(__name__)

_TIMEOUT = 10.0
_USGS_LOGIN_URL = "https://m2m.cr.usgs.gov/api/api/json/stable/login-token"
_GRAPH_BASE = "https://graph.facebook.com"


def _skip(check_id: str, detail: str) -> CheckResult:
    return CheckResult(check_id, CATEGORY_DEPENDENCY, "skip", detail=detail)


def _ok(check_id: str, observed: str) -> CheckResult:
    return CheckResult(check_id, CATEGORY_DEPENDENCY, "ok", observed=observed)


def _fail(check_id: str, detail: str) -> CheckResult:
    return CheckResult(check_id, CATEGORY_DEPENDENCY, "fail", detail=detail)


async def check_cdse(settings: Settings, client: httpx.AsyncClient) -> CheckResult:
    cid = "dep_cdse"
    secret = settings.COPERNICUS_CLIENT_SECRET.get_secret_value()
    if not settings.COPERNICUS_CLIENT_ID or not secret:
        return _skip(cid, "COPERNICUS_CLIENT_ID/SECRET unset")
    try:
        resp = await client.post(
            settings.COPERNICUS_TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": settings.COPERNICUS_CLIENT_ID,
                "client_secret": secret,
            },
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        return _fail(cid, type(exc).__name__)
    if resp.status_code == 200 and resp.json().get("access_token"):
        return _ok(cid, "token 200")
    return _fail(cid, f"HTTP {resp.status_code}")


async def check_usgs(settings: Settings, client: httpx.AsyncClient) -> CheckResult:
    cid = "dep_usgs_m2m"
    token = settings.USGS_M2M_TOKEN.get_secret_value()
    if not settings.USGS_M2M_USERNAME or not token:
        return _skip(cid, "USGS_M2M_USERNAME/TOKEN unset")
    try:
        resp = await client.post(
            _USGS_LOGIN_URL,
            json={"username": settings.USGS_M2M_USERNAME, "token": token},
            timeout=_TIMEOUT,
        )
    except Exception as exc:
        return _fail(cid, type(exc).__name__)
    body = resp.json() if resp.content else {}
    if resp.status_code == 200 and body.get("data"):
        return _ok(cid, "login ok (download access checked via LST freshness)")
    return _fail(cid, f"HTTP {resp.status_code} {body.get('errorCode') or ''}".strip())


async def check_meta_whatsapp(settings: Settings, client: httpx.AsyncClient) -> CheckResult:
    cid = "dep_meta_whatsapp"
    token = settings.META_WHATSAPP_TOKEN.get_secret_value()
    if not token or not settings.META_WHATSAPP_PHONE_NUMBER_ID:
        return _skip(cid, "META_WHATSAPP_TOKEN/PHONE_NUMBER_ID unset")
    url = f"{_GRAPH_BASE}/{settings.META_WHATSAPP_GRAPH_VERSION}/{settings.META_WHATSAPP_PHONE_NUMBER_ID}"
    try:
        # GET the phone-number node — validates token + id, sends no message.
        resp = await client.get(url, params={"access_token": token}, timeout=_TIMEOUT)
    except Exception as exc:
        return _fail(cid, type(exc).__name__)
    if resp.status_code == 200:
        return _ok(cid, "graph 200")
    return _fail(cid, f"HTTP {resp.status_code}")


def check_anthropic(settings: Settings) -> CheckResult:
    cid = "dep_anthropic"
    if not settings.ANTHROPIC_API_KEY.get_secret_value():
        return _skip(cid, "ANTHROPIC_API_KEY unset (advisory text is log-only)")
    if not settings.ANTHROPIC_MODEL_SONNET or not settings.ANTHROPIC_MODEL_HAIKU:
        return _fail(cid, "ANTHROPIC_MODEL_SONNET/HAIKU unset")
    return _ok(
        cid, f"key set; models {settings.ANTHROPIC_MODEL_SONNET}/{settings.ANTHROPIC_MODEL_HAIKU}"
    )


async def run_dependency_checks(
    settings: Settings, client: httpx.AsyncClient | None = None
) -> list[CheckResult]:
    """Run all dependency probes; returns one CheckResult each (never raises)."""
    results = [check_anthropic(settings)]
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=_TIMEOUT)
    try:
        results.append(await check_cdse(settings, client))
        results.append(await check_usgs(settings, client))
        results.append(await check_meta_whatsapp(settings, client))
    finally:
        if owns_client:
            await client.aclose()
    return results


__all__ = [
    "check_anthropic",
    "check_cdse",
    "check_meta_whatsapp",
    "check_usgs",
    "run_dependency_checks",
]
