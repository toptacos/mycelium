from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from mycelium.tools import ToolContext
from mycelium.telemetry import EventLog, Timer

_VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][\w]*(?:\.[\w-]+)*)\s*\}\}")


class WorkflowError(Exception):
    pass


@dataclass
class Step:
    id: str
    tool: str | None = None
    llm: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    prompt: str | None = None
    on_error: str = "fail"

    @property
    def is_llm(self) -> bool:
        return self.llm is not None


@dataclass
class Workflow:
    name: str
    description: str
    inputs: dict[str, Any]
    steps: list[Step]
    source: Path | None = None

    def required_inputs(self) -> list[str]:
        return [
            k
            for k, v in self.inputs.items()
            if not isinstance(v, dict) or "default" not in v
        ]


def load_workflow(path: str | Path) -> Workflow:
    path = Path(path)
    if not path.is_file():
        raise WorkflowError(f"workflow file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise WorkflowError(f"workflow {path} must be a YAML mapping")
    steps: list[Step] = []
    for raw in data.get("steps", []):
        sid = str(raw.get("id", f"step_{len(steps) + 1}"))
        steps.append(
            Step(
                id=sid,
                tool=raw.get("tool"),
                llm=raw.get("llm"),
                args=dict(raw.get("args", {})),
                prompt=raw.get("prompt"),
                on_error=raw.get("on_error", "fail"),
            )
        )
    if not steps:
        raise WorkflowError(f"workflow {path} has no steps")
    ids = [s.id for s in steps]
    if len(set(ids)) != len(ids):
        raise WorkflowError(f"workflow {path} has duplicate step ids: {ids}")
    return Workflow(
        name=str(data.get("name", path.stem)),
        description=str(data.get("description", "")),
        inputs=dict(data.get("inputs", {})),
        steps=steps,
        source=path,
    )


def substitute(value: Any, scope: dict[str, Any]) -> Any:
    if isinstance(value, str):

        def repl(match: re.Match) -> str:
            ref = match.group(1)
            if ref in scope:
                return str(scope[ref])
            cur: Any = scope
            for part in ref.split("."):
                if isinstance(cur, dict) and part in cur:
                    cur = cur[part]
                else:
                    return match.group(0)
            return str(cur)

        return _VAR_RE.sub(repl, value)
    if isinstance(value, list):
        return [substitute(v, scope) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, scope) for k, v in value.items()}
    return value


@dataclass
class StepResult:
    id: str
    ok: bool
    output: str
    latency_ms: float
    error: str | None = None


@dataclass
class WorkflowResult:
    workflow: str
    ok: bool
    steps: list[StepResult] = field(default_factory=list)
    outputs: dict[str, str] = field(default_factory=dict)
    checkpoint: Path | None = None
    dry_run: bool = False
    resumed: bool = False

    @property
    def failed_step(self) -> StepResult | None:
        for s in self.steps:
            if not s.ok:
                return s
        return None


