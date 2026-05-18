# =============================================================================
# IFDS Paper Trading — SWING PIVOT (2026-05-18-tól)
# =============================================================================
#
# Day 1 = 2026-05-19 kedd (új paper trading swing-mode-ban).
# Architektúra: 15:30 CEST market BUY entry → daily 22:00 EOD eval (mental stop)
#                → másnap 15:30 next-day exit + same-day 21:40 TIME_STOP MOC.
# Részletes spec: docs/PIPELINE_LOGIC.md §6.SWING-EXIT
# Task referencia: docs/tasks/2026-05-17-swing-execution-exit.md (Task #4)
#
# IDŐZÓNA: Europe/Budapest (rendszer időzóna)
#   - Nyári idő (CEST, UTC+2): 2026-03-29 – 2026-10-25
#   - Téli idő (CET, UTC+1):   2026-10-25 – 2027-03-28
#
# NYSE órarend Budapest időben:
#   - CEST (ápr–okt): NYSE 15:30–22:00 | Early close: –19:00
#   - CET  (nov–márc): NYSE 15:30–22:00 (ha US is téli)
#
# ⚠️  DST ÁTMENET FIGYELMEZTETÉS:
#   US és EU DST váltás nem azonos napon van!
#   - 2026 tavasz: US márc 8 → EU márc 29 (3 hét eltérés!)
#     Ezalatt: NYSE 14:30–21:00 Budapest idő (+5h, nem +6h)
#     → 21:40 MOC = 16:40 EDT = 40 perc KÉSÉS!
#     → Megoldás: márc 8-29 között crontab kézi módosítás szükséges
#   - 2026 ősz: EU okt 25 → US nov 1 (1 hét eltérés)
#     Ugyanaz a probléma, okt 25 – nov 1 között
#
# Minden script tartalmaz trading day guard-ot (NYSE holidays → exit 0)
# =============================================================================

# ─── HETI MAKRO PIPELINE (vasárnap esti universe + macro snapshot) ──────────

# Phase 1-3: BMI, Universe, Szektorok, Cross-Asset Regime
# Vasárnap 22:00 Budapest = heti universe rebalance + BMI snapshot
# Kimenet: state/phase13_ctx.json.gz (a hét során használja Phase 4-6)
0 22 * * 0 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3

# ─── HÉTFŐ-PÉNTEK SWING CRON ────────────────────────────────────────────────

# Phase 4-6: scoring, GEX, MMS, swing sizing
# 14:30 Budapest = 08:30 EDT (1h NYSE open előtt — pre-market scoring + sizing)
# Kimenet: output/execution_plan_run_<date>_<time>.csv (14:55-re kész)
30 14 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh

# Gateway health check — IBKR kapcsolat ellenőrzés
# 15:25 Budapest = 09:25 EDT (5 perc submit_orders előtt)
# ⚠️ Ha FAIL → Gateway újraindítás MIELŐTT 15:30 jön!
25 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py

# Submit market BUY (Day 63 §3.6 — 15:30 CEST entry)
# 15:30 Budapest = 09:30 EDT (NYSE open)
# Swing-mode: market BUY only (no bracket), state/swing_positions.json írva
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py

# Másnapi exit végrehajtás (HARD_SL/MENTAL_SL/TP1/TP2/TRAIL_SL — eod_flags)
# 15:30 Budapest = 09:30 EDT (NYSE open) — másnap végrehajtja az előző esti EOD eval flag-eket
# Megjegyzés: ugyanabban a percben fut a submit_orders + close_eod, mert
# új entry-k MKT BUY-ja és előző napi flagű exit-ek MKT SELL-je független
# (külön IBKR clientId: submit=10, close=11).
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py --mode=eod_flags

# IBKR submit heartbeat monitor — 15:45 CEST, 15 min after submit
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && source .env && source .venv/bin/activate && python scripts/paper_trading/monitor_submit_heartbeat.py >> logs/heartbeat_monitor_$(date +\%Y\%m\%d).log 2>&1

# Same-day TIME_STOP MOC SELL — 21:40 CEST
# 21:40 Budapest = 15:40 EDT (10 perc NYSE close előtt)
# Csak a TIME_STOP flagű pozíciókat zárja MOC SELL-lel (days_held >= 5)
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py --mode=time_stop

# Daily EOD eval — 22:00 CEST
# 22:00 Budapest = 16:00 EDT (NYSE close)
# A 6-condition swing exit eval (HARD_SL / MENTAL_SL / TP2 / TP1 / TRAIL_SL / TIME_STOP),
# Polygon napi bar-ból; state/swing_positions.json frissítve next_action flag-ekkel
0 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py --mode=eod_eval

# EOD report — napi P&L, kumulatív összesítés, swing-state Telegram
# 22:05 Budapest = 16:05 EDT (EOD eval után 5 perccel)
5 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# Daily metrics — structured JSON (swing_state block + walk-forward méréshez)
# 22:10 Budapest = 16:10 EDT (EOD report után 5 perccel)
10 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/daily_metrics.py

# Events → SQLite import (log elemzéshez)
# 22:45 Budapest = 16:45 EDT
45 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tools/events_to_sqlite.py

# ─── REGGELI ELLENŐRZÉS ─────────────────────────────────────────────────────

# Leftover pozíció check — IBKR vs swing_positions.json sync
# 10:10 Budapest = 04:10 EDT (pre-market)
10 10 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py

# ─── EARLY CLOSE NAPOK ──────────────────────────────────────────────────────

# Early close TIME_STOP futtatás (day after Thanksgiving, Christmas Eve, stb.)
# 18:40 Budapest = 12:40 EDT (20 perc early close előtt)
40 18 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python -c "from ifds.utils.calendar import is_early_close; exit(0 if is_early_close() else 1)" && .venv/bin/python scripts/paper_trading/close_positions.py --mode=time_stop

# =============================================================================
# DEAKTIVÁLT / LEGACY jobok (2026-05-18 swing pivot-tól)
# =============================================================================
#
# A régi 5-min trail loop + intraday LOSS_EXIT + bracket OCA architektúra a
# swing pivot-tal teljesen lecserélődött. A defaults.py-ban ezek a gate-ek
# False-ra állítva: ibkr_bracket_enabled, loss_exit_intraday_enabled,
# pt_monitor_5min_mode. A régi cron entry-k itt referenciaként, fallback-hez.
#
# LEGACY (régi 22:00 daily pipeline — kettéválasztva vasárnap heti + hétközi):
# 0 22 * * 1-5 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3
#
# LEGACY (régi 16:15 Phase 4-6 + intraday entry — előrehozva 14:30-ra):
# 0 16 * * 1-5 .venv/bin/python scripts/paper_trading/check_gateway.py
# 15 16 * * 1-5 ./scripts/deploy_intraday.sh
#
# LEGACY (régi 16:00–21:55 5-min trail monitor — kikapcsolva, swing-eval naponta egyszer):
# */5 16-21 * * 1-5 .venv/bin/python scripts/paper_trading/pt_monitor.py
#
# LEGACY (régi 21:45 MOC close all — swing pivot a TIME_STOP-ot 21:40-en már zárja):
# 45 21 * * 1-5 .venv/bin/python scripts/paper_trading/close_positions.py
#
# LEGACY (régi AVWAP conversion script — MKT entry-vel megszűnt):
# 0 19 * * 1-5 .venv/bin/python scripts/paper_trading/pt_avwap.py
#
# =============================================================================
