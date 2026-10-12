# AGENTS.md

Local-first agent workstation ("mycelium", command `mcy`). Python 3.11+, uv, pytest.

## Commands

```bash
uv sync                          # install deps
uv run pytest -q                 # full suite (157 tests; ~39s core + ~3min e2e)
uv run pytest -m "not e2e" -q    # core tier only
uv run pytest -m live -q         # real Ollama (skips with reason if absent)
uv run mcy doctor                # environment check (tri-state OK/FAIL/skip)
uv run mcy --workspace <dir> run "task"   # headless agent run
bash scripts/run-samples.sh scripted      # 5 sample-prompt e2es, deterministic
python scripts/bench.py          # measured benchmarks -> logs/bench.json
scripts/release.sh check         # tests + changelog + conventional-commit scan
```

There is no lint/typecheck command yet. If you add one, put it here.

## Layout

- `mycelium/` — package: `cli.py`, `agent.py`, `backends.py`, `context.py`,
  `memory.py`, `workflows.py`, `server.py`, `telemetry.py`, `config.py`,
  `runtime.py`, `doctor.py`, `prompts_lib.py`
- `mycelium/tools/` — fs, scaffold, research, content, integrations,
  memory_tools (`Tool`/`ToolRegistry`/`ToolContext` in `__init__.py`)
- `tests/` — conftest has `FakeProvider` (in-process HTTP fixture server),
  `build_agent` helper; e2es live in `test_sample_prompts.py`
- `workflows/`, `prompts/`, `config/mycelium.toml`, `scripts/fixtures/`
- `site/` (landing page + `site/casts/*.cast` screencasts), `brand/` (SVG logo masters)
- `vms/` (Vagrantfiles + provisioners for ubuntu/fedora/windows), `docs/` (12 guides)
- e2e tests: `tests/test_e2e_{cli,proxy,installer}.py` (marked `e2e`; spawn real processes)

## Conventions

- async everywhere; pytest `asyncio_mode = "auto"`.
- Canonical messages are OpenAI-style dicts; backends translate to/from
  provider shapes (see `backends.py`).
- Deterministic tests use `ScriptedBackend` (queued `ChatResponse`s) — never a
  real model.
- No comments in code; docs live in README.md and docs/.
