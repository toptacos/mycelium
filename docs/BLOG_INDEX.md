# Blog Index — launch content

Every post below was **drafted by mycelium itself** (`mcy run "Use
create_content ..."` against the local `qwen3:0.6b` model), then reviewed and
edited by a human. The model, word cap, and audience are recorded in each
post's front matter — the same metadata the tool writes.

The verbose logs from every generation run are in `logs/blog/*.log`. That is
the honest record: generation times, token counts, and the model's actual raw
output, before editing.

## Posts

| # | Post | Final file | Model | Words cap | Editorial outcome |
|---|---|---|---|---|---|
| 1 | Introducing mycelium | `docs/blog/01-introducing-mycelium.md` | qwen3:0.6b | 700 | rewritten: draft had no commands or numbers |
| 2 | vs Claude Code + ccr | `docs/blog/02-vs-claude-code-ccr.md` | qwen3:0.6b | 700 | rewritten: draft hallucinated blockchain; called Claude Code open-source |
| 3 | Local AI tooling compared | `docs/blog/03-local-tooling-compared.md` | qwen3:0.6b | 700 | rewritten: draft hallucinated "ecological system" + invented competitor "Lib-blog.md" |
| 4 | The local-first case | `docs/blog/04-local-first-case.md` | qwen3:0.6b | 650 | edited: draft claims made specific and sourced |
| 5 | Scaffolding with 522MB | `docs/blog/05-scaffolding-with-522mb.md` | qwen3:0.6b | 650 | rewritten: draft was generic CLI advice (Tkinter, PyTorch), not the measured run |
| 6 | Kraken hands | `docs/blog/06-kraken-hands.md` | human | — | canonical on kraken.topta.co/blog; composition with Kraken, plan-only Docker |

Raw model output is preserved verbatim in the verbose logs; each final post
carries an editor's note listing exactly what was wrong and where the
corrections come from.

## Editorial policy for dogfooded content

1. **The model writes; a human edits.** Structure, facts, and links are
   corrected; the model's voice examples are kept where they work.
2. **The raw draft is preserved.** We do not quietly rewrite the model's output
   and call it generated. Front matter + logs show exactly what came out.
3. **No fabricated numbers.** Every claim in the final posts traces to
   `docs/BENCHMARKS.md`, `logs/bench.json`, or a cast.
4. **Known model failure modes are documented, not hidden** — see the editor's
   note appended to each post.

## Regenerating

```bash
bash scripts/generate-blog-posts.sh          # all five, live model
uv run mcy run "Use create_content with kind='blog', topic='...'"   # one
```

Each post takes 2-6 minutes on a CPU-only machine. Verbose logs land in
`logs/blog/`.
