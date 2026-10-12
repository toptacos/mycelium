from __future__ import annotations

import json
import statistics
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_session_id() -> str:
    return f"s_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"


class EventLog:
    def __init__(
        self,
        path: Path,
        session_id: str | None = None,
        verbose: bool = False,
        console: TextIO | None = None,
    ) -> None:
        self.path = Path(path)
        self.session_id = session_id or new_session_id()
        self.verbose = verbose
        self.console = console
        self.events: list[dict[str, Any]] = []
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **fields: Any) -> dict[str, Any]:
        record: dict[str, Any] = {
            "ts": utc_now(),
            "session": self.session_id,
            "event": event,
        }
        record.update(fields)
        self.events.append(record)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, default=str) + "\n")
        if self.verbose:
            detail = " ".join(
                f"{k}={_short(v)}" for k, v in fields.items() if k not in ("messages",)
            )
            print(f"[{record['ts'][11:23]}] {event} {detail}", file=self.console)
        return record

    def emit_llm(
        self,
        *,
        model: str,
        backend: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        tool_calls: int = 0,
        error: str | None = None,
    ) -> None:
        self.emit(
            "llm_call",
            model=model,
            backend=backend,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=round(latency_ms, 1),
            tool_calls=tool_calls,
            error=error,
        )

    def emit_tool(
        self,
        *,
        name: str,
        ok: bool,
        latency_ms: float,
        result_chars: int = 0,
        error: str | None = None,
    ) -> None:
        self.emit(
            "tool_call",
            tool=name,
            ok=ok,
            latency_ms=round(latency_ms, 1),
            result_chars=result_chars,
            error=error,
        )


def _short(value: Any, limit: int = 60) -> str:
    s = str(value)
    return s if len(s) <= limit else s[: limit - 1] + "~"


@dataclass
class SessionAnalysis:
    path: str
    session_id: str = ""
    events: int = 0
    llm_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latencies_ms: list[float] = field(default_factory=list)
    tool_calls: int = 0
    tool_errors: int = 0
    tools_by_name: dict[str, int] = field(default_factory=dict)
    compactions: int = 0
    tokens_reclaimed: int = 0
    errors: int = 0
    error_messages: list[str] = field(default_factory=list)
    steps: int = 0
    wall_ms: float = 0.0

    def summary_lines(self) -> list[str]:
        lat = self.latencies_ms
        lines = [
            f"session        : {self.session_id or 'unknown'}",
            f"events         : {self.events}",
            f"agent steps    : {self.steps}",
            f"llm calls      : {self.llm_calls}",
            f"tokens         : {self.prompt_tokens} prompt + {self.completion_tokens} completion = {self.prompt_tokens + self.completion_tokens}",
            f"tool calls     : {self.tool_calls} ({self.tool_errors} errors)",
            f"compactions    : {self.compactions} ({self.tokens_reclaimed} tokens reclaimed)",
            f"errors         : {self.errors}",
        ]
        if lat:
            lines.append(
                f"llm latency ms : avg {statistics.fmean(lat):.0f} / p50 {statistics.median(lat):.0f} / max {max(lat):.0f}"
            )
        if self.tools_by_name:
            breakdown = ", ".join(
                f"{k} x{v}"
                for k, v in sorted(self.tools_by_name.items(), key=lambda kv: -kv[1])
            )
            lines.append(f"tool usage     : {breakdown}")
        if self.wall_ms:
            lines.append(f"wall clock     : {self.wall_ms:.0f} ms")
        if self.error_messages:
            lines.append("error detail   :")
            lines.extend(f"  - {m}" for m in self.error_messages[:10])
        return lines


def analyze_session(path: str | Path) -> SessionAnalysis:
    path = Path(path)
    analysis = SessionAnalysis(path=str(path))
    first_ts: float | None = None
    last_ts: float | None = None

    def ts_of(rec: dict) -> float | None:
        raw = rec.get("ts")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw).timestamp()
        except ValueError:
            return None

    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            analysis.events += 1
            analysis.session_id = analysis.session_id or rec.get("session", "")
            ev = rec.get("event")
            t = ts_of(rec)
            if t is not None:
                first_ts = t if first_ts is None else min(first_ts, t)
                last_ts = t if last_ts is None else max(last_ts, t)
            if ev == "llm_call":
                analysis.llm_calls += 1
                analysis.prompt_tokens += rec.get("prompt_tokens", 0)
                analysis.completion_tokens += rec.get("completion_tokens", 0)
                analysis.latencies_ms.append(rec.get("latency_ms", 0.0))
                analysis.tool_calls += rec.get("tool_calls", 0)
                if rec.get("error"):
                    analysis.errors += 1
                    analysis.error_messages.append(f"llm: {rec['error']}")
            elif ev == "tool_call":
                analysis.tool_calls += 1
                analysis.tools_by_name[rec.get("tool", "?")] = (
                    analysis.tools_by_name.get(rec.get("tool", "?"), 0) + 1
                )
                if not rec.get("ok", True):
                    analysis.tool_errors += 1
                    analysis.errors += 1
                    analysis.error_messages.append(
                        f"tool {rec.get('tool')}: {rec.get('error')}"
                    )
            elif ev == "compaction":
                analysis.compactions += 1
                analysis.tokens_reclaimed += rec.get("reclaimed", 0)
            elif ev == "agent_step":
                analysis.steps += 1
            elif ev in ("error", "agent_error", "workflow_error"):
                analysis.errors += 1
                analysis.error_messages.append(f"{ev}: {rec.get('error', '')}")

    if first_ts is not None and last_ts is not None:
        analysis.wall_ms = (last_ts - first_ts) * 1000
    return analysis


class Timer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    @property
    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000
