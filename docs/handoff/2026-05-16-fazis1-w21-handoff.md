# Fázis 1 (W21) — Hétfő 5/18 piacnyitásra deploy handoff

**Készült:** 2026-05-16 szombat (CC tervezte, jóváhagyva)
**Deadline:** 2026-05-18 hétfő 15:30 CEST piacnyitás
**Scope:** 4 CC task deploy-olva, hétfő 16:15 első éles cron mind a 4 új feature-vel
**Stratégia:** **minden ülés ÚJ CC SESSION-ben** (kontextus-biztonság)

---

## 0. Minden új CC session legelején — kötelező boilerplate

Új Claude Code session indításkor pasztáld be az alábbi promptot **első üzenetként**:

```
/continue

Olvasd el a Fázis 1 handoff dokumentumot:
docs/handoff/2026-05-16-fazis1-w21-handoff.md

Ott találod az aktuális ülés scope-ját és előfeltételeit. Indulhatunk?
```

A `/continue` skill betölti a STATUS.md + journal + open task listát. A handoff doc megmondja, melyik ülésben vagyunk.

---

## 1. Ülés A — Szombat 5/16 délután (Task #1 + #2)

**Időablak:** ma 12:30 – 16:00 (~3.5h)
**Cél:** earnings 7→10 deploy + IBKR Gateway monitoring deploy

### Előfeltételek (Tamás, 10 min Mac Mini-n)

1. **`.env` ellenőrzés** (Telegram WARNING-hoz szükséges):
   ```bash
   grep -E "^IFDS_TELEGRAM_BOT_TOKEN|^IFDS_TELEGRAM_CHAT_ID" ~/SSH-Services/ifds/.env
   # mindkettő legyen beállítva
   ```

