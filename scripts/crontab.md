# =============================================================================
# IFDS Paper Trading — Swing Hybrid Exit (2026-04-06-tól)
# =============================================================================
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
#     → close_positions.py 21:40 = 16:40 EDT = 40 perc KÉSÉS!
#     → Megoldás: márc 8-29 között crontab kézi módosítás szükséges
#   - 2026 ősz: EU okt 25 → US nov 1 (1 hét eltérés)
#     Ugyanaz a probléma, okt 25 – nov 1 között
#
# Minden script tartalmaz trading day guard-ot (NYSE holidays → exit 0)
# =============================================================================

# ─── ESTI PIPELINE (NYSE zárás után) ────────────────────────────────────────

# Phase 1-3: BMI, Universe, Szektorok, Cross-Asset Regime
# 22:00 Budapest = 16:00 EDT (NYSE zárás) → záróárakból dolgozik
# Kimenet: state/phase13_ctx.json.gz (másnap 15:45-kor használja Phase 4-6)
0 22 * * 1-5 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3

# EOD report — napi P&L, kumulatív összesítés
# 22:05 Budapest = 16:05 EDT (fill-ek lezárultak)
5 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# Events → SQLite import (log elemzéshez)
# 22:45 Budapest = 16:45 EDT
45 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tools/events_to_sqlite.py

# ─── REGGELI ELLENŐRZÉS ─────────────────────────────────────────────────────

# Leftover pozíció check — IBKR vs PositionTracker
# 10:10 Budapest = 04:10 EDT (pre-market)
10 10 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py

# ─── PIACNYITÁS KÖRNYÉKE ────────────────────────────────────────────────────

# Gateway health check — IBKR kapcsolat ellenőrzés
# BC23: 16:00 Budapest = 10:00 EDT (15 perc a submit előtt)
# ⚠️ Ha FAIL → Gateway újraindítás MIELŐTT 16:15 jön!
0 16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py

# Phase 4-6 + MKT entry — Scoring, GEX, VWAP, Sizing, Order submission
# BC23: 16:15 Budapest = 10:15 EDT (45 perc NYSE open után — opening range beáll)
# Friss intraday árakból dolgozik, VWAP guard aktív
15 16 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh

# ─── INTRADAY MONITORING ────────────────────────────────────────────────────

# Trailing stop monitor — TP1 detektálás, trail SL update, Scenario B
# */5 perc, 16:00–21:55 Budapest = 10:00–15:55 EDT (kereskedési órák)
*/5 16-21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py

# ─── NAPI ZÁRÁS (SWING MANAGEMENT) ─────────────────────────────────────────

# Swing close management — hold_days++, breakeven, trail, max hold D+5 MOC
# 21:40 Budapest = 15:40 EDT (10 perc MOC deadline előtt)
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py

# ─── EARLY CLOSE NAPOK ──────────────────────────────────────────────────────

# Extra close_positions futtatás early close napokon
# 18:40 Budapest = 12:40 EDT (20 perc early close előtt)
# Csak early close napokon fut (day after Thanksgiving, Christmas Eve, stb.)
40 18 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python -c "from ifds.utils.calendar import is_early_close; exit(0 if is_early_close() else 1)" && .venv/bin/python scripts/paper_trading/close_positions.py

# =============================================================================
# TÖRÖLT/INAKTÍV jobok (2026-04-06-tól)
# =============================================================================
# submit_orders.py    → deploy_intraday.sh átvette (MKT entry)
# pt_avwap.py         → MKT entry, VWAP guard Phase 6-ban fut
# deploy_daily.sh (régi 10:00, teljes pipeline) → kettéválasztva:
#   22:00 Phase 1-3 + 15:45 Phase 4-6
# pt_monitor.py 15:xx → 16:00-ra módosítva (NYSE open 15:30, nincs pozíció előtte)
