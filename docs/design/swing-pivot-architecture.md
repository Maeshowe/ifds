# Swing Pivot Architecture — Design Skeleton

**Verzió:** 0.1 (skeleton)
**Készült:** 2026-05-19 (W21, Fázis 1 nyitás)
**Készítő:** Chat (Claude) — Swing Pivot Dev
**Status:** SKELETON — a részletes specifikáció Fázis 2-ben (W23-W24) készül
**Hivatkozási alap:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) (14 stratégiai döntés, decision-frozen)

---

## 1. A dokumentum célja

Ez a skeleton **magas szintű komponens-térkép** a swing pivot architektúrához. **NEM** részletes specifikáció — a számszerű paraméterek, képletek, és edge-case logika a Fázis 2-ben írandó **3 detail spec dokumentumba** kerül:

| Detail spec | Helye | Fázis 2 ütemezés |
|---|---|---|
| `swing-scoring-spec.md` | `docs/design/` | W23 vége — W24 eleje |
| `swing-risk-spec.md` | `docs/design/` | W24 |
| `swing-sizing-spec.md` | `docs/design/` | W24 |

**Ez a skeleton csak a kapcsolódási pontokat és a komponens-tartományokat rögzíti** — egy egyezményes "térkép", amire a 3 detail spec hivatkozhat.

## 2. A 14 stratégiai döntés komponens-térképe

A 14 döntés 4 architektúra-rétegre lebontva:

### 2.1. Adatréteg (universum + scoring input)

| # | Komponens | Régi (intraday) | Új (swing) | Spec |
|---|---|---|---|---|
| 9 | Universum | FMP screener ~1390 ticker | **S&P 500 + Russell 1000 (~1000)** | scoring-spec |
| 10 | Earnings exclusion | 7 nap (release only) | **10 nap + 10-Q/10-K (SEC EDGAR)** | scoring-spec |
| 2 | UW dark pool / GEX | scoring-aktív | **shadow log Day 90-ig** | scoring-spec |
| 13 | Flow al-komponensek | 7 al-komponens (PCR, OTM, DP, block, buy, squat, RVOL) | **PCR + OTM-inverse only** (Bonferroni) | scoring-spec |

### 2.2. Scoring + döntési réteg

| # | Komponens | Régi | Új | Spec |
|---|---|---|---|---|
| 13 | Komponens-súlyok | flow=0.60, tech=0.30, funda=0.10 | **csak flow (PCR + OTM-inverse)** | scoring-spec |
| 13 | Multiplier chain | $M_{\text{VIX}} \cdot M_{\text{GEX}} \cdot M_{\text{target}} \cdot M_{\text{contradiction}}$ | **csak $M_{\text{target}}$** ($M_c$ sign-flip elemzés Fázis 2-ben dönt) | scoring-spec |
| 13 | Combined threshold | ≥70 (Phase 4), ≥85 (Phase 6 qualified) | **S_j > 50** (Bonferroni-minimum) | scoring-spec |

### 2.3. Sizing + risk réteg

| # | Komponens | Régi | Új | Spec |
|---|---|---|---|---|
| 7 | Risk per trade | 0.7% ($700) | **0.35% ($350)** | sizing-spec |
| 7 | Max concurrent | 5 (BMI guard 4-3-2) | **12 (steady state ~10)** | sizing-spec |
| 7 | Daily new entries | "napi 5" (kötelező) | **2-3 (csak ha érdemes)** | sizing-spec |
| 11 | Sector cap | 2 ticker/sector | **30% notional/szektor** | sizing-spec |
| 7 | Stop multiplier | 1.5×ATR (bracket SL) | **2.0×ATR (mental stop)** | risk-spec |

### 2.4. Execution + exit réteg

| # | Komponens | Régi | Új | Spec |
|---|---|---|---|---|
| 1, 6 | Architektúra-karakter | intraday momentum (6h hold) | **swing momentum (3-5 nap hold)** | risk-spec |
| 6 | Entry idő | 16:20 CEST | **15:30 CEST** (= 09:30 ET market open) | risk-spec |
| 6, 12 | Stop-loss típus | IBKR bracket SL | **mental stop, daily EOD eval** | risk-spec |
| 8 | Time-stop | (nincs explicit) | **5 trading nap → full MOC** | risk-spec |
| 8 | TP struktúra | TP1 1.25×ATR / TP2 2.0×ATR | **TP1 1.5×ATR (50%) / TP2 3.0×ATR (50%)** | risk-spec |
| 12 | Hard SL | (nincs) | **-8% weekly cumulative → MARKET SELL** | risk-spec |
| 14 | Élesítési kritérium | Day 63: +$3k | **Day 126: +$2k + Sharpe>0.5 + 25 pos excess** | (decision doc §7) |

## 3. Komponens-folyam (data → trade)

