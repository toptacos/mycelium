#!/usr/bin/env bash
# Dogfood mycelium: generate the launch blog posts with the tool itself,
# against the live local model, with verbose logs captured per post.
set -uo pipefail

cd "$(dirname "$0")/.."
LOG_DIR="logs/blog"
WS="workspace"
mkdir -p "$LOG_DIR" "$WS/workflows"
cp -n workflows/*.yaml "$WS/workflows/" 2>/dev/null || true

post() {
  local slug="$1" topic="$2" audience="$3" words="$4"
  echo "[blog] $slug started $(date -u +%H:%M:%S)"
  uv run mcy --workspace "$WS" run \
    "Use the create_content tool with kind='blog', topic='$topic', audience='$audience', tone='clear, confident, and practical', max_words=$words. Then reply with the final file path and word count." \
    --verbose > "$LOG_DIR/$slug.log" 2>&1
  echo "[blog] $slug done rc=$? $(date -u +%H:%M:%S)"
}

post "introducing-mycelium" \
  "Introducing Mycelium: a local-first agent workstation that scaffolds apps, researches, creates content, calls APIs, and runs workflows on your own machine" \
  "backend developers and AI tinkerers" 700

post "mycelium-vs-claude-code-ccr" \
  "Mycelium vs Claude Code with a free Claude Code Router setup: what each does well, and when to keep your agent loop local" \
  "developers comparing AI coding setups" 700

post "local-ai-tooling-compared" \
  "Comparing local AI agent tools: Mycelium vs Open WebUI vs LibreChat vs Continue vs Aider - chat UIs versus agent workstations" \
  "developers choosing local AI tooling" 700

post "local-first-case" \
  "Why your AI agent should sleep on your machine: privacy, cost, and context control for local-first agents" \
  "privacy-minded engineers and engineering leads" 650

post "scaffolding-with-522mb" \
  "From prompt to project: scaffolding a tested Python CLI with a 522MB model on a laptop" \
  "developers curious about small local models" 650

echo "[blog] all done $(date -u +%H:%M:%S)"
