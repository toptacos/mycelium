#!/usr/bin/env bash
# List prompts, workflows, and backends. No model required.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
export MYCELIUM_NO_SPLASH=1
MCY=(uv run mcy)
if command -v mcy >/dev/null 2>&1 && [[ "${USE_PATH_MCY:-0}" == 1 ]]; then
  MCY=(mcy)
fi

echo "### prompts list"
"${MCY[@]}" prompts list
echo
echo "### workflow list"
"${MCY[@]}" workflow list
echo
echo "### models"
"${MCY[@]}" models