```
[22:00 CEST előző este — Phase 1-3 cron]
  S&P 500 + Russell 1000 universum (~1000 ticker)
       ↓
  Phase 2 universe filter:
    • market_cap, price, volume
    • earnings exclusion (10 nap)
    • SEC 10-Q/10-K exclusion (10 nap, SEC EDGAR)
       ↓
  Phase 3 sector rotation (változatlan — leader +15, laggard -20)
       ↓
  state/phase13_ctx.json.gz  (kb. 200-400 ticker)

[14:30 CEST — Phase 4-6 cron]
  Phase 4 scoring:
    S_j(t) = 100 × (PCR_score - OTM_score) + sector_adj(t)
    NO tech sub-score, NO funda sub-score, NO multiplier chain
    NO UW dark pool / GEX (shadow log only)
       ↓
  Phase 5 (GEX shadow) — log only, NEM hat
       ↓
  Phase 6 sizing:
    candidates = [j for j in scored if S_j > 50]
    daily_new = min(2-3, 12 - len(open_positions))
    for each new entry:
      sector_check (30% notional cap)
      notional = (equity * 0.0035) / (ATR_pct * 2.0) * entry_price
       ↓
  execution_plan.csv  (0-3 új ticker)

[15:30 CEST — submit_orders.py]
  Market BUY orders (NEM bracket — mental stop architektúra)
  Telegram értesítés a beadott pozíciókról
       ↓
  Pozíciók nyitottak

[T+1 ... T+5 napokon — daily monitor.py @ 22:00 CEST EOD]
  for each open position:
    days_held = today - entry_date
    cum_pnl_weekly = sum(daily_pnl[-5:])

    if cum_pnl_weekly < -8% of notional:
      → másnap 15:30 MARKET SELL (hard SL)
    elif close < entry - 2.0×ATR:
      → másnap 15:30 MARKET SELL (mental SL)
    elif close >= entry + 3.0×ATR:
      → másnap 15:30 MARKET SELL maradékra (TP2)
    elif close >= entry + 1.5×ATR and not tp1_hit:
      → másnap 15:30 MARKET SELL 50% (TP1)
      → trail SL felfelé 1.0×ATR-rel
    elif days_held >= 5:
      → today 21:40 CEST MOC SELL (time-stop)

[T+5 vagy korábbi exit napon — close_positions.py @ 21:40 CEST]
  MARKET SELL vagy MOC SELL a monitor által flagelt pozíciókra
```

## 4. Új vs régi kód-térkép (várt változások)

A Fázis 3 deploy (~jún 23) érinti:

| Modul | Várt változás karaktere | Spec |
|---|---|---|
| `src/ifds/phases/phase2_universe.py` | universum-source S&P+R1000 union (10-Q exclusion már Fázis 1) | scoring-spec |
| `src/ifds/phases/phase4_stocks.py` | **drasztikus egyszerűsítés** — csak PCR + OTM-inverse, NO tech/funda sub-score, NO EWMA esetleg, NO crowded threshold | scoring-spec |
| `src/ifds/phases/phase5_gex.py` | **shadow log only** mode — output a `state/uw_shadow_*.json`-ba, NEM a Phase 6 input | scoring-spec |
| `src/ifds/phases/phase6_sizing.py` | **multiplier chain → csak M_target**, sizing képlet átalakítva (0.35%, 2.0×ATR, 12 cap, 30% notional sector) | sizing-spec |
| `scripts/paper_trading/submit_orders.py` | **bracket TP/SL törlése** — market BUY only, NEM bracket | risk-spec |
| `scripts/paper_trading/pt_monitor.py` | **daily EOD eval** logika (mental stop, time-stop, hard SL, TP1/TP2 trigger) | risk-spec |
| `scripts/paper_trading/close_positions.py` | **MARKET SELL trigger** a monitor flag-ek alapján | risk-spec |
| `src/ifds/config/defaults.py` | sok TUNING paraméter változás | mindhárom spec |

## 5. Kulcs kapcsolódási pontok (interfész-stabil komponensek)

A swing pivot **NEM cseréli le** a következő stabil komponenseket:

| Komponens | Indok |
|---|---|
| Phase 1 BMI engine | A BMI YELLOW degenerált volt a 60 napi mintán, **DE** mint shadow / log feature érdemes megtartani — egy esetleges REGIME-szakaszváltás (GREEN / RED) érdekes lehet |
| Phase 3 sector rotation | A sector leader/laggard adjustment **megmarad** a `sector_adj(t)` formában — szignifikáns volt a régi mintán |
| Daily metrics collection (`daily_metrics.py`) | A struktúra univerzális; az új scoring/sizing field-eket hozzáadjuk |
| Telegram alerting | A bot-réteg változatlan — csak az üzenet-template-ek frissülnek |
| IBKR kapcsolat (`connection.py`) | A retry + Telegram alert (a 2026-05-19 monitoring task után) **kettősen** szolgálja a régi és új architektúrát |
| Circuit breaker (3% drawdown) | A kockázat-cap továbbra is releváns |
| MID Bundle shadow snapshot | Megőrzendő, mint **portfolio context layer** — a swing pivot kontextusában BC25 W26+ scope |

## 6. Mit NEM csinál ez a skeleton

