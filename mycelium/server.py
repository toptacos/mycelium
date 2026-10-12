from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from mycelium.config import Settings
from mycelium.backends import Backend, make_backend
from mycelium.context import estimate_tokens


def _anthropic_to_canonical(
    messages: list[dict[str, Any]], system: Any
) -> tuple[str | None, list[dict[str, Any]]]:
    sys_text: str | None = None
    if isinstance(system, str):
        sys_text = system
    elif isinstance(system, list):
        sys_text = "\n".join(
            b.get("text", "")
            for b in system
            if isinstance(b, dict) and b.get("type") == "text"
        )

    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content")
        if isinstance(content, str):
            out.append({"role": role, "content": content})
            continue
        if not isinstance(content, list):
            continue
        text_parts: list[str] = []
        tool_uses: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            btype = block.get("type")
            if btype == "text":
                text_parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_uses.append(
                    {
                        "id": block.get("id"),
                        "type": "function",
                        "function": {
                            "name": block.get("name"),
                            "arguments": json.dumps(block.get("input", {})),
                        },
                    }
                )
            elif btype == "tool_result":
                tool_results.append(
                    {
                        "tool_call_id": block.get("tool_use_id"),
                        "content": _tool_result_text(block.get("content")),
                    }
                )
        for tr in tool_results:
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": tr["tool_call_id"],
                    "content": tr["content"],
                }
            )
        if tool_uses:
            out.append(
                {
                    "role": "assistant",
                    "content": "\n".join(text_parts),
                    "tool_calls": tool_uses,
                }
            )
        elif text_parts:
            out.append({"role": role, "content": "\n".join(text_parts)})
    return sys_text, out


def _tool_result_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(b.get("text", "") for b in content if isinstance(b, dict))
    return str(content)


def _openai_tools_to_internal(
    tools: list[dict[str, Any]] | None,
) -> list[dict[str, Any]] | None:
    if not tools:
        return None
    out = []
    for t in tools:
        if t.get("type") == "function":
            out.append(t)
        elif "name" in t and "input_schema" in t:
            out.append(
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t.get("description", ""),
                        "parameters": t["input_schema"],
                    },
                }
            )
    return out or None


class ProxyState:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.backends: dict[str, Backend] = {}

    def backend_for(self, name: str) -> Backend:
        if name not in self.backends:
            cfg = self.settings.backend_config(name)
            self.backends[name] = make_backend(
                cfg.kind, name, cfg.base_url, cfg.api_key
            )
        return self.backends[name]


