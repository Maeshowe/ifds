# 01 — Rendszer-snapshot: Aktuális paraméterek és scoring kompozíció

**Utoljára frissítve**: 2026-05-08 (W19 D5 előtt — péntek)
**Aktív verzió**: BC23 (deploy 2026-04-13) + W18 add-onok (Breakeven Lock, M_contradiction, vix-close)

---

## 1. A scoring kompozíció

### A kompozit pontszám képlete

```
KOMPOZIT_PONTSZÁM = 0,60 × FLOW_SCORE + 0,30 × TECHNIKAI_SCORE + 0,10 × FUNDAMENTÁLIS_SCORE
```

- Range: 0-100 (a freshness_bonus 1,5 multipler kikapcsolása óta)
- Belépési küszöb: **`combined_score_minimum: 70`**
- Túlzsúfoltság-küszöb (clipping): **`clipping_threshold: 95`** (e felett SKIP)
- A pontozást **EWMA simítás** stabilizálja (10 napos exponenciálisan súlyozott mozgóátlag)

### A scoring súlyok (utolsó változás: BC23, 2026-04-13)

| Komponens | Súly | Korábbi | Indok |
|-----------|------|---------|-------|
| Flow | **0,60** | 0,40 | Az egyetlen statisztikailag szignifikáns prediktor (Pearson +0,136\*) |
| Technikai | 0,30 | 0,30 | Változatlan |
| Fundamentális | **0,10** | 0,30 | A backward-looking jellegű miatt nem-prediktív (Pearson -0,088) |

## 2. A flow score (60% súly) al-komponensei

A flow_score 7 al-komponens összegéből épül fel, alap 50-ből indulva.

| Al-komponens | Bonus tartomány | Pearson r vs P&L | Aktuális státusz |
|---------------|------------------|-------------------|-------------------|
| **PCR (put-call ratio)** | -10 — +15 | **+0,203\*\*** | **Erős pozitív, megtartani** |
| **RVOL (relatív volumen)** | -10 — +15 | **+0,147\*** | **Pozitív, megtartani** |
| **OTM Call Ratio** | 0 — +10 | **-0,194\*\*** | **NEGATÍV, INVERTÁLANDÓ** ⚠️ (W19+ task) |
| **Dark Pool %** | 0 — -15 | **-0,265\*\*** (60-trade audit) | ✅ Sign-flip + per-ticker fetch DEPLOYED (`9a169b9`, 2026-05-08) |
| Block trade | 0 — +15 | -0,117 (gyenge) | **Súly 0-ra állítandó** ⚠️ (W19+ task) |
| Buy pressure | -15 — +15 | +0,068 (nem szig.) | **Súly 0-ra állítandó** ⚠️ (W19+ task) |
| Squat bar | 0 — +10 | +0,036 (nem szig.) | **Súly 0-ra állítandó** ⚠️ (W19+ task) |

**Megjegyzés**: a flow al-komponens dekompozíció a **Feb-Apr 1 mintán** (232 trade) futott. A snapshot regresszió fix után (W19+) a post-Apr 13 mintán **újra futtatandó**.

## 3. A technikai score (30% súly) al-komponensei

| Al-komponens | Bonus tartomány | Mit mér | Aktuális érték |
|---------------|------------------|---------|-----------------|
| RSI ideális zóna | 0 — +30 | RSI [45, 65] → +30, [35, 45)/(65, 75] → +15 | Aktív |
| SMA50 bónusz | 0 — +30 | Ár > SMA50 → +30 | Aktív |
| RS vs SPY | 0 — +15 | 3 hónapos relatív teljesítmény | **+15** (BC23: volt 40, csökkentve) |

## 4. A fundamentális score (10% súly)

50-es bázis körüli pontszám:
- Bevétel-növekedés (>10% → +5; <-10% → -5)
- EPS-növekedés (>15% → +5; <-15% → -5)
- Profit margin (>15% → +5; <0% → -5)
- ROE (>15% → +5; <5% → -5)
- D/E arány (<0,5 → +5; >2,0 → -5; >3,0 → -10)
- Interest coverage (<1,5 → -5)

## 5. Pozíció-méretezés és multiplier chain

### A risk-budget

```
POZ_RISK = ACCOUNT_EQUITY × 0,007 = $700/ügylet
M_total = clamp(M_VIX × M_GEX × M_target × M_contradiction, 0,25, 2,0)
POZ_SIZE = (POZ_RISK × M_total) / (1,5 × ATR)
```

### Aktív multiplier-ek (BC23 utáni egyszerűsítés)

| Multiplier | Triggerelt érték | Mit véd | Aktív státusz |
|------------|-------------------|---------|----------------|
| **M_VIX** | 1,0× alapesetben, lineáris csökkenés VIX > 20-tól | Piaci volatilitás | ✅ |
| **M_GEX** | pozitív 1,0× / negatív 0,5× / magas-vol 0,6× | Gamma exposure | ✅ |
| **M_target** | 0,85× ha ár 20%+ a target felett, 0,60× ha 50%+ | Analyst consensus túlszorulás | ✅ |
| **M_contradiction** | 0,80× ha 4 OR-feltétel közül egy aktivál | Fundamentális ellenmondás | ✅ (W18 deploy) |

