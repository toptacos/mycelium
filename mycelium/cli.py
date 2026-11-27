from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from mycelium import __version__
from mycelium.paths import APP_NAME, CCR_COMPAT_PORT, COMMAND, DEFAULT_PORT


def _add_global(p: argparse.ArgumentParser) -> None:
    # SUPPRESS defaults: without this, subparser copies of these flags would
    # reset values already parsed by the parent parser.
    p.add_argument(
        "--workspace", help="workspace root (default: cwd)", default=argparse.SUPPRESS
    )
    p.add_argument(
        "--backend",
        help="backend name (local, openrouter, gemini, deepseek, anthropic)",
        default=argparse.SUPPRESS,
    )
    p.add_argument(
        "--model",
        help="model spec: backend:model or bare model name",
        default=argparse.SUPPRESS,
    )
    p.add_argument(
        "--home", help="override ~/.mycelium home dir", default=argparse.SUPPRESS
    )
    p.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="verbose event logging to stderr",
        default=argparse.SUPPRESS,
    )
    p.add_argument(
        "--no-splash",
        action="store_true",
        help="skip the startup animation",
        default=argparse.SUPPRESS,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=COMMAND,
        description="mycelium: local-first agent workstation. scaffold, research, content, integrations, workflows.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    _add_global(parser)
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="check environment: python, backends, config")
    _add_global(p_doc)

    p_chat = sub.add_parser(
        "chat", help="one agent turn, or interactive REPL if no prompt given"
    )
    _add_global(p_chat)
    p_chat.add_argument("prompt", nargs="*", help="task for the agent")
    p_chat.add_argument(
        "--read-only", action="store_true", help="disable mutating tools"
    )
    p_chat.add_argument("--max-steps", type=int, default=8)
    p_chat.add_argument("--json", action="store_true", help="emit result as JSON")

    p_run = sub.add_parser(
        "run", help="headless run from a prompt string or file, prints result"
    )
    _add_global(p_run)
    p_run.add_argument("task", help="prompt text, or @path/to/prompt.md")
    p_run.add_argument("--read-only", action="store_true")
    p_run.add_argument("--max-steps", type=int, default=8)
    p_run.add_argument("--json", action="store_true", help="emit result as JSON")
    p_run.add_argument(
        "--scripted", help="use scripted backend with responses from this JSON file"
    )

    p_serve = sub.add_parser(
        "serve", help="run the local proxy (OpenAI + Anthropic endpoints)"
    )
    _add_global(p_serve)
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=DEFAULT_PORT)
    p_serve.add_argument(
        "--ccr-port",
        action="store_true",
        help=f"use port {CCR_COMPAT_PORT} as a drop-in CCR replacement",
    )

    p_wf = sub.add_parser("workflow", help="list/show/run workflows")
    _add_global(p_wf)
    p_wf.add_argument("action", choices=["list", "show", "run", "validate"])
    p_wf.add_argument("name", nargs="?", help="workflow name or path")
    p_wf.add_argument(
        "--input",
        "-i",
        action="append",
        default=[],
        help="key=value inputs (repeatable)",
    )
    p_wf.add_argument("--dry-run", action="store_true")
    p_wf.add_argument("--resume", action="store_true")
    p_wf.add_argument("--read-only", action="store_true")

    p_learn = sub.add_parser("learn", help="add a durable memory")
    _add_global(p_learn)
    p_learn.add_argument("text")
    p_learn.add_argument(
        "--kind", default="fact", choices=["fact", "preference", "note", "summary"]
    )
    p_learn.add_argument("--tags", default="")

    p_mem = sub.add_parser("memory", help="inspect memory")
    _add_global(p_mem)
    p_mem.add_argument("action", choices=["show", "recall", "recent", "forget"])
    p_mem.add_argument("query", nargs="?", default="")
    p_mem.add_argument("--k", type=int, default=5)

    p_report = sub.add_parser(
        "report", help="analyze a session log: tokens, tools, latency, compactions"
    )
    _add_global(p_report)
    p_report.add_argument(
        "session", nargs="?", help="path to session.jsonl (default: workspace session)"
    )
    p_report.add_argument("--json", action="store_true")

    p_prompts = sub.add_parser("prompts", help="list/show the sample prompt library")
    _add_global(p_prompts)
    p_prompts.add_argument(
        "action", choices=["list", "show"], nargs="?", default="list"
    )
    p_prompts.add_argument("name", nargs="?")

    p_models = sub.add_parser("models", help="list configured backends and models")
    _add_global(p_models)

    p_ex = sub.add_parser(
        "example",
        help="list, show, or copy bundled recipes (from a git checkout)",
    )
    _add_global(p_ex)
    p_ex.add_argument(
        "action",
        nargs="?",
        default="list",
        help="list | show | copy | recipe id (copy)",
    )
    p_ex.add_argument("name", nargs="?", help="recipe id (04-kraken-compose)")
    p_ex.add_argument("dest", nargs="?", help="copy destination directory")

    return parser


