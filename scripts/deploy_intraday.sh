#!/bin/bash
# deploy_intraday.sh — Phase 4-6 with intraday data + order submission
#
# Runs at 15:45 Budapest time (Mon-Fri) via cron.
# = 09:45 EDT (15 min after NYSE open, CEST season)
# Requires Phase 1-3 context from the 22:00 pipeline run (state/phase13_ctx.json.gz).
#
# Usage: ./scripts/deploy_intraday.sh

set -euo pipefail

cd "$(dirname "$0")/.."

# Redirect all output to a daily intraday cron log
mkdir -p logs
LOG_FILE="logs/cron_intraday_$(date +%Y%m%d_%H%M%S).log"
exec >> "$LOG_FILE" 2>&1

echo "=== IFDS Intraday Pipeline (Phase 4-6) ==="
echo "$(date '+%Y-%m-%d %H:%M:%S') Starting..."

# Source environment
source .env 2>/dev/null || true
source .venv/bin/activate 2>/dev/null || true

# Phase 4-6 (uses saved Phase 1-3 context)
echo "--- Phase 4-6 ---"
python -m ifds run --phases 4-6

# Submit orders
echo "--- Submit Orders ---"
python scripts/paper_trading/submit_orders.py

# Company Intel (on freshly submitted tickers — actionable before market moves)
echo "--- Company Intel ---"
python scripts/company_intel.py --telegram 2>&1 || echo "Company Intel failed (non-blocking)"

echo "$(date '+%Y-%m-%d %H:%M:%S') Done."
