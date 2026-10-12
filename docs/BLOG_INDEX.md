# Blog Index — launch content

Every post below was **drafted by mycelium itself** (`mcy run "Use
create_content ..."` against the local `qwen3:0.6b` model), then reviewed and
edited by a human. The model, word cap, and audience are recorded in each
post's front matter — the same metadata the tool writes.

The verbose logs from every generation run are in `logs/blog/*.log`. That is
the honest record: generation times, token counts, and the model's actual raw
output, before editing.

## Posts

| Post | File | Model | Words cap | Status |
|---|---|---|---|---|
| Introducing mycelium | `content/introducing-mycelium-...-blog.md` | qwen3:0.6b | 700 | draft + editor's note |
| vs Claude Code + ccr | `content/mycelium-vs-claude-code-ccr-blog.md` | qwen3:0.6b | 700 | draft + editor's note |
| Local AI tooling compared | `content/local-ai-tooling-compared-blog.md` | qwen3:0.6b | 700 | draft + editor's note |
| The local-first case | `content/local-first-case-blog.md` | qwen3:0.6b | 650 | draft + editor's note |
| Scaffolding with 522MB | `content/scaffolding-with-522mb-blog.md` | qwen3:0.6b | 650 | draft + editor's note |

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
