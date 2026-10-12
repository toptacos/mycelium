# mycelium

**Plant it once. It grows.** A local-first agent workstation. One small Python package that **scaffolds applications, researches the web, creates content, calls third-party APIs, and runs multi-step workflows** — using models that run on your machine, learning as it goes, and staying conscious of its context window.

The name is the architecture: mycelium is the network under the forest floor. `mcy` is the fruiting body you call; the roots, threads, and memory live on your machine, where your data never leaves.

No subscription required. Point it at a local model (Ollama) and it works offline; add a free OpenRouter/Gemini/DeepSeek key and it works with cloud models; it can also serve as a drop-in router for Claude Code (see [docs/CCR_INTEROP.md](docs/CCR_INTEROP.md)).

```
you -> mycelium agent -> tools (fs, scaffold, research, content, api, workflow)
                     -> context manager (token budget, auto-compaction)
                     -> memory (JSONL, keyword recall, session distillation)
                     -> backend router -> ollama | openrouter | gemini | deepseek | anthropic
                     -> telemetry (JSONL session log + analysis)
```

## Install

One-liner (macOS/Linux) — the `MCY` acronym route:

```bash
curl -fsSL https://mycelium.topta.co/mcy | sh
```

Or from source — needs Python 3.11+ and [uv](https://docs.astral.sh/uv/). For local models, [Ollama](https://ollama.com) with at least one model pulled (`ollama pull qwen3:0.6b`).

```bash
git clone https://github.com/toptacos/mycelium.git && cd mycelium
uv sync
uv run mcy doctor          # verifies python, backends, config; says what to fix
```

Per-OS guides with captured output: [docs/INSTALL.md](docs/INSTALL.md). Verified on
Ubuntu 24.04, Fedora 40, macOS, and Windows — via Vagrant VMs
([docs/VM-GUIDES.md](docs/VM-GUIDES.md)) and a 3-OS CI matrix.

Cloud backends are optional. If a key is absent, `doctor` reports `skip`, not failure.

## Use

```bash
# headless run (exits 0 on success)
uv run mcy run "Scaffold a python-cli app called invoice-parser and run its tests"

# interactive REPL with /model switching, /tools, /memory
uv run mcy chat

# sample-prompt library: the five scenarios below, with success criteria
uv run mcy prompts list
uv run mcy prompts show scaffold-app

# workflows (YAML, checkpoints, resume, dry-run)
uv run mcy workflow list
uv run mcy workflow run release-notes --input repo_path=.
uv run mcy workflow run release-notes --dry-run

# memory: teach it something, then watch it recall
uv run mcy learn "deploys are fridays only" --kind preference --tags deploy
uv run mcy memory recall "when do we deploy"

# session analysis: tokens, tools, latency, compactions, errors
uv run mcy report
uv run mcy report --json

# local proxy: OpenAI + Anthropic endpoints (drop-in for ccr / Claude Code)
uv run mcy serve --port 8787
```

Global flags: `--workspace DIR --backend NAME --model spec --home DIR -v`.
Model spec: `backend:model` or a bare model name (uses the default backend).

## The five sample scenarios

Each has a prompt (in `prompts/` and `mcy prompts`), an end-to-end test
(`tests/test_sample_prompts.py`, deterministic via a scripted backend), and
asserted artifacts:

| Scenario | Tool(s) | Artifact asserted |
|---|---|---|
| scaffold an application | `scaffold_app` (+ real pytest run) | `apps/<name>/` tree; tests PASSED |
| research | `research_web`, `fs_write` | `research/<slug>.md` with source URL |
| content creation | `create_content` | `content/<slug>-<kind>.md` with front matter + H1 |
| third-party integration | `call_api` | HTTP status + payload interpretation |
| workflow execution | `run_workflow` | `RELEASE_NOTES.md` + step outcomes |

Run the whole library deterministically:

```bash
scripts/run-samples.sh scripted     # no model needed, ~30s
scripts/run-samples.sh live         # real Ollama, minutes on CPU
```

Watch them instead of reading about them: [docs/SCREENCASTS.md](docs/SCREENCASTS.md)
(asciinema casts of every scenario, including the live 6-minute scaffold).

## Configuration

Precedence: built-in defaults -> `~/.mycelium/mycelium.toml` -> `./mycelium.toml`
-> env vars (`MYCELIUM_BACKEND`, `MYCELIUM_MODEL`, `MYCELIUM_VERBOSE`,
`MYCELIUM_READ_ONLY`, `MYCELIUM_HOME`) -> CLI flags. Copy
[`config/mycelium.toml`](config/mycelium.toml) to start from a worked example.

Third-party connections live in `mycelium.toml`; tokens are read from
environment variables at call time and never written to disk or logs:

```toml
[connections.github]
base_url = "https://api.github.com"
auth_env = "GITHUB_TOKEN"          # export GITHUB_TOKEN=...
methods = ["GET", "POST", "PATCH"]
```

## How it stays lean

- **Dependencies**: `httpx`, `pyyaml`, `rich`. That's the runtime set.
- **Context budget**: every turn is token-estimated; when usage crosses
  `compact_threshold` of `context_window - reserve_tokens`, middle turns are
  compacted (LLM summary, extractive fallback) and the event is logged with
  tokens reclaimed.
- **Step budget**: the agent loop is capped (`max_steps`) and always terminates
  with a warning instead of spinning.
- **Tool results** are truncated (8k chars default) so a single big read cannot
  eat the window.
- **Workspace-scoped paths**: traversal and absolute escapes raise
  `PolicyViolation` before any write.

## How it learns

1. `remember` writes facts/preferences to `.mycelium/memory.jsonl` (project)
   and `~/.mycelium/memory.jsonl` (global).
2. Every successful agent run is **distilled** into a summary memory
   (task + outcome + tags).
3. New runs recall the top-5 matches by keyword overlap and inject them into
   the system prompt.
4. Compaction summaries are kept in-context; nothing learned is silently
   dropped — the decision trail is in the session log.

## Cross-system

Pure Python, stdlib paths (`pathlib`, `os.environ`), no shell-outs except the
optional in-scaffold test runner. Verified on macOS (this machine). Windows:
`uv sync` then `uv run mcy doctor`; the proxy binds `127.0.0.1` by default.

## Tests

```bash
uv run pytest                  # 157 tests: 139 core (~39s) + 18 subprocess e2e (~3min)
uv run pytest -m "not e2e" -q # core tier only
uv run pytest -m live          # real Ollama, skips politely if absent
```

Tiers: unit (backends, context, memory, telemetry, config), integration
(tools, workflows, proxy, CLI), the five sample-prompt e2es with artifact
assertions, property tests (Hypothesis), subprocess e2e (real CLI journeys, a
real proxy on a socket, the installer against a local git repo), and live model
tests. Details in [docs/TESTING.md](docs/TESTING.md).

## Benchmarks

Measured on this machine, including what we got wrong:

```bash
python scripts/bench.py        # writes logs/bench.json
```

[docs/BENCHMARKS.md](docs/BENCHMARKS.md) · [docs/COMPARISON.md](docs/COMPARISON.md)
(competitors, including where they beat us) · [docs/ROADMAP.md](docs/ROADMAP.md).

## Docs

| Document | Contents |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Modules, data flow, tool schema, backend translation, extension points |
| [docs/TESTING.md](docs/TESTING.md) | Test tiers, what is proven vs assumed, how to run |
| [docs/CCR_INTEROP.md](docs/CCR_INTEROP.md) | The Plain English article setup, and how mycelium replaces ccr |
| [docs/BENCHMARKS.md](docs/BENCHMARKS.md) | Measured latencies and token costs on this machine |

## Known limits

- Keyword recall, not embeddings. Good enough for a few hundred entries;
  not semantic search.
- `research_web` fetches one URL; no crawling, no search API.
- The proxy translates chat/completions and messages; it does not execute
  tools itself (the client drives the tool loop, as ccr does).
- Small local models need **explicit tool naming** in prompts ("Use the
  fs_list tool to...") and may emit tool calls as naked JSON — the repair
  pass handles the common shapes. See [docs/BENCHMARKS.md](docs/BENCHMARKS.md).
- Compaction quality with small models is unmeasured; the extractive fallback
  is deterministic but lossy.
