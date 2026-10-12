---
title: "Mycelium vs Claude Code with a free Claude Code Router setup: what each does well, and when to keep your agent loop local"
kind: blog
audience: developers comparing AI coding setups
tone: clear, confident, and practical
model: qwen3:0.6b
words_cap: 700
status: human-rewritten from a hallucinated model draft
---

# Mycelium vs Claude Code + ccr: two answers to one problem

The popular setup is real: **Claude Code doesn't care what model is behind the
API.** Point it at `claude-code-router` (ccr) — a local proxy on port 3456 —
and it talks to free OpenRouter/Gemini/DeepSeek models instead of a paid
Anthropic plan. `you -> claude -> ccr -> free model`.

We liked that article enough to implement the same endpoints natively. Then we
kept building.

## What each does well

**Claude Code + ccr**

- Best-in-class agentic coding UX: plan mode, subagents, skills, MCP servers
- The router pattern is clean: one config file, model routing by task
- When you do pay for Claude models, it's the smoothest way to spend the money

**mycelium**

- Same router contract, natively: `mcy serve --ccr-port` serves Anthropic
  `/v1/messages` and OpenAI `/v1/chat/completions`, so Claude Code works
  against local Ollama with zero extra installs
- The loop is built in: `mcy run` and `mcy chat` drive the same five backends
  without a separate client
- Around the loop: memory that distills every run, workflows with checkpoints,
  content/research/integration tools, and context budgeting with logged
  compaction
- No subscription anywhere in the critical path — local Ollama is the *default*,
  not a fallback

## When to keep your agent loop local

1. **Your code is the context.** A coding agent reads your whole workspace.
   Local-first means the workspace never leaves the machine; with a cloud
   backend it leaves on every turn.
2. **You want a budget you control.** Local turns cost electricity. Cloud free
   tiers rotate models; paid tiers meter tokens. Pick the tradeoff per step —
   mycelium routes by model spec, mid-session.
3. **You script it.** `mcy run` exits 0/2, emits `--json`, and runs headless in
   CI or a VM. The proxy plus the loop are the same binary.
4. **You want the receipts.** Every run writes a JSONL session log; `mcy report`
   turns it into tokens, tool calls, latency, compactions, errors.

## When Claude Code + ccr wins

- You want frontier-model reasoning on the hardest tasks and will pay for it
- You live in the terminal and want the most polished agentic UX available
- You need Claude Code's skill/MCP ecosystem

The setups are compatible: run `ccr activate` *or* run `mcy serve --ccr-port`
and point `ANTHROPIC_BASE_URL` at it. Same contract, more capability stacked
behind it.

```bash
mcy serve --ccr-port            # 127.0.0.1:3456, drop-in for ccr
export ANTHROPIC_BASE_URL=http://127.0.0.1:3456
export ANTHROPIC_AUTH_TOKEN=local
claude
```

## The honest take

Free models are not frontier models. For multi-step reasoning on the hardest
problems, paid Claude still wins; we route those steps to a cloud backend when
you have a key. For reading codebases, scaffolding, researching, and running
workflows — the daily work — a local 522MB model plus a budgeted loop gets you
most of the way, and the receipts are yours.

---

*Editor's note: drafted by `create_content` against the local qwen3:0.6b model
(2026-10-11, log: `logs/blog/mycelium-vs-claude-code-ccr.log`), then rewritten
by a human. The raw draft hallucinated that mycelium "uses blockchain-based
protocols and decentralized consensus" and that Claude Code is open-source —
both false. It also described Claude Code as a "code execution system" rather
than an agentic coding CLI. The structure above (what each does well / when
local wins / the router setup) follows the draft; every claim was corrected
against `docs/CCR_INTEROP.md`.*
