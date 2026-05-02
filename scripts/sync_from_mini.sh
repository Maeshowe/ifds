#!/bin/bash
# sync_from_mini.sh — Pull production data from Mac Mini to MacBook Pro
#
# Usage: ./scripts/sync_from_mini.sh [--dry-run]
#
# Syncs: data/, logs/, output/, scripts/paper_trading/logs/, state/, docs/analysis/
# Excludes: data/cache/ (stale forward-looking date ranges)
# Direction: Mac Mini → MacBook Pro (one-way, Mini is master)
#
# Human-edited content (docs/tasks, docs/review, docs/STATUS.md, docs/planning,
# docs/references) is intentionally NOT synced — those go through git in both
# directions. Only machine-generated outputs are rsync'd.

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
    "docs/analysis"
)

echo "╔══════════════════════════════════════════╗"
echo "║  IFDS Sync: Mac Mini → MacBook Pro       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "Remote: ${REMOTE}:${REMOTE_BASE}"
echo "Local:  ${LOCAL_BASE}"
echo ""

# ── Pre-flight checks ──
echo "── Pre-flight checks ──"

# (a) SSH connectivity
if ! ssh -q -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE}" "exit" 2>/dev/null; then
    echo "❌ ERROR: Cannot connect to ${REMOTE}"
    echo "   Check VPN, firewall, DDNS resolution, or SSH key auth."
    exit 1
fi

# (b) Remote project root exists
if ! ssh "${REMOTE}" "test -d ${REMOTE_BASE}" 2>/dev/null; then
    echo "❌ ERROR: ${REMOTE_BASE} does not exist on ${REMOTE}"
    exit 1
fi

# (c) Source directories exist on remote (warn but continue if any missing)
SKIP_DIRS=()
for dir in "${DIRS[@]}"; do
    if ! ssh "${REMOTE}" "test -d ${REMOTE_BASE}/${dir}" 2>/dev/null; then
        echo "⚠️  WARN: Remote dir missing: ${REMOTE_BASE}/${dir} (will skip)"
        SKIP_DIRS+=("${dir}")
    fi
done

echo "✓ Pre-flight checks passed"
echo ""

# ── Sync ──
for dir in "${DIRS[@]}"; do
    # Skip dirs flagged by pre-flight as missing on the remote
    skip=false
    for s in "${SKIP_DIRS[@]:-}"; do
        if [[ "${dir}" == "${s}" ]]; then
            skip=true
            break
        fi
    done
    if [[ "${skip}" == "true" ]]; then
        echo "── Skipping ${dir}/ (missing on remote) ──"
        echo ""
        continue
    fi

    echo "── Syncing ${dir}/ ──"
    mkdir -p "${LOCAL_BASE}/${dir}"
    rsync "${RSYNC_OPTS[@]}" \
        "${REMOTE}:${REMOTE_BASE}/${dir}/" \
        "${LOCAL_BASE}/${dir}/"
    echo ""
done

# ── Sync timestamp record ──
# Only record on real runs, not dry-runs (dry-run should not mutate state).
if [[ -z "${DRY_RUN}" ]]; then
    mkdir -p "${LOCAL_BASE}/state"
    date -u +"%Y-%m-%dT%H:%M:%SZ" > "${LOCAL_BASE}/state/.last_sync"
    echo "Last sync recorded: $(cat "${LOCAL_BASE}/state/.last_sync")"
fi

echo "✓ Sync complete"
