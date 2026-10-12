# Installation

Three paths, in order of recommendation:

1. **One-liner** (macOS/Linux) — the `MCY` acronym route:
   ```bash
   curl -fsSL https://mycelium.topta.co/mcy | sh
   ```
   Equivalent to `/install.sh`; add `--with-model` to also install Ollama and
   pull the 522MB default model.
2. **From source** (any OS with Python 3.11+ and `uv`) — 60 seconds.
3. **Contribute/test in a VM** — see [VM-GUIDES.md](VM-GUIDES.md).

Real captured output from an Intel Mac (macOS 25.6) follows in each section.

---

## 1. One-liner (macOS / Linux)

```bash
curl -fsSL https://mycelium.topta.co/mcy | sh
```

What it does, in order: installs `uv` if missing → clones/updates
`~/.mycelium/src` → `uv sync --dev` → writes the `mcy` shim to `~/.local/bin`
→ runs `mcy doctor` → prints next steps.

Useful environment overrides:

```bash
MCY_REF=main MCY_DIR=~/code/mycelium MCY_MODEL=1 bash install.sh
```

| Flag | Meaning |
|---|---|
| `--with-model` | also install Ollama + pull `qwen3:0.6b` (522MB) |
| `--no-doctor` | skip the doctor check |
| `--ref=<git-ref>` | install a tag/branch/commit |
| `MCY_DIR=...` | source checkout location (default `~/.mycelium/src`) |
| `MCY_BIN=...` | shim location (default `~/.local/bin`) |

If `~/.local/bin` is not on your PATH the installer says so and prints the
export line; nothing is hidden.

### Windows

The one-liner needs bash. On Windows use path 2 (from source) or WSL:

```powershell
# PowerShell
winget install astral-sh.uv
git clone https://github.com/toptacos/mycelium.git $env:USERPROFILE\mycelium
cd $env:USERPROFILE\mycelium
uv sync
uv run mcy doctor
```

---

## 2. From source

```bash
git clone https://github.com/toptacos/mycelium.git
cd mycelium
uv sync                       # runtime deps only
uv sync --dev                 # + pytest, hypothesis (contributors)
uv run mcy doctor
```

Verified output on this machine:

```
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ check              ┃ status ┃ detail                                                 ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ python             │ OK     │ 3.14.3                                                 │
│ home dir           │ OK     │ /Users/.../.mycelium                                   │
│ workspace          │ OK     │ /Users/.../mycelium/workspace                          │
│ config             │ OK     │ no config file; using built-in defaults                │
│ backend:local      │ OK     │ reachable; models: qwen3:0.6b, qwen2.5-coder:latest, … │
│ backend:openrouter │ skip   │ not configured (set $OPENROUTER_API_KEY to enable)     │
...
│ backend:anthropic  │ skip   │ not configured (set $ANTHROPIC_API_KEY to enable)      │
└────────────────────┴────────┴────────────────────────────────────────────────────────┘

all checks passed
```

`skip` means "optional cloud adapter, not configured" — never a failure.

## 3. The local model (optional but recommended)

```bash
# install Ollama from https://ollama.com, then:
ollama pull qwen3:0.6b        # 522MB, the default
# heavier options:
ollama pull qwen2.5-coder:latest
ollama pull llama3:latest
```

No key, no account, no network after the pull.

## 4. First run

```bash
uv run mcy prompts list                     # the five sample scenarios
uv run mcy run "Use the scaffold_app tool with name='hello' and template='python-cli' and run_tests=true. Report every file created."
uv run mcy chat                             # REPL: /model, /tools, /memory
uv run mcy report                           # analyze the session log
```

## 5. Per-OS notes

### macOS (verified)

- Intel and Apple Silicon both work; on Intel, inference is CPU-only and slow
  (~1 min/turn with the 522MB model). Apple Silicon is roughly 5-10x faster.
- Ollama via the app bundle or `brew install ollama`.

### Linux (verified in CI + VM guides)

- Ubuntu 24.04, Fedora 40 provisioned automatically in `vms/`.
- Ollama's official installer script is the supported path.

### Windows (verified in CI matrix)

- `uv` via `winget install astral-sh.uv` or the PowerShell installer.
- Ollama via `OllamaSetup.exe`; the provisioner is in
  `vms/windows/provision-windows.ps1`.
- Paths and config resolution are `pathlib`/`os.environ` based — no
  POSIX-only assumptions in the package.

## 6. Updating

```bash
# one-liner installs re-run and update in place
curl -fsSL https://mycelium.topta.co/mcy | sh

# source installs
git pull && uv sync
```

## 7. Uninstall

```bash
rm -rf ~/.mycelium ~/.local/bin/mcy        # one-liner install
# source installs: just delete the checkout
```

No services, no launch agents, no telemetry to deregister.
