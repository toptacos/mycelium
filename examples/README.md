# Examples

Runnable recipes for the public CLI (`mcy`). Each folder has a short README,
a shell script you can run after install, and `expected.txt` captured on a
real machine (structure matters more than exact wording).

| Example | Needs model? | What it shows |
|---|---|---|
| [01-explore](01-explore/) | no | `prompts list`, `workflow list`, `models` |
| [02-memory](02-memory/) | no | `learn` + `memory recall` round-trip |
| [03-workflow-dry-run](03-workflow-dry-run/) | no | `workflow run … --dry-run` |

Also see:

| Path | What it is |
|---|---|
| `logs/explore.txt` | Older captured explore session |
| [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md) | How the layers fit |
| [`docs/INSTALL.md`](../docs/INSTALL.md) | Per-OS install |
| [`scripts/run-samples.sh`](../scripts/run-samples.sh) | Five sample-prompt scenarios (scripted or live) |

## Prerequisites

```bash
# from a clone
uv sync
# or after the one-liner install
curl -fsSL https://mycelium.topta.co/mcy | sh
```

Then:

```bash
bash examples/01-explore/run.sh
bash examples/02-memory/run.sh
bash examples/03-workflow-dry-run/run.sh
```

Compare stdout to each folder's `expected.txt`. Paths and table borders may
differ; the command names and key phrases should appear.
