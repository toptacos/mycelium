from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

MAX_RETRIES = 3
RETRY_BASE_S = 0.5
RETRYABLE_STATUSES = (429, 500, 502, 503, 504)

_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class ChatResponse:
    content: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)


class Backend(Protocol):
    name: str

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        model: str,
        tools: list[dict[str, Any]] | None = None,
        system: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
    ) -> ChatResponse: ...

    async def aclose(self) -> None: ...


def _extract_tool_payload(payload: dict) -> tuple[str | None, dict | None]:
    name = payload.get("name") or payload.get("tool")
    args = payload.get("arguments")
    if args is None:
        args = payload.get("args")
    if args is None:
        args = payload.get("parameters")
    if args is None:
        args = payload.get("input")
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            args = {"_raw": args}
    if name and isinstance(args, dict):
        return str(name), args
    return None, None


def repair_tool_calls(content: str, next_id) -> list[ToolCall]:
    """Convert models that emit tool calls as text (fenced JSON, XML, or a bare
    leading JSON object) into structured tool calls."""
    if not content:
        return []
    found: list[ToolCall] = []
    for match in _FENCE_RE.finditer(content):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        name, args = (
            _extract_tool_payload(payload)
            if isinstance(payload, dict)
            else (None, None)
        )
        if name:
            found.append(ToolCall(id=next_id(), name=name, arguments=args))
    if found:
        return found
    for match in re.finditer(
        r"<tool_use>\s*(\{.*?\})\s*</tool_use>", content, re.DOTALL
    ):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            name, args = _extract_tool_payload(payload)
            if name:
                found.append(ToolCall(id=next_id(), name=name, arguments=args))
    if found:
        return found
    stripped = content.strip()
    if stripped.startswith("{"):
        try:
            payload, _ = json.JSONDecoder().raw_decode(stripped)
            if isinstance(payload, dict):
                name, args = _extract_tool_payload(payload)
                if name:
                    found.append(ToolCall(id=next_id(), name=name, arguments=args))
        except json.JSONDecodeError:
            pass
    return found
    for match in re.finditer(
        r"<tool_use>\s*(\{.*?\})\s*</tool_use>", content, re.DOTALL
    ):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        name = payload.get("name") or payload.get("tool")
        args = payload.get("arguments") or payload.get("args") or {}
        if name and isinstance(args, dict):
            found.append(ToolCall(id=next_id(), name=str(name), arguments=args))
    return found


def _split_system(
    messages: list[dict[str, Any]], system: str | None
) -> tuple[str | None, list[dict[str, Any]]]:
    sys_parts: list[str] = []
    rest: list[dict[str, Any]] = []
    if system:
        sys_parts.append(system)
    for m in messages:
        if m.get("role") == "system":
            sys_parts.append(m.get("content", ""))
        else:
            rest.append(m)
    return ("\n\n".join(p for p in sys_parts if p) or None), rest


class _HTTPBackendBase:
    def __init__(
        self, name: str, base_url: str, api_key: str | None, timeout_s: float = 120.0
    ) -> None:
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._timeout = timeout_s
        self._client = None

    async def _http(self):
        if self._client is None:
            import httpx

            headers = {"User-Agent": f"mycelium/0.1 (+local-first-agent)"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=httpx.Timeout(self._timeout),
            )
        return self._client

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _post(self, url: str, json_body: dict, *, attempts: int = MAX_RETRIES):
        import asyncio

        import httpx

        client = await self._http()
        last_error = "unknown"
        for attempt in range(attempts):
            try:
                resp = await client.post(url, json=json_body)
                if resp.status_code in RETRYABLE_STATUSES:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    if attempt < attempts - 1:
                        await asyncio.sleep(RETRY_BASE_S * (2**attempt))
                        continue
                    break
                resp.raise_for_status()
                return resp.json()
            except (
                httpx.ConnectError,
                httpx.ReadTimeout,
                httpx.RemoteProtocolError,
            ) as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempt < attempts - 1:
                    await asyncio.sleep(RETRY_BASE_S * (2**attempt))
        raise RuntimeError(
            f"backend {self.name} failed after {attempts} attempts: {last_error}"
        )


