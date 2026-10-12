---
title: "From prompt to project: scaffolding a tested Python CLI with a 522MB model on a laptop"
kind: blog
audience: developers curious about small local models
tone: clear, confident, and practical
model: qwen3:0.6b
words_cap: 650
status: human-edited from a model draft
---

# From prompt to project: a 522MB model that scaffolds

The pitch: a 522MB model (qwen3:0.6b via Ollama) takes a prompt and produces
a tested Python CLI. The reality is more interesting than the pitch.

## The run

```
$ mcy run "Use the scaffold_app tool with name='cast-demo2' and
template='python-cli' and run_tests=true. Report every file created and
whether tests passed."
```

What actually happened (verbose log, real timing):

- Turn 1: ~57s on CPU — the model emits a **native tool call**
  (`scaffold_app`, args parsed)
- Tool: ~10ms — 7 files written under `apps/cast-demo2/`
- The scaffold's own `pytest tests/` runs inside the tool: **1 passed**
- Turn 2: ~65s — the model lists every file it created, correctly

Total wall time on an Intel MacBook: about six minutes. On Apple Silicon,
materially faster.

## The files

```
apps/cast-demo2/
├── .gitignore
├── README.md
├── pyproject.toml
├── src/cast_demo2/{__init__,cli}.py
└── tests/{conftest,test_cli}.py
```

`src/` layout, a `conftest.py` that puts `src/` on `sys.path`, and a real test
that parses `--version`. The template is boring on purpose: boring scaffolds
pass their own tests.

## The failure modes (we shipped them in the changelog)

1. **Naked-JSON tool calls.** Our first live run of the heavier
   `qwen2.5-coder` model emitted the tool call as raw JSON *text*, not a
   structured call. We added a repair pass (fenced JSON, `<tool_use>` XML, bare
   leading JSON objects) and a regression test.
2. **295s per turn.** Same model, CPU-only. We switched the default to the
   522MB model and wrote the latency into the docs instead of hiding it.
3. **CPU contention.** Three concurrent generation jobs on one machine starve
   each other into read timeouts. The local backend now allows 600s per call
   and the media pipeline was serialized.

## The pattern that works

- **Name the tool explicitly**: "Use the scaffold_app tool with..." beats
  "scaffold something". Small models answer from memory otherwise.
- **Give the model a reportable outcome**: "report every file created" makes
  turn 2 self-verifying — the model's summary is a checksum on the tool's work.
- **Budget the loop**: step caps, tool-result truncation, and context
  compaction keep a long session from quietly degrading.

## Try it

```bash
ollama pull qwen3:0.6b
mcy run "Use the scaffold_app tool with name='hello' and template='python-cli' and run_tests=true"
cd apps/hello && python -m pytest tests/ -q
```

Full methodology and known gaps: `docs/BENCHMARKS.md`. The screencast of this
exact run: `docs/SCREENCASTS.md` (cast 03).

---

*Editor's note: drafted by `create_content` against the local qwen3:0.6b model
(2026-10-11, log: `logs/blog/scaffolding-with-522mb.log`), then rewritten by a
human. The raw draft was generic advice about building CLIs (it recommended
Tkinter `input_box()` and PyTorch for a scaffolding tool) with no connection to
the actual measured run. The numbers and failure modes above come from the real
session logs and `site/casts/03-scaffold-live.cast`.*
