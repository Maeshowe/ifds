# =============================================================================
# IFDS Paper Trading — Swing Hybrid Exit (2026-04-06-tól)
# =============================================================================
# MINDKÉT IDŐ NYÁRI — 2026-03-29-től (NYSE: 15:30-22:00 CET)
# Minden script tartalmaz trading day guard-ot (NYSE holidays → exit 0)
# =============================================================================

# --- Phase 1-3: napi záróadatok (BMI, Universe, Sectors) ---
0 22 * * 1-5 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3

# --- Phase 4-6: intraday adatok + MKT order submission (15:45 CET) ---
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh

# --- Gateway health check (15:30 CET, 15 min before intraday pipeline) ---
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py

# --- Leftover position check (10:10 CET, clientId=14) ---
10 10 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py

# --- Trailing stop monitor (15:00-21:55 CET, 5 percenként, clientId=15) ---
# Intraday TP1 detection + trail SL updates
*/5 15-21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py

# --- Swing management: close_positions.py (21:40 CET, clientId=11) ---
# Hold day increment, breakeven check, trail activation, max hold D+5 MOC, earnings exit
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py

# --- Early close days: extra close_positions run (18:40 CET = 12:40 ET) ---
# Runs on early close days only (day after Thanksgiving, Christmas Eve, etc.)
40 18 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python -c "from ifds.utils.calendar import is_early_close; exit(0 if is_early_close() else 1)" && .venv/bin/python scripts/paper_trading/close_positions.py

# --- EOD report (22:05 CET, clientId=12) ---
5 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# --- Events → SQLite import (22:45 CET, EOD report után) ---
45 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tools/events_to_sqlite.py

# =============================================================================
# TÖRÖLT/INAKTÍV jobok (2026-04-06-tól)
# =============================================================================
# submit_orders.py → deploy_intraday.sh átvette (MKT entry, nincs külön submit)
# pt_avwap.py → MKT entry, nincs AVWAP fallback szükség (a VWAP guard Phase 6-ban fut)
# deploy_daily.sh 10:00 → kettéválasztva: 22:00 Phase 1-3 + 15:45 Phase 4-6
