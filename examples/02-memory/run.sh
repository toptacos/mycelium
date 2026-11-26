#!/usr/bin/env bash
# Learn a preference and recall it. Isolated temp workspace.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MYCELIUM_NO_SPLASH=1
WS="$(mktemp -d)"
HOME_DIR="$(mktemp -d)"
trap 'rm -rf "$WS" "$HOME_DIR"' EXIT

MCY=(uv run mcy --workspace "$WS" --home "$HOME_DIR")
if command -v mcy >/dev/null 2>&1 && [[ "${USE_PATH_MCY:-0}" == 1 ]]; then
  MCY=(mcy --workspace "$WS" --home "$HOME_DIR")
fi

echo "### learn"
"${MCY[@]}" learn "deploys are fridays only" --kind preference --tags deploy
echo
echo "### memory recall"
"${MCY[@]}" memory recall "when do we deploy"
