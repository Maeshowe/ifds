#!/bin/bash
# sync_from_mini.sh — Pull production data from Mac Mini to MacBook Pro
#
# Usage: ./scripts/sync_from_mini.sh [--dry-run]
#
# Syncs: data/, logs/, output/, scripts/paper_trading/logs/, state/
# Excludes: data/cache/ (stale forward-looking date ranges)
# Direction: Mac Mini → MacBook Pro (one-way, Mini is master)

set -euo pipefail

REMOTE="safrtam@negotium.ddns.net"
REMOTE_BASE="~/SSH-Services/ifds"
LOCAL_BASE="$(cd "$(dirname "$0")/.." && pwd)"

DRY_RUN=""
if [[ "${1:-}" == "--dry-run" ]]; then
    DRY_RUN="--dry-run"
    echo "=== DRY RUN — no files will be changed ==="
fi

RSYNC_OPTS=(
    -avz
    --progress
    --delete
    --exclude="data/cache/"
    --exclude="__pycache__/"
    --exclude=".DS_Store"
    $DRY_RUN
)

DIRS=(
    "data"
    "logs"
    "output"
    "scripts/paper_trading/logs"
    "state"
)

echo "╔══════════════════════════════════════════╗"
echo "║  IFDS Sync: Mac Mini → MacBook Pro       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Remote: ${REMOTE}:${REMOTE_BASE}"
echo "Local:  ${LOCAL_BASE}"
echo ""

for dir in "${DIRS[@]}"; do
    echo "── Syncing ${dir}/ ──"
    mkdir -p "${LOCAL_BASE}/${dir}"
    rsync "${RSYNC_OPTS[@]}" \
        "${REMOTE}:${REMOTE_BASE}/${dir}/" \
        "${LOCAL_BASE}/${dir}/"
    echo ""
done

echo "✓ Sync complete"
