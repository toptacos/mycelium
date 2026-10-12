# Testing

```bash
uv run pytest            # default: everything not marked live (~40s)
uv run pytest -m live    # real Ollama + real sockets (~5 min; skips with a reason)
uv run pytest -k compaction -v
```

171 tests, 6 tiers. The suite needs no model server and no network except the
tests that deliberately spin up local HTTP fixtures.

## Tiers

| Tier | Files | What it proves |
|---|---|---|
| unit | `test_backends.py`, `test_context.py`, `test_memory.py`, `test_telemetry.py`, `test_config.py` | provider translation, token budgeting, compaction, recall ranking, log analysis, settings precedence |
| tool integration | `test_tools_fs.py`, `test_tools_scaffold.py`, `test_tools_research.py`, `test_tools_content.py`, `test_tools_integrations.py` | every tool's happy path, error path, and policy denial |
| workflow | `test_workflows.py` | substitution, tool+llm mixes, failure checkpoint, resume, dry-run, `on_error: continue` |
| agent + proxy + cli | `test_agent.py`, `test_server.py`, `test_cli.py` | the loop (budget, unknown tool, read-only, compaction, repair, distillation), both proxy APIs + SSE, every subcommand's exit code |
| sample-prompt e2e | `test_sample_prompts.py` | the five scenarios below |

Property tests (`test_properties.py`, Hypothesis): compaction never exceeds
budget, token estimates monotone, traversal components always denied, recall
deterministic.

## The five sample-prompt e2es

Deterministic by design: a `ScriptedBackend` returns queued responses, so the
model's role is played exactly while the agent, tools, workflow engine,
context manager, and telemetry all execute for real. Artifacts are asserted on
disk:

1. **scaffold-app** — `scaffold_app` with `run_tests=true`; asserts the
   `apps/change-calculator/` tree and a real pytest run of the scaffold's own
   suite (a nested `sys.executable -m pytest`).
2. **research** — `research_web` against a local HTML fixture server, then
   `fs_write`; asserts `research/example-com.md` contains the source URL.
3. **content** — `create_content` with a 500-word cap; asserts front matter
   and an H1 in `content/<slug>-blog.md`.
4. **integration** — `call_api` against a local JSON fixture server with a
   connection profile; asserts auth injection and status interpretation.
5. **workflow** — `run_workflow` executing a 3-step YAML (tool, llm, tool);
   asserts `RELEASE_NOTES.md` and the per-step telemetry order.

Because the scripted backend records every call, these tests also pin the
request shapes (system prompt present, tools schema non-empty).

## Local CI (mycelium as the engine)

`workflows/ci-local.yaml` mirrors the GitHub Actions pipeline — commit scan,
core suite, e2e suite, live tier, wheel build — executed by mycelium's own
workflow engine through the `run_command` tool. Full details, capability
mapping, and alternatives to GitHub Actions: [CI_ALTERNATIVES.md](CI_ALTERNATIVES.md).

```bash
mcy --workspace . workflow run ci-local
mcy --workspace . workflow run ci-local --input live=1
```

## Live tier

`tests/test_live.py` (`-m live`) skips with a stated reason when Ollama is
absent, so a green run never implies coverage you did not get:

- `/api/tags` health via `ollama list`
- single-turn chat on `qwen3:0.6b`
- an explicitly-named tool call (`fs_list`), asserting the tool actually ran

## Verified vs asserted

- **Verified by execution (CI-independent)**: all provider translations
  against fixture servers; proxy translation including SSE; the complete
  scaffold → test → artifact path; workflow checkpoint/resume; the learning
  loop (distill → recall appears in the next system prompt).
- **Verified live on this machine (2026-10-11)**: Ollama health; chat; an
  explicit `scaffold_app` tool call creating 7 files that pass their own
  pytest run; a live release-notes workflow writing `RELEASE_NOTES.md`; proxy
  chat completions round-trip in 1.6s.
- **Asserted but not benchmarked**: compaction *quality* (structural
  invariants only); memory recall *relevance* (deterministic keyword scoring).
- **Not tested at scale**: cloud backends (no keys on this machine); model
  injection resistance (single-user local tool; the containment controls do
  not depend on model behavior).

## Fixtures

`tests/conftest.py` provides `FakeProvider` — an in-process HTTP server that
records requests (method, path, headers, body) and serves canned JSON or raw
HTML. Provider translation tests point each backend's `base_url` at it, so
Gemini query-param auth, Authorization headers, and request shapes are all
asserted without network access.