class OllamaBackend(_HTTPBackendBase):
    """Native Ollama /api/chat. The OpenAI-compatible /v1 path silently ignores num_ctx."""

    async def chat(
        self,
        messages,
        *,
        model,
        tools=None,
        system=None,
        temperature=0.2,
        max_tokens=None,
    ) -> ChatResponse:
        sys_msg, rest = _split_system(messages, system)
        body: dict[str, Any] = {
            "model": model,
            "messages": rest,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            body["options"]["num_predict"] = max_tokens
        if sys_msg:
            body["system"] = sys_msg
        if tools:
            body["tools"] = tools
        data = await self._post("/api/chat", body)
        msg = data.get("message", {})
        tool_calls = [
            ToolCall(
                id=f"call_{i}",
                name=tc.get("function", {}).get("name", ""),
                arguments=tc.get("function", {}).get("arguments", {}) or {},
            )
            for i, tc in enumerate(msg.get("tool_calls", []))
        ]
        content = msg.get("content", "") or ""
        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            model=data.get("model", model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            raw=data,
        )


class OpenAICompatBackend(_HTTPBackendBase):
    """OpenAI-compatible /chat/completions: OpenRouter, llama.cpp, vLLM, LM Studio, DeepSeek."""

    async def chat(
        self,
        messages,
        *,
        model,
        tools=None,
        system=None,
        temperature=0.2,
        max_tokens=None,
    ) -> ChatResponse:
        sys_msg, rest = _split_system(messages, system)
        outbound: list[dict[str, Any]] = []
        if sys_msg:
            outbound.append({"role": "system", "content": sys_msg})
        outbound.extend(rest)
        body: dict[str, Any] = {
            "model": model,
            "messages": outbound,
            "temperature": temperature,
        }
        if max_tokens:
            body["max_tokens"] = max_tokens
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        data = await self._post("/chat/completions", body)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message", {})
        tool_calls = []
        for i, tc in enumerate(msg.get("tool_calls", []) or []):
            fn = tc.get("function", {})
            args_raw = fn.get("arguments", "{}")
            if isinstance(args_raw, str):
                try:
                    args = json.loads(args_raw) if args_raw.strip() else {}
                except json.JSONDecodeError:
                    args = {"_raw": args_raw}
            else:
                args = args_raw or {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id") or f"call_{i}",
                    name=fn.get("name", ""),
                    arguments=args,
                )
            )
        usage = data.get("usage", {})
        return ChatResponse(
            content=msg.get("content", "") or "",
            tool_calls=tool_calls,
            model=data.get("model", model),
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            raw=data,
        )


class GeminiBackend(_HTTPBackendBase):
    async def chat(
        self,
        messages,
        *,
        model,
        tools=None,
        system=None,
        temperature=0.2,
        max_tokens=None,
    ) -> ChatResponse:
        sys_msg, rest = _split_system(messages, system)
        contents: list[dict[str, Any]] = []
        for m in rest:
            role = "model" if m.get("role") == "assistant" else "user"
            parts: list[dict[str, Any]] = []
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    parts.append(
                        {
                            "functionCall": {
                                "name": tc["function"]["name"],
                                "args": json.loads(tc["function"]["arguments"] or "{}"),
                            }
                        }
                    )
            elif m.get("role") == "tool":
                parts.append(
                    {
                        "functionResponse": {
                            "name": m.get("name", "tool"),
                            "response": {"result": m.get("content", "")},
                        }
                    }
                )
            elif m.get("content"):
                parts.append({"text": m["content"]})
            if parts:
                contents.append({"role": role, "parts": parts})
        body: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens or 2048,
            },
        }
        if sys_msg:
            body["systemInstruction"] = {"parts": [{"text": sys_msg}]}
        if tools:
            body["tools"] = [{"function_declarations": [t["function"] for t in tools]}]
        url = f"/models/{model}:generateContent"
        if self.api_key:
            url += f"?key={self.api_key}"
        data = await self._post(url, body)
        cand = (data.get("candidates") or [{}])[0]
        parts = (cand.get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts if "text" in p)
        tool_calls = [
            ToolCall(
                id=f"call_{i}",
                name=p["functionCall"].get("name", ""),
                arguments=p["functionCall"].get("args", {}) or {},
            )
            for i, p in enumerate(parts)
            if "functionCall" in p
        ]
        usage = data.get("usageMetadata", {})
        return ChatResponse(
            content=text,
            tool_calls=tool_calls,
            model=model,
            prompt_tokens=usage.get("promptTokenCount", 0),
            completion_tokens=usage.get("candidatesTokenCount", 0),
            raw=data,
        )


