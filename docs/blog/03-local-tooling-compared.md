---
title: "Comparing local AI agent tools: Mycelium vs Open WebUI vs LibreChat vs Continue vs Aider - chat UIs versus agent workstations"
kind: blog
audience: developers choosing local AI tooling
tone: clear, confident, and practical
model: qwen3:0.6b
words_cap: 700
status: human-rewritten from a hallucinated model draft
---

# Local AI tooling, compared honestly

The local-LLaMA ecosystem has split into two shapes: **chat surfaces** (you
talk to a model) and **agent workstations** (a model *does* things to your
machine). Both are legitimate. Confusing them is how people end up
disappointed.

## The contenders

| Tool | Shape | Best at |
|---|---|---|
| **Open WebUI** | chat UI | conversational Ollama frontend, RAG over docs, multi-user |
| **LibreChat** | chat UI | multi-provider chat, teams, presets |
| **Continue** | IDE extension | inline completions and chat inside your editor |
| **Aider** | coding CLI | git-native pair programming, repo maps, multi-file edits |
| **mycelium** | agent workstation | scaffolding, research, content, integrations, workflows, memory |

## The real question: talking or doing?

Chat UIs are excellent at talking. They are not built to write files into a
workspace with a policy, run a scaffold's test suite, call an API with a scoped
token, and remember the outcome next week. That is a different product shape.

An agent workstation answers a different question: *"what can this model do to
my machine, safely, and what did it leave behind?"* mycelium's answer:

- Workspace-scoped tools; traversal-denying path policy; read-only mode that
  removes every mutating tool from the registry
- `call_api` connections with env-var tokens, never logged
- JSONL session log — `mcy report` shows tokens, tools, latency, compactions
- Memory that distills every run and recalls it next time

## Where the others are better (we mean this)

- **Open WebUI / LibreChat** — conversation management, multi-user, streaming
  UX. If your day is mostly conversation, use them.
- **Aider** — multi-file refactors with git integration. Our `fs_*` tools are
  more primitive; that's on the roadmap (v0.3 study).
- **Continue / Cline** — inline diffs in your IDE. We have no plugin.
- **CrewAI / LangGraph** — if you're building an agent as a library into a
  product, use a library. We're an application you run.

## A quick decision table

| If you... | Start with |
|---|---|
| want an agent that *does* things locally, no subscription | mycelium |
| want a chat UI for your Ollama box | Open WebUI |
| want AI pair programming in the IDE | Continue or Aider |
| are building an agent into a product | LangGraph / CrewAI |

Full matrix with sources: `docs/COMPARISON.md`. We deliberately publish no
unmeasured competitor numbers — their performance depends on your hardware.

---

*Editor's note: drafted by `create_content` against the local qwen3:0.6b model
(2026-10-11, log: `logs/blog/local-ai-tooling-compared.log`), then rewritten by
a human. The raw draft is a specimen worth studying: it described mycelium as
"an ecological system (microbial ecosystems) used for managing resources,
waste, or environmental sustainability" and invented a third competitor called
"Lib-blog.md" — hallucinated from the topic's filename pattern. That is what a
522MB model does with a topic it has no knowledge of, and exactly why every
generated post in this series ships with its raw log.*
