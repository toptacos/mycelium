from __future__ import annotations

from typing import Any

from mycelium.memory import KIND_FACT, KIND_PREFERENCE, VALID_KINDS
from mycelium.tools import Tool, ToolContext


async def remember(args: dict[str, Any], ctx: ToolContext) -> str:
    text = args["text"].strip()
    kind = args.get("kind", KIND_FACT)
    tags = args.get("tags") or []
    if not text:
        return "error: text is required"
    entry = ctx.memory.add(text, kind=kind, tags=[str(t) for t in tags], source="agent")
    return f"remembered as {entry.kind} (id={entry.id}, tags={entry.tags or '[]'})"


async def recall_memory(args: dict[str, Any], ctx: ToolContext) -> str:
    query = args["query"]
    k = int(args.get("k", 5))
    hits = ctx.memory.recall(query, k=k)
    if not hits:
        return f"no memories match {query!r}"
    lines = [f"top {len(hits)} memories for {query!r}:"]
    lines += [f"- ({e.kind}) {e.text}" for e in hits]
    return "\n".join(lines)


def memory_tools() -> list[Tool]:
    return [
        Tool(
            name="remember",
            description="Persist a fact, preference, or note to long-term memory. Recalled automatically on related future tasks.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "kind": {
                        "type": "string",
                        "enum": list(VALID_KINDS),
                        "default": KIND_FACT,
                    },
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["text"],
            },
            handler=remember,
            mutating=True,
        ),
        Tool(
            name="recall_memory",
            description="Search long-term memory for entries related to a query.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "k": {"type": "integer", "default": 5},
                },
                "required": ["query"],
            },
            handler=recall_memory,
        ),
    ]