def _console():
    from rich.console import Console

    return Console()


def _load_scripted(path: str | None):
    if not path:
        return None
    from mycelium.backends import ChatResponse, ScriptedBackend, ToolCall

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    responses = []
    for r in data:
        tool_calls = [
            ToolCall(
                id=t.get("id", f"call_{i}"),
                name=t["name"],
                arguments=t.get("arguments", {}),
            )
            for i, t in enumerate(r.get("tool_calls", []))
        ]
        responses.append(
            ChatResponse(
                content=r.get("content", ""),
                tool_calls=tool_calls,
                model=r.get("model", ""),
            )
        )
    return ScriptedBackend(responses)


async def _cmd_doctor(args) -> int:
    from mycelium.config import load_settings
    from mycelium.doctor import run_checks

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
        verbose=args.verbose,
    )
    checks = await run_checks(settings)
    from rich.table import Table

    table = Table(title="mycelium doctor")
    table.add_column("check")
    table.add_column("status")
    table.add_column("detail")
    failed = 0
    for c in checks:
        if c.status == "FAIL":
            failed += 1
        table.add_row(c.name, c.status, c.detail)
    _console().print(table)
    if failed:
        print(
            f"\n{failed} check(s) failed. Fix the items above, or set --backend/--model to a working one."
        )
        return 1
    print("\nall checks passed")
    return 0


async def _cmd_chat(args) -> int:
    from mycelium.runtime import assemble

    agent, settings, log, registry, memory = assemble(
        args.workspace,
        backend=args.backend,
        model=args.model,
        verbose=args.verbose,
        read_only=args.read_only or None,
    )
    agent.config.max_steps = args.max_steps
    if args.prompt:
        task = " ".join(args.prompt)
        result = await agent.run(task)
        if args.json:
            print(
                json.dumps(
                    {
                        "content": result.content,
                        "steps": result.steps,
                        "tool_calls": result.tool_calls,
                        "tools_used": result.used_tools,
                        "prompt_tokens": result.prompt_tokens,
                        "completion_tokens": result.completion_tokens,
                        "ok": result.ok,
                        "warning": result.warning,
                        "session": log.session_id,
                    },
                    indent=2,
                )
            )
        else:
            _console().print(result.content)
            if result.warning:
                print(f"warning: {result.warning}", file=sys.stderr)
        return 0 if result.ok else 2
    return await _repl(agent, settings, log, registry, memory)


