# Benchmarks (measured on this machine)

Machine: MacBookPro (Intel x86_64, i9-9980HK class), macOS 25.6, **CPU-only
inference** (Metal is unavailable on Intel Macs). Python 3.14.3, Ollama local.
Measured 2026-10-11 from the JSONL session logs and live smoke runs.

## Latency, per model, per agent turn

Includes the full loop overhead (one tool-less turn):

| Model | Size | gen tok/s observed | wall per turn | note |
|---|---|---|---|---|
| `qwen3:0.6b` | 522MB | ~2.9 (167 tok / 57s) | **57-65s** | default; fast enough to iterate |
| `qwen2.5-coder:latest` | 4.7GB | ~0.09 (26 tok / 295s) | **295s** | unusable interactively here |

The 18GB MoE `qwen3-coder:30b` is present on this machine but was not run; the
localagent project measured it at 4.4-7.2 tok/s (low active parameters reduce
compute, and CPU inference is bandwidth-bound). Treat that as prior art, not a
measurement from this repo.

## Live runs (what actually happened)

1. **Explicit tool call** (`qwen3:0.6b`): "Use the fs_list tool..." ->
   `tool_calls=1`, 2 steps, 1066 prompt tokens, ok. The tool loop works with
   explicitly named tools.
2. **Scaffold e2e** (`qwen3:0.6b`): "Use the scaffold_app tool with
   name='demo-note'..." -> native tool call, 7 files written, model's summary
   listed every file correctly. Scaffolded `pytest tests/` -> **1 passed**.
3. **Workflow** (`release-notes`, `qwen3:0.6b`): fs_list (16ms), fs_read (1ms),
   LLM draft (215s), fs_write (2ms) -> ok, `RELEASE_NOTES.md` written. Tool
   steps are effectively free; the model dominates wall time.
4. **Proxy**: `POST /v1/chat/completions` -> real Ollama, **1.6s** round trip
   including startup (16 prompt / 32 completion tokens). The proxy adds noise,
   not latency.

## Token costs (scripted e2e, deterministic)

The five sample-prompt scenarios complete in **2-4 LLM calls, ~2-5k prompt
tokens** each against `qwen3:0.6b`-class context windows (32k default). With
`--verbose`, a typical run shows 550-750 context tokens per step — tool
schemas plus system prompt plus task. Tool schemas are ~600 tokens of every
request's prompt; the registry is filtered to available tools, so read-only
sessions pay less.

## Context behavior

- Context usage at agent start: 2% of budget (626/31744 tokens).
- The scaffolded-tools registry costs ~600 tokens of every prompt. If you only
  ever use three tools, trim the registry (`registry.filter`) — see
  `AgentConfig` and `runtime.build_registry`.
- Compaction was exercised in tests (budget 400 tokens, threshold 0.5): events
  fire, tokens reclaimed > 0 every time, pinned task survives. Live runs never
  approached the threshold.

## Tool-call reliability, honestly

- `qwen3:0.6b`, **explicit** tool naming: worked in all live attempts
  (fs_list, scaffold_app — the latter as a native tool call).
- `qwen2.5-coder:latest`, same scaffold prompt: emitted the tool call as
  **naked JSON text** (`{"name": "scaffold_app", "arguments": {...}}`). This
  prompted the repair pass, which now catches fenced JSON, `<tool_use>` XML,
  and bare leading JSON objects. With that fix the same run succeeds.
- Generic prompts ("do X") on small models: the model may answer from memory
  instead of calling a tool. Name the tool in the prompt. (The sibling
  localagent project measured 0% implicit tool-calling on `qwen3:0.6b` and
  ~89% explicit across four models; treat small-model tool use as
  prompt-engineering, not a guarantee.)

## Known measurement gaps

- n=1 per scenario. These are smoke measurements, not benchmarks with
  confidence intervals.
- Compaction *quality* (does the summary preserve what matters) is asserted
  structurally in tests, not evaluated semantically.
- Cloud backends unmeasured here (no keys on this machine).
- Cold vs warm model load is not separated: the first turn includes model
  load time on CPU, which is most of the 57s.
