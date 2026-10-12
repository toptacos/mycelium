# Roadmap

Planning document, not a commitment. Dates are quarters, not promises.
Versioning per [VERSIONING.md](VERSIONING.md).

## v0.1 — "roots" (this release)

- Agent loop, five backends, seven tools, workflows with checkpoints
- Memory + distillation, context budgeting + compaction, telemetry + report
- Proxy (OpenAI + Anthropic endpoints), CLI (10 commands)
- 139 tests, VM guides, casts, branding, site source, marketing kit

## v0.2 — "hyphae" (next)

Theme: the network reaches further.

- **Embedding recall** — swap keyword scoring for a local embedding model
  (fastembed, optional dependency); keyword fallback stays.
- **MCP client** — connect to MCP servers as tool sources, with the same
  workspace-scoped policy. (Tool poisoning/rug-pulls are the threat; see the
  MCP section in ARCHITECTURE.md before enabling.)
- **Streaming in the CLI** — `mcy chat` streams tokens as they arrive.
- **Scaffold from a URL** — `scaffold_app --from <git-url|tar>` with review
  prompt before executing.
- **Windows CI for the live tier** — Ollama on windows-latest runners.

## v0.3 — "fruiting"

Theme: visible outputs.

- **Template & Workflow Marketplace** — `mcy install <pack>`, signed packs,
  review queue. Curated packs may be paid; everything remains installable
  from source (see OPEN_SOURCE_STRATEGY.md).
- **Content skills** — style guides as memory files; `create_content` loads a
  named house style.
- **`mcy watch`** — file-watcher mode: re-run a workflow when inputs change.

## v0.4 — "forest"

Theme: multiple agents, one network.

- **Multi-agent** — subagent spawning with scoped capabilities and a shared
  memory namespace (read-mostly for children).
- **Project-level policy file** — `.mycelium/policy.toml` for per-project tool
  allowlists, committed to the repo.
- **Audit export** — signed session-log export for teams that need evidence.

## v1.0 — stability promise

- Public API freeze per VERSIONING.md (CLI, config schema, tool schemas,
  workflow YAML, proxy endpoints, event names).
- Breaking-change policy: only in majors, with a migration note in the
  changelog every time.
- LTS branch: v1.x receives fixes for 12 months.

## Research threads (no version)

- Compaction quality with small models: currently structural only. Need an
  eval harness (plant N facts, compact, measure recall).
- Tool-call reliability taxonomy: build the benchmark the way the localagent
  project did (implicit vs explicit naming, per model).
- Local fine-tune for tool calling on the smallest viable model.
- Context-aware model routing: pick backend per step from prompt shape.

## Explicit non-goals

- A chat UI (Open WebUI, LibreChat own this; we integrate instead).
- Hosted agent execution (contradicts local-first).
- A plugin runtime with arbitrary network access (containment first).
- Windows tray app (CLI + `mcy serve` is enough).
