#!/usr/bin/env bash
# Record all demo screencasts as asciinema v2 casts into site/casts/.
# Real commands, real outputs, real model where needed. Run from repo root.
set -euo pipefail
cd "$(dirname "$0")/.."

R="uv run python scripts/record-casts.py"
WS_ARGS="--workspace workspace"
mkdir -p site/casts workspace/workflows
cp -n workflows/*.yaml workspace/workflows/ 2>/dev/null || true

echo "== 01 install + doctor =="
$R --name 01-install-doctor --title "install and doctor" \
  --cmd "uv sync" \
  --cmd "uv run mcy doctor"

echo "== 02 explore =="
$R --name 02-explore --title "explore prompts, models, workflows" \
  --cmd "uv run mcy prompts list" \
  --cmd "uv run mcy models" \
  --cmd "uv run mcy workflow list"

echo "== 03 scaffold (live model, ~2 min) =="
$R --name 03-scaffold-live --title "scaffold an app with a 522MB model" \
  --cmd "uv run mcy $WS_ARGS run \"Use the scaffold_app tool with name='cast-demo' and template='python-cli' and run_tests=true. Report every file created and whether tests passed.\"" \
  --max-wait 420

echo "== 04 workflow (live tools) =="
$R --name 04-workflow --title "run a workflow end to end" \
  --cmd "uv run mcy $WS_ARGS workflow run onboard-check --input app_name=cast-demo"

echo "== 05 proxy (ccr-compatible) =="
$R --name 05-proxy --title "the local proxy: OpenAI + Anthropic endpoints" \
  --cmd "uv run mcy serve --port 8787 &" \
  --cmd "sleep 2" \
  --cmd "curl -s http://127.0.0.1:8787/healthz" \
  --cmd "curl -s http://127.0.0.1:8787/v1/models | head -c 240" \
  --cmd "curl -s -X POST http://127.0.0.1:8787/v1/chat/completions -H 'content-type: application/json' -d '{\"model\": \"qwen3:0.6b\", \"messages\": [{\"role\": \"user\", \"content\": \"Reply with exactly: cast ok\"}], \"max_tokens\": 24}'" \
  --cmd "kill %1"

echo "== 06 learn + report =="
$R --name 06-learn-report --title "teach it something, then analyze the session" \
  --cmd "uv run mcy $WS_ARGS learn \"demo day is thursday\" --kind preference --tags schedule" \
  --cmd "uv run mcy $WS_ARGS memory recall \"what day is demo\"" \
  --cmd "uv run mcy $WS_ARGS report"

echo "== 07 sample suite (scripted, deterministic) =="
$R --name 07-sample-suite --title "the five sample-prompt scenarios" \
  --cmd "bash scripts/run-samples.sh scripted 2>&1 | tail -30" \
  --max-wait 300

echo "done. casts:" && ls -la site/casts/
