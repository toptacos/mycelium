# Reef inventory

Filesort indexes this folder only (not `example-home/` or `.mycelium/`).

- `panel` — nginx:alpine on `127.0.0.1:18181`
- `cache` — redis:7-alpine on `127.0.0.1:16379`
- Shared Docker network name: `kraken`
- Operator rule: plan with `kraken up`; never `--start` under `KRAKEN_OFFLINE=1`
