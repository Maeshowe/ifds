Status: OPEN
Updated: 2026-04-03
Note: Hétfő reggeli deployment — IFDS Swing Hybrid Exit

# IFDS — Deployment Checklist (2026-04-06 hétfő)

## Végleges napi folyamat (2026-04-06-tól)

Időzóna: Europe/Budapest (CEST, UTC+2 ápr–okt). NYSE: 15:30–22:00 Budapest = 09:30–16:00 EDT.

### Esti pipeline (NYSE zárás után)

| Budapest | EDT | Mi fut | Log |
|---|---|---|---|
| 22:00 | 16:00 | Phase 1-3 (BMI, szektorok, cross-asset) | `cron_YYYYMMDD_220000.log` |
| 22:05 | 16:05 | EOD report (P&L, Telegram) | `pt_eod.log` |
| 22:45 | 16:45 | Events → SQLite | — |

### Másnap reggel

| Budapest | EDT | Mi fut | Log |
|---|---|---|---|
| 10:10 | 04:10 | monitor_positions.py (leftover check) | `pt_monitor_positions.log` |

### Piacnyitás + kereskedés

| Budapest | EDT | Mi fut | Log |
|---|---|---|---|
| 15:30 | 09:30 | Gateway health check | — |
| 15:45 | 09:45 | **Phase 4-6 + MKT entry** | `cron_YYYYMMDD_154500.log` |
| 16:00–21:55 | 10:00–15:55 | pt_monitor.py (*/5 perc, trail + TP1) | `pt_monitor.log` |
| 21:40 | 15:40 | **Swing close management** | `pt_close_YYYY-MM-DD.log` |

### Speciális napok

| Típus | Mi történik |
|---|---|
| NYSE ünnepnap | Minden script kilép (is_trading_day guard) |
| Early close | Extra close_positions.py 18:40 Budapest (= 12:40 EDT) |
| DST átmenet (márc 8-29, okt 25 – nov 1) | Kézi crontab módosítás: minden időpont -1 óra |

### Telegram üzenetek

| Mikor | Típus | Tartalom |
|---|---|---|
| ~22:03 | MACRO SNAPSHOT | BMI, szektorok, cross-asset regime, skip day shadow |
| ~15:48 | TRADING PLAN | Pozíciók, VWAP guard, MKT fill-ek, risk layer hatás |
| Intraday | TP1 FILL / TRAIL | Ha TP1 triggered vagy trail aktiválódik |
| ~22:05 | EOD REPORT | Napi P&L, kumulatív, TP1 hit rate |

---

## Deployment lépések

### 1. Git pull (Mac Mini terminal)

```bash
cd ~/SSH-Services/ifds
git pull origin master
```

Ellenőrizd: `git log --oneline -20` — 19 commit a mai napról.

### 2. Tesztek

```bash
source .venv/bin/activate
python -m pytest --tb=short -q
```

Elvárt: 1291+ passing, 0 failure.

### 3. Crontab beállítás

```bash
crontab -e
```

Tartalom: `scripts/crontab.md`-ből másolás. A fő változások a régihez képest:
- Régi `deploy_daily.sh` (teljes pipeline) → `deploy_daily.sh --phases 1-3`
- **ÚJ:** `deploy_intraday.sh` 15:45 (Phase 4-6 + submit)
- **ÚJ:** pt_monitor.py időablak: `*/5 16-21` (volt `*/5 15-21`)
- **TÖRÖLT:** standalone `submit_orders.py`, `pt_avwap.py`
- **ÚJ:** early close extra close (18:40)
- **ÚJ:** `events_to_sqlite.py` (22:45)

### 4. deploy_intraday.sh futtathatóság

```bash
chmod +x scripts/deploy_intraday.sh
```

### 5. State fájlok

```bash
# PositionTracker — üres state ha nincs
cat state/open_positions.json 2>/dev/null || echo '{"positions":[], "last_updated":""}' > state/open_positions.json
```

### 6. Hétfő reggeli manuális Phase 1-3

A vasárnapi cron NEM fut (trading day guard — NYSE zárva).
Hétfő reggel piacnyitás előtt manuálisan:

```bash
cd ~/SSH-Services/ifds
source .venv/bin/activate
./scripts/deploy_daily.sh --phases 1-3
```

Ellenőrizd:
- [ ] Log: cross-asset regime, BMI, ctx.json.gz létrejött
- [ ] Telegram: MACRO SNAPSHOT üzenet megérkezett

### 7. Hétfő 15:45 — első automatikus entry

```bash
tail -f logs/cron_20260406_154500.log
```

Ellenőrizendő:
- [ ] Phase 4-6 lefut (Phase 1-3 context loaded)
- [ ] VWAP guard logok
- [ ] Cross-Asset regime override (ha nem NORMAL)
- [ ] MKT orderek elküldve
- [ ] open_positions.json frissült
- [ ] Telegram: TRADING PLAN üzenet megérkezett

### 8. Hétfő 21:40 — első swing close

```bash
tail -30 logs/pt_close_2026-04-06.log
```

Ellenőrizendő:
- [ ] hold_days increment (0→1 NEM — D+0, hold_days marad 0)
- [ ] Breakeven check fut
- [ ] Pozíciók NYITVA maradnak (NINCS MOC exit D+0-n)
- [ ] open_positions.json: pozíciók benne vannak

### 9. Kedd reggel — kritikus ellenőrzés

```bash
# Pozíciók nyitva?
cat state/open_positions.json | python -m json.tool

# IBKR-ben is?
python scripts/paper_trading/monitor_positions.py

# Ha eltérés → nuke.py ELŐTT ellenőrizd a PositionTracker-t
```

---

## Rollback terv

Ha bármi rosszul megy:

```bash
# Crontab visszaállítás
crontab -e
# → töröld a deploy_intraday.sh sort
# → deploy_daily.sh --phases 1-3 → deploy_daily.sh (flag nélkül, teljes pipeline)
# → pt_monitor.py: */5 16-21 → */5 9-19 (régi)
# → régi submit_orders.py + pt_avwap.py sorok visszarakása

# A pipeline magától fut a régi módon (full Phase 0-6, LMT entry, MOC exit)
```

---

## Napi fájl checklist

| Fájl | Mit ellenőrizz |
|---|---|
| `state/open_positions.json` | Nyitott pozíciók (hold_days, tp1_triggered, breakeven) |
| `state/phase13_ctx.json.gz` | Phase 1-3 context (létezik-e, friss-e) |
| `logs/cron_YYYYMMDD_220000.log` | Esti Phase 1-3 (cross-asset, BMI) |
| `logs/cron_YYYYMMDD_154500.log` | Phase 4-6 + entry (VWAP, MKT fill) |
| `logs/pt_close_YYYY-MM-DD.log` | Swing close (hold_days, breakeven, trail) |
| `logs/pt_monitor.log` | Intraday trail + TP1 fill detektálás |