### Inaktív (1,0× fixre állított) multiplier-ek

| Multiplier | Korábbi érték | Inaktiválás indoka |
|------------|----------------|--------------------|
| M_flow | 1,25× ha flow_score > 80 | A flow_score a kompozit-pontszámban már 60% súlyt kap, dupla-számolás |
| M_insider | 0,75× — 1,25× | A 60 napi adatban nem-prediktív |
| M_funda | 0,50× ha funda_score < 60 | A funda komponens 10% súlyon nem ad érdemleges signal-t |
| M_utility | 1,0× — 1,3× score-alapú | A 60 napi adatban nem-prediktív |

## 6. Maximum pozíciószám és kockázati struktúra

| Paraméter | Aktuális érték | Korábbi | Megjegyzés |
|-----------|----------------|---------|------------|
| `max_positions` | **5** (fix) | 8 (BC23 előtt) | Jelölt: dinamikus küszöb (max 5) ⚠️ |
| `dynamic_position_score_threshold` | 85 | n/a | Paraméter rögzítve, **nincs aktívan használva** |
| `risk_per_trade_pct` | 0,7% | 0,5% | $700/ügylet 100k bázison |
| `max_single_position_risk_pct` | 1,5% | 1,5% | Hard cap |
| `max_gross_exposure` | $80 000 | $100 000 | 5 pozíció × max ~$16 000 |
| `max_single_ticker_exposure` | $20 000 | $20 000 | Per-ticker hard cap |
| `max_positions_per_sector` | 2 | 3 | BC23: koncentráció csökkentése |

### Korreláció-szabályok (sektor-csoport limitek)

| Csoport | Max pozíció | Sektorok |
|---------|-------------|----------|
| Cyclical | 3 | XLK, XLY, XLI, XLF, XLB |
| Defensive | 2 | XLP, XLV, XLU, XLRE |
| Financial | 2 | XLF |
| Commodity | 2 | XLE, XLB |

## 7. ATR-alapú profit-küszöbök és stop-loss

| Paraméter | Aktuális érték | Korábbi | Indok |
|-----------|----------------|---------|-------|
| `stop_loss_atr_multiple` | 1,5×ATR | 1,5× | Változatlan |
| `tp1_atr_multiple` | **1,25×ATR** | 0,75× → 1,5× → 1,25× | W16 follow-up tuning |
| `tp2_atr_multiple` | **2,0×ATR** | 3,0× | BC23: reachable swing target |
| `scale_out_pct` | **0,50** | 0,33 | BC23: equal bracket split (50/50) |
| `breakeven_threshold_atr` | 0,3×ATR | 0,3× | Nem aktívan használt |
| `trailing_stop_atr` | 1,0×ATR | 1,0× | Trail távolság |

### A 2026-05-06 felfedezett profit-trigger Breakeven Lock

A "Breakeven Lock" mechanizmus (W18 deploy) **NEM csak a 19:00 CEST window-ban** aktivál — **profit-küszöb alapján is**, ~+1% profit fölött (becsült). Pontos küszöb még nem dokumentált; **W19+ task a profit-küszöb csökkentése 0,5%-ra**.

## 8. Univerzum-építés szabályai

| Paraméter | Érték |
|-----------|-------|
| Minimum piaci kapitalizáció | $2 milliárd |
| Minimum ár | $5 |
| Minimum napi forgalom | 500 000 részvény |
| Opciós piaci aktivitás | Kötelező |
| Earnings exclusion | 7 naptári nap előretekintés |

A 2-pass earnings exclusion (FMP earnings calendar bulk + per-ticker fetch) a 60 napi adatban átlagosan **425 ticker-t** szűr ki ticker-specifikus módon. **Adatminőség gap**: az ADR earnings (BUD eset 2026-05-05) **hiányos** az FMP-ben.

## 9. Az adatszolgáltatók aktuális állapota

| Forrás | Tier | Havi költség | Funkció |
|--------|------|--------------|---------|
| Polygon Stocks Advanced | Advanced | $199 | OHLCV, real-time, BMI, technikai |
| Polygon Options Developer | Developer | $79 | Opciós lánc, GEX, Greeks |
| Polygon Indices Starter | Starter | $49 | VIX backup, ETF |
| Polygon Currencies Starter | Starter | $49 | Tervezett (DXY, currency) |
| FMP Ultimate | Ultimate | $139 | Screener, earnings, fundamentumok |
| **Unusual Whales Basic** | **Basic** | **$150** | Dark pool, GEX, opciós flow |
| FRED | Free | $0 | VIX, TNX, yield curve |
| **Total** | | **$665/hó** | |

**Fontos**: az `API_STACK.md` (2026-03-01-i) **frissítendő** a 2026-05-08-i állapotra (BC23 utáni változások, M_contradiction, dp_pct rekalibráció).

