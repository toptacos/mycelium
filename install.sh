#!/usr/bin/env bash
# mycelium installer — served at https://mycelium.topta.co/install.sh
#
# One-liner (uses the MCY acronym):
#   curl -fsSL https://mycelium.topta.co/mcy | sh
#
# Or explicitly:
#   curl -fsSL https://mycelium.topta.co/install.sh | sh
#
# What it does:
#   1. installs uv (if missing)          — astral.sh/uv/install.sh
#   2. clones or updates the repo        — ~/.mycelium/src by default
#   3. uv sync --dev
#   4. installs the `mcy` shim on PATH  — ~/.local/bin/mcy
#   5. optionally installs Ollama + qwen3:0.6b (--with-model / prompt)
#   6. runs `mcy doctor` and prints next steps
#
# Flags (env or args):
#   MCY_REF=main            git ref to install
#   MCY_DIR=~/.mycelium/src source directory
#   MCY_MODEL=1             also install Ollama + qwen3:0.6b
#   MCY_NO_DOCTOR=1         skip the doctor run
set -euo pipefail

REPO_URL="${MCY_REPO:-https://github.com/toptacos/mycelium.git}"
REF="${MCY_REF:-main}"
SRC_DIR="${MCY_DIR:-$HOME/.mycelium/src}"
BIN_DIR="${MCY_BIN:-$HOME/.local/bin}"
MODEL="${MCY_MODEL:-0}"
SKIP_DOCTOR="${MCY_NO_DOCTOR:-0}"

for arg in "$@"; do
  case "$arg" in
    --with-model) MODEL=1 ;;
    --no-doctor) SKIP_DOCTOR=1 ;;
    --ref=*) REF="${arg#*=}" ;;
    *) echo "unknown flag: $arg" >&2; exit 2 ;;
  esac
done

say() { printf '\033[1;36m[mcy]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[mcy]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31m[mcy]\033[0m %s\n' "$*" >&2; exit 1; }

say "mycelium installer (ref: $REF)"

# ---- 1. uv -----------------------------------------------------------------
if ! command -v uv >/dev/null 2>&1; then
  say "installing uv"
  curl -fsSL https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi
command -v uv >/dev/null 2>&1 || die "uv not on PATH after install"

# ---- 2. source -------------------------------------------------------------
if [ -d "$SRC_DIR/.git" ]; then
  say "updating $SRC_DIR"
  git -C "$SRC_DIR" fetch --depth 1 origin "$REF"
  git -C "$SRC_DIR" checkout -f FETCH_HEAD
else
  say "cloning into $SRC_DIR"
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$SRC_DIR"
fi

# ---- 3. deps ---------------------------------------------------------------
say "syncing dependencies (uv sync --dev)"
(cd "$SRC_DIR" && uv sync --dev)

# ---- 4. mcy shim -----------------------------------------------------------
mkdir -p "$BIN_DIR"
cat > "$BIN_DIR/mcy" <<EOF
#!/usr/bin/env bash
exec uv run --project "$SRC_DIR" python -m mycelium.cli "\$@"
EOF
chmod +x "$BIN_DIR/mcy"
say "installed $BIN_DIR/mcy"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) warn "$BIN_DIR is not on PATH; add:  export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac

# ---- 5. local model (optional) ---------------------------------------------
if [ "$MODEL" = "1" ]; then
  if ! command -v ollama >/dev/null 2>&1; then
    say "installing ollama"
    curl -fsSL https://ollama.com/install.sh | sh || warn "ollama install failed; install manually from https://ollama.com"
  fi
  if command -v ollama >/dev/null 2>&1; then
    say "pulling qwen3:0.6b (522MB)"
    ollama pull qwen3:0.6b || warn "model pull failed; run: ollama pull qwen3:0.6b"
  fi
else
  say "skipping local model (pass --with-model to install Ollama + qwen3:0.6b)"
fi

# ---- 6. doctor --------------------------------------------------------------
if [ "$SKIP_DOCTOR" != "1" ]; then
  say "running: mcy doctor"
  "$BIN_DIR/mcy" doctor || warn "doctor reported issues; re-run with: mcy doctor"
fi

say "done. try:  mcy prompts list  |  mcy chat  |  mcy run \"...\""
say "docs: https://github.com/toptacos/mycelium"
