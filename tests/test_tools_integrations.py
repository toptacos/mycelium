import pytest

from mycelium.tools.integrations import call_api
from conftest import build_agent


async def ctx_with_connections(ws, home, scripted, connections: dict):
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    settings.connections = connections
    assert agent.ctx.connections == connections
    return agent.ctx


async def test_call_api_get_injects_auth(ws, home, scripted, provider, monkeypatch):
    monkeypatch.setenv("TEST_API_TOKEN", "secret-123")
    provider.route("GET", "/status", payload={"ok": True})
    conns = {"svc": {"base_url": provider.url, "auth_env": "TEST_API_TOKEN"}}
    ctx = await ctx_with_connections(ws, home, scripted, conns)
    out = await call_api({"connection": "svc", "path": "/status"}, ctx)
    assert "status: 200" in out
    assert '"ok": true' in out
    sent = provider.requests[-1]
    assert sent["headers"]["Authorization"] == "Bearer secret-123"


async def test_call_api_unknown_connection(ws, home, scripted):
    ctx = await ctx_with_connections(ws, home, scripted, {})
    out = await call_api({"connection": "nope"}, ctx)
    assert "unknown connection" in out


async def test_call_api_missing_token_denied(ws, home, scripted, provider, monkeypatch):
    monkeypatch.delenv("TEST_API_TOKEN", raising=False)
    provider.route("GET", "/status", payload={"ok": True})
    conns = {"svc": {"base_url": provider.url, "auth_env": "TEST_API_TOKEN"}}
    ctx = await ctx_with_connections(ws, home, scripted, conns)
    out = await call_api({"connection": "svc", "path": "/status"}, ctx)
    assert "not set" in out
    assert provider.requests == []


async def test_call_api_method_allowlist(ws, home, scripted, provider, monkeypatch):
    monkeypatch.setenv("TEST_API_TOKEN", "t")
    provider.route("GET", "/ping", payload={"pong": True})
    provider.route("DELETE", "/items/1", payload={"deleted": True})
    conns = {
        "svc": {
            "base_url": provider.url,
            "auth_env": "TEST_API_TOKEN",
            "methods": ["GET"],
        }
    }
    ctx = await ctx_with_connections(ws, home, scripted, conns)
    ok = await call_api({"connection": "svc", "path": "/ping"}, ctx)
    assert "status: 200" in ok
    denied = await call_api(
        {"connection": "svc", "method": "DELETE", "path": "/items/1"}, ctx
    )
    assert "not allowed" in denied
    assert all(r["method"] == "GET" for r in provider.requests)


async def test_call_api_post_json_body(ws, home, scripted, provider, monkeypatch):
    monkeypatch.setenv("TEST_API_TOKEN", "t")
    provider.route("POST", "/items", payload={"id": 7})
    conns = {
        "svc": {
            "base_url": provider.url,
            "auth_env": "TEST_API_TOKEN",
            "methods": ["GET", "POST"],
        }
    }
    ctx = await ctx_with_connections(ws, home, scripted, conns)
    out = await call_api(
        {
            "connection": "svc",
            "method": "POST",
            "path": "/items",
            "body": {"name": "widget"},
        },
        ctx,
    )
    assert "status: 200" in out
    assert provider.requests[-1]["body"] == {"name": "widget"}


async def test_call_api_bad_base_url(ws, home, scripted):
    ctx = await ctx_with_connections(
        ws, home, scripted, {"svc": {"base_url": "ftp://nope"}}
    )
    out = await call_api({"connection": "svc"}, ctx)
    assert "invalid base_url" in out
