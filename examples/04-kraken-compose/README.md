# 04 — Kraken compose workstation

mycelium is the head. Kraken is the hands. Isolated homes, plan-only Docker,
loopback binds. No production writes.

`dry-run` and `live` need no model. `summarize` needs a local Ollama model.

```bash
bash examples/04-kraken-compose/run.sh dry-run
bash examples/04-kraken-compose/run.sh live
```

From any mycelium checkout:

```bash
uv run mcy example copy 04-kraken-compose /tmp/reef
bash /tmp/reef/run.sh dry-run
```

Do **not** run `docker compose up`, `kraken up --start`, or rsync. The shift
calls `kraken up --file compose.yaml` without `--start`.

Expected: see `expected.txt` for dry-run. Exit 0. `live` writes `ENVIRONMENT.md`
and leaves containers stopped.

## Suggested prompts

- Plan my local stack (no containers)
- Run the Kraken compose example dry-run, then live. Do not start Docker.
- Copy 04-kraken-compose with `mcy example` and doctor it
