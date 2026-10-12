import pytest

from mycelium.runtime import build_registry
from mycelium.tools import PolicyViolation, resolve_in_workspace
from mycelium.tools.fs import fs_grep, fs_list, fs_read, fs_write


async def test_resolve_in_workspace_rejects_traversal(ws):
    with pytest.raises(PolicyViolation):
        resolve_in_workspace(ws, "../../etc/passwd")
    with pytest.raises(PolicyViolation):
        resolve_in_workspace(ws, "/etc/passwd")
    assert resolve_in_workspace(ws, "sub/dir/file.txt").is_relative_to(ws.resolve())


async def test_resolve_in_workspace_allows_dot(ws):
    assert resolve_in_workspace(ws, ".").resolve() == ws.resolve()


async def make_ctx(ws, home, scripted):
    from conftest import build_agent

    agent, settings, log, registry, memory = build_agent(ws, home, scripted)
    return agent.ctx


async def test_fs_write_then_read_roundtrip(ws, home, scripted):
    ctx = await make_ctx(ws, home, scripted)
    await fs_write({"path": "notes/hello.txt", "content": "hello mycelium"}, ctx)
    out = await fs_read({"path": "notes/hello.txt"}, ctx)
    assert "# notes/hello.txt" in out
    assert "hello mycelium" in out
    assert (ws / "notes" / "hello.txt").is_file()


async def test_fs_write_escapes_denied(ws, home, scripted):
    ctx = await make_ctx(ws, home, scripted)
    with pytest.raises(PolicyViolation):
        await fs_write({"path": "../escape.txt", "content": "x"}, ctx)


async def test_fs_read_missing_file(ws, home, scripted):
    ctx = await make_ctx(ws, home, scripted)
    out = await fs_read({"path": "nope.txt"}, ctx)
    assert "not a file" in out


async def test_fs_list_tree(ws, home, scripted):
    (ws / "src").mkdir()
    (ws / "src" / "main.py").write_text("print(1)")
    (ws / "README.md").write_text("# hi")
    ctx = await make_ctx(ws, home, scripted)
    out = await fs_list({"path": "."}, ctx)
    assert "f README.md" in out
    assert "d src" in out
    assert "f src/main.py" in out


async def test_fs_list_skips_vcs_noise(ws, home, scripted):
    (ws / "__pycache__").mkdir()
    (ws / "__pycache__" / "x.pyc").write_text("junk")
    (ws / ".git").mkdir()
    (ws / ".git" / "config").write_text("[core]")
    ctx = await make_ctx(ws, home, scripted)
    out = await fs_list({"path": "."}, ctx)
    assert "pyc" not in out
    assert ".git" not in out


async def test_fs_grep(ws, home, scripted):
    (ws / "a.py").write_text("def foo():\n    return 1\n")
    (ws / "b.py").write_text("x = 1\n")
    ctx = await make_ctx(ws, home, scripted)
    out = await fs_grep({"pattern": "def foo", "glob": "*.py"}, ctx)
    assert "a.py:1" in out
    out2 = await fs_grep({"pattern": "nothing_matches"}, ctx)
    assert out2 == "(no matches)"


async def test_fs_read_truncates(ws, home, scripted):
    (ws / "big.txt").write_text("x" * 30000)
    ctx = await make_ctx(ws, home, scripted)
    out = await fs_read({"path": "big.txt"}, ctx)
    assert "truncated" in out
    assert len(out) < 13000


async def test_registry_call_unknown_tool(ws, home, scripted):
    ctx = await make_ctx(ws, home, scripted)
    registry = build_registry()
    result = await registry.call("nope_tool", {}, ctx)
    assert result.ok is False
    assert "unknown tool" in result.output


async def test_read_only_blocks_mutating(ws, home, scripted):
    from mycelium.config import load_settings
    from mycelium.runtime import make_event_log, make_memory, build_registry
    from mycelium.tools import ToolContext

    settings = load_settings(workspace=ws, home=home, read_only=True)
    registry = build_registry().filter(include_mutating=False)
    assert "fs_write" not in registry
    assert "scaffold_app" not in registry
    assert "fs_read" in registry