## 10. A legutóbbi paraméter-változások időrendi naplója

| Dátum | Komponens | Változás | Ok |
|-------|-----------|----------|-----|
| 2026-04-13 | Pontozási súlyok | flow 0,40→0,60, funda 0,30→0,10 | BC23 redesign |
| 2026-04-13 | Freshness bonus | 1,5 → 1,0 | Inverz quintilis minta cáfolata |
| 2026-04-13 | RS vs SPY bonus | 40 → 15 | Momentum-chasing csökkentés |
| 2026-04-13 | TP2 multiplier | 3,0 → 2,0 | Reálisabb swing cél |
| 2026-04-13 | Bracket split | 33/67 → 50/50 | Egyenlő allokáció |
| 2026-04-13 | Submit idő | 15:45 → 16:15 CEST | Opening range stabilizáció |
| 2026-04-13 | MMS sizing | True → False | 93/100 undetermined, flat 0,75× |
| 2026-04-15 | TP1 multiplier | 0,75 → 1,5 → 1,25 | W16 tuning |
| 2026-04-29 | VIX close | Új | daily_metrics.py Phase 0 integráció |
| 2026-04-29 | LOSS_EXIT whipsaw | Audit | -2% szabály átlagosan védett |
| 2026-05-02 | M_contradiction | Új | FMP-ből 4 OR-feltétel |
| 2026-05-02 | sync_from_mini.sh | Bugfix | docs/analysis/ + state/.last_sync |
| 2026-05-06 | Breakeven Lock profit-trigger | Felfedezve LIVE | UEC esetből (~1% profit fölött aktivál) |
| 2026-05-08 | dp_pct rekalibráció | ✅ DEPLOYED (`9a169b9`) | sign-flip + threshold (12%/18%) + per-ticker fetch |
| 2026-05-08 | Snapshot regresszió fix | ✅ DEPLOYED (`d3fce73`) | teszt-sanitációs hiba: e2e teszt valódi save_phase4_snapshot hívás |
| 2026-05-11 | Snapshot fix validáció | ✅ 1390 ticker, 22,89 KB | első élesben futás megerősítette a fix-et |
| 2026-05-11 | Bug start date korrekció | 2026-04-10 → **2026-04-05** | snapshot lista méret-evolúció alapján |
| 2026-05-11 | UW HTTP 429 rate limits | ⚠️ ÚJ FINDING | per-ticker fetch deploy mellékhatása (1.6 backlog) |
| 2026-05-12 | LOSS_EXIT bracket SL bug 3. instancia | 🆘 FORM -29 SHORT | MOC fill-after új minta (1.3 bővítendő) |
| 2026-05-12 | Snapshot fix 2. nap validáció | ✅ 161 qualified, konzisztens | a 159 (hétfő) ↔ 161 (kedd) stabil |
| 2026-05-12 | UW HTTP 429 növekedés | ⚠️ 50 → 170+ ticker | sürgősség egy hét alatt 3-4×-ezett |
| 2026-05-12 | M_contradiction LIVE 7. nap | ⚠️ 33% iránybeli helyesség (2/6) | rosszabb mint random; sign-flip vizsgálandó |

## 11. Aktív CC tasks és nyitott implementációk

| Task | Státusz | Effort | Fájl |
|------|---------|--------|------|
| Snapshot regresszió fix | ✅ DEPLOYED (`d3fce73`) | n/a | `docs/tasks/2026-05-08-snapshot-regression-fix.md` |
| dp_pct rekalibráció | ✅ DEPLOYED (`9a169b9`) | n/a | `docs/tasks/2026-05-08-dp-pct-recalibration.md` |
| LOSS_EXIT bracket SL cancellation | OPEN, P1 | ~30-45 min | `docs/planning/backlog-ideas.md` |
| 10-Q SEC Filing Exclusion | OPEN, P1 | ~2-3 óra | `docs/planning/backlog-ideas.md` |
| ADR earnings adatforrás fix | OPEN, P1 | ~3-4 óra | `docs/planning/backlog-ideas.md` |
| UW rate limit kezelés finomítás ⭐ ÚJ | OPEN, P1 | ~1-2 óra | `docs/master-reference/04-risks-and-open-questions.md` 1.6 |
| IBKR Gateway monitoring + Telegram alert ⭐ ÚJ | OPEN, P1 | ~1 óra | `docs/master-reference/04-risks-and-open-questions.md` 1.7 |
| LOSS_EXIT küszöb finomítás per-ticker ATR-arányos ⭐ ÚJ | OPEN, P2 | ~1-2 óra | `docs/master-reference/04-risks-and-open-questions.md` 2.4 |
| Entry timing optimalizáció backtest ⭐ ÚJ (Tamás javaslata) | OPEN, P2 (analitikus) | ~1-2 óra Chat | `docs/master-reference/04-risks-and-open-questions.md` 2.5 |

---

**A frissítésért felel**: Chat (Claude) — eseményalapú (paraméter-tuning, deploy után). Heti konzisztencia-check péntek 22:00 weekly metric után.
