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

# --- pytest pre-flight ---
echo "[pre-flight] Running pytest..." >> "$LOG"
if ! python -m pytest --tb=short -q >> "$LOG" 2>&1; then
    echo "[pre-flight] FAILED — pipeline aborted" >> "$LOG"
    # Telegram alert
    python - << 'PYEOF' >> "$LOG" 2>&1
import os, requests
token = os.getenv("IFDS_TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("IFDS_TELEGRAM_CHAT_ID")
if token and chat_id:
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": "⚠️ IFDS pre-flight FAILED — pytest errors, pipeline aborted. Check cron log."},
        timeout=10,
    )
PYEOF
    exit 1
fi
echo "[pre-flight] OK" >> "$LOG"
# --- end pre-flight ---

python -m ifds run >> "$LOG" 2>&1
EXIT_CODE=$?
echo "=== Exit: $EXIT_CODE ===" >> "$LOG"

if [ $EXIT_CODE -eq 0 ]; then
    echo "=== Company Intel $(date) ===" >> "$LOG"
    python scripts/company_intel.py --telegram >> "$LOG" 2>&1
    echo "=== Intel Exit: $? ===" >> "$LOG"
fi

exit $EXIT_CODE