async def _repl(agent, settings, log, registry, memory) -> int:
    console = _console()
    console.print(f"[bold]mycelium[/bold] chat  (workspace: {settings.workspace})")
    console.print(
        f"model: {agent.backend_name}:{agent.model}  |  commands: /exit /model /tools /memory"
    )
    from mycelium.runtime import build_backend

    while True:
        try:
            line = console.input("[bold green]you>[/bold green] ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        line = line.strip()
        if not line:
            continue
        if line in ("/exit", "/quit"):
            return 0
        if line.startswith("/model "):
            spec = line.split(None, 1)[1]
            try:
                backend_name, model = settings.resolve_model(spec)
                agent.backend_name, agent.model = backend_name, model
                agent.backend = build_backend(settings, backend_name)
                agent.ctx.backend = agent.backend
                console.print(f"switched to {backend_name}:{model}")
            except Exception as exc:
                console.print(f"[red]{exc}[/red]")
            continue
        if line == "/tools":
            console.print(registry.describe() or "(no tools)")
            continue
        if line.startswith("/memory"):
            query = line[len("/memory") :].strip()
            console.print(memory.recall_text(query, k=5) or "(no matches)")
            continue
        result = await agent.run(line)
        console.print(f"[bold]agent>[/bold] {result.content}")
        if result.tool_calls:
            console.print(
                f"[dim]({result.steps} steps, {result.tool_calls} tool calls, model {agent.model})[/dim]"
            )
        if result.warning:
            console.print(f"[yellow]warning: {result.warning}[/yellow]")


async def _cmd_run(args) -> int:
    from mycelium.runtime import assemble
    from mycelium.agent import AgentConfig

    task = args.task
    if task.startswith("@"):
        task = Path(task[1:]).read_text(encoding="utf-8")
    scripted = _load_scripted(getattr(args, "scripted", None))
    agent, settings, log, registry, memory = assemble(
        args.workspace,
        backend=args.backend,
        model=args.model,
        verbose=args.verbose,
        read_only=args.read_only or None,
        scripted_backend=scripted,
        config=AgentConfig(max_steps=args.max_steps),
    )
    result = await agent.run(task)
    if args.json:
        print(
            json.dumps(
                {
                    "content": result.content,
                    "steps": result.steps,
                    "tool_calls": result.tool_calls,
                    "tools_used": result.used_tools,
                    "prompt_tokens": result.prompt_tokens,
                    "completion_tokens": result.completion_tokens,
                    "compactions": result.compactions,
                    "ok": result.ok,
                    "warning": result.warning,
                    "session": log.session_id,
                },
                indent=2,
            )
        )
    else:
        _console().print(result.content)
        if result.warning:
            print(f"warning: {result.warning}", file=sys.stderr)
    return 0 if result.ok else 2


async def _cmd_serve(args) -> int:
    from mycelium.config import load_settings
    from mycelium.server import serve

    port = CCR_COMPAT_PORT if args.ccr_port else args.port
    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
        verbose=args.verbose,
    )
    serve(settings, host=args.host, port=port)
    return 0


async def _cmd_workflow(args) -> int:
    from mycelium.config import load_settings
    from mycelium.runtime import (
        build_backend,
        build_registry,
        make_event_log,
        make_memory,
    )
    from mycelium.tools import ToolContext
    from mycelium.workflows import WorkflowRunner, load_workflow

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
        verbose=args.verbose,
    )
    wf_dir = settings.workspace / "workflows"
    if args.action == "list":
        from rich.table import Table

        paths = sorted(wf_dir.glob("*.y*ml")) if wf_dir.is_dir() else []
        if not paths:
            print(f"no workflows in {wf_dir}")
            return 0
        table = Table(title=f"workflows in {wf_dir}")
        table.add_column("name")
        table.add_column("description")
        for p in paths:
            try:
                wf = load_workflow(p)
                table.add_row(wf.name, wf.description)
            except Exception as exc:
                table.add_row(p.stem, f"[red]invalid: {exc}[/red]")
        _console().print(table)
        return 0
    if not args.name:
        print("error: workflow name or path required", file=sys.stderr)
        return 2
    path = Path(args.name)
    if not path.is_file():
        for cand in (wf_dir / f"{args.name}.yaml", wf_dir / f"{args.name}.yml"):
            if cand.is_file():
                path = cand
                break
    if args.action in ("show", "validate"):
        wf = load_workflow(path)
        print(
            f"name: {wf.name}\ndescription: {wf.description}\ninputs: {json.dumps(wf.inputs)}"
        )
        for s in wf.steps:
            target = (
                f"llm: {s.prompt or s.llm}"
                if s.is_llm
                else f"tool: {s.tool} args={json.dumps(s.args)}"
            )
            print(f"  step {s.id}: {target}")
        return 0

    inputs = {}
    for item in args.input:
        if "=" not in item:
            print(f"error: --input expects key=value, got {item!r}", file=sys.stderr)
            return 2
        k, v = item.split("=", 1)
        try:
            inputs[k] = json.loads(v)
        except json.JSONDecodeError:
            inputs[k] = v
    log = make_event_log(settings, verbose=args.verbose)
    memory = make_memory(settings)
    registry = build_registry()
    if args.read_only:
        registry = registry.filter(include_mutating=False)
    backend = build_backend(settings)
    ctx = ToolContext(
        workspace=settings.workspace,
        settings=settings,
        memory=memory,
        log=log,
        backend=backend,
        read_only=args.read_only,
    )
    runner = WorkflowRunner(registry, ctx)
    result = await runner.run(path, inputs, dry_run=args.dry_run, resume=args.resume)
    print(f"workflow {result.workflow}: {'ok' if result.ok else 'FAILED'}")
    for s in result.steps:
        print(f"  [{'ok' if s.ok else 'ERR'}] {s.id} ({s.latency_ms:.0f} ms)")
        if not s.ok and s.error:
            print(f"      {s.error}")
    if result.checkpoint:
        print(f"checkpoint: {result.checkpoint} (resume with --resume)")
    if args.verbose and result.steps:
        print("\nfinal step output:\n" + result.steps[-1].output[:2000])
    return 0 if result.ok else 3


