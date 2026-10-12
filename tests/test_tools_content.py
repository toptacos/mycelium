import re

import pytest

from mycelium.backends import ChatResponse
from mycelium.tools.content import CONTENT_KINDS, _slugify, create_content
from conftest import build_agent


async def ctx_for(ws, home, scripted):
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    return agent.ctx


async def test_create_content_writes_draft(ws, home, scripted):
    draft = (
        "# Why local-first agents matter\n\nPrivacy, ownership, and speed. "
        + ("word " * 60).strip()
    )
    scripted.push(ChatResponse(content=draft, prompt_tokens=40, completion_tokens=120))
    ctx = await ctx_for(ws, home, scripted)
    out = await create_content(
        {"kind": "blog", "topic": "Local-First AI Agents", "max_words": 300}, ctx
    )
    path = ws / "content" / "local-first-ai-agents-blog.md"
    assert path.is_file()
    body = path.read_text()
    assert body.startswith("---")
    assert "kind: blog" in body
    assert "Why local-first agents matter" in body
    assert "created content/local-first-ai-agents-blog.md" in out
    assert "preview" in out


async def test_create_content_all_kinds(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    for kind in CONTENT_KINDS:
        scripted.push(ChatResponse(content=f"# {kind} draft\n\nbody text"))
        out = await create_content({"kind": kind, "topic": f"topic for {kind}"}, ctx)
        slug = f"topic-for-{kind}"
        assert (ws / "content" / f"{slug}-{kind}.md").is_file(), out


async def test_create_content_rejects_bad_kind(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await create_content({"kind": "haiku", "topic": "x"}, ctx)
    assert "unknown kind" in out


async def test_create_content_rejects_tiny_word_cap(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await create_content({"kind": "blog", "topic": "x", "max_words": 10}, ctx)
    assert "at least 50" in out


async def test_create_content_handles_empty_draft(ws, home, scripted):
    scripted.push(ChatResponse(content="   ", prompt_tokens=5, completion_tokens=0))
    ctx = await ctx_for(ws, home, scripted)
    out = await create_content({"kind": "outline", "topic": "empty case"}, ctx)
    assert "empty draft" in out


def test_slugify():
    assert _slugify("Hello, World! 123") == "hello-world-123"
    assert _slugify("!!!") == "content"
