# VM Guides

Prove the tool works on a clean machine, not just yours. Three paths:

| Path | Best for | Time |
|---|---|---|
| Vagrant + VirtualBox | Ubuntu, Fedora, Windows matrices | ~20 min/box |
| Multipass | macOS/Linux hosts, quick smoke | ~10 min |
| GitHub Actions | every PR (already wired) | free |

All three run the same in-guest smoke test: `scripts/vm-inside-smoke.sh`.

## What the smoke test proves

1. `python --version && uv --version`
2. `mcy doctor` exits 0 (or prints exactly what to fix)
3. The full unit + integration suite passes on this OS
4. The five sample-prompt scenarios pass (deterministic, scripted backend)
5. The proxy answers `/healthz` on 127.0.0.1
6. If Ollama is present, the live tier runs too

If any step fails, exit code is non-zero and the last line is
`SMOKE FAIL on <uname>`.

## 1. Vagrant (Ubuntu 24.04)

```bash
cd vms/ubuntu
vagrant up --provider virtualbox    # provisions: uv, ollama, qwen3:0.6b, uv sync
vagrant ssh -c "bash /vagrant/scripts/vm-inside-smoke.sh"
vagrant destroy -f
```

The provisioner (`vms/ubuntu/provision-ubuntu.sh`) is the same script the
one-liner documents, written for apt. Fedora is identical with dnf
(`vms/fedora/provision-fedora.sh`).

## 2. Vagrant (Windows Server 2022)

```bash
cd vms/windows
vagrant up --provider virtualbox
vagrant powershell -c "cd C:\vagrant; uv run pytest -q"
vagrant destroy -f
```

`provision-windows.ps1` installs uv via the official installer, installs
Ollama via `OllamaSetup.exe /S`, pulls the model, and runs the suite. Windows
is Windows-only in CI and in the guest — no cross-shell assumptions in the
package itself.

## 3. Multipass (macOS/Linux hosts)

```bash
multipass launch 24.04 --name mycelium --cloud-init vms/common/multipass-cloud-init.yaml
multipass exec mycelium -- bash -c "curl -fsSL https://astral.sh/uv/install.sh | sh && echo done"
# then copy or mount the repo and run the smoke test inside
multipass delete mycelium && multipass purge
```

The cloud-init installs uv, Ollama, and `qwen3:0.6b` on first boot.

## 4. All boxes at once

```bash
scripts/vm-smoke.sh            # ubuntu + fedora + windows
scripts/vm-smoke.sh ubuntu     # one box
```

Requirements: VirtualBox + Vagrant installed on the host. The script
brings each box up, runs the smoke test via SSH/WinRM, and destroys the box —
no state left behind.

## 5. CI (already running)

`.github/workflows/ci.yml` runs the suite on `ubuntu-latest`, `macos-latest`,
and `windows-latest` across Python 3.11-3.13, and the live Ollama tier on
Ubuntu with `qwen3:0.6b`. A green badge on `main` means: three OSes, three
Pythons, real model.

## Expected results (recorded)

- Ubuntu 24.04 / Fedora 40 / macOS: identical pass signatures (paths and
  Python minor version aside).
- Windows: suite passes; the live tier runs on `windows-latest` in CI.
- The one failure class we have seen is environmental, and the doctor prints
  the fix: e.g. `backend:local FAIL unreachable — required: it is the active
  backend` when Ollama isn't running.
