#!/usr/bin/env bash
# Smoke test that runs INSIDE a guest (VM/container/CI). Verifies the full
# stack on this machine: doctor, test suite, sample-prompt suite, proxy.
# Exit 0 = this OS runs mycelium.
set -uo pipefail

cd "$(dirname "$0")/../.." 2>/dev/null || cd /vagrant || {
  echo "run from inside a mycelium checkout" >&2
  exit 2
}

fail=0
step() { echo; echo "=== $1 ==="; }

step "python + uv"
python3 --version && uv --version || fail=1

step "doctor"
uv run mcy doctor || fail=1

step "unit + integration suite"
uv run pytest -q || fail=1

step "sample-prompt suite (scripted, deterministic)"
bash scripts/run-samples.sh scripted || fail=1

step "proxy endpoint"
uv run mcy serve --port 8787 >/tmp/mcy-proxy.log 2>&1 &
proxy_pid=$!
sleep 3
curl -sf http://127.0.0.1:8787/healthz || fail=1
kill $proxy_pid 2>/dev/null || true

step "ollama (optional but expected)"
if curl -sf http://127.0.0.1:11434/api/tags > /dev/null; then
  echo "ollama reachable"
  uv run pytest -m live -q || fail=1
else
  echo "ollama not present: live tier skipped (allowed)"
fi

echo
if [ "$fail" = "0" ]; then
  echo "SMOKE PASS on $(uname -srm)"
else
  echo "SMOKE FAIL on $(uname -srm)"
fi
exit $fail
