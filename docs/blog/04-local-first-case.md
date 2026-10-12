---
title: "Why your AI agent should sleep on your machine: privacy, cost, and context control for local-first agents"
kind: blog
audience: privacy-minded engineers and engineering leads
tone: clear, confident, and practical
model: qwen3:0.6b
words_cap: 650
status: human-edited from a model draft
---

# Why your AI agent should sleep on your machine

Your coding agent reads your whole workspace. Every turn, that context goes
somewhere. Local-first is the choice about *where*.

## Privacy

A local agent's blast radius is your machine:

- The loop runs against Ollama on `127.0.0.1`; nothing leaves unless a tool you
  enabled says so
- Tools are workspace-scoped; path traversal is denied before any write
- Third-party tokens are read from environment variables at call time and never
  written to disk or logs
- The session log is a local JSONL file — read it, analyze it, delete it

Contrast: a cloud coding agent ships your workspace on every request, and its
retention policy is a procurement question, not just an engineering one.

## Cost

Local turns cost electricity, not tokens. On the Intel MacBook we measured
57-65s per agent turn with a 522MB model — slow, but free and unbounded. The
paid path stays available as an *adapter*: OpenRouter, Gemini, DeepSeek,
Anthropic are configured backends, never the default. Route the easy steps
local and the hard steps cloud when you choose to.

## Context control

Local-first lets you instrument what cloud UIs hide. mycelium budgets context
per turn (tokens estimated, budget = window − reserve), compacts middle turns
when usage crosses 80%, and *logs the compaction with tokens reclaimed*. The
tenth run is better than the first because memory distills every run and
recalls it next time. You can audit both claims from the session log.

## The tradeoffs, stated

- Small local models need explicit tool naming in prompts ("Use the fs_list
  tool to..."), or they answer from memory instead of calling a tool
- CPU-only inference is slow; Apple Silicon changes that materially
- MCP, plugins, and IDE UX are thinner than commercial products — by design,
  the loop is scriptable instead

## The takeaway

Privacy, cost, and context control all come from the same property: the agent
sleeps where your code sleeps. Everything else — tools, workflows, memory,
telemetry — is built on top of that one decision.

---

*Editor's note: drafted by `create_content` against the local qwen3:0.6b model
(2026-10-11, log: `logs/blog/local-first-case.log`), then edited by a human.
The draft's structure (privacy/cost/context) survived; its claims were vague
("reduces exposure to external data sources") and are now specific and
traceable to `docs/ARCHITECTURE.md` and `docs/BENCHMARKS.md`.*
