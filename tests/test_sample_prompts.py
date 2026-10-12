import json
from pathlib import Path

import pytest

from mycelium.backends import ChatResponse, ToolCall
from conftest import build_agent


def tc(name: str, args: dict) -> ChatResponse:
    return ChatResponse(
        content="",
        tool_calls=[ToolCall(id="c1", name=name, arguments=args)],
        prompt_tokens=25,
        completion_tokens=8,
    )


def final(text: str) -> ChatResponse:
    return ChatResponse(content=text, prompt_tokens=25, completion_tokens=15)


def read_log(ws: Path) -> list[dict]:
    path = ws / ".mycelium" / "logs" / "session.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines()]


# ---------------------------------------------------------------- scaffold app


async def test_sample_prompt_scaffold_app(ws, home, scripted):
    scripted.push(
        tc(
            "scaffold_app",
            {
                "name": "change-calculator",
                "template": "python-cli",
                "description": "compute change",
                "run_tests": True,
            },
        )
    )
    scripted.push(
        final(
            "Scaffolded apps/change-calculator with 5 files; the scaffold test suite PASSED."
        )
    )
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)

    prompt = (
        "Scaffold a new Python CLI application called 'change-calculator' using the "
        "python-cli template. Then run its test suite and report whether all tests pass."
    )
    result = await agent.run(prompt)

    assert result.ok, result.warning
    assert result.used_tools == ["scaffold_app"]
    root = ws / "apps" / "change-calculator"
    assert (root / "pyproject.toml").is_file()
    assert (root / "src" / "change_calculator" / "cli.py").is_file()
    assert (root / "tests" / "test_cli.py").is_file()
    assert (root / "README.md").is_file()
    assert "change-calculator" in (root / "pyproject.toml").read_text()
    tool_events = [
        e
        for e in read_log(ws)
        if e["event"] == "tool_call" and e["tool"] == "scaffold_app"
    ]
    assert tool_events and tool_events[0]["ok"]
    assert tool_events[0]["result_chars"] > 100
    assert "PASSED" in result.content
    assert result.content


async def test_sample_prompt_scaffold_tests_actually_run(ws, home, scripted):
    scripted.push(
        tc(
            "scaffold_app",
            {"name": "greeter", "template": "python-cli", "run_tests": True},
        )
    )
    scripted.push(final("done"))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("scaffold greeter with tests")
    out = (ws / "apps" / "greeter").exists()
    assert out
    events = read_log(ws)
    assert any(
        e["event"] == "tool_call" and e["tool"] == "scaffold_app" for e in events
    )


# -------------------------------------------------------------------- research


async def test_sample_prompt_research(ws, home, scripted, provider):
    provider.route_raw(
        "GET",
        "/",
        text="<html><body><h1>Example Domain</h1><p>This domain is for use in illustrative examples.</p></body></html>",
    )
    scripted.push(
        tc(
            "research_web",
            {"url": provider.url + "/", "question": "what is this page for?"},
        )
    )
    scripted.push(
        ChatResponse(
            content="The page documents the example.com reserved domain.",
            prompt_tokens=60,
            completion_tokens=14,
        )
    )
    scripted.push(
        tc(
            "fs_write",
            {
                "path": "research/example-com.md",
                "content": "# Research: example.com\n\nsource: "
                + provider.url
                + "\nanswer: documents the reserved example domain\n- key fact 1\n- key fact 2\n",
            },
        )
    )
    scripted.push(
        final(
            "Saved research/example-com.md. The page documents the example.com reserved domain."
        )
    )
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)

    result = await agent.run(
        "Research the page and save notes to research/example-com.md with the source URL and the answer."
    )
    assert result.ok, result.warning
    notes = ws / "research" / "example-com.md"
    assert notes.is_file()
    body = notes.read_text()
    assert provider.url in body
    assert "answer: documents the reserved example domain" in body
    assert result.used_tools == ["research_web", "fs_write"]
    assert len(provider.requests) == 1


# --------------------------------------------------------------------- content


