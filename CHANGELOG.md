# Changelog

All notable changes to mycelium are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Screencast recordings (`site/casts/`) and `docs/SCREENCASTS.md` player embeds.
- Asciicast recorder (`scripts/record-casts.py`) used to capture all demos.
- Multi-OS VM guides with Vagrantfiles for Ubuntu 24.04, Fedora 40, and
  Windows Server 2022 (`vms/`), plus `scripts/vm-smoke.sh` provisioning test.
- Install helpers: `install.sh` (served at mycelium.topta.co), one-liner via the
  `MCY` acronym, per-OS install guides with real captured output.
- Marketing and branding package: brand guidelines with SVG logo masters
  (`brand/`), landing page source (`site/`), marketing plan, social post drafts.
- Open-source strategy and monetization analysis (`docs/OPEN_SOURCE_STRATEGY.md`).
- Roadmap to v1.0 (`docs/ROADMAP.md`).
- Competitor comparison and benchmark harness (`scripts/bench.py`,
  `docs/COMPARISON.md`).
- Examples directory with captured verbose session logs (`examples/`).

## [0.1.0] - 2026-10-11

First public-quality release. Local-first agent workstation with scaffolding,
research, content, integrations, and workflows; five backends; context-budgeted
memory; JSONL telemetry with session analysis.

### Added
- **Agent** (`agent.py`): plan-act loop with step budget, tool-result
  truncation, memory distillation, and automatic context compaction (LLM
  summary with extractive fallback).
- **Backends** (`backends.py`): Ollama (native `/api/chat`), OpenAI-compatible
  (OpenRouter, DeepSeek, llama.cpp, vLLM), Gemini, Anthropic, and a deterministic
  ScriptedBackend. Retry with backoff; repair pass for fenced-JSON, XML, and
  bare-JSON tool calls.
- **Tools** (`tools/`): fs_read/fs_write/fs_list/fs_grep (workspace-scoped,
  traversal-denying), scaffold_app (4 templates, optional real test run),
  research_web (fetch + grounded summary), create_content (6 kinds, word
  caps), call_api (connection profiles, env-var tokens, method allowlist),
  remember/recall_memory, run_workflow.
- **Workflows** (`workflows.py`): YAML steps with `{{inputs.x}}`,
  `{{steps.<id>.output}}`, `{{env.VAR}}` substitution; dry-run; checkpoints;
  resume; `on_error: continue`.
- **Proxy** (`server.py`): OpenAI `/v1/chat/completions` and Anthropic
  `/v1/messages` endpoints (stream + non-stream), `count_tokens`, models list.
  Drop-in replacement for claude-code-router (`mcy serve --ccr-port`).
- **CLI** (`cli.py`): doctor, chat (REPL with /model, /tools, /memory), run
  (headless, --scripted, --json), serve, workflow, learn, memory, report
  (session analysis), prompts, models.
- **Memory** (`memory.py`): JSONL store, keyword recall with tag bonus, project
  + global scopes, forget.
- **Telemetry** (`telemetry.py`): JSONL session log; `report` analysis of
  tokens, tools, latency, compactions, errors.
- **Tests**: 139 tests across unit, integration, e2e (five sample-prompt
  scenarios with artifact assertions), Hypothesis properties, and a live tier
  against real Ollama.
- Docs: README, ARCHITECTURE, TESTING, CCR_INTEROP, BENCHMARKS.

[Unreleased]: https://github.com/toptacos/mycelium/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/toptacos/mycelium/releases/tag/v0.1.0
