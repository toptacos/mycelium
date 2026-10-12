import json

import pytest

from mycelium.backends import (
    AnthropicBackend,
    ChatResponse,
    GeminiBackend,
    OllamaBackend,
    OpenAICompatBackend,
    ScriptedBackend,
    ToolCall,
    make_backend,
    repair_tool_calls,
)


async def test_ollama_request_shape(provider):
    provider.route(
        "POST",
        "/api/chat",
        payload={
            "model": "qwen3:0.6b",
            "message": {
                "role": "assistant",
                "content": "hello there",
                "tool_calls": [],
            },
            "prompt_eval_count": 21,
            "eval_count": 7,
        },
    )
    backend = OllamaBackend("local", provider.url, None)
    resp = await backend.chat(
        [{"role": "user", "content": "hi"}],
        model="qwen3:0.6b",
        tools=[{"type": "function", "function": {"name": "fs_list"}}],
    )
    req = provider.requests[-1]["body"]
    assert req["model"] == "qwen3:0.6b"
    assert req["stream"] is False
    assert req["messages"][0]["role"] == "user"
    assert resp.content == "hello there"
    assert resp.prompt_tokens == 21
    assert resp.completion_tokens == 7
    await backend.aclose()


async def test_ollama_tool_calls_parsed(provider):
    provider.route(
        "POST",
        "/api/chat",
        payload={
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {"function": {"name": "fs_list", "arguments": {"path": "."}}}
                ],
            }
        },
    )
    backend = OllamaBackend("local", provider.url, None)
    resp = await backend.chat([{"role": "user", "content": "list"}], model="m")
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "fs_list"
    assert resp.tool_calls[0].arguments == {"path": "."}
    await backend.aclose()


async def test_openai_auth_and_tool_parsing(provider):
    provider.route(
        "POST",
        "/v1/chat/completions",
        payload={
            "model": "qwen/qwen3-coder:free",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "listing",
                        "tool_calls": [
                            {
                                "id": "call_x",
                                "type": "function",
                                "function": {
                                    "name": "fs_list",
                                    "arguments": '{"path": "."}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ],
            "usage": {"prompt_tokens": 50, "completion_tokens": 9},
        },
    )
    backend = OpenAICompatBackend("openrouter", provider.url + "/v1", "sk-or-test")
    resp = await backend.chat(
        [{"role": "user", "content": "list files"}],
        model="qwen/qwen3-coder:free",
        tools=[{"type": "function", "function": {"name": "fs_list", "parameters": {}}}],
    )
    sent = provider.requests[-1]
    assert sent["headers"]["Authorization"] == "Bearer sk-or-test"
    assert sent["body"]["tool_choice"] == "auto"
    assert resp.tool_calls[0].name == "fs_list"
    assert resp.tool_calls[0].arguments == {"path": "."}
    assert (
        resp.usage_prompt == 50
        if hasattr(resp, "usage_prompt")
        else resp.prompt_tokens == 50
    )
    await backend.aclose()


async def test_openai_malformed_arguments_kept_raw(provider):
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
                                "id": "c1",
                                "type": "function",
                                "function": {
                                    "name": "fs_read",
                                    "arguments": "{not json",
                                },
                            }
                        ],
                    }
                }
            ],
        },
    )
    backend = OpenAICompatBackend("custom", provider.url, None)
    resp = await backend.chat([{"role": "user", "content": "x"}], model="m")
    assert resp.tool_calls[0].arguments == {"_raw": "{not json"}
    await backend.aclose()


async def test_gemini_contents_and_function_call(provider):
    provider.route(
        "POST",
        "/models/gemini-2.0-flash:generateContent",
        payload={
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [
                            {"text": "checking"},
                            {
                                "functionCall": {
                                    "name": "fs_list",
                                    "args": {"path": "."},
                                }
                            },
                        ],
                    }
                }
            ],
            "usageMetadata": {"promptTokenCount": 11, "candidatesTokenCount": 4},
        },
    )
    backend = GeminiBackend("gemini", provider.url, "AIza-test")
    resp = await backend.chat(
        [
            {"role": "user", "content": "list"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "1",
                        "type": "function",
                        "function": {"name": "fs_list", "arguments": "{}"},
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": "1",
                "name": "fs_list",
                "content": "files",
            },
        ],
        model="gemini-2.0-flash",
        tools=[
            {
                "type": "function",
                "function": {"name": "fs_list", "description": "d", "parameters": {}},
            }
        ],
        system="be terse",
    )
    sent = provider.requests[-1]
    assert sent["path"].endswith("?key=AIza-test")
    body = sent["body"]
    assert body["systemInstruction"]["parts"][0]["text"] == "be terse"
    assert body["contents"][0]["role"] == "user"
    assert any("functionCall" in p for p in body["contents"][1]["parts"])
    assert body["contents"][2]["parts"][0]["functionResponse"]["name"] == "fs_list"
    assert body["tools"][0]["function_declarations"][0]["name"] == "fs_list"
    assert resp.content == "checking"
    assert resp.tool_calls[0].name == "fs_list"
    assert resp.prompt_tokens == 11
    await backend.aclose()


