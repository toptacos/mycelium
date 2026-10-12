import json

import httpx
import pytest

pytestmark = pytest.mark.live


async def ollama_reachable() -> bool:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://127.0.0.1:11434/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


needs_ollama = pytest.mark.skipif(
    not __import__("asyncio").run(ollama_reachable()),
    reason="Ollama not reachable at 127.0.0.1:11434 (start it with `ollama serve`)",
)


async def test_live_ollama_health(provider):
    import subprocess

    out = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=30)
    assert out.returncode == 0
    assert "NAME" in out.stdout


@needs_ollama
async def test_live_single_turn_chat(ws, home):
    from conftest import build_agent
    from mycelium.config import load_settings
    from mycelium.runtime import build_backend

    settings = load_settings(
        workspace=ws, home=home, backend="local", model="local:qwen3:0.6b"
    )
    backend = build_backend(settings)
    agent, _, log, _, _ = build_agent(
        ws,
        home,
        backend,
        settings_overrides={"backend": "local", "model": "local:qwen3:0.6b"},
    )
    result = await agent.run("Say hello in exactly three words.")
    print(
        json.dumps(
            {
                "ok": result.ok,
                "content": result.content,
                "prompt_tokens": result.prompt_tokens,
                "steps": result.steps,
            },
            indent=2,
        )
    )
    assert result.ok
    assert result.content.strip()
    assert result.prompt_tokens > 0
    await backend.aclose()


@needs_ollama
async def test_live_explicit_tool_call(ws, home):
    from conftest import build_agent
    from mycelium.runtime import build_backend
    from mycelium.config import load_settings

    (ws / "README.md").write_text("# live test workspace")
    settings = load_settings(
        workspace=ws, home=home, backend="local", model="local:qwen3:0.6b"
    )
    backend = build_backend(settings)
    agent, _, log, _, _ = build_agent(
        ws,
        home,
        backend,
        settings_overrides={"backend": "local", "model": "local:qwen3:0.6b"},
    )
    result = await agent.run(
        "Use the fs_list tool with path '.' to list the workspace files. Reply only after the tool result."
    )
    print(
        json.dumps(
            {
                "ok": result.ok,
                "tools_used": result.used_tools,
                "content": result.content[:300],
                "steps": result.steps,
            },
            indent=2,
        )
    )
    assert result.ok
    assert result.content.strip()
    await backend.aclose()
