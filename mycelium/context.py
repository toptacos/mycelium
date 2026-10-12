from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN))


def estimate_messages_tokens(messages: list[dict[str, Any]]) -> int:
    total = 0
    for m in messages:
        total += estimate_tokens(m.get("content", "") or "")
        if m.get("tool_calls"):
            total += estimate_tokens(str(m["tool_calls"]))
        total += 4
    return total


@dataclass
class Turn:
    role: str
    content: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None
    tokens: int = 0
    pinned: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "name": self.name,
        }


@dataclass
class CompactionEvent:
    turns_dropped: int
    tokens_before: int
    tokens_after: int
    summary_tokens: int

    @property
    def reclaimed(self) -> int:
        return max(0, self.tokens_before - self.tokens_after)


@dataclass
class CompactionPlan:
    drop_turns: list[Turn]
    tokens_before: int
    projected_tokens_after: int

    @property
    def reclaims(self) -> int:
        return max(0, self.tokens_before - self.projected_tokens_after)


class ContextManager:
    """Tracks a token budget and compacts middle turns when the window fills."""

    def __init__(
        self,
        window_tokens: int = 32768,
        reserve_tokens: int = 1024,
        compact_threshold: float = 0.8,
        keep_recent: int = 6,
    ) -> None:
        if not 0.1 <= compact_threshold <= 1.0:
            raise ValueError("compact_threshold must be within [0.1, 1.0]")
        self.window_tokens = window_tokens
        self.reserve_tokens = reserve_tokens
        self.compact_threshold = compact_threshold
        self.keep_recent = keep_recent
        self.turns: list[Turn] = []
        self.system_tokens = 0
        self.compaction_events: list[CompactionEvent] = []

    @property
    def budget_tokens(self) -> int:
        return max(256, self.window_tokens - self.reserve_tokens)

    @property
    def used_tokens(self) -> int:
        return self.system_tokens + sum(t.tokens for t in self.turns)

    @property
    def headroom(self) -> int:
        return max(0, self.budget_tokens - self.used_tokens)

    @property
    def usage_ratio(self) -> float:
        return self.used_tokens / self.budget_tokens if self.budget_tokens else 1.0

    def set_system(self, system_prompt: str) -> None:
        self.system_tokens = estimate_tokens(system_prompt)

    def add(
        self,
        role: str,
        content: str = "",
        *,
        tool_calls: list[dict[str, Any]] | None = None,
        tool_call_id: str | None = None,
        name: str | None = None,
        pinned: bool = False,
    ) -> Turn:
        turn = Turn(
            role=role,
            content=content,
            tool_calls=list(tool_calls or []),
            tool_call_id=tool_call_id,
            name=name,
            pinned=pinned,
        )
        turn.tokens = (
            estimate_tokens(content)
            + (estimate_tokens(str(tool_calls)) if turn.tool_calls else 0)
            + 4
        )
        self.turns.append(turn)
        return turn

    def needs_compaction(self) -> bool:
        return self.usage_ratio >= self.compact_threshold

    def plan_compaction(self, summary_estimate: int = 64) -> CompactionPlan | None:
        candidates = [t for t in self.turns if not t.pinned]
        if len(candidates) <= self.keep_recent:
            return None
        keep_set = set(id(t) for t in candidates[-self.keep_recent :])
        droppable = [t for t in candidates if id(t) not in keep_set]
        if not droppable:
            return None
        tokens_before = self.used_tokens
        dropped_tokens = sum(t.tokens for t in droppable)
        kept_tokens = tokens_before - dropped_tokens + summary_estimate
        plan = CompactionPlan(
            drop_turns=droppable,
            tokens_before=tokens_before,
            projected_tokens_after=kept_tokens,
        )
        return plan if plan.reclaims > 0 else None

    def apply(self, summary_text: str, plan: CompactionPlan) -> CompactionEvent:
        dropped_ids = set(id(t) for t in plan.drop_turns)
        self.turns = [t for t in self.turns if id(t) not in dropped_ids]
        summary_turn = Turn(
            role="system",
            content=f"[compaction summary of {len(plan.drop_turns)} earlier turns]\n{summary_text}",
        )
        summary_turn.tokens = estimate_tokens(summary_turn.content) + 4
        self.turns.insert(0, summary_turn)
        event = CompactionEvent(
            turns_dropped=len(plan.drop_turns),
            tokens_before=plan.tokens_before,
            tokens_after=self.used_tokens,
            summary_tokens=summary_turn.tokens,
        )
        self.compaction_events.append(event)
        return event

    def messages(self) -> list[dict[str, Any]]:
        return [t.to_dict() for t in self.turns]


def extractive_fallback_summary(
    turns: list[Turn], max_sentences_per_turn: int = 1
) -> str:
    """Deterministic, offline compaction summary: first sentence of each dropped turn."""
    lines: list[str] = []
    for t in turns:
        text = (t.content or "").strip()
        if not text:
            label = t.name or "tool"
            lines.append(f"- {t.role}({label}): no content")
            continue
        sentences = [
            s.strip() for s in text.replace("\n", " ").split(". ") if s.strip()
        ]
        snippet = ". ".join(sentences[:max_sentences_per_turn])
        lines.append(f"- {t.role}: {snippet[:200]}")
    return "\n".join(lines) if lines else "(nothing to summarize)"
