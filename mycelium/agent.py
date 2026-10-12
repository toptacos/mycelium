from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mycelium.backends import Backend, ChatResponse, repair_tool_calls
from mycelium.context import (
    ContextManager,
    estimate_messages_tokens,
    extractive_fallback_summary,
)
from mycelium.memory import MemoryStore, KIND_SUMMARY
from mycelium.telemetry import EventLog, Timer
from mycelium.tools import ToolContext, ToolRegistry, Tool


@dataclass
class AgentConfig:
    max_steps: int = 8
    temperature: float = 0.2
    max_tokens: int | None = 1536
    auto_compact: bool = True
    max_tool_result_chars: int = 8000


@dataclass
class AgentResult:
    content: str = ""
    steps: int = 0
    tool_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    compactions: int = 0
    tokens_reclaimed: int = 0
    ok: bool = True
    warning: str | None = None
    used_tools: list[str] = field(default_factory=list)


class Agent:
    def __init__(
        self,
        settings,
        backend: Backend,
        registry: ToolRegistry,
        memory: MemoryStore,
        log: EventLog,
        *,
        config: AgentConfig | None = None,
        runner: Any = None,
    ) -> None:
        self.settings = settings
        self.backend = backend
        self.registry = registry
        self.memory = memory
        self.log = log
        self.config = config or AgentConfig()
        self.context = ContextManager(
            window_tokens=settings.context_window,
            reserve_tokens=settings.reserve_tokens,
            compact_threshold=settings.compact_threshold,
        )
        self.ctx = ToolContext(
            workspace=settings.workspace,
            settings=settings,
            memory=memory,
            log=log,
            backend=backend,
            runner=runner,
            read_only=settings.read_only,
        )
        backend_name, model = settings.resolve_model()
        self.backend_name = backend_name
        self.model = model

    def system_prompt(self, task: str = "") -> str:
        recalled = self.memory.recall_text(task, k=5) if task else ""
        parts = [
            "You are mycelium, a local-first agent running entirely on the user's machine.",
            "You help with software development, research, content creation, and workflow automation.",
            "Use the provided tools to act on the workspace; prefer tools over guessing about files.",
            "Keep answers concise. When you create or modify files, say exactly which paths changed.",
        ]
        if recalled:
            parts.append(recalled)
        if self.ctx.read_only:
            parts.append("This session is READ-ONLY: mutating tools are disabled.")
        tools = self.registry.describe()
        if tools:
            parts.append("Available tools:\n" + tools)
        return "\n\n".join(parts)

    async def run(self, task: str) -> AgentResult:
        cfg = self.config
        result = AgentResult()
        system = self.system_prompt(task)
        self.context.set_system(system)
        self.context.add("user", task, pinned=True)
        self.log.emit(
            "agent_start",
            task=task[:200],
            model=f"{self.backend_name}:{self.model}",
            read_only=self.ctx.read_only,
        )

        tool_seq = 0
        for step in range(1, cfg.max_steps + 1):
            if cfg.auto_compact and self.context.needs_compaction():
                await self._compact()
            messages = self.context.messages()
            est = estimate_messages_tokens(messages)
            self.log.emit(
                "agent_step",
                step=step,
                context_tokens=self.context.used_tokens,
                budget=self.context.budget_tokens,
                usage=f"{self.context.usage_ratio:.0%}",
                est_messages_tokens=est,
            )
            try:
                timer = Timer()
                resp = await self.backend.chat(
                    messages,
                    model=self.model,
                    tools=self.registry.schemas(),
                    system=system,
                    temperature=cfg.temperature,
                    max_tokens=cfg.max_tokens,
                )
                latency_ms = timer.ms
            except Exception as exc:
                self.log.emit(
                    "agent_error", step=step, error=f"{type(exc).__name__}: {exc}"
                )
                result.ok = False
                result.warning = f"backend error: {type(exc).__name__}: {exc}"
                break

            tool_calls = resp.tool_calls
            if not tool_calls and not resp.content.strip():
                result.ok = False
                result.warning = "model returned empty response"
                break
            if not tool_calls and resp.content.strip():
                repaired = repair_tool_calls(resp.content, lambda: f"repair_{tool_seq}")
                if repaired:
                    tool_seq += 1
                    tool_calls = repaired
                    self.log.emit("tool_call_repaired", count=len(repaired))

            prompt_tokens = resp.prompt_tokens or est
            completion_tokens = resp.completion_tokens or 0
            result.prompt_tokens += prompt_tokens
            result.completion_tokens += completion_tokens
            self.log.emit_llm(
                model=f"{self.backend_name}:{self.model}",
                backend=self.backend_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                latency_ms=latency_ms,
                tool_calls=len(tool_calls),
            )

            self.context.add(
                "assistant",
                resp.content,
                tool_calls=[tc.__dict__ for tc in tool_calls] or None,
            )
            result.steps = step

            if not tool_calls:
                result.content = resp.content.strip()
                self._distill(task, result)
                self.log.emit(
                    "agent_finish",
                    steps=step,
                    tool_calls=result.tool_calls,
                    tokens=prompt_tokens + completion_tokens,
                )
                return result

            for tc in tool_calls:
                call = await self.registry.call(tc.name, tc.arguments or {}, self.ctx)
                result.tool_calls += 1
                result.used_tools.append(tc.name)
                output = call.output
                if len(output) > cfg.max_tool_result_chars:
                    output = (
                        output[: cfg.max_tool_result_chars]
                        + f"\n... [truncated {len(output) - cfg.max_tool_result_chars} chars]"
                    )
                self.context.add("tool", output, tool_call_id=tc.id, name=tc.name)
        else:
            result.ok = False
            result.warning = (
                f"step budget ({cfg.max_steps}) exhausted before completion"
            )

        self.log.emit(
            "agent_stop", steps=result.steps, tool_calls=result.tool_calls, ok=result.ok
        )
        return result

    async def _compact(self) -> None:
        plan = self.context.plan_compaction()
        if plan is None:
            return
        summary_source = "\n\n".join(
            f"{t.role}: {t.content[:500]}" for t in plan.drop_turns if t.content
        )
        summary = ""
        try:
            resp = await self.backend.chat(
                [
                    {
                        "role": "system",
                        "content": "Summarize this conversation history into at most 8 terse bullet points. Preserve file paths, decisions, tool names, and any numbers.",
                    },
                    {"role": "user", "content": summary_source[:16000]},
                ],
                model=self.model,
                max_tokens=256,
            )
            summary = resp.content.strip()
        except Exception:
            summary = ""
        if not summary:
            summary = extractive_fallback_summary(plan.drop_turns)
        event = self.context.apply(summary, plan)
        self.log.emit(
            "compaction",
            turns_dropped=event.turns_dropped,
            tokens_before=event.tokens_before,
            tokens_after=event.tokens_after,
            reclaimed=event.reclaimed,
            summarizer="llm"
            if summary and not summary.startswith("\n-")
            else "extractive",
        )

    def _distill(self, task: str, result: AgentResult) -> None:
        if not result.ok or not result.content:
            return
        try:
            summary = f"Task: {task[:120]}\nOutcome: {result.content[:400]}"
            tags = sorted(
                {w.lower() for w in task.replace(".", " ").split() if len(w) > 4}
            )[:5]
            self.memory.add(summary, kind=KIND_SUMMARY, tags=tags, source="distill")
        except Exception:
            pass