async def test_anthropic_tool_use(provider):
    provider.route(
        "POST",
        "/v1/messages",
        payload={
            "model": "claude-sonnet-4-5",
            "content": [
                {"type": "text", "text": "listing files"},
                {
                    "type": "tool_use",
                    "id": "toolu_1",
                    "name": "fs_list",
                    "input": {"path": "."},
                },
            ],
            "usage": {"input_tokens": 33, "output_tokens": 12},
        },
    )
    backend = AnthropicBackend("anthropic", provider.url, "sk-ant-test")
    resp = await backend.chat(
        [{"role": "user", "content": "list files"}],
        model="claude-sonnet-4-5",
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "fs_list",
                    "description": "list",
                    "parameters": {"type": "object"},
                },
            }
        ],
        system="be brief",
    )
    sent = provider.requests[-1]
    assert sent["headers"]["Authorization"] == "Bearer sk-ant-test"
    body = sent["body"]
    assert body["system"] == "be brief"
    assert body["tools"][0]["name"] == "fs_list"
    assert body["tools"][0]["input_schema"] == {"type": "object"}
    assert resp.content == "listing files"
    assert resp.tool_calls[0].id == "toolu_1"
    assert resp.tool_calls[0].arguments == {"path": "."}
    assert resp.prompt_tokens == 33
    assert resp.completion_tokens == 12
    await backend.aclose()


async def test_retry_on_429_then_success(provider):
    provider.routes[("POST", "/api/chat")] = (429, {"error": "slow down"})
    backend = OllamaBackend("local", provider.url, None)
    with pytest.raises(RuntimeError):
        await backend.chat([{"role": "user", "content": "hi"}], model="m")
    provider.route(
        "POST",
        "/api/chat",
        payload={"message": {"role": "assistant", "content": "recovered"}},
    )
    backend2 = OllamaBackend("local", provider.url, None)
    resp = await backend2.chat([{"role": "user", "content": "hi"}], model="m")
    assert resp.content == "recovered"
    await backend2.aclose()


def test_scripted_backend_records_and_pops():
    backend = ScriptedBackend(
        [ChatResponse(content="first"), ChatResponse(content="second")]
    )

    import asyncio

    r1 = asyncio.run(backend.chat([{"role": "user", "content": "a"}], model="m"))
    r2 = asyncio.run(backend.chat([{"role": "user", "content": "b"}], model="m"))
    r3 = asyncio.run(backend.chat([{"role": "user", "content": "c"}], model="m"))
    assert r1.content == "first"
    assert r2.content == "second"
    assert r3.content == "scripted: ok"
    assert len(backend.calls) == 3
    assert backend.calls[0]["messages"][0]["content"] == "a"


def test_repair_tool_calls_from_fenced_json():
    content = 'Let me list files.\n```json\n{"name": "fs_list", "arguments": {"path": "."}}\n```'
    calls = repair_tool_calls(content, lambda: "gen_0")
    assert len(calls) == 1
    assert calls[0].name == "fs_list"
    assert calls[0].arguments == {"path": "."}


def test_repair_ignores_plain_markdown():
    content = 'Here is a json example:\n```json\n{"key": "value"}\n```\nThat is all.'
    assert repair_tool_calls(content, lambda: "x") == []


def test_repair_xml_style():
    content = '<tool_use>{"tool": "fs_read", "args": {"path": "a.py"}}</tool_use>'
    calls = repair_tool_calls(content, lambda: "x")
    assert calls[0].name == "fs_read"
    assert calls[0].arguments == {"path": "a.py"}


def test_repair_naked_json_object():
    content = '{"name": "fs_list", "arguments": {"path": "."}}'
    calls = repair_tool_calls(content, lambda: "x")
    assert len(calls) == 1
    assert calls[0].name == "fs_list"
    assert calls[0].arguments == {"path": "."}


def test_repair_naked_json_with_trailing_prose():
    content = (
        '{"name": "fs_read", "arguments": {"path": "a.py"}}\nI will read the file now.'
    )
    calls = repair_tool_calls(content, lambda: "x")
    assert calls and calls[0].name == "fs_read"


def test_repair_input_key_alias():
    content = '{"tool": "remember", "input": {"text": "note it"}}'
    calls = repair_tool_calls(content, lambda: "x")
    assert calls[0].name == "remember"
    assert calls[0].arguments == {"text": "note it"}


def test_repair_rejects_json_without_tool_shape():
    content = '{"key": "value", "other": 1}'
    assert repair_tool_calls(content, lambda: "x") == []
    content2 = '{"name": "fs_list"}'
    assert repair_tool_calls(content2, lambda: "x") == []


def test_make_backend_factory():
    assert make_backend("ollama", "local", "http://x", None).name == "local"
    assert isinstance(make_backend("scripted", "s", "", None), ScriptedBackend)
