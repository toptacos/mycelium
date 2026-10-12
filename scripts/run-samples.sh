#!/usr/bin/env bash
# Run the five sample-prompt scenarios end to end.
#   scripts/run-samples.sh scripted   # deterministic, no model needed
#   scripts/run-samples.sh live       # real Ollama (slow on CPU)
set -euo pipefail

cd "$(dirname "$0")/.."
MODE="${1:-scripted}"
WS="${MYCELIUM_WS:-workspace}"
HOME_DIR="${MYCELIUM_HOME:-$PWD/.mycelium-home}"

mkdir -p "$WS/workflows"
cp -n workflows/*.yaml "$WS/workflows/" 2>/dev/null || true

cat > "$WS/mycelium.toml" <<'EOF'
[connections.example]
base_url = "http://127.0.0.1:9799"
methods = ["GET"]
EOF

FIXTURE_PID=""
if [ "$MODE" = "scripted" ]; then
  uv run python scripts/fixture-server.py 9799 &
  FIXTURE_PID=$!
  sleep 1
fi
trap '[ -n "$FIXTURE_PID" ] && kill "$FIXTURE_PID" 2>/dev/null || true' EXIT

run() {
  local name="$1" task="$2"
  echo "=============================================================="
  echo "### $name"
  echo "=============================================================="
  if [ "$MODE" = "live" ]; then
    uv run mcy --workspace "$WS" --home "$HOME_DIR" --verbose run "$task"
  else
    uv run mcy --workspace "$WS" --home "$HOME_DIR" --verbose run "$task" --scripted "scripts/fixtures/$name.json"
  fi
  echo
}

run scaffold-app "Use the scaffold_app tool with name='change-calculator' and template='python-cli' and run_tests=true. Then report every file created and whether tests passed."
run research "Use research_web on http://127.0.0.1:9799/ and answer 'what is this page for?'. Save notes to research/example-com.md using fs_write with the source URL included."
run content "Use create_content with kind='blog', topic='why local-first AI agents matter', audience='backend developers', max_words=300. Then report the file path and word count."
run integration "Use call_api with connection='example', method='GET', path='/status'. Summarize the status and payload."
run workflow "Use run_workflow with workflow='release-notes' and inputs={\"repo_path\": \".\"}. Report each step outcome."

echo "=============================================================="
echo "### session analysis"
echo "=============================================================="
uv run mcy --workspace "$WS" --home "$HOME_DIR" report

echo
echo "artifacts:"
find "$WS/apps" "$WS/research" "$WS/content" "$WS/RELEASE_NOTES.md" -type f 2>/dev/null | sort || true