async def _cmd_learn(args) -> int:
    from mycelium.config import load_settings
    from mycelium.runtime import make_memory

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
    )
    memory = make_memory(settings)
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    entry = memory.add(args.text, kind=args.kind, tags=tags, source="cli")
    print(f"learned {entry.kind}: {entry.text} (id={entry.id}) -> {memory.path}")
    return 0


async def _cmd_memory(args) -> int:
    from mycelium.config import load_settings
    from mycelium.runtime import make_memory

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
    )
    memory = make_memory(settings)
    if args.action == "recall":
        hits = memory.recall(args.query, k=args.k)
        if not hits:
            print("(no matches)")
            return 0
        for e in hits:
            print(f"- ({e.kind}) {e.text}  [tags: {','.join(e.tags) or '-'}]")
        return 0
    if args.action == "forget":
        ok = memory.forget(args.query)
        print("forgotten" if ok else f"no entry with id {args.query}")
        return 0 if ok else 2
    entries = memory.recent(args.k)
    print(f"memory: {memory.path} ({memory.count()} entries)")
    if not entries:
        print("(empty)")
        return 0
    for e in entries:
        print(f"- ({e.kind}) {e.text[:140]}")
    return 0


async def _cmd_report(args) -> int:
    from mycelium.config import load_settings
    from mycelium.telemetry import analyze_session

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
    )
    path = (
        Path(args.session)
        if args.session
        else settings.workspace / ".mycelium" / "logs" / "session.jsonl"
    )
    if not path.is_file():
        print(f"no session log at {path}", file=sys.stderr)
        return 2
    analysis = analyze_session(path)
    if args.json:
        print(
            json.dumps(
                {
                    "session": analysis.session_id,
                    "events": analysis.events,
                    "steps": analysis.steps,
                    "llm_calls": analysis.llm_calls,
                    "prompt_tokens": analysis.prompt_tokens,
                    "completion_tokens": analysis.completion_tokens,
                    "tool_calls": analysis.tool_calls,
                    "tool_errors": analysis.tool_errors,
                    "compactions": analysis.compactions,
                    "tokens_reclaimed": analysis.tokens_reclaimed,
                    "errors": analysis.errors,
                    "errors_detail": analysis.error_messages,
                    "tools_by_name": analysis.tools_by_name,
                    "latencies_ms": analysis.latencies_ms,
                    "wall_ms": analysis.wall_ms,
                },
                indent=2,
            )
        )
    else:
        print("\n".join(analysis.summary_lines()))
    return 0