2. **§3 diagnosztikai grep parancsok** (Task #2 fix iránya ettől függ):
   ```bash
   cd ~/SSH-Services/ifds

   # (1) Mi a leggyakoribb hiba a check_gateway log-okban?
   grep -h "ERROR\|FAIL\|Cannot connect" logs/pt_gateway_*.log 2>/dev/null | sort | uniq -c | sort -rn | head -5

   # (2) Volt-e silent failure a 16:15 cron-ban az elmúlt 7 napban?
   for d in logs/cron_intraday_2026050[8-9]_*.log logs/cron_intraday_2026051[0-9]_*.log; do
     echo "=== $d ==="
     tail -3 "$d" 2>/dev/null
   done

   # (3) IBKR Gateway state mező a legfrissebb futás során
   grep -iE "gateway|client.*connect|ib.*connect" logs/cron_intraday_20260515_*.log 2>/dev/null | head -10
   ```

3. **Outputot átadod CC-nek** az ülés elején (4-6 sor)

### Ülés A CC scope

- Task #1: [docs/tasks/2026-05-19-earnings-exclusion-7to10.md](../tasks/2026-05-19-earnings-exclusion-7to10.md) — ~25 min, config + tests + docs
- Task #2: [docs/tasks/2026-05-19-ibkr-gateway-monitoring.md](../tasks/2026-05-19-ibkr-gateway-monitoring.md) — ~1.5h, §3 diag alapján Fix A/B/C közül választás
- 2 commit + push
- Mac Mini deploy verify: `git pull` + opcionális 1-ticker dry run

### Ülés A check (záráskor)

- [ ] 2 új commit pusholva (`feat(phase2): earnings 10d` + `feat(monitoring): IBKR Gateway`)
- [ ] `python -m pytest tests/ -q` → 1568+ passing (1564 + 4-5 új)
- [ ] STATUS.md frissítve
- [ ] Tamás Mac Mini-n `git pull` sikeres

---

## 2. Ülés B — Vasárnap 5/17 reggel (Task #3 SEC EDGAR)

**Időablak:** holnap 09:00 – 13:00 (~4h)
**Cél:** SEC 10-Q/10-K filing szűrés Phase 2-ben

### Előfeltételek (Tamás, 5 min)

1. **SEC EDGAR User-Agent env var** beállítása:
   ```bash
   # Mac Mini: ~/SSH-Services/ifds/.env
   echo 'IFDS_SEC_EDGAR_USER_AGENT="IFDS-Trading research@yourdomain.com"' >> .env
   # FONTOS: a SEC megköveteli a valós email-t a User-Agent header-ben
   ```

2. **Live SEC EDGAR ping** (verifikáció előtt):
   ```bash
   curl -s -H "User-Agent: IFDS-Trading research@yourdomain.com" \
     "https://data.sec.gov/submissions/CIK0000320193.json" | head -3
   # várt: "AAPL" / "Apple Inc." json válasz
   ```

### Ülés B CC scope

- Task #3: [docs/tasks/2026-05-21-sec-10q-exclusion.md](../tasks/2026-05-21-sec-10q-exclusion.md) — ~2.5-3h
- **KÖTELEZŐ live schema verifikáció** commit ELŐTT (ifds-rules.md: live API schema)
- **KÖTELEZŐ live smoke a teljes 1425-ticker universe-en** commit ELŐTT (ifds-rules.md: rate-limit live smoke)
- 3 metrika kapu: ≥95% success, ≤5% hard error, ≤5 min total time
- 1 commit + push

### Ülés B check (záráskor)

- [ ] `src/ifds/data/sec_edgar.py` modul létezik + 8-10 unit teszt zöld
- [ ] Live smoke 1425 ticker: ≥95% success rate
- [ ] Cache: `state/sec_cik_cache.json` heti TTL működik
- [ ] Fail-open: ha SEC EDGAR le, Phase 2 nem szűr filing-re (csak earnings-re)
- [ ] STATUS.md frissítve

---

## 3. Ülés C — Vasárnap 5/17 délután (Task #4 UW shadow log)

**Időablak:** holnap 15:00 – 17:00 (~2h)
**Cél:** UW scoring deaktiváció + shadow log dual-write infra

### Előfeltételek

- Ülés A + B sikeresen befejezve (Task #1 + #3 deployolva)
- Mac Mini-n `git pull` Ülés B után

### Ülés C CC scope

- Task #4: [docs/tasks/2026-05-26-uw-shadow-log.md](../tasks/2026-05-26-uw-shadow-log.md) — ~1.75h
- UW scoring deaktiváció (`mms_enabled: False`, `dp_pct_enabled: False`, GEX Polygon-only)
- `state/uw_shadow/YYYY-MM-DD.jsonl` dual-write infra
- 5-6 új teszt
- 1 commit + push

### Ülés C check (záráskor)

- [ ] UW scoring deaktiválva a kritikus path-on
- [ ] Shadow log dual-write működik
- [ ] Phase 6 sizing már NEM használja az UW scoring-ot
- [ ] STATUS.md frissítve
- [ ] **/wrap-up** futtatva — Fázis 1 lezárás journal entry

---

## 4. Hétfő pre-market check — Tamás (5/18 09:00 – 14:30)

**Új CC session csak ha kell.** Egyébként ezek Tamás manuális ellenőrzései:

### 09:00 — sync + state

```bash
cd ~/SSH-Services/ifds
git pull origin master
cat state/.last_sync   # legalább szombati legyen
python -m pytest tests/ -q | tail -2   # 1575+ passing
```

### 10:00 — pre-market smoke

```bash
# Dry-run egy ticker-re (ha lehetséges)
python -m ifds run --phases 2 2>&1 | head -30   # earnings + 10-Q szűrés látszik?

# IBKR Gateway warm-up
python scripts/paper_trading/check_gateway.py
```

### 13:00 — final verification

```bash
# Cron-ok aktívak?
crontab -l | grep -E "deploy_(daily|intraday)"

# Mind a 4 új feature env-konfigja?
grep -E "earnings_exclusion_days|sec_edgar|uw_shadow|gateway_monitor" src/ifds/config/defaults.py
# várt: earnings_exclusion_days=10, sec_edgar_enabled=True, uw_shadow_enabled=True

# .env minden szükséges kulcs
grep -cE "^IFDS_(TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID|POLYGON_API_KEY|FMP_API_KEY|FRED_API_KEY|UW_API_KEY|SEC_EDGAR_USER_AGENT)" .env
# várt: 7
```

### 15:00 — green light

- All API health check OK
- IBKR Gateway connected
- Tested message a Telegram-ra (manuális ping)
- 14:30 — `python scripts/paper_trading/check_gateway.py` egyszer

### 15:30 — Piacnyitás → 16:00 cron `check_gateway` → 16:15 első éles cron

### 16:30 — Az első cron eredmények ellenőrzése

```bash
tail -30 logs/cron_intraday_20260518_161500.log
grep -c "HTTP 429" logs/cron_intraday_20260518_161500.log   # ~0
grep "Pass 2: enriched" logs/cron_intraday_20260518_161500.log   # 90%+
grep "10-Q filter" logs/cron_intraday_20260518_161500.log   # új SEC szűrő aktív
grep "shadow log" logs/cron_intraday_20260518_161500.log   # új UW shadow infra
```

---

## 5. Backout terv (ha valami nem stimmel)

**Ha hétfő reggel egy task hibás:**

```bash
# Mac Mini-n
cd ~/SSH-Services/ifds
git log --oneline -10   # nézd meg melyik commit-ig kell visszamenni
git revert <commit_hash>   # vagy git reset --hard <known_good_commit> (ha helyi-only)
git pull   # vagy push, ha javításhoz kell

# Pre-2026-05-16 stabil állapot:
# commit 41896a6 — docs(wrap-up): 2026-05-16 session close
```

---

## 6. Risk mitigáció

| Task | Risk | Mitigáció |
|---|---|---|
| #1 earnings 10d | 0 | 1 sor revert |
| #2 IBKR monitoring | Low | Telegram WARNING `try/except`-ban |
| #3 SEC EDGAR | **Medium** | **Fail-open**: SEC le → Phase 2 csak earnings-re szűr |
| #4 UW shadow log | Low | Dual-write nem érinti sizing-ot |

---

## 7. Friss kontextus a CC számára

- **Aktuális commit:** `41896a6` docs(wrap-up): 2026-05-16
- **Tesztek:** 1564 passing
- **Open tasks:** 4 db Fázis 1 (`2026-05-19-*` + `2026-05-21-*` + `2026-05-26-*`)
- **Friss kritikus rules** (`.claude/rules/ifds-rules.md`):
  - **Rate-limit live-smoke** — teljes terheléses smoke commit előtt (Task #3-hoz kötelező)
  - **Adat-egészség check** — feature input verifikáció
  - **Test env hygiene** — production state nem írható tesztből
  - **Live API schema verify** — új external API integráció előtt (Task #3-hoz kötelező)
- **Master reference** (`docs/master-reference/INDEX.md`) — system snapshot + risks

---

## 8. Kommunikációs flow

**CC → Tamás:**
- Ülés A induláskor: §3 diag eredmények kérése
- Ülés A végén: Mac Mini deploy verify kérése
- Ülés B előtt: SEC User-Agent ellenőrzés
- Ülés B élő smoke után: success rate jelentés (≥95% kell)
- Mindegyik ülés végén: STATUS.md + journal entry

**Tamás → CC:**
- Diag grep eredmények
- API ping eredmények
- Mac Mini sync confirmation
- Hétfő pre-market check eredmények

---

*Ez a handoff dokumentum elegendő ahhoz, hogy bármely új CC session a 3 ülés bármelyikét fel tudja venni anélkül, hogy a teljes Fázis 1 előzményt újra elmagyarázni kéne.*
