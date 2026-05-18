#!/bin/bash
# deploy_intraday.sh — Phase 4-6 only (2026-05-18 swing pivot)
#
# Runs at 14:30 Budapest time (Mon-Fri) via cron — 1h before NYSE open.
# = 08:30 EDT (CEST season). Generates the execution_plan_run_<date>_*.csv
# that the 15:30 CEST submit_orders.py cron consumes at NYSE open.
#
# Requires Phase 1-3 context from the Sunday 22:00 macro pipeline run
# (state/phase13_ctx.json.gz).
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
# Generates output/execution_plan_run_<date>_*.csv for the 15:30 CEST submit cron.
echo "--- Phase 4-6 ---"
python -m ifds run --phases 4-6

# NOTE: 2026-05-18 swing pivot — submit_orders.py + company_intel.py REMOVED
# from this script. The new architecture runs Phase 4-6 at 14:30 CEST
# (1h pre-NYSE-open for scoring + sizing) and submits at 15:30 CEST via the
# separate cron entry. Pre-market market BUY rejected by IBKR Error 10349
# (DAY TIF outside RTH) — the open-of-NYSE submit is required.
#
# LEGACY (pre-2026-05-18, kept for reference):
# echo "--- Submit Orders ---"
# python scripts/paper_trading/submit_orders.py
#
# echo "--- Company Intel ---"
# python scripts/company_intel.py --telegram 2>&1 || echo "Company Intel failed (non-blocking)"

echo "$(date '+%Y-%m-%d %H:%M:%S') Done."
