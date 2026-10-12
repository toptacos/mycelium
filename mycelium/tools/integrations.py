from __future__ import annotations

import json
from typing import Any

from mycelium.tools import Tool, ToolContext, PolicyViolation

DEFAULT_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]
MAX_RESPONSE_CHARS = 4000


async def call_api(args: dict[str, Any], ctx: ToolContext) -> str:
    import httpx

    name = args["connection"]
    method = (args.get("method") or "GET").upper()
    path = args.get("path", "/")
    body = args.get("body")
    query = args.get("query")

    profile = ctx.connections.get(name)
    if profile is None:
        known = ", ".join(sorted(ctx.connections)) or "(none configured)"
        return f"error: unknown connection {name!r}; configured: {known}"

    base_url = profile.get("base_url", "").rstrip("/")
    if not base_url.startswith(("http://", "https://")):
        return f"error: connection {name!r} has invalid base_url"

    allowed = [m.upper() for m in profile.get("methods", DEFAULT_METHODS)]
    if method not in allowed:
        return f"error: method {method} not allowed for connection {name!r}; allowed: {', '.join(allowed)}"

    headers = dict(profile.get("headers", {}))
    auth_env = profile.get("auth_env")
    if auth_env:
        import os

        token = os.environ.get(auth_env)
        if not token:
            if profile.get("auth_optional"):
                pass
            else:
                return f"error: env var {auth_env} for connection {name!r} is not set"
        elif token:
            headers[profile.get("auth_header", "Authorization")] = f"Bearer {token}"

    url = base_url + (path if path.startswith("/") else "/" + path)
    async with httpx.AsyncClient(
        timeout=float(profile.get("timeout_s", 20)), headers=headers
    ) as client:
        resp = await client.request(
            method, url, params=query, json=body if body is not None else None
        )
        text = resp.text
        truncated = len(text) > MAX_RESPONSE_CHARS
        if truncated:
            text = text[:MAX_RESPONSE_CHARS]

    lines = [
        f"connection: {name}",
        f"request: {method} {url}",
        f"status: {resp.status_code}",
    ]
    try:
        pretty = json.dumps(resp.json(), indent=2)
    except (json.JSONDecodeError, ValueError):
        pretty = text
    if truncated:
        pretty += f"\n... [truncated at {MAX_RESPONSE_CHARS} chars]"
    return "\n".join(lines) + f"\nbody:\n{pretty}"


def integrations_tool() -> Tool:
    return Tool(
        name="call_api",
        description=(
            "Call a configured third-party HTTP API. Connections are named profiles in mycelium.toml "
            "with a base_url and an auth_env naming the environment variable holding the token. "
            "The token is read from the environment at call time and never logged."
        ),
        parameters={
            "type": "object",
            "properties": {
                "connection": {
                    "type": "string",
                    "description": "Connection profile name",
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
                    "default": "GET",
                },
                "path": {"type": "string", "default": "/"},
                "body": {
                    "type": "object",
                    "description": "JSON request body (optional)",
                },
                "query": {
                    "type": "object",
                    "description": "Query parameters (optional)",
                },
            },
            "required": ["connection"],
        },
        handler=call_api,
        requires_net=True,
        mutating=True,
    )