class WorkflowRunner:
    def __init__(
        self, registry, ctx: ToolContext, checkpoint_dir: Path | None = None
    ) -> None:
        self.registry = registry
        self.ctx = ctx
        self.checkpoint_dir = (
            Path(checkpoint_dir)
            if checkpoint_dir
            else ctx.workspace / ".mycelium" / "checkpoints"
        )

    def _checkpoint_path(self, name: str) -> Path:
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        return self.checkpoint_dir / f"{name}.json"

    def _load_checkpoint(self, name: str) -> dict[str, Any]:
        path = self._checkpoint_path(name)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}

    def _write_checkpoint(
        self,
        name: str,
        completed: list[str],
        outputs: dict[str, str],
        inputs: dict[str, Any],
        source: str,
    ) -> Path:
        path = self._checkpoint_path(name)
        path.write_text(
            json.dumps(
                {
                    "workflow": name,
                    "source": source,
                    "inputs": inputs,
                    "completed": completed,
                    "outputs": outputs,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return path

    async def run(
        self,
        workflow: Workflow | str | Path,
        inputs: dict[str, Any] | None = None,
        *,
        dry_run: bool = False,
        resume: bool = False,
    ) -> WorkflowResult:
        if isinstance(workflow, (str, Path)):
            workflow = load_workflow(workflow)
        inputs = dict(inputs or {})
        for key, spec in workflow.inputs.items():
            if key not in inputs:
                if isinstance(spec, dict) and "default" in spec:
                    inputs[key] = spec["default"]
                elif key in workflow.required_inputs():
                    raise WorkflowError(
                        f"missing required input {key!r} for workflow {workflow.name!r}"
                    )

        log = self.ctx.log
        result = WorkflowResult(workflow=workflow.name, ok=True, dry_run=dry_run)

        if dry_run:
            scope = self._build_scope(inputs, {})
            for step in workflow.steps:
                rendered = substitute({"args": step.args, "prompt": step.prompt}, scope)
                log.emit(
                    "workflow_step_planned",
                    workflow=workflow.name,
                    step=step.id,
                    dry_run=True,
                )
                result.outputs[step.id] = json.dumps(rendered, sort_keys=True)
                result.steps.append(
                    StepResult(id=step.id, ok=True, output="(dry-run)", latency_ms=0)
                )
            return result

        completed: list[str] = []
        outputs: dict[str, str] = {}
        if resume:
            cp = self._load_checkpoint(workflow.name)
            if cp:
                completed = list(cp.get("completed", []))
                outputs = dict(cp.get("outputs", {}))
                result.resumed = True
                log.emit(
                    "workflow_resumed", workflow=workflow.name, completed=completed
                )

        for step in workflow.steps:
            if step.id in completed:
                result.steps.append(
                    StepResult(
                        id=step.id,
                        ok=True,
                        output=outputs.get(step.id, ""),
                        latency_ms=0,
                    )
                )
                continue
            scope = self._build_scope(inputs, outputs)
            timer = Timer()
            try:
                if step.is_llm:
                    output = await self._run_llm_step(step, scope)
                else:
                    output = await self._run_tool_step(step, scope)
            except Exception as exc:
                latency = timer.ms
                sr = StepResult(
                    id=step.id,
                    ok=False,
                    output="",
                    latency_ms=latency,
                    error=f"{type(exc).__name__}: {exc}",
                )
                result.steps.append(sr)
                log.emit(
                    "workflow_error",
                    workflow=workflow.name,
                    step=step.id,
                    error=sr.error,
                )
                if step.on_error == "continue":
                    outputs[step.id] = f"error: {sr.error}"
                    continue
                result.ok = False
                result.checkpoint = self._write_checkpoint(
                    workflow.name,
                    completed,
                    outputs,
                    inputs,
                    str(workflow.source or ""),
                )
                return result
            latency = timer.ms
            outputs[step.id] = output
            completed.append(step.id)
            result.steps.append(
                StepResult(id=step.id, ok=True, output=output, latency_ms=latency)
            )
            log.emit(
                "workflow_step",
                workflow=workflow.name,
                step=step.id,
                kind="llm" if step.is_llm else "tool",
                latency_ms=round(latency, 1),
            )

        result.outputs = outputs
        cp_path = self._checkpoint_path(workflow.name)
        if cp_path.exists():
            cp_path.unlink()
        return result

    def _build_scope(
        self, inputs: dict[str, Any], outputs: dict[str, str]
    ) -> dict[str, Any]:
        import os

        scope: dict[str, Any] = {}
        for k, v in inputs.items():
            scope[f"inputs.{k}"] = v
        for k, v in outputs.items():
            scope[f"steps.{k}.output"] = v
        scope["env"] = dict(os.environ)
        return scope

    async def _run_tool_step(self, step: Step, scope: dict[str, Any]) -> str:
        if not step.tool:
            raise WorkflowError(f"step {step.id!r} has neither tool nor llm")
        args = substitute(step.args or {}, scope)
        call = await self.registry.call(step.tool, args, self.ctx)
        if not call.ok:
            raise WorkflowError(
                f"step {step.id!r} failed in tool {step.tool}: {call.error}"
            )
        return call.output

    async def _run_llm_step(self, step: Step, scope: dict[str, Any]) -> str:
        if self.ctx.backend is None:
            raise WorkflowError(
                f"step {step.id!r} needs an llm but no backend is configured"
            )
        prompt = substitute(step.prompt or step.llm or "", scope)
        backend_name, model = self.ctx.settings.resolve_model()
        resp = await self.ctx.backend.chat(
            [{"role": "user", "content": prompt}], model=model
        )
        return resp.content.strip()


async def run_workflow_tool_handler(args: dict[str, Any], ctx: ToolContext) -> str:
    if ctx.runner is None:
        return "error: workflow runner not configured in this context"
    name = args["workflow"]
    path = Path(name)
    if not path.is_file():
        path = ctx.workspace / "workflows" / f"{name}.yaml"
        if not path.is_file():
            path = ctx.workspace / "workflows" / f"{name}.yml"
    if not path.is_file():
        return (
            f"error: workflow {name!r} not found in workspace workflows/ or as a path"
        )
    inputs = args.get("inputs") or {}
    dry_run = bool(args.get("dry_run", False))
    resume = bool(args.get("resume", False))
    result = await ctx.runner.run(path, inputs, dry_run=dry_run, resume=resume)
    lines = [
        f"workflow: {result.workflow} ({'ok' if result.ok else 'FAILED'}, dry_run={result.dry_run}, resumed={result.resumed})"
    ]
    for s in result.steps:
        marker = "ok " if s.ok else "ERR"
        lines.append(f"  [{marker}] {s.id} ({s.latency_ms:.0f} ms)")
        if not s.ok and s.error:
            lines.append(f"        error: {s.error}")
    if result.checkpoint:
        lines.append(f"checkpoint written: {result.checkpoint}")
    final = result.outputs.get(result.steps[-1].id, "") if result.steps else ""
    if final:
        lines.append("final output:\n" + final[:1500])
    return "\n".join(lines)


def workflow_tool() -> "Tool":
    from mycelium.tools import Tool

    return Tool(
        name="run_workflow",
        description=(
            "Execute a YAML workflow from the workspace workflows/ directory. Steps call tools or the model; "
            "steps can reference {{inputs.x}} and {{steps.<id>.output}}. Failed workflows write a checkpoint; "
            "resume=true continues from it."
        ),
        parameters={
            "type": "object",
            "properties": {
                "workflow": {
                    "type": "string",
                    "description": "Workflow name (workflows/<name>.yaml) or path",
                },
                "inputs": {"type": "object"},
                "dry_run": {"type": "boolean", "default": False},
                "resume": {"type": "boolean", "default": False},
            },
            "required": ["workflow"],
        },
        handler=run_workflow_tool_handler,
        mutating=True,
    )
