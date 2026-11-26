#!/usr/bin/env bash
# Dry-run the release-notes workflow. No model required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MYCELIUM_NO_SPLASH=1
WS="$(mktemp -d)"
HOME_DIR="$(mktemp -d)"
trap 'rm -rf "$WS" "$HOME_DIR"' EXIT
mkdir -p "$WS/workflows"
cp "$ROOT/workflows/release-notes.yaml" "$WS/workflows/"

MCY=(uv run mcy --workspace "$WS" --home "$HOME_DIR")
if command -v mcy >/dev/null 2>&1 && [[ "${USE_PATH_MCY:-0}" == 1 ]]; then
  MCY=(mcy --workspace "$WS" --home "$HOME_DIR")
fi

echo "### workflow run release-notes --dry-run"
"${MCY[@]}" workflow run release-notes --dry-run --input repo_path="$ROOT"
