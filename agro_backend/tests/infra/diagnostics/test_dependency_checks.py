"""Unit tests for the external dependency self-tests (mocked httpx)."""

from __future__ import annotations

from types import SimpleNamespace

import httpx
from pydantic import SecretStr

from app.infra.diagnostics import dependency_checks as dc


def _settings(**over: object) -> SimpleNamespace:
    base: dict[str, object] = {
        "COPERNICUS_CLIENT_ID": "cid",
        "COPERNICUS_CLIENT_SECRET": SecretStr("sec"),
        "COPERNICUS_TOKEN_URL": "https://cdse.example/auth/token",
        "USGS_M2M_USERNAME": "user",
        "USGS_M2M_TOKEN": SecretStr("tok"),
        "META_WHATSAPP_TOKEN": SecretStr("mtok"),
        "META_WHATSAPP_PHONE_NUMBER_ID": "123",
        "META_WHATSAPP_GRAPH_VERSION": "v20.0",
        "ANTHROPIC_API_KEY": SecretStr("akey"),
        "ANTHROPIC_MODEL_SONNET": "claude-sonnet-4-5",
        "ANTHROPIC_MODEL_HAIKU": "claude-haiku-4-5",
    }
    base.update(over)
    return SimpleNamespace(**base)


def _client(handler: object) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))  # type: ignore[arg-type]


async def test_cdse_ok() -> None:
    def h(req: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access_token": "t", "expires_in": 600})

    async with _client(h) as c:
        r = await dc.check_cdse(_settings(), c)
    assert r.check_id == "dep_cdse"
    assert r.status == "ok"


async def test_cdse_fail_on_401() -> None:
    async with _client(lambda req: httpx.Response(401, json={"error": "invalid_client"})) as c:
        r = await dc.check_cdse(_settings(), c)
    assert r.status == "fail"


async def test_cdse_skip_when_unconfigured() -> None:
    async with _client(lambda req: httpx.Response(200, json={})) as c:
        r = await dc.check_cdse(_settings(COPERNICUS_CLIENT_ID=""), c)
    assert r.status == "skip"


async def test_usgs_ok_and_auth_fail() -> None:
    async with _client(lambda req: httpx.Response(200, json={"data": "apikey"})) as c:
        assert (await dc.check_usgs(_settings(), c)).status == "ok"
    async with _client(
        lambda req: httpx.Response(200, json={"data": None, "errorCode": "AUTH_INVALID"})
    ) as c:
        assert (await dc.check_usgs(_settings(), c)).status == "fail"


async def test_meta_ok_fail_skip() -> None:
    async with _client(lambda req: httpx.Response(200, json={"id": "123"})) as c:
        assert (await dc.check_meta_whatsapp(_settings(), c)).status == "ok"
    async with _client(lambda req: httpx.Response(401, json={"error": {}})) as c:
        assert (await dc.check_meta_whatsapp(_settings(), c)).status == "fail"
    async with _client(lambda req: httpx.Response(200, json={})) as c:
        r = await dc.check_meta_whatsapp(_settings(META_WHATSAPP_PHONE_NUMBER_ID=""), c)
    assert r.status == "skip"


def test_anthropic_config_check() -> None:
    assert dc.check_anthropic(_settings()).status == "ok"
    assert dc.check_anthropic(_settings(ANTHROPIC_API_KEY=SecretStr(""))).status == "skip"
    assert dc.check_anthropic(_settings(ANTHROPIC_MODEL_SONNET="")).status == "fail"


async def test_run_dependency_checks_covers_all_four() -> None:
    def h(req: httpx.Request) -> httpx.Response:
        u = str(req.url)
        if "login-token" in u:
            return httpx.Response(200, json={"data": "apikey"})
        if "token" in u:
            return httpx.Response(200, json={"access_token": "t"})
        return httpx.Response(200, json={"id": "123"})  # meta graph node

    async with _client(h) as c:
        results = await dc.run_dependency_checks(_settings(), client=c)
    assert {r.check_id for r in results} == {
        "dep_anthropic",
        "dep_cdse",
        "dep_usgs_m2m",
        "dep_meta_whatsapp",
    }
    assert all(r.category == "dependency" for r in results)
