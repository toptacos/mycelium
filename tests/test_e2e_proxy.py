import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

pytestmark = pytest.mark.e2e

REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def proxy_url(ws: Path, home: Path, provider):
    (ws / "mycelium.toml").write_text(
        f'[backends.fake]\nkind = "openai"\nbase_url = "{provider.url}"\ndefault_model = "test-model"\nmodels = ["test-model"]\n\n[backends.fake2]\nkind = "ollama"\nbase_url = "{provider.url}"\ndefault_model = "test-model"\n'
    )
    env = dict(os.environ)
    env["MYCELIUM_HOME"] = str(home)
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "mycelium.cli",
            "--workspace",
            str(ws),
            "--backend",
            "fake",
            "serve",
            "--port",
            "0",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=str(REPO_ROOT),
        env=env,
    )
    url = None
    for _ in range(60):
        line = proc.stdout.readline()
        if not line:
            break
        if "listening on" in line:
            url = line.split("listening on")[1].strip().rstrip("]").strip()
            break
    if url is None:
        proc.kill()
        pytest.fail("proxy did not report a listening URL")
    yield url
    proc.send_signal(signal.SIGINT)
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


async def test_proxy_health_and_models(proxy_url):
    async with httpx.AsyncClient(timeout=10) as client:
        health = await client.get(f"{proxy_url}/healthz")
        assert health.status_code == 200
        assert health.json()["service"] == "mycelium-proxy"
        models = await client.get(f"{proxy_url}/v1/models")
        ids = [m["id"] for m in models.json()["data"]]
        assert "fake:test-model" in ids


async def test_proxy_openai_roundtrip(proxy_url, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "e2e proxy reply"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 7, "completion_tokens": 3},
        },
    )
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{proxy_url}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [
                    {"role": "system", "content": "be terse"},
                    {"role": "user", "content": "hi"},
                ],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["choices"][0]["message"]["content"] == "e2e proxy reply"
    assert body["usage"]["total_tokens"] == 10
    sent = provider.requests[-1]["body"]
    assert sent["messages"][0]["role"] == "system"


async def test_proxy_anthropic_roundtrip(proxy_url, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [
                {"message": {"role": "assistant", "content": "anthropic e2e reply"}}
            ],
        },
    )
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{proxy_url}/v1/messages",
            json={
                "model": "test-model",
                "max_tokens": 256,
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["content"][0]["text"] == "anthropic e2e reply"


async def test_proxy_streaming(proxy_url, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [{"message": {"role": "assistant", "content": "streamed e2e"}}],
        },
    )
    chunks = []
    async with httpx.AsyncClient(timeout=20) as client:
        async with client.stream(
            "POST",
            f"{proxy_url}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "go"}],
                "stream": True,
            },
        ) as resp:
            assert resp.status_code == 200
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and "[DONE]" not in line:
                    chunks.append(json.loads(line[6:]))
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert text == "streamed e2e"


async def test_proxy_count_tokens_and_404(proxy_url):
    async with httpx.AsyncClient(timeout=10) as client:
        counted = await client.post(
            f"{proxy_url}/v1/messages/count_tokens",
            json={"messages": [{"role": "user", "content": "x" * 400}]},
        )
        assert counted.json()["input_tokens"] == 100
        missing = await client.get(f"{proxy_url}/nope")
        assert missing.status_code == 404


def test_proxy_bad_json_400(proxy_url):
    import httpx as _httpx

    with _httpx.Client(timeout=10) as client:
        resp = client.post(
            f"{proxy_url}/v1/chat/completions",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )
    assert resp.status_code == 400
