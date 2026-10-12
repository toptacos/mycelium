# Comparison

How mycelium relates to the tools you might already use. Measured claims are
from this machine (Intel Mac, CPU-only, 2026-10-11); qualitative columns are
design facts, not benchmarks. Fair warning: we are the authors of exactly one
of these columns.

## The landscape

| Tool | What it is | Where mycelium differs |
|---|---|---|
| Claude Code + ccr | agentic coding CLI; ccr is the local router to free/paid models | we implement the same router endpoints natively, and add the loop, memory, workflows around it |
| Open WebUI | self-hosted chat UI for Ollama/OpenAI | chat-first; no workspace-scoped tools, no workflow checkpoints |
| LibreChat | multi-provider chat UI, team features | chat-first; no local tool execution loop |
| Continue.dev | IDE extension with local model support | lives inside your IDE; mycelium is standalone and scriptable |
| Aider | pair-programming CLI with git integration | stronger story for code edits; no content/research/integration tools, no memory ledger |
| Cline / Ro Code | VS Code agents | IDE-bound; mycelium runs headless in CI/VMs |
| localagent (sibling project) | sandboxed local agent with security focus | shares the local-first ethos and Ollama quirks; mycelium adds workflows, content, integrations, and the proxy surface |
| CrewAI / LangGraph | agent frameworks (Python libraries) | libraries you build with; mycelium is an application you run |
| Dify / n8n | workflow/automation platforms | visual-first, often server-hosted; mycelium is a CLI with YAML and checkpoints |

## Feature matrix

Legend: ● native, ◐ partial/plugin, ○ absent by design (wrong layer, not a flaw)

| Capability | mycelium | CC+ccr | Open WebUI | Continue | Aider | CrewAI | n8n |
|---|---|---|---|---|---|---|---|
| Runs fully local (no key) | ● | ● | ● | ● | ● | ● | ◐ |
| Workspace-scoped tools | ● | ● | ○ | ◐ | ● | ◐ | ○ |
| Scaffolds tested apps | ● | ◐ | ○ | ○ | ◐ | ○ | ○ |
| Research (fetch + grounded answer) | ● | ◐ | ◐ | ○ | ○ | ○ | ◐ |
| Content creation (capped drafts) | ● | ◐ | ○ | ◐ | ○ | ○ | ○ |
| Third-party API calls with scoped tokens | ● | ◐ | ○ | ◐ | ○ | ● | ● |
| Workflows with checkpoints/resume | ● | ○ | ○ | ○ | ○ | ◐ | ● |
| Persistent memory + recall | ● | ○ | ◐ | ◐ | ○ | ◐ | ○ |
| Context budgeting + auto-compaction | ● | ◐ | ◐ | ◐ | ◐ | ○ | ○ |
| Session telemetry + analysis | ● | ○ | ○ | ○ | ○ | ◐ | ◐ |
| OpenAI/Anthropic proxy endpoints | ● | ● | ● | ○ | ○ | ○ | ○ |
| Headless / CI-scriptable | ● | ● | ○ | ○ | ● | ● | ● |
| Cross-OS VM guides + CI matrix | ● | ○ | ◐ | ◐ | ◐ | ◐ | ◐ |

## Measured on this machine (ours)

| Metric | mycelium | Source |
|---|---|---|
| Runtime dependencies | 3 (httpx, pyyaml, rich) | `pyproject.toml` |
| CLI cold start | ~1.7-2.6s (dominated by interpreter + imports) | `logs/bench.json` |
| Core test suite (139) | ~39s | `logs/bench.json` |
| Full suite (157, incl. subprocess e2e) | ~3.1min | `logs/bench.json` |
| Five sample scenarios (deterministic) | ~30s | `scripts/run-samples.sh scripted` |
| Proxy healthz round-trip | 7ms warm, 142ms cold | `logs/bench.json` |
| Local model, per agent turn | 57-65s (qwen3:0.6b, CPU) | `docs/BENCHMARKS.md` |

We deliberately do not publish unmeasured competitor numbers. Their performance
depends on your hardware and their version; any table we invented would be
marketing, not measurement.

## Where the others are better (honestly)

- **Open WebUI / LibreChat** — chat UX, conversation management, multi-user.
  If your day is mostly conversation, use them. mycelium is for *doing*.
- **Aider** — git-native edit workflows and repo maps; it is better at
  multi-file refactors than our `fs_*` tools today. Roadmap v0.3 studies this.
- **Continue / Cline** — IDE integration (inline diffs, file context menus).
  We have no IDE plugin and may never need one; `mcy` is scriptable instead.
- **CrewAI / LangGraph** — orchestration *inside* your Python app. If you're
  building an agent as a library, use a library.
- **n8n / Dify** — visual workflow building at scale with hundreds of SaaS
  connectors. We have one generic `call_api` and connection profiles; we are
  not trying to be iPaaS.
- **localagent** — stronger sandbox story (OS-enforced containers per tool
  call). We chose single-user containment instead. If you run untrusted
  prompts routinely, that project's threat model is stricter than ours.

## Choosing

| If you... | Start with |
|---|---|
| want an agent that *does* things locally with no subscription | mycelium |
| want free models behind Claude Code's UX | ccr (or our `mcy serve --ccr-port`) |
| want a chat UI for your Ollama box | Open WebUI |
| want AI pair programming in the IDE | Continue or Aider |
| want to orchestrate many SaaS APIs visually | n8n |
| are building an agent into a product | LangGraph / CrewAI |
