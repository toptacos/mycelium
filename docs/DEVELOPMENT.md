# Development

## Setup

```bash
git clone https://github.com/toptacos/mycelium.git
cd mycelium
uv sync                      # runtime + dev deps into .venv
uv run mcy doctor            # sanity: python, backends, config
```

Python 3.11+ is the floor (`tomllib` is stdlib from 3.11).

## Day-to-day

```bash
uv run pytest -q                  # full suite, ~30s
uv run pytest -m live -q          # real Ollama tier (skips politely if absent)
uv run pytest -k compaction -v    # focus
bash scripts/run-samples.sh scripted   # five sample-prompt e2es
scripts/release.sh check               # tests + changelog + commit scan
```

## Module map

| File | Owns | Read it when |
|---|---|---|
| `mycelium/cli.py` | argparse surface, subcommands | adding a command |
| `mycelium/agent.py` | the loop: budget, repair, compaction, distillation | changing turn behavior |
| `mycelium/backends.py` | provider translation + retries | adding a provider |
| `mycelium/context.py` | token budget, compaction planning | changing window math |
| `mycelium/tools/__init__.py` | Tool contract, registry, policy | adding a tool |
| `mycelium/workflows.py` | YAML engine, checkpoints | changing step semantics |
| `mycelium/server.py` | proxy endpoints | touching the HTTP surface |
| `mycelium/telemetry.py` | event schema + analysis | adding an event type |
| `mycelium/runtime.py` | assembly | wiring anything new |

## Adding a tool

1. Create the handler in `mycelium/tools/<name>.py` with signature
   `async def <name>(args: dict, ctx: ToolContext) -> str`.
2. Return strings. Raise `PolicyViolation` for denials — the registry converts
   it to an `error: policy violation: ...` tool result so the model can react.
3. Export a `Tool(...)` from a factory (`fs_tools()`, `scaffold_tool()`).
4. Register it in `runtime.build_registry()`.
5. Test happy path, error path, and policy denial in `tests/test_tools_<name>.py`.
6. Document it in README's tool table if user-facing.

## Adding a backend

1. Implement `Backend` (name, `chat()`, `aclose()`) in `backends.py`.
2. Translate the canonical message shape (see ARCHITECTURE.md) both ways.
3. Add a `[backends.<name>]` default in `config.py:DEFAULT_BACKENDS`.
4. Cover it in `tests/test_backends.py` against `FakeProvider` — assert the
   outbound body, auth mechanism, and tool-call parsing.

## Adding a workflow step kind

`WorkflowRunner._run_tool_step` / `_run_llm_step` are the only dispatch points.
Add the new kind, extend `substitute()` scope if it needs new references, and
test with a YAML fixture plus a checkpoint/resume case.

## Event schema (telemetry)

Every event is one JSON object per line in `.mycelium/logs/session.jsonl`.
Names in use: `agent_start`, `agent_step`, `llm_call`, `tool_call`,
`tool_call_repaired`, `compaction`, `agent_finish`, `agent_stop`,
`agent_error`, `workflow_step`, `workflow_step_planned`, `workflow_resumed`,
`workflow_error`. `mcy report` parses these; adding a type means updating
`analyze_session` in the same commit (there's a test in `test_telemetry.py`).

## Style

- No comments in code; code should read as documentation. Rationale and
  tradeoffs live in `docs/` and commit bodies.
- async everywhere; tests use `asyncio_mode = "auto"`.
- Deterministic tests never touch a real model: scripted backend or
  FakeProvider.
- Cross-platform: `pathlib`, `os.environ`, no shell-outs except the scaffold
  test runner (which is optional and guarded).

## Pre-submit checklist

1. `uv run pytest -q` green.
2. New behavior has a test that fails without it.
3. `CHANGELOG.md` has an Unreleased entry.
4. Commit message is conventional (`feat(tools): ...`).
