Status: OPEN
Updated: 2026-04-03
Note: Hétfő reggeli deployment — BC20A Swing Hybrid Exit élesítés

# Deployment Checklist — 2026-04-06 (hétfő)

## Előfeltételek
- [x] BC20 + BC21 + BC20A + Log Infra + NYSE Calendar mind DONE (15 fázis, 18 commit)
- [x] 1291 teszt passing, 0 failure
- [ ] Mac Mini online, IB Gateway fut

## 1. Git pull (Mac Mini terminal)

```bash
cd ~/SSH-Services/ifds
git pull origin master
```

Ellenőrizd: a 19 commit mind lejött (`git log --oneline -20`).

## 2. Crontab módosítás

```bash
crontab -e
```

A teljes crontab a `scripts/crontab.md`-ben van. Töröld a meglévő crontab-ot és másold be:

```bash
crontab -l > ~/crontab_backup_$(date +%Y%m%d).txt   # backup
crontab scripts/crontab.md
crontab -l                                            # ellenőrzés
```

**Főbb változások:**
- `deploy_daily.sh` → `deploy_daily.sh --phases 1-3` (22:00)
- **ÚJ:** `deploy_intraday.sh` (15:45) — Phase 4-6 + submit
- `submit_orders.py` standalone → **TÖRÖLVE** (deploy_intraday.sh átveszi)
- `pt_avwap.py` → **TÖRÖLVE** (MKT entry, nincs AVWAP fallback)
- **ÚJ:** early close day extra `close_positions.py` run (18:40)
- **ÚJ:** `events_to_sqlite.py` (22:45)

## 3. deploy_daily.sh ellenőrzés

```bash
cat scripts/deploy_daily.sh
```

A `python -m ifds run "$@"` sor van benne → a `--phases 1-3` átadódik a CLI-nek. ✅

## 4. deploy_intraday.sh ellenőrzés

```bash
cat scripts/deploy_intraday.sh
chmod +x scripts/deploy_intraday.sh
```

Tartalma kb:
```bash
#!/bin/bash
cd ~/SSH-Services/ifds
source .venv/bin/activate
python -m ifds run --phases 4-6
python scripts/paper_trading/submit_orders.py
```

## 5. State fájlok inicializálása

```bash
# PositionTracker — üres state ha még nincs
cat state/open_positions.json 2>/dev/null || echo '{"positions":[], "last_updated":""}' > state/open_positions.json

# Phase 1-3 context — ez vasárnap este 22:00-kor jön létre
# (ha nem létezik hétfőn 15:45-kor, a Phase 4-6 fallback-el full pipeline-ra)
ls -la state/phase13_ctx.json.gz
```

## 6. Vasárnap este — NINCS futás (trading day guard)

Vasárnap (ápr 5) nem trading day → a pipeline trading day guard skip-el.
Az első Phase 1-3 futás **hétfő 22:00-kor** lesz.

**Ez azt jelenti:** hétfő 15:45-kor a Phase 4-6 NEM talál Phase 1-3 contextet!
**Megoldás:** hétfő 15:45 előtt manuálisan futtatni:

```bash
cd ~/SSH-Services/ifds
./scripts/deploy_daily.sh --phases 1-3
```

**Vagy:** hétfő reggelre a deploy_daily.sh-t manuálisan futtatni (teljes pipeline):
```bash
./scripts/deploy_daily.sh
```
Ez létrehozza a Phase 1-3 contextet is.

## 7. Hétfő 15:45 — első Swing entry

```bash
# Figyelj a logra real-time:
tail -f logs/cron_20260406_154500.log
```

Ellenőrizendő:
- [ ] Phase 4-6 lefut (Phase 1-3 context loaded)
- [ ] VWAP guard logok (REJECT/REDUCE/NORMAL)
- [ ] Cross-Asset Regime megjelenik (NORMAL/CAUTIOUS/RISK_OFF/CRISIS)
- [ ] MKT orderek beküldve (nem LMT!)
- [ ] PositionTracker frissült (`cat state/open_positions.json`)

## 8. Hétfő 21:45 — első Swing close

```bash
tail -50 logs/pt_close_2026-04-06.log
```

Ellenőrizendő:
- [ ] hold_days increment működik
- [ ] Breakeven check fut (logban látszik)
- [ ] NINCS MOC exit D+0-n (csak ha max_hold == 0, ami nem fordulhat elő)
- [ ] PositionTracker-ben a pozíciók nyitva maradnak (hold_days=1)

## 9. Kedd reggel — ellenőrzés

```bash
# Pozíciók nyitva maradtak?
cat state/open_positions.json | python -m json.tool

# IBKR-ben is nyitva?
python scripts/paper_trading/monitor_positions.py

# Ha leftover/phantom: nuke.py
```

## Rollback terv

Ha bármi rosszul megy:

```bash
# 1. Crontab visszaállítás az eredeti egyetlen 22:00 futásra
crontab -e
# → töröld a deploy_intraday.sh sort, vedd ki a --phases 1-3 flag-et

# 2. A pipeline magától fut a régi módon (full Phase 0-6, MOC exit)
```

## Fontos: az első hét figyelése

A swing rendszer első hetében napi ellenőrzés:
1. Reggel: `open_positions.json` — hány pozíció, hányadik napja nyitva
2. 16:00 CET: TP1 fill-ek a `pt_monitor.log`-ban
3. 21:50 CET: `pt_close.log` — breakeven, trail update, earnings check
4. Kedd-péntek: pozíciók tényleg nyitva maradnak-e (nem MOC-olta mind)
