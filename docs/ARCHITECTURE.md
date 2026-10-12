# Architecture

## Layers

```
cli.py / server.py            entry points: mcy command, local proxy
agent.py                      plan-act loop: budget, repair, compaction, distillation
tools/                        capability tools (fs, scaffold, research, content, api, workflow, memory)
workflows.py                  YAML workflow engine: substitution, checkpoints, resume
context.py                    token budget, compaction planning/application
memory.py                     JSONL memory: add, recall, forget, project+global scopes
backends.py                   provider translation: ollama/openai/gemini/anthropic/scripted
telemetry.py                  JSONL event log + session analysis
config.py                     settings: TOML merge, env overrides, backend registry
runtime.py                    assembly: wires the above into an Agent
doctor.py                     environment checks (tri-state OK/FAIL/skip)
```

## One agent turn

`Agent.run(task)`:

1. Build the system prompt: identity + tool list + **recalled memories** for
   this task + read-only notice if applicable.
2. Seed the context with the task (pinned so compaction never drops it).
3. Loop up to `max_steps`:
   - If `ContextManager.needs_compaction()`: summarize the middle turns (LLM,
     extractive fallback), apply, emit a `compaction` event with tokens
     reclaimed.
   - `backend.chat(messages, tools=registry.schemas())`.
   - No tool calls -> final answer -> distill a summary memory -> return.
   - Tool calls -> `registry.call()` each (policy + error capture) -> append
     results (truncated) -> continue.
4. Budget exhausted -> return partial with `warning`.

Every step emits `agent_step` with context tokens/budget/usage; every model
call emits `llm_call` with token counts and latency.

## Tool contract

```python
Tool(
    name="fs_write",
    description="...",                 # sent to the model
    parameters={"type": "object", ...} # JSON schema, OpenAI function form
    handler=async fn(args, ctx) -> str,
    mutating=True,                     # blocked when read_only
    requires_net=True,
)
```

`ToolRegistry.schemas()` renders the OpenAI function form; backends translate
it to Ollama `tools`, Gemini `function_declarations`, or Anthropic
`input_schema`. `ToolContext` carries workspace, settings, memory, log,
backend, and the workflow runner.

Results are captured as `CallResult(ok, output, latency_ms, error)`; failures
are returned as text (`error: ...`) so the model can recover rather than crash
the loop.

## Backend translation

One canonical message shape flows in:

```python
{"role": "user"|"assistant"|"tool"|"system",
 "content": str,
 "tool_calls": [{"id", "type": "function", "function": {"name", "arguments(json-str)"}}],
 "tool_call_id", "name"}
```

| Backend | Wire format | Notes |
|---|---|---|
| ollama | `POST /api/chat` | native endpoint; the OpenAI-compatible `/v1` path silently ignores `num_ctx` |
| openrouter, deepseek, llama.cpp, vLLM | `POST /chat/completions` | `tool_choice=auto`; args parsed from JSON string |
| gemini | `POST /models/{m}:generateContent?key=` | contents/parts, `functionCall`/`functionResponse`, key in query |
| anthropic | `POST /v1/messages` | system extracted; tool blocks converted both ways |

429/5xx are retried 3x with exponential backoff, then raised as `RuntimeError`
carrying the last status line.

### Repair pass

Weak local models often emit tool calls as text. `repair_tool_calls` recognizes
three shapes and converts them to structured calls: fenced ```json blocks,
`<tool_use>{...}</tool_use>` XML, and a bare leading JSON object. Payload keys
`name`/`tool` and `arguments`/`args`/`parameters`/`input` are all accepted.
This is a compatibility shim, not a security control.

## Context management

`ContextManager` tracks `system_tokens + sum(turn.tokens)` against
`window_tokens - reserve_tokens`. At `compact_threshold` usage, it drops
unpinned middle turns (keeping the pinned task and the last `keep_recent`
turns), prepends a summary turn, and returns a `CompactionEvent` logged to
telemetry. Token estimates are `ceil(chars/4)` — a heuristic, deliberately
dependency-free; real tokenizers can be swapped into `estimate_tokens`.

## Workflow engine

```yaml
steps:
  - id: read
    tool: fs_read
    args: {path: "README.md"}
  - id: draft
    llm: "Summarize: {{steps.read.output}}"
```

`substitute()` resolves `{{inputs.x}}`, `{{steps.<id>.output}}`, `{{env.VAR}}`.
A failing step (tool error, or `on_error: fail` default) writes a checkpoint
(`.mycelium/checkpoints/<name>.json`) with completed step ids and outputs;
`--resume` continues from it. `--dry-run` renders the substitution plan
without side effects.

## Proxy (server.py)

`ThreadingHTTPServer` exposing:

- `POST /v1/chat/completions` (OpenAI, stream + non-stream)
- `POST /v1/messages` (Anthropic, stream + non-stream) — this is what lets
  Claude Code use mycelium exactly like ccr
- `POST /v1/messages/count_tokens`
- `GET /v1/models`, `GET /healthz`

The proxy does **not** execute tools: it passes `tools` through to the backend
and returns `tool_calls`/`tool_use` to the client, which drives the loop. That
is the same division of labor as ccr.

## Security posture

This is a single-user local workstation, so the controls are containment, not
multi-tenant isolation:

- Workspace path resolution (`resolve + commonpath`) denies traversal and
  absolute escapes before any write.
- `read_only` removes every mutating tool from the registry for the session.
- `call_api` only calls pre-configured connection profiles; tokens come from
  env vars at call time and are never logged (telemetry records tool names,
  latencies, sizes — not bodies).
- No tool executes arbitrary shell commands. `scaffold_app --run-tests` runs
  only the scaffold's own suite, with a 180s timeout.
- `run_command` is the only exec surface: no shell (`shlex.split` + argv),
  executable allowlist (`[commands] allow`), workspace-scoped cwd, timeout, and
  nonzero exits raise `ToolFailure` so workflows fail with the receipt intact.
  It is `mutating=True` and never granted to read-only sessions.

## Extension points

- **New tool**: write a `Tool`, register it in `runtime.build_registry`.
- **New backend**: implement `chat()` on the `Backend` protocol in
  `backends.py`, add a `[backends.x]` section.
- **New template**: add a dict entry in `tools/scaffold.py: TEMPLATES`.
- **New workflow**: drop a YAML in `workflows/`; no code changes.
- **Real tokenizer**: replace `estimate_tokens` in `context.py`.