async def test_sample_prompt_content(ws, home, scripted):
    draft = (
        "# Why Local-First AI Agents Matter\n\n"
        + ("Privacy and ownership matter for teams. " * 30).strip()
    )
    scripted.push(
        tc(
            "create_content",
            {
                "kind": "blog",
                "topic": "Why local-first AI agents matter",
                "audience": "backend developers",
                "max_words": 500,
            },
        )
    )
    scripted.push(ChatResponse(content=draft, prompt_tokens=40, completion_tokens=150))
    scripted.push(
        final(
            "Created content/why-local-first-ai-agents-matter-blog.md at 42 words (cap 500)."
        )
    )
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)

    result = await agent.run(
        "Create a blog post about 'why local-first AI agents matter for privacy' for backend developers, max 500 words."
    )
    assert result.ok, result.warning
    path = ws / "content" / "why-local-first-ai-agents-matter-blog.md"
    assert path.is_file()
    body = path.read_text()
    assert body.startswith("---")
    assert "kind: blog" in body
    assert body.split("---")[2].strip().startswith("# Why Local-First AI Agents Matter")


# ---------------------------------------------------------------- integration


async def test_sample_prompt_integration(ws, home, scripted, provider):
    provider.route(
        "GET", "/status", payload={"ok": True, "region": "us-east-1", "uptime_s": 12345}
    )
    (ws / "mycelium.toml").write_text(
        f'[connections.example]\nbase_url = "{provider.url}"\nmethods = ["GET"]\n'
    )
    scripted.push(
        tc("call_api", {"connection": "example", "method": "GET", "path": "/status"})
    )
    scripted.push(
        final(
            "The example connection returned HTTP 200 with ok=true, region us-east-1, uptime 12345s."
        )
    )
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    assert "example" in agent.ctx.connections

    result = await agent.run(
        "Use the 'example' connection to GET /status and interpret the payload."
    )
    assert result.ok, result.warning
    assert result.used_tools == ["call_api"]
    assert "200" in result.content
    assert provider.requests and provider.requests[0]["path"] == "/status"


# ------------------------------------------------------------------- workflow


async def test_sample_prompt_workflow(ws, home, scripted):
    wf_dir = ws / "workflows"
    wf_dir.mkdir(exist_ok=True)
    (wf_dir / "release-notes.yaml").write_text(
        "name: release-notes\n"
        "description: write release notes\n"
        "inputs:\n"
        "  repo_path:\n"
        '    default: "."\n'
        "steps:\n"
        "  - id: list\n"
        "    tool: fs_list\n"
        "    args:\n"
        '      path: "{{inputs.repo_path}}"\n'
        "  - id: draft\n"
        '    llm: "Write release notes from this listing: {{steps.list.output}}"\n'
        "  - id: write\n"
        "    tool: fs_write\n"
        "    args:\n"
        '      path: "RELEASE_NOTES.md"\n'
        '      content: "{{steps.draft.output}}"\n'
    )
    (ws / "README.md").write_text("# mycelium demo")
    scripted.push(
        tc("run_workflow", {"workflow": "release-notes", "inputs": {"repo_path": "."}})
    )
    scripted.push(
        ChatResponse(
            content="# Release Notes\n\n- Listened the workspace\n- Everything works",
            prompt_tokens=45,
            completion_tokens=18,
        )
    )
    scripted.push(
        final(
            "Workflow release-notes completed: steps list, draft, write. RELEASE_NOTES.md written."
        )
    )
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)

    result = await agent.run("Run the release-notes workflow with repo_path='.'")
    assert result.ok, result.warning
    notes = ws / "RELEASE_NOTES.md"
    assert notes.is_file()
    assert "# Release Notes" in notes.read_text()
    assert result.used_tools == ["run_workflow"]
    assert "RELEASE_NOTES.md written" in result.content
    events = read_log(ws)
    wf_events = [e for e in events if e["event"] == "workflow_step"]
    assert [e["step"] for e in wf_events] == ["list", "draft", "write"]
