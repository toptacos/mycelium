#!/usr/bin/env bash
# One sequential media job: blog posts first, then screencast re-recording.
# Serializes model access on CPU-only machines (concurrent generations time out).
set -uo pipefail
cd "$(dirname "$0")/.."

echo "########## phase 1: blog posts ##########"
bash scripts/generate-blog-posts.sh
echo "########## phase 2: casts ##########"
bash scripts/record-all-casts.sh
echo "########## done $(date -u +%H:%M:%S) ##########"
