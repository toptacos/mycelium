# 02 — Learn + recall

Teach mycelium a preference, then recall it from local JSONL memory.
Uses an isolated temp workspace. No model server required.

```bash
bash examples/02-memory/run.sh
```

Expected: see `expected.txt`. `learn` prints an id; `memory recall` prints the
preference line with the `deploy` tag.
