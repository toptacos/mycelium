---
name: kraken-mycelium-workstation
description: >-
  Use when setting up, running, or automating a local developer environment
  with Kraken plus mycelium — plan-only Docker compose, isolated homes, the
  topta.co hub workstation, environment doctor, or periodic public-site
  analysis. Prefer in-repo run.sh over docker compose up, rsync, or production
  seed/migrate.
---

# Kraken + mycelium workstation

mycelium is the head. Kraken is the hands. This is a **local developer
toolkit**. It is not how production `*.topta.co` is served.

## First commands

Generic (any clone of mycelium):

```bash
uv run mcy example list
uv run mcy example copy 04-kraken-compose
bash examples/04-kraken-compose/run.sh dry-run
bash examples/04-kraken-compose/run.sh live
```

topta.co hub (TopTacos checkout):

```bash
bash workstation/toptaco-hub/run.sh status
bash workstation/toptaco-hub/run.sh dry-run
bash workstation/toptaco-hub/run.sh live
```

Kraken-only stub in the current directory:

```bash
kraken init --env
kraken up --file compose.yaml
```

`dry-run` and `live` need no model. Use `summarize` / `analyze` only when the
operator asked for an AI brief of live public pages.

## Never

- `docker compose up` / `docker compose up -d`
- `kraken up --start`
- rsync or scp to droplets
- production seed, truncate, or `DELETE FROM`
- `bash …/run.sh install-schedule` unless the operator asked to load launchd

`kraken up` without `--start` is the plan. Loopback binds only.
`KRAKEN_OFFLINE=1` stays set in the example `run.sh` files.

## If the operator says “doctor the local environment”

Run `run.sh dry-run` then `live` (or `status` then `live` on the hub). Do not
invent a compose stack beside these recipes.
