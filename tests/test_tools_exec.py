import pytest

from mycelium.tools import PolicyViolation
from mycelium.tools.exec import DEFAULT_ALLOW, run_command
from conftest import build_agent


async def ctx_for(ws, home, scripted, **overrides):
    agent, settings, log, registry, memory = build_agent(
        ws, home, scripted, settings_overrides=overrides
    )
    return agent.ctx


async def test_run_command_executes_allowlisted_binary(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command({"command": "python3 -c \"print('exec works')\""}, ctx)
    assert "exit 0" in out
    assert "exec works" in out


async def test_run_command_captures_nonzero_exit(ws, home, scripted):
    from mycelium.tools import ToolFailure

    ctx = await ctx_for(ws, home, scripted)
    with pytest.raises(ToolFailure, match="exit 3") as excinfo:
        await run_command({"command": 'python3 -c "import sys; sys.exit(3)"'}, ctx)
    assert "exit 3" in excinfo.value.output


async def test_run_command_denies_unlisted_executable(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    with pytest.raises(PolicyViolation, match="not in the command allowlist"):
        await run_command({"command": "rm -rf /tmp/nope"}, ctx)


async def test_run_command_respects_configured_allowlist(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted, command_allow=["echo"])
    out = await run_command({"command": "echo hi"}, ctx)
    assert "hi" in out
    with pytest.raises(PolicyViolation):
        await run_command({"command": 'python3 -c "print(1)"'}, ctx)


async def test_run_command_empty_command(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command({"command": "   "}, ctx)
    assert "command is required" in out


async def test_run_command_binary_not_found(ws, home, scripted):
    ctx = await ctx_for(
        ws, home, scripted, command_allow=["definitely-not-a-real-binary-xyz"]
    )
    out = await run_command({"command": "definitely-not-a-real-binary-xyz"}, ctx)
    assert "not found on PATH" in out


async def test_run_command_timeout(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command(
        {"command": 'python3 -c "import time; time.sleep(5)"', "timeout_s": 1}, ctx
    )
    assert "timed out" in out


async def test_run_command_shell_metacharacters_are_inert(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command(
        {"command": "python3 -c \"print('a; rm -rf nothing')\""}, ctx
    )
    assert "exit 0" in out
    assert "a; rm -rf nothing" in out


async def test_run_command_respects_cwd(ws, home, scripted):
    (ws / "sub").mkdir()
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command(
        {
            "command": 'python3 -c "import os; print(os.path.basename(os.getcwd()))"',
            "cwd": "sub",
        },
        ctx,
    )
    assert "sub" in out


async def test_run_command_denies_cwd_escape(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    with pytest.raises(PolicyViolation):
        await run_command({"command": "python3 --version", "cwd": "../.."}, ctx)


async def test_run_command_truncates_huge_output(ws, home, scripted):
    ctx = await ctx_for(ws, home, scripted)
    out = await run_command({"command": "python3 -c \"print('x' * 20000)\""}, ctx)
    assert "truncated" in out


async def test_run_command_registered_by_default(ws, home, scripted):
    from mycelium.runtime import build_registry

    registry = build_registry()
    assert "run_command" in registry
    tool = registry.get("run_command")
    assert tool.mutating is True
    assert "allowlist" in tool.description
