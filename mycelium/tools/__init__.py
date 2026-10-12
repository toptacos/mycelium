from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable

from mycelium.memory import MemoryStore
from mycelium.telemetry import EventLog

ToolHandler = Callable[[dict[str, Any], "ToolContext"], Awaitable[str]]


class PolicyViolation(Exception):
    pass


class ToolFailure(Exception):
    """A tool ran correctly but its subject failed (e.g. a command exited
    non-zero). Carries the output so the receipt survives the failure."""

    def __init__(self, error: str, output: str = "") -> None:
        super().__init__(error)
        self.output = output


def resolve_in_workspace(workspace: Path, relative: str | Path) -> Path:
    """Resolve a user/model-supplied path, denying escapes via traversal or symlink tricks."""
    if not str(relative).strip():
        raise PolicyViolation("empty path")
    candidate = Path(relative).expanduser()
    target = (candidate if candidate.is_absolute() else workspace / candidate).resolve()
    ws = workspace.resolve()
    if target != ws and ws not in target.parents:
        raise PolicyViolation(f"path escapes workspace: {relative}")
    return target


@dataclass
class ToolContext:
    workspace: Path
    settings: Any
    memory: MemoryStore
    log: EventLog
    backend: Any = None
    runner: Any = None
    read_only: bool = False

    @property
    def connections(self) -> dict[str, dict]:
        return dict(self.settings.connections)


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: ToolHandler
    mutating: bool = False
    requires_net: bool = False


@dataclass
class CallResult:
    tool: str
    ok: bool
    output: str
    latency_ms: float
    error: str | None = None


class ToolRegistry:
    def __init__(self, tools: list[Tool] | None = None) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools or []:
            self.register(t)

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"duplicate tool name: {tool.name}")
        self._tools[tool.name] = tool
        return tool

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(name)
        return self._tools[name]

    def names(self) -> list[str]:
        return sorted(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def filter(
        self, *, include_mutating: bool = True, include_net: bool = True
    ) -> "ToolRegistry":
        return ToolRegistry(
            [
                t
                for t in self._tools.values()
                if (include_mutating or not t.mutating)
                and (include_net or not t.requires_net)
            ]
        )

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in self._tools.values()
        ]

    def describe(self) -> str:
        return "\n".join(
            f"- {t.name}: {t.description}" + (" [mutating]" if t.mutating else "")
            for t in self._tools.values()
        )

    async def call(
        self, name: str, args: dict[str, Any], ctx: ToolContext
    ) -> CallResult:
        import time

        from mycelium.telemetry import Timer

        timer = Timer()
        try:
            tool = self.get(name)
        except KeyError:
            output = (
                f"error: unknown tool {name!r}. available: {', '.join(self.names())}"
            )
            latency = timer.ms
            ctx.log.emit_tool(
                name=name, ok=False, latency_ms=latency, error="unknown tool"
            )
            return CallResult(
                tool=name,
                ok=False,
                output=output,
                latency_ms=latency,
                error="unknown tool",
            )

        if ctx.read_only and tool.mutating:
            output = f"error: tool {name!r} is mutating and this session is read-only"
            latency = timer.ms
            ctx.log.emit_tool(
                name=name, ok=False, latency_ms=latency, error="read-only session"
            )
            return CallResult(
                tool=name,
                ok=False,
                output=output,
                latency_ms=latency,
                error="read-only session",
            )

        if not isinstance(args, dict):
            args = {}

        try:
            output = await tool.handler(args, ctx)
            latency = timer.ms
            ctx.log.emit_tool(
                name=name, ok=True, latency_ms=latency, result_chars=len(output)
            )
            return CallResult(tool=name, ok=True, output=output, latency_ms=latency)
        except ToolFailure as exc:
            latency = timer.ms
            ctx.log.emit_tool(name=name, ok=False, latency_ms=latency, error=str(exc))
            return CallResult(tool=name, ok=False, output=exc.output, latency_ms=latency, error=str(exc))
        except PolicyViolation as exc:
            latency = timer.ms
            output = f"error: policy violation: {exc}"
            ctx.log.emit_tool(name=name, ok=False, latency_ms=latency, error=str(exc))
            return CallResult(
                tool=name, ok=False, output=output, latency_ms=latency, error=str(exc)
            )
        except Exception as exc:
            latency = timer.ms
            output = f"error: {type(exc).__name__}: {exc}"
            ctx.log.emit_tool(
                name=name,
                ok=False,
                latency_ms=latency,
                error=f"{type(exc).__name__}: {exc}",
            )
            return CallResult(
                tool=name, ok=False, output=output, latency_ms=latency, error=str(exc)
            )