async def _cmd_prompts(args) -> int:
    from mycelium.prompts_lib import PROMPT_LIBRARY

    if args.action == "list" or not args.name:
        for name, meta in PROMPT_LIBRARY.items():
            print(f"{name:18s} {meta['summary']}")
        return 0
    entry = PROMPT_LIBRARY.get(args.name)
    if not entry:
        print(
            f"unknown prompt {args.name!r}; available: {', '.join(PROMPT_LIBRARY)}",
            file=sys.stderr,
        )
        return 2
    print(entry["text"])
    return 0


async def _cmd_example(args) -> int:
    from mycelium.examples_lib import (
        ALIASES,
        canonical_id,
        copy_example,
        example_dir,
        list_examples,
    )

    action = args.action or "list"
    name = args.name
    dest = args.dest
    if action not in {"list", "show", "copy"}:
        dest = name
        name = action
        action = "copy"

    if action == "list":
        items = list_examples()
        if not items:
            print(
                "no examples found; run mcy from a mycelium git checkout",
                file=sys.stderr,
            )
            return 2
        for item in items:
            print(f"{item['id']:24s} {item['path']}")
        print()
        print("next: mcy example copy 04-kraken-compose")
        print("      bash examples/04-kraken-compose/run.sh dry-run")
        return 0

    if not name:
        print("usage: mcy example show|copy <id> [dest]", file=sys.stderr)
        return 2

    src = example_dir(name)
    if src is None:
        available = ", ".join(item["id"] for item in list_examples()) or "(none)"
        aliases = ", ".join(f"{k}->{v}" for k, v in ALIASES.items())
        print(
            f"unknown example {name!r}; available: {available}; aliases: {aliases}",
            file=sys.stderr,
        )
        return 2

    if action == "show":
        readme = src / "README.md"
        print(readme.read_text(encoding="utf-8") if readme.exists() else src)
        print(f"\npath: {src}")
        print(f"next: bash {src / 'run.sh'} dry-run")
        return 0

    target = Path(dest) if dest else Path.cwd() / canonical_id(name)
    try:
        copied = copy_example(name, target)
    except FileExistsError as exc:
        print(f"error: destination exists: {exc}", file=sys.stderr)
        return 2
    except FileNotFoundError:
        print(f"unknown example {name!r}", file=sys.stderr)
        return 2
    print(f"copied {canonical_id(name)} -> {copied}")
    print(f"next: bash {copied / 'run.sh'} dry-run")
    print(f"      bash {copied / 'run.sh'} live")
    return 0


async def _cmd_models(args) -> int:
    from mycelium.config import load_settings

    settings = load_settings(
        args.workspace,
        backend=args.backend,
        model=args.model,
        home=Path(args.home) if args.home else None,
    )
    from rich.table import Table

    table = Table(title="backends")
    table.add_column("name")
    table.add_column("kind")
    table.add_column("models")
    table.add_column("key")
    for name, cfg in settings.backends.items():
        key = (
            f"${cfg.api_key_env}" + (" (set)" if cfg.api_key else " (missing)")
            if cfg.needs_key
            else "-"
        )
        table.add_row(
            name, cfg.kind, ", ".join(cfg.models) or (cfg.default_model or "-"), key
        )
    _console().print(table)
    return 0


_HANDLERS = {
    "doctor": _cmd_doctor,
    "chat": _cmd_chat,
    "run": _cmd_run,
    "serve": _cmd_serve,
    "workflow": _cmd_workflow,
    "learn": _cmd_learn,
    "memory": _cmd_memory,
    "report": _cmd_report,
    "prompts": _cmd_prompts,
    "models": _cmd_models,
    "example": _cmd_example,
}


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    for name in ("workspace", "backend", "model", "home"):
        if not hasattr(args, name):
            setattr(args, name, None)
    if not hasattr(args, "verbose"):
        args.verbose = False
    if not hasattr(args, "no_splash"):
        args.no_splash = False
    from mycelium import splash

    if splash.enabled(args):
        try:
            splash.show()
        except Exception:
            pass
    handler = _HANDLERS[args.command]
    try:
        return asyncio.run(handler(args))
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
