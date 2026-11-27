---
title: "mycelium is the head, Kraken is the hands: compose a laptop workstation without starting Docker"
kind: blog
audience: backend developers and AI tinkerers
tone: clear, confident, and practical
canonical: https://kraken.topta.co/blog/kraken-vs-mycelium
status: human-written
---

# mycelium is the head. Kraken is the hands.

Everyone assumes an agent and a plugin runner are the same kind of CLI.
They are not.

**mycelium** (`mcy`) plans. You name a goal in English. A model (or a
YAML workflow) picks tools inside a workspace jail.

**Kraken** (`kraken` / `k`) executes typed verbs. You name a tentacle and
an action. JSON in, policy, exec, JSON out. Core never imports the
handler. This is TopTaco's Kraken, not Payward.

They sit on the same laptop. They are not substitutes. Canonical write-up:
[Kraken vs mycelium](https://kraken.topta.co/blog/kraken-vs-mycelium).

## The default path needs no model

`mcy example copy 04-kraken-compose` then `bash examples/04-kraken-compose/run.sh dry-run`.
That shift doctors both CLIs and prints `kraken up --file compose.yaml`.
It does not pass `--start`. Loopback binds. Isolated homes. CI agents
with no Ollama still have a toolkit.

```bash
uv run mcy example list
uv run mcy example copy 04-kraken-compose
bash examples/04-kraken-compose/run.sh dry-run
```

Harbor-shaped cousin, in the TopTaco monorepo:

```bash
bash workstation/toptaco-hub/run.sh status
bash workstation/toptaco-hub/run.sh dry-run
```

Worked notes: [plan-only compose](https://kraken.topta.co/blog/plan-only-compose),
[hub shift](https://kraken.topta.co/blog/toptaco-hub-shift).

## What it is not

It is not how `*.topta.co` is served. Production stays static `dist/` on
nginx plus Laravel on the API host. On a droplet, Kraken shrinks to typed
shortcuts — no Ollama, no mycelium loop, no compose-as-site.
[Laptop toolkit, production shortcuts](https://kraken.topta.co/blog/laptop-not-production).

Do not `docker compose up`. Do not `kraken up --start` unless you mean
containers. Do not rsync. Do not seed.

## Prompts that land on the recipe

- Plan my local stack (no containers)
- Shift the topta.co hub workstation
- Analyze public pages with the local model

Agents find the doors in AGENTS.md, the `kraken-mycelium-workstation`
skill, and `mcy example`. Store notes are invisible.
[How agents find the workstation](https://kraken.topta.co/blog/how-agents-find-the-toolkit).
