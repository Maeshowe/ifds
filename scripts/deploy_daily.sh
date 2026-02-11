#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

source .venv/bin/activate
set -a; source .env; set +a

LOG="logs/cron_$(date +%Y%m%d_%H%M%S).log"
mkdir -p logs

echo "=== IFDS Run $(date) ===" >> "$LOG"
python -m ifds run >> "$LOG" 2>&1
EXIT_CODE=$?
echo "=== Exit: $EXIT_CODE ===" >> "$LOG"

exit $EXIT_CODE