- **NEM** ad konkrét képleteket — a $S_j$ scoring funkcionál pontos formája (normalizáció, küszöbök, sector adjustment csatolódása) a `swing-scoring-spec.md`-ban
- **NEM** ad backtest eredményeket — az entry timing (15:30 vs 16:20 vs 17:15) és az $M_{\text{contradiction}}$ sign-flip analízisek **Fázis 2-ben futnak**
- **NEM** rögzít cron ütemezést — a Fázis 3 deploy-jal párhuzamosan
- **NEM** specifikál Telegram template-eket — a 3 detail spec részeként, vagy külön kis design dokumentumban

## 7. A skeleton frissítési ciklusa

Ez a skeleton **élő dokumentum** a Fázis 1-2 alatt:
- **W21-W22 (Fázis 1)**: ha a 10-Q exclusion design közben új kapcsolódási pont derül ki, ide kerül egy szakasz
- **W23-W24 (Fázis 2)**: amikor a 3 detail spec elkészül, ez a skeleton **átalakul "Architecture Overview" dokumentummá** (rövidebb, csak a magas szintű térkép marad, a részletek a spec dokumentumokra mutatnak)

## 8. Nyitott design kérdések (Fázis 2-ben dől el)

A Day 63 outcome doc **nyitva** hagyott néhány design kérdést, amelyeket a Fázis 2 elemzés és spec-írás során kell tisztázni:

### 8.1. PCR és OTM-inverse skálázás

A `S_j(t) = 100 × (PCR_score - OTM_score) + sector_adj(t)` formában a `PCR_score` és `OTM_score` **mindkettő [0, 1] tartományba** normalizáltak. A normalizálás módja:
- **Z-score** (universe-mean-relative): a daily univerzum mean-jéhez képest
- **Percentile** (rank-relative): a daily univerzum rangsorához képest
- **Absolute** (előre kalibrált küszöbökhöz képest)

Javaslat: **percentile-alapú normalizálás** (univerzum-rank), mert a PCR és OTM Call abszolút értékei piaci regime-függőek (magas VIX → magasabb PCR mindenkinek). A percentile-rank **regime-rezisztens**.

**Fázis 2 design:** `swing-scoring-spec.md`.

### 8.2. EWMA simítás megtartása?

A régi rendszerben az EWMA (10 napi span) **simította** a kompozit pontszámot — a swing-en a 3-5 napi hold mellett a **smoothing horizon** és a **hold horizon** összemérhetők. Lehet:
- (A) **EWMA elhagyása**: a swing 5×-erősebb signal nem igényli — a smoothing felesleges
- (B) **EWMA megtartása rövidebb span-nel** (pl. 5 napi): a daily noise-t simítja, de nem siet túl
- (C) **Hibrid**: EWMA a PCR-re, raw az OTM-re (a kettő különböző zaj-karakterű)

Javaslat: **(B)** — EWMA(5) konzervatív default, Fázis 3 deploy után A/B teszt opcionálisan.

### 8.3. Hétfői entry vs napi entry

A swing 3-5 napi hold + **hét közbeni új entry** lehetősége: ha hétfőn nyitottunk 3 pozíciót, kedden még további 2-3 új entry lehet (a 12 cap-on belül). DE: ha péntek délután nyitunk egy 5 napi swing-et, az hétfő → péntek → **a következő hétfő-péntek tartana** — az átlagos hold meghaladná az 5 napot.

Lehet:
- (A) **Bármely napon entry** (mostani javaslat, max 12 concurrent)
- (B) **Csak hétfő-szerda entry** (csüt-pén nincs új entry, így mindig péntekre lezárul)
- (C) **Csüt-pén entry rövidebb time-stop-pal** (pl. 3 napi hard time-stop pénteken nyitottra)

Javaslat: **(A) most**, (C) backteszt-ellenőrzéssel Fázis 2 végén.

### 8.4. Concurrent positions cap rendszer

A "max 12 concurrent" hogyan érvényesül, ha a daily 2-3 new entry javaslat **több ticker** scoringot ad ≥50-nel?
- (A) **Rangsor + greedy fill**: a S_j szerint top-2-3, már nyitott pozíciók prioritást élveznek
- (B) **Score-weighted lottery**: a top tickerekből véletlenszerű választás
- (C) **Sector-balanced rangsor**: a top-N úgy, hogy a 30% notional sector cap-et NE sértse

Javaslat: **(C)** — sector-balanced greedy, a 30% cap és a rangsor együtt.

## 9. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) (decision-frozen baseline)
- [`docs/strategic-review/2026-05-08-strategic-review-mathematical.md`](../strategic-review/2026-05-08-strategic-review-mathematical.md) (matematikai alapok)
- [`docs/master-reference/04-risks-and-open-questions.md`](../master-reference/04-risks-and-open-questions.md) (W21+ aktív backlog)
- Várhatóan: `docs/design/swing-scoring-spec.md`, `swing-risk-spec.md`, `swing-sizing-spec.md` (Fázis 2)

---

**A dokumentum vége (v0.1 skeleton).** A Fázis 2 spec-írás megkezdése után ez a skeleton frissül; végleges Architecture Overview formába W24 végén.
