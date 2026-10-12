#!/usr/bin/env bash
# Provisioning for the Fedora VM (runs as root via vagrant).
set -euxo pipefail

dnf install -y curl git gcc-c++ make

curl -fsSL https://astral.sh/uv/install.sh | sh
ln -sf /root/.local/bin/uv /usr/local/bin/uv

curl -fsSL https://ollama.com/install.sh | sh
ollama serve > /var/log/ollama.log 2>&1 &
sleep 5
ollama pull qwen3:0.6b

cd /vagrant
uv sync --dev

echo "== provisioning complete =="
uv run mcy doctor || true
