#!/usr/bin/env bash
# MCY — the acronym route to the mycelium installer.
# Hosted at https://mycelium.topta.co/mcy so that:
#
#   curl -fsSL https://mycelium.topta.co/mcy | sh
#
# works exactly like the full /install.sh path. Keep this file in sync with
# install.sh (it is the same script; this one documents the acronym contract).
set -euo pipefail
cd "$(dirname "$0")"
exec ./install.sh "$@"
