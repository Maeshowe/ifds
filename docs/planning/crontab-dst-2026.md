# IFDS Crontab — DST váltások 2026

## Időzóna szituációk

| Időszak | USA | EU | NYSE CET-ben |
|---|---|---|---|
| → 2026-03-07 | EST (UTC-5) | CET (UTC+1) | 15:30–22:00 |
| 2026-03-08 → 2026-03-28 | EDT (UTC-4) | CET (UTC+1) | **14:30–21:00** |
| 2026-03-29 → | EDT (UTC-4) | CEST (UTC+2) | 15:30–22:00 |

## Manuális váltások

- **2026-03-08 (hétfő reggel előtt):** Váltás BLOKK B-re ✅ — ELMARADT, holnap javítani
- **2026-03-29 (vasárnap este előtt):** Visszaváltás BLOKK A-ra

---

## Aktív crontab (Mac Mini)

```crontab
# =============================================================================
# IFDS Paper Trading
# =============================================================================

# Pipeline (10:00 CET — időzónától független)
0 10 * * 1-5 /Users/safrtam/SSH-Services/ifds/scripts/deploy_daily.sh

# Leftover position check (10:10 CET, clientId=14)
10 10 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/monitor_positions.py >> logs/pt_monitor_positions.log 2>&1

# =============================================================================
# BLOKK A — MINDKÉT IDŐ NYÁRI (2026-03-29-től): NYSE 15:30–22:00 CET
# =============================================================================
# Trailing stop monitor (15:00–21:55 CET, 5 percenként, clientId=15)
# */5 15-21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py >> logs/pt_monitor.log 2>&1
# Order submission (9:35 ET = 15:35 CET, clientId=10)
# 35 15 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py >> logs/pt_submit.log 2>&1
# MOC close (15:40 ET = 21:40 CET, clientId=11)
# 40 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/pt_close.log 2>&1
# EOD report (16:05 ET = 22:05 CET, clientId=12)
# 5 22 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py >> logs/pt_eod.log 2>&1

# =============================================================================
# BLOKK B — USA NYÁRI, EU TÉLI (2026-03-08–2026-03-28): NYSE 14:30–21:00 CET
# =============================================================================
# Trailing stop monitor (14:00–20:55 CET, 5 percenként, clientId=15)
*/5 14-20 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/pt_monitor.py >> logs/pt_monitor.log 2>&1
# Order submission (9:35 ET = 14:35 CET, clientId=10)
35 14 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/submit_orders.py >> logs/pt_submit.log 2>&1
# MOC close (15:40 ET = 20:40 CET, clientId=11)
40 20 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/close_positions.py >> logs/pt_close.log 2>&1
# EOD report (16:05 ET = 21:05 CET, clientId=12)
5 21 * * 1-5 cd /Users/safrtam/SSH-Services/ifds && .venv/bin/python scripts/paper_trading/eod_report.py >> logs/pt_eod.log 2>&1
```

## Váltási instrukció (crontab -e a Mac Minin)

**BLOKK A → BLOKK B (2026-03-08):**
- BLOKK A 4 sorát `#`-tel kommentezni
- BLOKK B 4 sorából `#`-t eltávolítani

**BLOKK B → BLOKK A (2026-03-29):**
- BLOKK B 4 sorát `#`-tel kommentezni
- BLOKK A 4 sorából `#`-t eltávolítani
