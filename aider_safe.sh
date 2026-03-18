#!/bin/bash
REPO="/home/bune/deadlift_radio"
LOG="$REPO/.aider_sessions/$(date +%Y%m%dT%H%M%S).log"
mkdir -p "$REPO/.aider_sessions"
cd "$REPO" || exit 1
export $(cat "$REPO/.env" | xargs)

MODEL="${1:-ollama/llama3.1:70b}"
TASK="${2:-}"
shift 2 2>/dev/null

echo "=== AIDER SESSION $(date) ===" >> "$LOG"
echo "Model: $MODEL" >> "$LOG"

if [ -n "$TASK" ]; then
    aider \
      --model "$MODEL" \
      --no-auto-commits \
      --no-check-update \
      --yes-always \
      --message "$TASK" \
      "$@" 2>&1 | tee -a "$LOG"
else
    aider \
      --model "$MODEL" \
      --no-auto-commits \
      --no-check-update \
      "$@" 2>&1 | tee -a "$LOG"
fi
