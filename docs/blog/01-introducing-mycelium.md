---
title: "Introducing Mycelium: a local-first agent workstation that scaffolds apps, researches, creates content, calls APIs, and runs workflows on your own machine"
kind: blog
audience: backend developers and AI tinkerers
tone: clear, confident, and practical
model: qwen3:0.6b
words_cap: 700
status: human-edited from a model draft
---

# Introducing Mycelium: a local-first agent workstation

Everyone assumes an agent needs a subscription. It doesn't.

**mycelium** is a local-first agent workstation. One small Python package —
three runtime dependencies — that **scaffolds applications, researches the web,
creates content, calls third-party APIs, and runs multi-step workflows**, using
a 522MB model that lives on your machine.

## What it actually does

- **Scaffold.** `scaffold_app` writes a Python CLI, FastAPI service, Node CLI,
  or static site into `apps/<name>/` — and with `run_tests=true`, executes the
  scaffold's own pytest suite. The scaffold we shipped passes its own tests.
- **Research.** `research_web` fetches a page, strips it, and answers a
  question *strictly from it*, with the source URL recorded.
- **Content.** `create_content` drafts blogs, READMEs, newsletters, outlines,
  tutorials, and changelog entries with enforced word caps.
- **Connect.** `call_api` calls connection profiles you define in
  `mycelium.toml`. Tokens are read from environment variables at call time and
  never written to disk or logs.
- **Workflows.** YAML workflows with `{{inputs.x}}` and
  `{{steps.<id>.output}}` substitution, dry-run, and checkpoints — a failed
  run resumes where it stopped.
- **Remember.** Every run is distilled into a JSONL memory and recalled on
  related future tasks. Context is budgeted; middle turns are compacted (and
  logged) when the window fills.

## Why "mycelium"?

The mushroom is the part you see; the network is the part that works. `mcy` is
the fruiting body you call on the command line. The roots, threads, and memory
live on your machine — where your data never leaves.

## The honest numbers

From an Intel MacBook, CPU-only:

- 522MB default model (`ollama pull qwen3:0.6b`)
- 57-65s per agent turn with that model — we built around it: tool calls take
  milliseconds, the loop is budgeted, and every number in our docs says which
  machine produced it
- 3 runtime dependencies; 157 tests; the core suite runs in ~39s
- Proxy round-trip to the local model: 1.6s

```bash
curl -fsSL https://mycelium.topta.co/mcy | sh
mcy doctor
mcy run "Use the scaffold_app tool with name='hello' and template='python-cli' and run_tests=true"
```

No account. No key. No telemetry — the session log is a local file you can
read, analyze with `mcy report`, or delete.

## What it isn't

It isn't a chat UI (Open WebUI owns that), isn't an IDE plugin (Continue and
Aider are better there), and its small default model needs tool names spelled
out in prompts. The full comparison, including where competitors beat us, is in
`docs/COMPARISON.md`.

Plant it once. It grows.

---

*Editor's note: this post was drafted by `create_content` against the local
qwen3:0.6b model (2026-10-11, log: `logs/blog/introducing-mycelium.log`), then
rewritten by a human. The raw draft was structurally reasonable but empty —
"designed to empower you", no commands, no numbers. Everything factual above
traces to `docs/BENCHMARKS.md`, `logs/bench.json`, or a screencast.*
