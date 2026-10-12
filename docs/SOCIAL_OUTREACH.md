# Social Outreach Kit

Drafts for launch week. Voice rules from `brand/BRANDING.md`: grounded, honest
about limits, gardener's pragmatism. No hype adjectives. Every claim links to a
measurement.

---

## X / Twitter

**Launch (pin this):**

> mycelium is a local-first agent workstation. Scaffold apps, research, write,
> connect APIs, run workflows — powered by a 522MB model on your machine.
> No subscription. 3 deps. 139 tests.
> curl -fsSL https://mycelium.topta.co/mcy | sh

**Thread — "we measured, on purpose":**

> 1/ The default model runs ~57-65s per agent turn on a CPU-only Mac.
>    That's the honest number, so we built around it: tool calls take
>    milliseconds and the loop is budgeted. 🧵
>
> 2/ The small model sometimes emits tool calls as naked JSON.
>    Instead of hiding it, we added a repair pass — and wrote the failure
>    into the changelog. Reliability you can read.
>
> 3/ Every run writes a JSONL session log you can analyze yourself:
>    tokens, tool calls, latency, compactions, errors. `mcy report`.
>    No telemetry leaves your machine. Ever.

**Thread — the category:**

> 1/ Chat UIs (Open WebUI, LibreChat) are great at talking.
>    mycelium is built for *doing*: scaffolding with passing tests, workflows
>    with checkpoints, connections with scoped tokens.
>
> 2/ ccr makes Claude Code work with free models.
>    We liked it enough to implement the same endpoints natively —
>    then added the agent loop, memory, and workflows around it.

## Reddit (r/LocalLLaMA)

**Title:** I benchmarked a 522MB model doing real tool-calling work — workflow,
scaffold, and what actually failed

> Longtime lurker, first post. I wanted to know how far a small local model
> goes on actual engineering work, so I built a tool around the question and
> measured it on my Intel Mac (CPU-only).
>
> What worked: explicit tool calls (fs_list, scaffold_app), a 4-step workflow
> writing release notes, the proxy at 1.6s round-trip.
> What didn't: 295s/turn on qwen2.5-coder (switched defaults), and the model
> emitting tool calls as naked JSON (fixed with a repair pass).
>
> Full numbers, methodology, and gaps: [BENCHMARKS.md]. The tool is
> Apache-2.0; happy to answer questions.

## LinkedIn (privacy-lead persona)

> Your coding assistant's telemetry is a procurement question, not just an
> engineering one. We shipped mycelium — a local-first agent workstation —
> as a working answer: the loop runs on your machine, tools are
> workspace-scoped, API tokens are read from env at call time and never
> logged, and the session log is a local file you can delete.
> Apache-2.0. Links in comments.

## dev.to / Medium (cross-post summary)

> **We used the tool to write its own launch posts.** Every post in this
> series was drafted by `mcy run "Use create_content ..."` against a local
> 522MB model, then reviewed and edited by a human. This post is about what
> the model got right, what it got wrong, and why the honest latency (57-65s
> per turn on CPU) is in the marketing instead of hidden.

## Hacker News (Show HN draft)

> Show HN: Mycelium – a local-first agent workstation on a 522MB model
>
> Hi HN — mycelium scaffolds apps (with tests that actually run), researches
> pages, drafts content, calls configured APIs, and runs YAML workflows with
> checkpoints. It runs on a 522MB model locally; cloud backends are optional
> adapters.
>
> The architecture borrows from the ccr pattern (local proxy, Anthropic +
> OpenAI endpoints) but adds the agent loop, a JSONL memory that distills
> every run, and context budgeting with logged compaction.
>
> Two honest caveats: CPU-only generation is ~1 minute per turn, and small
> models need explicit tool naming in prompts. Both are measured in
> docs/BENCHMARKS.md.
>
> Repo: github.com/toptacos/mycelium

## Outreach targets

| Target | Angle | Contact |
|---|---|---|
| LocalLLaMA mods | benchmark post, no promo links in body | modmail + r/LocalLLaMA |
| TLDR AI | "local-first vs $20/mo" angle | dan@tldrnewsletter.com (submissions form) |
| Ben's Bites | tools section | submissions@bensbites.com |
| Ollama Discord #showcase | screenshot + cast link | discord.gg/ollama |
| Panaversity (ccr setup authors) | "we built on the same pattern" | their community |

## Cadence rules

- One original post per platform per week. Cross-posts are rewritten, not dumped.
- Reply to every comment for the first 72 hours after launch.
- Every claim carries a link to a measured number. If we can't measure it, we
  don't post it.
