from __future__ import annotations

from pathlib import Path
from typing import Any

from mycelium.agent import Agent, AgentConfig
from mycelium.backends import Backend, ScriptedBackend, make_backend
from mycelium.config import Settings, load_settings
from mycelium.memory import MemoryStore
from mycelium.telemetry import EventLog
from mycelium.tools import ToolRegistry, ToolContext
from mycelium.tools.fs import fs_tools
from mycelium.tools.scaffold import scaffold_tool
from mycelium.tools.research import research_tool
from mycelium.tools.content import content_tool
from mycelium.tools.integrations import integrations_tool
from mycelium.tools.exec import exec_tool
from mycelium.tools.memory_tools import memory_tools
from mycelium.workflows import WorkflowRunner, workflow_tool


def build_registry() -> ToolRegistry:
    registry = ToolRegistry()
    for t in fs_tools():
        registry.register(t)
    registry.register(scaffold_tool())
    registry.register(research_tool())
    registry.register(content_tool())
    registry.register(integrations_tool())
    registry.register(exec_tool())
    for t in memory_tools():
        registry.register(t)
    registry.register(workflow_tool())
    return registry


def build_backend(settings: Settings, name: str | None = None) -> Backend:
    backend_name, model = settings.resolve_model()
    use_name = name or backend_name
    cfg = settings.backend_config(use_name)
    return make_backend(cfg.kind, use_name, cfg.base_url, cfg.api_key)


def make_memory(settings: Settings) -> MemoryStore:
    project_memory = settings.workspace / ".mycelium" / "memory.jsonl"
    global_memory = settings.home / "memory.jsonl"
    return MemoryStore(project_memory, extra_paths=[global_memory])


def make_event_log(
    settings: Settings, session_id: str | None = None, verbose: bool | None = None
) -> EventLog:
    log_dir = settings.workspace / ".mycelium" / "logs"
    return EventLog(
        log_dir / "session.jsonl",
        session_id=session_id,
        verbose=settings.verbose if verbose is None else verbose,
    )


def make_runner(registry: ToolRegistry, ctx: ToolContext) -> WorkflowRunner:
    return WorkflowRunner(registry, ctx)


def assemble(
    workspace: str | Path | None = None,
    *,
    backend: str | None = None,
    model: str | None = None,
    verbose: bool | None = None,
    read_only: bool | None = None,
    scripted_backend: Backend | None = None,
    registry: ToolRegistry | None = None,
    config: AgentConfig | None = None,
    home: Path | None = None,
) -> tuple[Agent, Settings, EventLog, ToolRegistry, MemoryStore]:
    settings = load_settings(
        workspace,
        backend=backend,
        model=model,
        verbose=verbose,
        read_only=read_only,
        home=home,
    )
    log = make_event_log(settings)
    memory = make_memory(settings)
    registry = registry or build_registry()
    if settings.read_only:
        registry = registry.filter(include_mutating=False)
    backend_obj = scripted_backend or build_backend(settings)
    runner = make_runner(
        registry,
        ToolContext(
            workspace=settings.workspace,
            settings=settings,
            memory=memory,
            log=log,
            backend=backend_obj,
            read_only=settings.read_only,
        ),
    )
    agent = Agent(
        settings, backend_obj, registry, memory, log, config=config, runner=runner
    )
    return agent, settings, log, registry, memory
