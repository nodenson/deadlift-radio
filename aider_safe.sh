#!/bin/bash
# Safe aider launcher - constrained to this repo only
# No auto-commits, no URL fetching, logs all sessions

REPO="/home/bune/deadlift_radio"
LOG="$REPO/.aider_sessions/$(date +%Y%m%dT%H%M%S).log"
mkdir -p "$REPO/.aider_sessions"

cd "$REPO" || exit 1

export $(cat "$REPO/.env" | xargs)

echo "=== AIDER SESSION $(date) ===" >> "$LOG"
echo "Model: ${1:-ollama/llama3.1:70b}" >> "$LOG"
echo "Task: ${2:-interactive}" >> "$LOG"

aider \
  --model "${1:-ollama/llama3.1:70b}" \
  --no-auto-commits \
  --no-git \
  --no-check-update \
  --map-tokens 2048 \
  "$@" 2>&1 | tee -a "$LOG"
