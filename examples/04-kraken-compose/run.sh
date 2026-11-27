#!/usr/bin/env bash
# Isolate a Kraken home + mycelium home, then plan a compose environment.
# Usage: bash run.sh [dry-run|live|summarize]
# dry-run and live need no model. summarize needs a local Ollama model.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$ROOT/../.." && pwd)"
cd "$ROOT"

MODE="${1:-live}"
export KRAKEN_HOME="$ROOT/example-home"
export MYCELIUM_HOME="$ROOT/.mycelium-home"
export MYCELIUM_SRC="${MYCELIUM_SRC:-$REPO}"
export MYCELIUM_WORKSPACE="$ROOT"
export MYCELIUM_NO_SPLASH=1
export KRAKEN_OFFLINE=1

mkdir -p "$KRAKEN_HOME" "$MYCELIUM_HOME"
chmod +x bin/mcy

if [[ ! -d "$MYCELIUM_SRC" ]]; then
  echo "error: mycelium source not found at $MYCELIUM_SRC (set MYCELIUM_SRC)" >&2
  exit 1
fi

echo "== kraken init (isolated home) =="
if ! command -v kraken >/dev/null 2>&1; then
  echo "error: kraken not on PATH. Install kraken-builder, then retry." >&2
  exit 1
fi
kraken init --home "$KRAKEN_HOME"

add_tentacle() {
  local name="$1"
  local src=""
  local cand
  for cand in \
    "$HOME/.kraken/tentacles/$name" \
    "$HOME/Projects/Kraken/kraken-builder/examples/tentacles/$name" \
    "${KRAKEN_BUILDER:-}/examples/tentacles/$name"
  do
    if [[ -n "$cand" && -d "$cand" ]]; then
      src="$cand"
      break
    fi
  done
  if [[ -z "$src" ]]; then
    echo "skip tentacle $name (source not found)"
    return 0
  fi
  echo "== kraken tentacle add $name from $src =="
  kraken tentacle add "$src" || echo "tentacle add $name already present or failed (continuing)"
}

add_tentacle filesort
add_tentacle notes
add_tentacle hello

MCY=(uv run --directory "$MYCELIUM_SRC" mcy --workspace "$ROOT" --home "$MYCELIUM_HOME")

echo "== mycelium workflow list =="
"${MCY[@]}" workflow list

echo "== mycelium workflow show shift =="
"${MCY[@]}" workflow show shift

case "$MODE" in
  dry-run)
    echo "== shift --dry-run =="
    "${MCY[@]}" workflow run shift --dry-run
    ;;
  live)
    echo "== shift (no LLM) =="
    "${MCY[@]}" workflow run shift
    ;;
  summarize)
    echo "== shift --input summarize=1 =="
    "${MCY[@]}" workflow run shift --input summarize=1
    ;;
  *)
    echo "usage: bash run.sh [dry-run|live|summarize]" >&2
    exit 2
    ;;
esac

echo
echo "KRAKEN_HOME=$KRAKEN_HOME"
echo "report: $ROOT/ENVIRONMENT.md"
if [[ -f ENVIRONMENT.md ]]; then
  echo "== ENVIRONMENT.md head =="
  head -n 40 ENVIRONMENT.md
fi
