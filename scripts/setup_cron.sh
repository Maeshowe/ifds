#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CRON_LINE="0 22 * * 1-5 $PROJECT_DIR/scripts/deploy_daily.sh"

(crontab -l 2>/dev/null | grep -v deploy_daily; echo "$CRON_LINE") | crontab -

echo "Cron installed: $CRON_LINE"
crontab -l