class AnthropicBackend(_HTTPBackendBase):
    async def chat(
        self,
        messages,
        *,
        model,
        tools=None,
        system=None,
        temperature=0.2,
        max_tokens=None,
    ) -> ChatResponse:
        sys_msg, rest = _split_system(messages, system)
        outbound: list[dict[str, Any]] = []
        for m in rest:
            role = m.get("role")
            if role == "tool":
                outbound.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": m.get("tool_call_id"),
                                "content": m.get("content", ""),
                            }
                        ],
                    }
                )
                continue
            blocks: list[dict[str, Any]] = []
            if m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": json.loads(tc["function"]["arguments"] or "{}"),
                        }
                    )
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            if blocks:
                outbound.append(
                    {
                        "role": "assistant" if role == "assistant" else "user",
                        "content": blocks,
                    }
                )
        body: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens or 2048,
            "messages": outbound,
            "temperature": temperature,
        }
        if sys_msg:
            body["system"] = sys_msg
        if tools:
            body["tools"] = [
                {
                    "name": t["function"]["name"],
                    "description": t["function"]["description"],
                    "input_schema": t["function"]["parameters"],
                }
                for t in tools
            ]
        import httpx

        client = await self._http()
        resp = await client.post(
            "/v1/messages", json=body, headers={"anthropic-version": "2023-06-01"}
        )
        resp.raise_for_status()
        data = resp.json()
        text = ""
        tool_calls = []
        for i, block in enumerate(data.get("content", [])):
            if block.get("type") == "text":
                text += block.get("text", "")
            elif block.get("type") == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.get("id") or f"call_{i}",
                        name=block.get("name", ""),
                        arguments=block.get("input", {}) or {},
                    )
                )
        usage = data.get("usage", {})
        return ChatResponse(
            content=text,
            tool_calls=tool_calls,
            model=data.get("model", model),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            raw=data,
        )


class ScriptedBackend:
    """Deterministic test double: returns queued ChatResponses and records every call."""

    name = "scripted"

    def __init__(
        self,
        responses: list[ChatResponse] | None = None,
        default: ChatResponse | None = None,
    ) -> None:
        self.responses = list(responses or [])
        self.default = default or ChatResponse(content="scripted: ok")
        self.calls: list[dict[str, Any]] = []

    def push(self, *responses: ChatResponse) -> None:
        self.responses.extend(responses)

    async def chat(
        self,
        messages,
        *,
        model,
        tools=None,
        system=None,
        temperature=0.2,
        max_tokens=None,
    ) -> ChatResponse:
        self.calls.append(
            {
                "messages": [dict(m) for m in messages],
                "model": model,
                "tools": tools,
                "system": system,
            }
        )
        if self.responses:
            resp = self.responses.pop(0)
            resp.model = resp.model or model
            return resp
        return ChatResponse(content=self.default.content, model=model)

    async def aclose(self) -> None:  # pragma: no cover - trivial
        return None


def make_backend(
    kind: str, name: str, base_url: str, api_key: str | None
) -> _HTTPBackendBase | ScriptedBackend:
    kind = kind.lower()
    if kind == "scripted":
        return ScriptedBackend()
    if kind == "ollama":
        # local CPU inference can legitimately take minutes per turn
        return OllamaBackend(name, base_url, api_key, timeout_s=600.0)
    if kind == "gemini":
        return GeminiBackend(name, base_url, api_key)
    if kind == "anthropic":
        return AnthropicBackend(name, base_url, api_key)
    return OpenAICompatBackend(name, base_url, api_key)
