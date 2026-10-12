#!/usr/bin/env bash
# Provisioning for the Ubuntu VM (runs as root via vagrant).
set -euxo pipefail

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl git build-essential

# uv (Python package manager)
curl -fsSL https://astral.sh/uv/install.sh | sh
echo 'export PATH="/root/.local/bin:$PATH"' > /etc/profile.d/uv.sh
ln -sf /root/.local/bin/uv /usr/local/bin/uv

# Ollama + a small model
curl -fsSL https://ollama.com/install.sh | sh
ollama serve > /var/log/ollama.log 2>&1 &
sleep 5
ollama pull qwen3:0.6b

# Sync deps (repo is mounted at /vagrant)
cd /vagrant
uv sync --dev

echo "== provisioning complete =="
uv run mcy doctor || true
