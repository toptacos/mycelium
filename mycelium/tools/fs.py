from __future__ import annotations

from pathlib import Path
from typing import Any

from mycelium.tools import Tool, ToolContext, resolve_in_workspace

MAX_READ_CHARS = 12000


async def fs_read(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx.workspace, args["path"])
    if not path.is_file():
        return f"error: not a file: {args['path']}"
    text = path.read_text(encoding="utf-8", errors="replace")
    truncated = len(text) > MAX_READ_CHARS
    if truncated:
        text = text[:MAX_READ_CHARS]
    rel = path.relative_to(ctx.workspace.resolve())
    header = f"# {rel} ({path.stat().st_size} bytes)"
    if truncated:
        header += f" [truncated to {MAX_READ_CHARS} chars]"
    return f"{header}\n{text}"


async def fs_write(args: dict[str, Any], ctx: ToolContext) -> str:
    path = resolve_in_workspace(ctx.workspace, args["path"])
    content = args.get("content", "")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    rel = path.relative_to(ctx.workspace.resolve())
    return f"wrote {len(content)} chars to {rel}"


async def fs_list(args: dict[str, Any], ctx: ToolContext) -> str:
    base = resolve_in_workspace(ctx.workspace, args.get("path", "."))
    if not base.is_dir():
        return f"error: not a directory: {args.get('path', '.')}"
    max_entries = int(args.get("max_entries", 200))
    lines: list[str] = []
    count = 0
    for p in sorted(base.rglob("*")):
        if any(
            part
            in {
                ".git",
                "__pycache__",
                ".venv",
                "node_modules",
                ".mypy_cache",
                ".pytest_cache",
            }
            for part in p.parts
        ):
            continue
        rel = p.relative_to(ctx.workspace.resolve())
        lines.append(("d " if p.is_dir() else "f ") + str(rel))
        count += 1
        if count >= max_entries:
            lines.append(f"... truncated at {max_entries} entries")
            break
    if not lines:
        return "(empty)"
    return "\n".join(lines)


async def fs_grep(args: dict[str, Any], ctx: ToolContext) -> str:
    import re

    pattern = args["pattern"]
    glob = args.get("glob", "*")
    base = resolve_in_workspace(ctx.workspace, args.get("path", "."))
    if not base.is_dir():
        return f"error: not a directory: {args.get('path', '.')}"
    rx = re.compile(pattern)
    hits: list[str] = []
    for p in sorted(base.rglob(glob)):
        if not p.is_file():
            continue
        if any(
            part in {".git", "__pycache__", ".venv", "node_modules"} for part in p.parts
        ):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if rx.search(line):
                rel = p.relative_to(ctx.workspace.resolve())
                hits.append(f"{rel}:{lineno}: {line.strip()[:160]}")
                if len(hits) >= 50:
                    return "\n".join(hits) + "\n... truncated at 50 hits"
    return "\n".join(hits) if hits else "(no matches)"


def fs_tools() -> list[Tool]:
    return [
        Tool(
            name="fs_read",
            description="Read a UTF-8 text file from the workspace. Returns content with a header.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path relative to workspace root",
                    }
                },
                "required": ["path"],
            },
            handler=fs_read,
        ),
        Tool(
            name="fs_write",
            description="Write text content to a file in the workspace, creating parent directories. Overwrites existing files.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
            handler=fs_write,
            mutating=True,
        ),
        Tool(
            name="fs_list",
            description="List files and directories in the workspace as a tree of relative paths.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "default": "."},
                    "max_entries": {"type": "integer", "default": 200},
                },
            },
            handler=fs_list,
        ),
        Tool(
            name="fs_grep",
            description="Search file contents with a regex. Returns matching lines as path:lineno: text.",
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "glob": {"type": "string", "default": "*"},
                    "path": {"type": "string", "default": "."},
                },
                "required": ["pattern"],
            },
            handler=fs_grep,
        ),
    ]
