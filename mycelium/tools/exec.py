from __future__ import annotations

import asyncio
import shlex
from pathlib import Path
from typing import Any

from mycelium.tools import (
    Tool,
    ToolContext,
    PolicyViolation,
    ToolFailure,
    resolve_in_workspace,
)

DEFAULT_ALLOW = (
    "uv",
    "pytest",
    "git",
    "python",
    "python3",
    "node",
    "npm",
    "ollama",
    "ruff",
    "mypy",
)
DEFAULT_TIMEOUT_S = 600
MAX_OUTPUT_CHARS = 8000


def allowed_commands(ctx: ToolContext) -> list[str]:
    configured = getattr(ctx.settings, "command_allow", None)
    return list(configured) if configured else list(DEFAULT_ALLOW)


def command_timeout(ctx: ToolContext) -> int:
    return int(
        getattr(ctx.settings, "command_timeout_s", DEFAULT_TIMEOUT_S)
        or DEFAULT_TIMEOUT_S
    )


async def run_command(args: dict[str, Any], ctx: ToolContext) -> str:
    command = (args.get("command") or "").strip()
    if not command:
        return "error: command is required"
    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return f"error: could not parse command (quoting?): {exc}"
    if not argv:
        return "error: empty command"

    executable = Path(argv[0]).name
    allow = allowed_commands(ctx)
    if executable not in allow:
        raise PolicyViolation(
            f"executable {executable!r} is not in the command allowlist; allowed: {', '.join(allow)} "
            "(configure [commands] allow in mycelium.toml)"
        )

    workspace = resolve_in_workspace(ctx.workspace, args.get("cwd", "."))
    if not workspace.is_dir():
        return f"error: not a directory: {args.get('cwd', '.')}"

    timeout_s = int(args.get("timeout_s") or command_timeout(ctx))
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            cwd=str(workspace),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
    except FileNotFoundError:
        return f"error: {executable} not found on PATH"
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_s)
    except asyncio.TimeoutError:
        proc.kill()
        return f"error: command timed out after {timeout_s}s: {command}"

    text = stdout.decode("utf-8", "replace")
    truncated = len(text) > MAX_OUTPUT_CHARS
    if truncated:
        text = (
            text[:MAX_OUTPUT_CHARS]
            + f"\n... [truncated {len(text) - MAX_OUTPUT_CHARS} chars]"
        )
    status = "exit 0" if proc.returncode == 0 else f"exit {proc.returncode}"
    body = (
        f"$ {command}\n{status} (cwd {args.get('cwd', '.')}, {timeout_s}s cap)\n{text}"
    )
    if proc.returncode != 0:
        raise ToolFailure(f"{argv[0]} {status}", output=body)
    return body


def exec_tool() -> Tool:
    return Tool(
        name="run_command",
        description=(
            "Run an allowlisted executable in the workspace and return its combined "
            "output and exit code. The executable must be in the allowlist (default: "
            "uv, pytest, git, python, python3, node, npm, ollama, ruff, mypy). "
            "Used for local CI: running tests, builds, and checks. No shell is "
            "involved, so shell metacharacters are inert."
        ),
        parameters={
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "argv string, e.g. 'uv run pytest -q'",
                },
                "cwd": {
                    "type": "string",
                    "default": ".",
                    "description": "directory relative to workspace",
                },
                "timeout_s": {"type": "integer", "default": 600},
            },
            "required": ["command"],
        },
        handler=run_command,
        mutating=True,
    )
