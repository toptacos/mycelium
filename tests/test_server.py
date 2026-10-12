import json
import threading
from http.server import ThreadingHTTPServer

import httpx
import pytest

from mycelium.config import load_settings
from mycelium.server import ProxyState, make_handler


@pytest.fixture
def proxy(ws, home, provider):
    (ws / "mycelium.toml").write_text(
        f'[backends.fake]\nkind = "openai"\nbase_url = "{provider.url}"\ndefault_model = "test-model"\nmodels = ["test-model"]\n\n[backends.fake2]\nkind = "ollama"\nbase_url = "{provider.url}"\ndefault_model = "test-model"\n'
    )
    settings = load_settings(workspace=ws, home=home, backend="fake")
    state = ProxyState(settings)
    server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(state))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


async def test_healthz(proxy):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{proxy}/healthz")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_models_endpoint(proxy):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{proxy}/v1/models")
    assert resp.status_code == 200
    ids = [m["id"] for m in resp.json()["data"]]
    assert "fake:test-model" in ids
    assert "test-model" in ids


async def test_openai_chat_completions(proxy, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "model": "test-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "hi from backend"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 3, "total_tokens": 8},
        },
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{proxy}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "hi from backend"
    assert body["usage"]["prompt_tokens"] == 5
    sent = provider.requests[-1]["body"]
    assert sent["messages"][0]["content"] == "hello"


async def test_anthropic_messages_endpoint(proxy, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [
                {"message": {"role": "assistant", "content": "anthropic-shaped reply"}}
            ],
        },
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{proxy}/v1/messages",
            json={
                "model": "test-model",
                "max_tokens": 512,
                "system": "be brief",
                "messages": [
                    {"role": "user", "content": [{"type": "text", "text": "ping"}]}
                ],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["type"] == "message"
    assert body["content"][0]["type"] == "text"
    assert body["content"][0]["text"] == "anthropic-shaped reply"
    assert body["stop_reason"] == "end_turn"
    sent = provider.requests[-1]["body"]
    contents = [m.get("content") for m in sent["messages"]]
    assert "ping" in contents
    assert "be brief" in contents


async def test_anthropic_tool_use_passthrough(proxy, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "fs_list",
                                    "arguments": '{"path": "."}',
                                },
                            }
                        ],
                    }
                }
            ],
        },
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{proxy}/v1/messages",
            json={
                "model": "test-model",
                "max_tokens": 256,
                "messages": [{"role": "user", "content": "list"}],
            },
        )
    assert resp.status_code == 200
    blocks = resp.json()["content"]
    assert blocks[0]["type"] == "tool_use"
    assert blocks[0]["name"] == "fs_list"
    assert blocks[0]["input"] == {"path": "."}


async def test_count_tokens(proxy):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{proxy}/v1/messages/count_tokens",
            json={"messages": [{"role": "user", "content": "a" * 400}]},
        )
    assert resp.status_code == 200
    assert resp.json()["input_tokens"] >= 90


async def test_unknown_path_404(proxy):
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(f"{proxy}/nope")
    assert resp.status_code == 404


async def test_openai_streaming_sse(proxy, provider):
    provider.route(
        "POST",
        "/chat/completions",
        payload={
            "choices": [
                {"message": {"role": "assistant", "content": "streamed reply here"}}
            ],
        },
    )
    async with httpx.AsyncClient(timeout=15) as client:
        async with client.stream(
            "POST",
            f"{proxy}/v1/chat/completions",
            json={
                "model": "test-model",
                "messages": [{"role": "user", "content": "go"}],
                "stream": True,
            },
        ) as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers["content-type"]
            chunks = []
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and "[DONE]" not in line:
                    chunks.append(json.loads(line[6:]))
    assert chunks
    text = "".join(c["choices"][0]["delta"].get("content", "") for c in chunks)
    assert text == "streamed reply here"
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"


async def test_model_routing_backend_prefix(proxy, provider):
    provider.route(
        "POST",
        "/api/chat",
        payload={"message": {"role": "assistant", "content": "via fake2 ollama"}},
    )
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"{proxy}/v1/chat/completions",
            json={
                "model": "fake2:test-model",
                "messages": [{"role": "user", "content": "hi"}],
            },
        )
    assert resp.status_code == 200
    assert resp.json()["choices"][0]["message"]["content"] == "via fake2 ollama"
    assert provider.requests[-1]["path"] == "/api/chat"
