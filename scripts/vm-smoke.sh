#!/usr/bin/env bash
# Drive the VM matrix: bring up each box, run the in-guest smoke test, destroy.
# Requires VirtualBox + Vagrant (https://developer.hashicorp.com/vagrant).
# Usage: scripts/vm-smoke.sh [ubuntu|fedora|windows]
set -euo pipefail
cd "$(dirname "$0")/.."

BOX="${1:-all}"

run_box() {
  local name="$1" dir="vms/$1"
  echo "############### $name ###############"
  [ -d "$dir" ] || { echo "missing $dir"; return 1; }
  (cd "$dir" && vagrant up --provider virtualbox) || return 1
  if [ "$name" = "windows" ]; then
    (cd "$dir" && vagrant powershell -c "cd C:\vagrant; bash scripts/vm-inside-smoke.sh") || return 1
  else
    (cd "$dir" && vagrant ssh -c "bash /vagrant/scripts/vm-inside-smoke.sh") || return 1
  fi
  (cd "$dir" && vagrant destroy -f)
}

case "$BOX" in
  ubuntu)   run_box ubuntu ;;
  fedora)   run_box fedora ;;
  windows)  run_box windows ;;
  all)
    for b in ubuntu fedora windows; do
      run_box "$b" || echo "!!! $b failed"
    done
    ;;
  *) echo "usage: scripts/vm-smoke.sh [ubuntu|fedora|windows|all]"; exit 2 ;;
esac
