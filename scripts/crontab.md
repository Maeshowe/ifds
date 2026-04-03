# =============================================================================
# IFDS Paper Trading
# =============================================================================

# Pipeline (10:00 CET / 10:00 CET — időzónától független)
0 10 * * 1-5 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh

# Leftover position check (10:10 CET, clientId=14)
10 10 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py

# -----------------------------------------------------------------------------
# USA NYÁRI IDŐ, EU TÉLI IDŐ — 2026-03-08 → 2026-03-28 (NYSE: 14:30-21:00 CET)
# -----------------------------------------------------------------------------
# Trailing stop monitor (14:00-20:55 CET, 5 percenként, clientId=15)
#*/5 14-20 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py
# Order submission (9:35 ET = 14:35 CET, clientId=10)
#30 14 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py
#35 14 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py
# AVWAP limit→MKT monitor (9:45-11:30 ET = 14:45-16:30 CET, percenként, clientId=16)
#*/1 14-16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_avwap.py
# MOC close (15:40 ET = 20:40 CET, clientId=11)
#40 20 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py
# EOD report (16:05 ET = 21:05 CET, clientId=12)
#5 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# -----------------------------------------------------------------------------
# MINDKÉT IDŐ NYÁRI — 2026-03-29-től (NYSE: 15:30-22:00 CET)
# -----------------------------------------------------------------------------
# Trailing stop monitor (15:00-21:55 CET, 5 percenként, clientId=15)
*/5 15-21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py
# Order submission (9:35 ET = 15:35 CET, clientId=10)
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py
35 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py
# AVWAP limit→MKT monitor (9:45-11:30 ET = 15:45-17:30 CEST, percenként, clientId=16)
*/1 15-17 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_avwap.py
# MOC close (15:40 ET = 21:40 CET, clientId=11)
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py
# EOD report (16:05 ET = 22:05 CET, clientId=12)
5 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# =============================================================================
# Events → SQLite import (22:45 CET, EOD report után)
# =============================================================================
45 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tools/events_to_sqlite.py