# Screencasts

Demos are recorded as [asciinema v2](https://docs.asciinema.org/manual/asciicast/v2/)
casts in `site/casts/` — real commands, real outputs, real model where needed.
Re-record everything with `scripts/record-all-casts.sh`.

| Cast | Shows | Duration | Model |
|---|---|---|---|
| `01-install-doctor` | `uv sync` + `mcy doctor` | ~6s | none |
| `02-explore` | `prompts list`, `models`, `workflow list` | ~10s | none |
| `03-scaffold-live` | scaffold a Python CLI, run its tests | ~6 min | qwen3:0.6b live |
| `04-workflow` | `workflow run onboard-check` end to end | ~3s | none (tool steps) |
| `05-proxy` | proxy + OpenAI/Anthropic endpoints via curl | ~10s | qwen3:0.6b live |
| `06-learn-report` | `learn`, `memory recall`, `report` | ~5s | none |
| `07-sample-suite` | `scripts/run-samples.sh scripted` | ~30s | scripted |

## Playing

In a browser with the asciinema player:

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/asciinema-player@3.7.1/dist/bundle/asciinema-player.css">
<div id="cast"></div>
<script src="https://cdn.jsdelivr.net/npm/asciinema-player@3.7.1/dist/bundle/asciinema-player.min.js"></script>
<script>
  AsciinemaPlayer.create("casts/03-scaffold-live.cast", document.getElementById("cast"));
</script>
```

Or locally:

```bash
brew install asciinema      # or: uv tool install asciinema
asciinema play site/casts/03-scaffold-live.cast
```

## What you'll see in 03 (the honest one)

1. The task is sent with the tool named explicitly ("Use the scaffold_app
   tool with name='cast-demo'...").
2. The first model turn takes ~57-65s on this CPU-only machine. The cast is
   real time — we don't cut the wait.
3. `scaffold_app` executes in ~10ms and creates 7 files.
4. The scaffold's own `pytest` run passes.
5. The model lists every file it created and gets it right.

## Recording new casts

`scripts/record-casts.py` drives a pty, feeds commands, and uses a unique PS1
marker to know when each command finished — so slow commands are captured in
full:

```bash
uv run python scripts/record-casts.py --name my-demo --title "my demo" \
  --cmd "uv run mcy doctor" --cmd "uv run mcy prompts list"
```

Casts land in `site/casts/<name>.cast`. The recorder is deterministic plumbing;
the *content* is whatever the machine actually printed, warts included.
