# =============================================================================
# IFDS Paper Trading — SWING PIVOT (2026-05-18-tól)
# =============================================================================
#
# Day 1 = 2026-05-18 hétfő (új paper trading swing-mode-ban).
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
#   🔒 A BELÉPŐRE ez 2026-10-19 óta KÓDBAN kezelt, nem kézi szerkesztéssel:
#      az `ifds.utils.calendar.is_before_moo_cutoff()` America/New_York-ban
#      értékel, és a 09:28 ET cutoff után a belépő visszaesik a régi MKT/DAY
#      alakra (hangos WARNING-gal). A DST-gap héten tehát a MOO ELMARAD, de
#      nem keletkezik elutasított order. Ha a MOO-t abban a héten is akarjuk,
#      a slotot 14:20-ra kell vinni — a guard teszteli mindkét esetet
#      (tests/test_moo_entry_routing.py).
#      ⚠️ A 21:40 MOC és a 22:00 eod_eval slotokra ez NEM vonatkozik: azok
#      továbbra is kézi szerkesztést igényelnek a gap-héten.
#
# Minden script tartalmaz trading day guard-ot (NYSE holidays → exit 0)
# =============================================================================

# ─── HETI MAKRO PIPELINE (vasárnap esti universe + macro snapshot) ──────────

# Phase 1-3: BMI, Universe, Szektorok, Cross-Asset Regime
# Vasárnap 22:00 Budapest = heti universe rebalance + BMI snapshot
# Kimenet: state/phase13_ctx.json.gz (a hét során használja Phase 4-6)
# IFDS_SKIP_TRADING_DAY_GUARD=1 prefix kötelező: a vasárnap NYSE-closed nap, és a runner
# trading-day guard-ja egyébként SKIP-elné a futást (a `304a64d` óta a SKIP nem crash-el,
# csak [SKIP] log + Telegram-üzenet → context stale marad). A vasárnapi cron SZÁNDÉKA
# a következő hét friss BMI + universe + sector context-jét generálni — ezért kell az override.
# Lásd: docs/tasks/2026-05-25-operator-emergency-procedure.md Pattern 5b §5b.2.
0 22 * * 0 IFDS_SKIP_TRADING_DAY_GUARD=1 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh --phases 1-3

# Phase 1-3 heartbeat — vasárnap 23:00 (1 óra time-window a 22:00 macro cronnak — Task #E)
# Detect: ha a heti cron silent-fail, vagy a context file stale/missing
0 23 * * 0 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/check_phase13_freshness.py

# ─── HÉTFŐ-PÉNTEK SWING CRON ────────────────────────────────────────────────

# Phase 4-6: scoring, GEX, MMS, swing sizing
# 14:30 Budapest = 08:30 EDT (1h NYSE open előtt — pre-market scoring + sizing)
# Kimenet: output/execution_plan_run_<date>_<time>.csv (14:55-re kész)
30 14 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && ./scripts/deploy_intraday.sh

# Gateway health check — IBKR kapcsolat ellenőrzés
# 15:25 Budapest = 09:25 EDT (5 perc submit_orders előtt)
# ⚠️ Ha FAIL → Gateway újraindítás MIELŐTT 15:30 jön!
25 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/check_gateway.py

# Másnapi exit végrehajtás (HARD_SL/MENTAL_SL/TP1/TP2/TRAIL_SL — eod_flags)
# 15:30 Budapest = 09:30 EDT (NYSE open) — CLOSE fut ELŐSZÖR (sector cap felszabadítás)
# Day 2 (2026-05-19) race-condition fix: a submit korábban ugyanabban a
# percben futott és felülírta a close által frissített state-et.
30 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py --mode=eod_flags

