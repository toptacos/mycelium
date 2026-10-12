import pytest

from mycelium.backends import ChatResponse
from mycelium.tools.research import html_to_text, research_web
from conftest import build_agent


async def ctx_for(ws, home, scripted):
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    return agent.ctx


def test_html_to_text_strips_tags_and_scripts():
    html = """
    <html><head><style>body{color:red}</style><script>alert(1)</script></head>
    <body><h1>Title</h1><p>First paragraph.</p><p>Second paragraph.</p>
    <ul><li>item one</li><li>item two</li></ul></body></html>
    """
    text = html_to_text(html)
    assert "color:red" not in text
    assert "alert(1)" not in text
    assert "Title" in text
    assert "First paragraph." in text
    assert "item two" in text


async def test_research_web_answers_question(ws, home, scripted, provider):
    provider.route_raw(
        "GET",
        "/",
        text="<html><body><h1>Example Domain</h1><p>This domain is for examples.</p></body></html>",
    )
    ctx = await ctx_for(ws, home, scripted)
    scripted.push(
        ChatResponse(
            content="the page explains example domains",
            prompt_tokens=80,
            completion_tokens=12,
        )
    )
    out = await research_web(
        {"url": provider.url + "/", "question": "what is this page for?"}, ctx
    )
    assert "what is this page for?" in out
    assert "the page explains example domains" in out
    assert provider.url in out
    assert "page_chars" in out
    assert len(provider.requests) == 1
    assert provider.requests[0]["path"] == "/"


async def test_research_web_rejects_non_http(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await research_web({"url": "ftp://example.com"}, ctx)
    assert "must start with http" in out


async def test_research_web_handles_json_pages(ws, home, scripted, provider):
    provider.route("GET", "/status", payload={"ok": True, "version": "1.2"})
    ctx = await ctx_for(ws, home, scripted)
    scripted.push(ChatResponse(content="status ok, version 1.2"))
    out = await research_web({"url": provider.url + "/status"}, ctx)
    assert "status ok, version 1.2" in out
    assert "page_chars" in out


async def test_research_web_upstream_error_propagates(ws, home, scripted, provider):
    import httpx

    ctx = await ctx_for(ws, home, scripted)
    with pytest.raises(httpx.HTTPStatusError):
        await research_web({"url": provider.url + "/missing"}, ctx)
