import json
from pathlib import Path

import pytest

from mycelium.agent import AgentConfig
from mycelium.backends import ChatResponse, ToolCall
from mycelium.runtime import build_registry
from conftest import build_agent


def tc(name: str, args: dict, content: str = "") -> ChatResponse:
    return ChatResponse(
        content=content,
        tool_calls=[ToolCall(id="c1", name=name, arguments=args)],
        prompt_tokens=30,
        completion_tokens=10,
    )


def final(text: str) -> ChatResponse:
    return ChatResponse(content=text, prompt_tokens=30, completion_tokens=12)


async def test_agent_single_turn_no_tools(ws, home, scripted):
    scripted.push(final("The workspace contains README.md and src/."))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("what is in the workspace?")
    assert result.ok
    assert "README.md" in result.content
    assert result.steps == 1
    assert result.tool_calls == 0


async def test_agent_tool_loop(ws, home, scripted):
    (ws / "README.md").write_text("# demo")
    scripted.push(tc("fs_list", {"path": "."}))
    scripted.push(tc("fs_read", {"path": "README.md"}))
    scripted.push(final("README.md says '# demo'. Done."))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("list the workspace and read README.md")
    assert result.ok
    assert result.tool_calls == 2
    assert result.used_tools == ["fs_list", "fs_read"]
    assert "Done" in result.content
    assert result.prompt_tokens == 90


async def test_agent_step_budget_exhaustion(ws, home, scripted):
    for _ in range(50):
        scripted.push(tc("fs_list", {"path": "."}))
    agent, settings, log, registry, memory = build_agent(
        ws, home, scripted, config=AgentConfig(max_steps=3)
    )
    result = await agent.run("keep listing forever")
    assert result.ok is False
    assert "budget" in (result.warning or "")
    assert result.steps == 3


async def test_agent_unknown_tool_then_final(ws, home, scripted):
    scripted.push(tc("nope_tool", {}))
    scripted.push(final("that tool did not exist; finishing"))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("use a tool that does not exist")
    assert result.ok
    assert "finishing" in result.content


async def test_agent_read_only_blocks_mutation(ws, home, scripted):
    scripted.push(tc("fs_write", {"path": "x.txt", "content": "should not persist"}))
    scripted.push(final("could not write"))
    agent, settings, log, registry, memory = build_agent(
        ws, home, scripted, settings_overrides={"read_only": True}
    )
    agent.registry = build_registry()
    result = await agent.run("write x.txt")
    assert not (ws / "x.txt").exists()
    assert result.used_tools == ["fs_write"]
    tool_events = [
        json.loads(line)
        for line in (ws / ".mycelium" / "logs" / "session.jsonl")
        .read_text()
        .splitlines()
    ]
    denials = [e for e in tool_events if e.get("tool") == "fs_write" and not e["ok"]]
    assert denials and denials[0]["error"] == "read-only session"


async def test_agent_empty_model_response_aborts(ws, home, scripted):
    scripted.push(final("   "))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("hi")
    assert result.ok is False
    assert "empty" in (result.warning or "")


async def test_agent_backend_error_captured(ws, home):
    class Boom:
        name = "boom"

        async def chat(self, *a, **k):
            raise ConnectionError("backend down")

        async def aclose(self):
            return None

    agent, settings, log, registry, memory = build_agent(ws, home, Boom())
    result = await agent.run("hi")
    assert result.ok is False
    assert "backend down" in (result.warning or "")


async def test_agent_auto_compaction(ws, home, scripted):
    for _ in range(60):
        scripted.push(tc("fs_list", {"path": "."}))
    scripted.push(final("done after compaction"))
    agent, settings, log, registry, memory = build_agent(
        ws,
        home,
        scripted,
        settings_overrides={
            "context_window": 500,
            "reserve_tokens": 100,
            "compact_threshold": 0.5,
            "max_steps": 100,
        },
        config=AgentConfig(max_steps=60),
    )
    result = await agent.run("list files many times")
    analysis_events = [
        json.loads(line)
        for line in (ws / ".mycelium" / "logs" / "session.jsonl")
        .read_text()
        .splitlines()
    ]
    compactions = [e for e in analysis_events if e["event"] == "compaction"]
    assert len(compactions) >= 1, "expected at least one compaction event"
    assert all(c["reclaimed"] > 0 for c in compactions)
    assert all(c["turns_dropped"] >= 1 for c in compactions)


async def test_agent_memory_distillation(ws, home, scripted):
    scripted.push(final("scaffolded the app successfully"))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    await agent.run("scaffold a python cli for me")
    entries = [
        json.loads(line)
        for line in (ws / ".mycelium" / "memory.jsonl").read_text().splitlines()
    ]
    assert any(e["kind"] == "summary" for e in entries)
    recalled = memory.recall("scaffold python")
    assert recalled
    assert "scaffolded" in recalled[0].text


async def test_agent_repair_of_fenced_tool_call(ws, home, scripted):
    scripted.push(
        ChatResponse(
            content='I will list:\n```json\n{"name": "fs_list", "arguments": {"path": "."}}\n```'
        )
    )
    scripted.push(final("listed via repaired tool call"))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    result = await agent.run("please list the workspace")
    assert result.used_tools == ["fs_list"]
    assert "repaired" in result.content


async def test_agent_recalls_memory_in_system_prompt(ws, home, scripted):
    scripted.push(final("ok"))
    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    memory.add("user prefers uv over pip", kind="preference", tags=["python"])
    system = agent.system_prompt("install python deps with uv")
    assert "prefers uv over pip" in system