# Submit MOO BUY (2026-10-19 — nyitó aukciós belépő)
# 15:20 Budapest = 09:20 EDT — a NYSE MOO cutoff (09:28 ET) ELŐTT 8 perccel.
#
# ⚠️ MIÉRT MOZDULT 15:31 → 15:20. A 15:31 = 09:31 ET, azaz EGY PERCCEL a csengő
# UTÁN, és a mérés szerint a belépési költség TELJES egésze ez az egy perc:
# nyitás→fill +48,3 bp [31,0; 64,3], p < 0,0001, míg terv→nyitás −1,5 bp (p=0,88).
# Az aukciós megbízás ugyanezen a könyvön +1,35 bp. Forrás:
# docs/review/2026-10-19-execution-wall-by-horizon.md
#
# ⚠️ A SORREND MEGFORDUL: a submit mostantól a close ELŐTT fut (15:20 vs 15:30).
# Két következménye van, mindkettő konzervatív, de tudni kell róluk:
#   1. Egy MA exitelő ticker 15:20-kor még pozícióként látszik (`get_existing_symbols`),
#      tehát aznap NEM lép be újra. Swing-architektúrában (5 napos hold, előző esti
#      flag) ez ritka és inkább kívánatos — de viselkedés-változás.
#   2. A MOO BUY az aukcióban (09:30:00) tölt, az eod_flags SELL utána → a vétel
#      megelőzi az eladást. Teli könyv + rotáció esetén buying-power-t igényel.
# A Day 2 (2026-05-19) same-minute state-race NEM tér vissza: a két job 10 percre van.
#
# ⚠️ NINCS ÉLŐ SMOKE. A kereskedés áll (D8), ezért a `tif="OPG"` kombinációt IBKR
# paper accounton MÉG NEM ELLENŐRIZTÜK. A paper account csendben elutasít dolgokat
# (lásd ifds-rules.md 2026-04-08, Adaptive algo) → az ÚJRAINDÍTÁS ELSŐ NAPJÁN
# kötelező ellenőrizni: `trade.orderStatus.status` és az IBKR Orders tab.
# A kód `lib.orders.create_swing_entry_order` guardja a 09:28 ET cutoff után
# automatikusan visszaesik a régi MKT/DAY belépőre, tehát egy DST-elcsúszás
# nem hibát okoz, hanem a status quo-t.
#
# Swing-mode: market BUY only (no bracket), state/swing_positions.json írva
# (külön IBKR clientId: submit=10, close=11).
20 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py

# IBKR submit heartbeat monitor — 15:45 CEST, 15 min after submit
45 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && source .env && source .venv/bin/activate && python scripts/paper_trading/monitor_submit_heartbeat.py >> logs/heartbeat_monitor_$(date +\%Y\%m\%d).log 2>&1

# Same-day TIME_STOP MOC SELL — 21:40 CEST
# 21:40 Budapest = 15:40 EDT (10 perc NYSE close előtt)
# Csak a TIME_STOP flagű pozíciókat zárja MOC SELL-lel (days_held >= 5)
40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py --mode=time_stop

# Daily EOD eval — 22:30 CEST  (volt 22:00; +30 perc 2026-10-23 óta)
# 22:30 Budapest = 16:30 ET télen — 30 perccel a 16:00-s NYSE close UTÁN.
# A +30 a késleltetett (15 perces) market-data csomag előfeltétele: egy T-ben olvasott
# bar a T-15 szalagot tükrözi, teljes napi barhoz a szalag 16:00 ET-ig kell. +20 perc
# ennek a jobnak 5 perc ráhagyást adna, +30 tizenötöt. A nulla-ráhagyásos eset nem
# hibát ad, hanem CSONKA bart — csendben.
# A 6-condition swing exit eval (HARD_SL / MENTAL_SL / TP2 / TP1 / TRAIL_SL / TIME_STOP),
# Polygon napi bar-ból; state/swing_positions.json frissítve next_action flag-ekkel
30 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py --mode=eod_eval

# Daily metrics — structured JSON + Part A record_pending_exits (cumulative writer)
# 22:40 Budapest = 16:40 ET télen (EOD eval után 10 perccel; volt 22:10)
# FONTOS: ez a Part A cron rögzíti a broker-realized P&L-t + commission-t a
# cumulative_pnl.json-ba a 21:40 MOC exitekből. Az eod_report-nak EZUTÁN kell futnia.
40 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/daily_metrics.py

# EOD report — napi P&L, kumulatív összesítés, swing-state Telegram
# 22:41 Budapest = 16:41 ET télen (data-quality fix #2: a 22:40 Part A UTÁN, hogy a
# Telegram a teljes aznapi cumulative-t + MOC exiteket mutassa, ne a tegnapit)
41 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py

# State/IBKR reconciliation — divergence detect + Telegram WARNING (Task #D)
# 22:45 Budapest = 16:45 ET télen (5 perccel a metrics után, mielőtt Tamás review jön)
45 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/reconcile_state.py

# Daily review-data aggregátum (1a) — Chat napi review inputja
# 22:50 Budapest = 16:50 ET télen (a reconcile UTÁN, hogy a state settled; review_data → sync a MacBookra)
# Csak az 1a (determinisztikus aggregátor, lokális fájlokból); az 1c cross-check az IBKR MCP-t igényli → CC-kézi lépés. Hozzáadva 2026-07-10.
50 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/generate_review_data.py

# Events → SQLite import (log elemzéshez)
# 23:15 Budapest = 17:15 ET télen (volt 22:45 — a tolt lánc után)
15 23 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/tools/events_to_sqlite.py

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
