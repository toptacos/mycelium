# Examples

Real captured output from real runs on the author's machine (Intel MacBook,
macOS 25.6, CPU-only, 2026-10-11). Nothing here is hand-edited.

| Path | What it is |
|---|---|
| `logs/explore.txt` | `mcy prompts list`, `mcy workflow list`, `mcy models` |
| `logs/bench.json` | output of `python scripts/bench.py` — CLI start, import, suite times, proxy RTT, memory IO |
| `logs/blog/*.log` | verbose telemetry from generating each launch blog post with the live model |

Screencasts (asciinema casts) live in `site/casts/` — see
[docs/SCREENCASTS.md](../docs/SCREENCASTS.md).

## Reproduce

```bash
uv run mcy prompts list
uv run mcy workflow list
uv run mcy models
python scripts/bench.py --out logs/bench.json
bash scripts/generate-blog-posts.sh     # writes logs/blog/
```

Numbers will differ on your machine (especially the model turns — Apple
Silicon is 5-10x faster than the Intel CPU this was measured on). The
*structure* of the output is what matters.
