#!/usr/bin/env bash
# Re-run the pieces that failed when Ollama died: blog post 5 + live cast 03.
set -uo pipefail
cd "$(dirname "$0")/.."
LOG_DIR="logs/blog"
WS="workspace"
mkdir -p "$LOG_DIR" "$WS/workflows"
cp -n workflows/*.yaml "$WS/workflows/" 2>/dev/null || true

echo "[blog] scaffolding-with-522mb started $(date -u +%H:%M:%S)"
uv run mcy --workspace "$WS" run \
  "Use the create_content tool with kind='blog', topic='From prompt to project: scaffolding a tested Python CLI with a 522MB model on a laptop', audience='developers curious about small local models', tone='clear, confident, and practical', max_words=650. Then reply with the final file path and word count." \
  --verbose > "$LOG_DIR/scaffolding-with-522mb.log" 2>&1
echo "[blog] scaffolding-with-522mb done rc=$? $(date -u +%H:%M:%S)"

echo "[cast] 03 re-record"
uv run python scripts/record-casts.py --name 03-scaffold-live --title "scaffold an app with a 522MB model" \
  --cmd "uv run mcy --workspace workspace run \"Use the scaffold_app tool with name='cast-demo2' and template='python-cli' and run_tests=true. Report every file created and whether tests passed.\"" \
  --max-wait 420
echo "[cast] done $(date -u +%H:%M:%S)"