def make_handler(state: ProxyState):
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        server_version = "mycelium-proxy/0.1"
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            print(f"[proxy] {self.address_string()} {fmt % args}")

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error_json(self, status: int, message: str) -> None:
            self._send_json(
                status, {"error": {"message": message, "type": "proxy_error"}}
            )

        def _read_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")

        def do_GET(self) -> None:
            path = self.path.split("?")[0]
            if path in ("/healthz", "/health"):
                self._send_json(200, {"status": "ok", "service": "mycelium-proxy"})
                return
            if path == "/v1/models":
                data = []
                for bname, cfg in state.settings.backends.items():
                    for m in cfg.models or (
                        [cfg.default_model] if cfg.default_model else []
                    ):
                        data.append(
                            {"id": f"{bname}:{m}", "object": "model", "owned_by": bname}
                        )
                        data.append({"id": m, "object": "model", "owned_by": bname})
                seen: set[str] = set()
                uniq = [d for d in data if not (d["id"] in seen or seen.add(d["id"]))]
                self._send_json(200, {"object": "list", "data": uniq})
                return
            self._send_error_json(404, f"unknown path {path}")

        def do_POST(self) -> None:
            import asyncio

            path = self.path.split("?")[0]
            try:
                body = self._read_body()
            except json.JSONDecodeError as exc:
                self._send_error_json(400, f"invalid json: {exc}")
                return
            try:
                if path == "/v1/chat/completions":
                    asyncio.run(self._handle_openai(body))
                elif path == "/v1/messages":
                    asyncio.run(self._handle_anthropic(body))
                elif path == "/v1/messages/count_tokens":
                    text = _messages_plain_text(body)
                    self._send_json(200, {"input_tokens": estimate_tokens(text)})
                else:
                    self._send_error_json(404, f"unknown path {path}")
            except Exception as exc:
                self._send_error_json(500, f"{type(exc).__name__}: {exc}")

        async def _chat(
            self, body: dict[str, Any], *, anthropic: bool
        ) -> tuple[Any, str]:
            if anthropic:
                system, messages = _anthropic_to_canonical(
                    body.get("messages", []), body.get("system")
                )
            else:
                messages = body.get("messages", [])
                system = None
                for m in messages:
                    if m.get("role") == "system":
                        system = (
                            (system + "\n\n" + m.get("content", ""))
                            if system
                            else m.get("content", "")
                        )
                messages = [m for m in messages if m.get("role") != "system"]
            model_spec = body.get("model", "")
            temperature = float(body.get("temperature", 0.2))
            max_tokens = body.get("max_tokens")
            tools = _openai_tools_to_internal(body.get("tools"))
            backend_name, model = state.settings.resolve_model(model_spec or None)
            backend = state.backend_for(backend_name)
            resp = await backend.chat(
                messages,
                model=model,
                tools=tools,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp, model

        async def _handle_openai(self, body: dict[str, Any]) -> None:
            resp, model = await self._chat(body, anthropic=False)
            if body.get("stream"):
                self._stream_openai(resp, model)
                return
            payload = {
                "id": f"chatcmpl-{uuid.uuid4().hex[:12]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": resp.content,
                            "tool_calls": [tc.__dict__ for tc in resp.tool_calls],
                        },
                        "finish_reason": "tool_calls" if resp.tool_calls else "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": resp.prompt_tokens,
                    "completion_tokens": resp.completion_tokens,
                    "total_tokens": resp.prompt_tokens + resp.completion_tokens,
                },
            }
            self._send_json(200, payload)

        async def _handle_anthropic(self, body: dict[str, Any]) -> None:
            resp, model = await self._chat(body, anthropic=True)
            content: list[dict[str, Any]] = []
            if resp.content:
                content.append({"type": "text", "text": resp.content})
            for tc in resp.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": tc.id,
                        "name": tc.name,
                        "input": tc.arguments,
                    }
                )
            if body.get("stream"):
                self._stream_anthropic(resp, model)
                return
            payload = {
                "id": f"msg_{uuid.uuid4().hex[:12]}",
                "type": "message",
                "role": "assistant",
                "content": content,
                "model": model,
                "stop_reason": "tool_use" if resp.tool_calls else "end_turn",
                "usage": {
                    "input_tokens": resp.prompt_tokens,
                    "output_tokens": resp.completion_tokens,
                },
            }
            self._send_json(200, payload)

        def _begin_sse(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True

        def _sse(self, payload: dict[str, Any]) -> None:
            self.wfile.write(
                f"event: {payload['type']}\ndata: {json.dumps(payload)}\n\n".encode()
            )
            self.wfile.flush()

        def _stream_openai(self, resp, model: str) -> None:
            self._begin_sse()
            chat_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"

            def chunk(delta: dict[str, Any], finish: str | None = None) -> None:
                data = {
                    "id": chat_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
                }
                self.wfile.write(f"data: {json.dumps(data)}\n\n".encode())
                self.wfile.flush()

            if resp.content:
                step = 48
                for i in range(0, len(resp.content), step):
                    chunk({"content": resp.content[i : i + step]})
            for tc in resp.tool_calls:
                chunk(
                    {
                        "tool_calls": [
                            {
                                "index": 0,
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments),
                                },
                            }
                        ]
                    }
                )
            chunk({}, finish="stop")
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()

        def _stream_anthropic(self, resp, model: str) -> None:
            self._begin_sse()
            msg_id = f"msg_{uuid.uuid4().hex[:12]}"
            self._sse(
                {
                    "type": "message_start",
                    "message": {
                        "id": msg_id,
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": model,
                        "usage": {
                            "input_tokens": resp.prompt_tokens,
                            "output_tokens": 0,
                        },
                    },
                }
            )
            idx = 0
            if resp.content:
                self._sse(
                    {
                        "type": "content_block_start",
                        "index": idx,
                        "content_block": {"type": "text", "text": ""},
                    }
                )
                step = 48
                for i in range(0, len(resp.content), step):
                    self._sse(
                        {
                            "type": "content_block_delta",
                            "index": idx,
                            "delta": {
                                "type": "text_delta",
                                "text": resp.content[i : i + step],
                            },
                        }
                    )
                self._sse({"type": "content_block_stop", "index": idx})
                idx += 1
            for tc in resp.tool_calls:
                self._sse(
                    {
                        "type": "content_block_start",
                        "index": idx,
                        "content_block": {
                            "type": "tool_use",
                            "id": tc.id,
                            "name": tc.name,
                            "input": {},
                        },
                    }
                )
                self._sse(
                    {
                        "type": "content_block_delta",
                        "index": idx,
                        "delta": {
                            "type": "input_json_delta",
                            "partial_json": json.dumps(tc.arguments),
                        },
                    }
                )
                self._sse({"type": "content_block_stop", "index": idx})
                idx += 1
            self._sse(
                {
                    "type": "message_delta",
                    "delta": {
                        "stop_reason": "tool_use" if resp.tool_calls else "end_turn"
                    },
                    "usage": {"output_tokens": resp.completion_tokens},
                }
            )
            self._sse({"type": "message_stop"})

    return Handler


def _messages_plain_text(body: dict[str, Any]) -> str:
    parts: list[str] = []
    if isinstance(body.get("system"), str):
        parts.append(body["system"])
    for m in body.get("messages", []):
        c = m.get("content")
        if isinstance(c, str):
            parts.append(c)
        elif isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "text":
                    parts.append(b.get("text", ""))
    return "\n".join(parts)


def serve(
    settings: Settings, host: str = "127.0.0.1", port: int = 8787
) -> ThreadingHTTPServer:
    state = ProxyState(settings)
    handler = make_handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    bound_port = server.server_address[1]
    print(f"mycelium proxy listening on http://{host}:{bound_port}", flush=True)
    print(
        "endpoints: GET /healthz, GET /v1/models, POST /v1/chat/completions, POST /v1/messages",
        flush=True,
    )
    print(
        f"default backend: {settings.backend} (model {settings.model or 'backend default'})",
        flush=True,
    )
    print(
        f"drop-in for CCR/claude-code: export ANTHROPIC_BASE_URL=http://{host}:{bound_port} ; export ANTHROPIC_AUTH_TOKEN=local",
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down", flush=True)
    finally:
        server.server_close()
    return server
