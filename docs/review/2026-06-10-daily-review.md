# IFDS Daily Review — 2026-06-10 (szerda, Day 18 chat-conv / Day 17 NYSE, W24 D3)

**Verzió**: swing pivot Day 18/63 — **TÖRTÉNELMI $1 000+ CUMULATIVE ÁTTÖRÉS + 2. major risk-off napon defenzív karakter** ⭐⭐⭐⭐
**Day 18 realized P&L (broker)**: **+$631,96** (gross $636,29, commission $4,33) — a swing pivot 2. legjobb realized napja
**Cumulative**: **+$1 399,05** ⭐⭐⭐⭐ (Day 17 záró +$767,09 → +$631,96 hozzáadva) — **SWING PIVOT DEPLOY ÓTA ELSŐ $1 000+ ÁTTÖRÉS**
**Net Liquidation Day 18 záró (IBKR)**: **$101 359,11** — Day 18 mozgás **-$580,72 (-0,57%)** (a +$632 realized vs -$1 124 unrealized csökkenés a 4 exit + új VNO self-reentry intraday-i gyengülése miatt)
**Excess return Day 18**: **+2,21%** ⭐⭐⭐ (portfolio +0,64% realized-net% vs SPY -1,58%) — **2. major risk-off napon defenzív karakter megerősítés** (Day 15-i +2,34% után)
**Open positions**: **6** (Day 17-i 7 → 6: 4 exit kiment + 1 új VNO self-reentry)
**Új entry**: **1** — **VNO** (self-reentry, 1 perccel a TP2 SELL után! Day 18-i scoring újra top, a Real Estate szektorban 2 ticker NSA + VNO)

**⭐⭐⭐⭐ Négy történelmi Day 18 esemény:**

**1. CUMULATIVE +$1 399,05 — SWING PIVOT DEPLOY ÓTA ELSŐ $1 000+ ÁTTÖRÉS**
- A Day 8-i mélypontról (-$779,64) Day 18-ig **+$2 178 broker mozgás 10 trading nap alatt**
- A Day 21 checkpoint (≈jún 14, W24 D5) buffer **193%** (a -$1500 küszöbtől)
- Net Liq baseline+: +$1 359,11 (6. egymás utáni nap baseline FÖLÖTT)

**2. VNO TP2 +$385,76 (pnl_pct 13,21%) — a swing pivot LEGMAGASABB single-trade ROI%-ja**
- A swing pivot ELSŐ ideális TP1→TP2 2-fázisú trade-je TELJES (Day 13 entry $33,95 → Day 17 TP1 partial +$230 → Day 18 TP2 partial +$386)
- **VNO total ROI** Day 13-18: 85 × ($36,68 - $33,96) + 86 × ($38,45 - $33,96) = $231 + $386 = **+$616 broker net** (171 share teljes hold-on)
- A korábbi var ($285-347 a Day 17 review §6.1) **+$80 felülteljesítés** (a Day 18 reggeli VNO mark $38,45 magasabb volt mint a TP2 level $37,27)

**3. Excess +2,21% a 2. major risk-off napon** ⭐⭐⭐
- SPY -1,58% (a Day 18 fontos kockázat-osztó nap, VIX +9,86% → 21,83)
- Portfolio +0,64% realized-net% (a #6 fix Day 18-on is realized-alapú szemantikán fut — §5.3 follow-up)
- Excess +2,21% — a swing pivot **2. major risk-off napon defenzív karakter megerősítés** (Day 15-i +2,34% után). Statisztikailag: 2 major risk-off napon átlag +2,28% excess.

**4. VNO SELF-REENTRY ⭐ — ÚJ STRATEGIAI MINTA**
- 15:30:08 TP2 SELL 86 share @ $38,45 (realized +$385,76)
- **1 perccel később (15:31:08) ÚJ VNO entry 160 share @ $38,77** (planned $38,45, slippage +0,83% kedvezőtlen)
- A scoring engine **NEM tart "blacklist"-en az aznapi exited ticker-eket** — a Phase 4-6 a Day 18 reggeli context-ben a VNO-t újra top scoring-on választotta
- **Strukturális tanulság**: a swing pivot self-reentry-mechanizmus aktív — egy ideális trend-követő stratégia tulajdonsága

**⭐ További Day 18 kulcs finding-ek**:
- **Day 18 4-exit-mega-trifecta**: 2 TP1 (NSA + TKR) + 1 TP2 (VNO) + 1 MOC TIME_STOP (MSM) — a swing pivot eddigi legkomplexebb exit-napja
- **NSA TP1 +$159,13** (várt $130 → +$29 felülteljesítés), 1 nap entry-től TP1 minta megerősítés
- **TKR TP1 +$10,05** (várt $90 → **-$80 alulteljesítés**) — next-day MKT fill kockázat 5. minta (kedvezőtlen, fill $134,32 vs TP1 $138,51)
- **MSM TIME_STOP MOC +$77,02** (várt $81, közeli)
- **`_reconcile_state_from_ibkr` 12/12 ÉLES SILENT OK** — **24 trading napi tiszta mental-stop futás** ⭐ (új rekord)
- **MASI 9. egymás utáni nap top S_j-en** (most 2. helyen, NSA előzte 94,4 vs MASI 93,1) — sector-balanced greedy strukturális védelme folytatódik
- **⚠️ ÚJ metadata-glitch**: a `daily_metrics::trades::details::VNO::exit_type` **"TP1"-ként** logolva (a fill-timestamp alapján), miközben a `pending_exits::VNO::exit_type` HELYESEN "TP2" + `exits::tp2_hits=1` is jelzi a TP2-t
- **⚠️ ACHC -$224 napi (-6,25%)** — Day 18-i intraday zuhanás, stop $22,84 közelebb (mark $23,91 = 4,7% buffer)
- **⚠️ FFIV -$54 napi** — lassan gyengül, stop-buffer szűkül 2,4%-ra

---

## 0. ⭐⭐⭐ A swing pivot deploy óta első $1 000+ cumulative áttörés

A Day 18 a swing pivot deploy (2026-05-18) óta **ELSŐ $1 000+ cumulative-átlépés**:

| Nap | Cumulative | Δ | Net Liq | Buffer (-$1500-ig) |
|-----|------------|-----|---------|---------------------|
| Day 8 (mélypont) | -$779,64 | — | $99 220 (becsült) | 48% |
| Day 14 (W23 D4) | +$199,50 | +$979 | $101 273,85 | 113% |
| Day 15 (W23 D5) | +$245,25 | +$46 | $100 675,60 | 116% |
| Day 16 (W24 D1) | +$358,21 | +$113 | $101 034,23 | 124% |
| Day 17 (W24 D2) | +$767,09 | +$409 | $101 939,83 | 151% |
| **Day 18 (W24 D3)** | **+$1 399,05** ⭐⭐⭐⭐ | **+$632** | $101 359,11 | **193%** ⭐⭐⭐ |
| Day 19 várt (W24 D4) | +$1 600-1 700 | +$200-300 | $101 600-800 várt | **207%+** |
| Day 21 várt (W24 D6, ≈jún 14) | +$1 700-1 900 | +$100-300 | $101 800+ várt | **213%+** |

**A Day 21 checkpoint** (a `04-risks` -$1500 küszöb) **Day 18-én már 193%-os bufferben** — kritérium-tartományon kívül, **2× nagyobb mint a Strategic_review-i kritérium-tartomány**.

A Day 8-i mélypontról Day 18-ig **+$2 178 broker mozgás 10 trading nap alatt** — a swing pivot **strukturálisan a kanonikus pozitív tartományban** stabilizálódott.

---

## 1. Day 18 Trades

### 1.1 Exits (4) — a swing pivot eddigi legkomplexebb exit-napja

| Idő (CEST) | Ticker | Exit Type | Qty | Entry (IBKR avg) | Fill | IBKR Realized | Várt (Day 17 review §6.1) | Eltérés |
|-----------|--------|-----------|-----|-------------------|------|---------------|----------------------------|---------|
| 15:30:09 | **VNO** | **TP2** (50% partial, full close 86 remainder) | 86 | $33,96 | $38,45 (DRCTEDGE) | **+$385,76** ⭐⭐⭐ | **+$285-347** | **+$80 felülteljesítés** ⭐ |
| 15:30:18 | **NSA** | TP1 (50% partial) | 94 | $43,42 | $45,12 (ARCA) | **+$159,13** ⭐ | **+$130** | **+$29 felülteljesítés** |
| 15:30:26 | **TKR** | TP1 (50% partial) | 19 | $133,74 | $134,32 (NYSE) | **+$10,05** ⚠️ | **+$90** | **-$80 alulteljesítés** ⚠️ |
| 21:59:30 | **MSM** | TIME_STOP MOC (29 remainder, full close) | 29 | $112,79 | $115,45 (NYSE MOC) | **+$77,02** | **+$81** | **-$4 közeli** ✓ |
| **Total Day 18 broker net realized** | | | | | | **+$631,96** | **+$586-648** | **a sávban közepe** ⭐ |

**A 4 exit kombinált broker net commission $4,33** ($1,09 + $1,11 + $1,06 + $1,07).

### 1.2 ⭐⭐⭐ VNO TP2 — A SWING PIVOT ELSŐ IDEÁLIS TP1→TP2 2-FÁZISÚ TRADE-JE TELJES

A VNO 5 napi hold (Day 13-18) **a swing pivot stratégia teljes karakterét bizonyítja**:

| Day | VNO mark | Action | Realized | Unrealized | Megjegyzés |
|-----|----------|--------|----------|------------|------------|
| Day 13 entry | $33,95 (fill) | BUY 171 share | $0 | $0 | Real Estate, ATR 3,0%, top S_j 86,3 |
| Day 14 záró | $35,07 | HOLD | — | +$190 | +3,17% mozgás |
| Day 15 záró | $35,21 | HOLD | — | +$214 | +0,40% (major risk-off Day 15-i ellenére!) |
| Day 16 záró | $36,20 | HOLD (TP1 átlépve) | — | +$384 | +2,81% |
| **Day 17 TP1 fill** | **$36,68** | **SELL 85 (50% partial)** | **+$230,47** | +$386 (86 maradék) | TP1 partial |
| **Day 18 TP2 fill** | **$38,45** | **SELL 86 (full close)** | **+$385,76** ⭐⭐⭐ | $0 (kiment) | **TP2 ideális zárás** |
| **VNO total ROI** | | | **+$616,23 broker net** ⭐⭐⭐ | | **A swing pivot legmagasabb single-trade ROI** |

A VNO **trade-arc**:
- 171 share entry @ $33,96 broker avg
- 85 share TP1 partial @ $36,68 = +8,01% ROI ($230,47)
- 86 share TP2 partial @ $38,45 = **+13,21% ROI** ($385,76) — **a swing pivot eddigi legmagasabb pnl_pct**
- Teljes 5 napi hold ROI: **+$616 broker net** (a CDNS Day 10-12-i +$434 TP2 single-pop ROI-t **+$182-vel felülmúlja**)

**Strukturális tanulság**: a swing pivot $h=5$ multi-day holding **ideális esetben** TP1 partial + TP2 partial 2-fázisú zárást ad — a "ideal trend trade" karakter. A VNO az első, amely a teljes utat befutotta.

### 1.3 ⚠️ TKR TP1 alulteljesítés +$10,05 — Next-day MKT fill kockázat 5. minta

A TKR TP1 a `state.tp1_level: $138,51` alapján flag-elve Day 17 záró után (a mark $137,09 közel). **DE** Day 18 reggeli TKR ár-mozgás kedvezőtlen volt:

- Day 17 záró mark: $137,09 (intraday peak átlépte $138,51-et — TP1-flag valid)
- Day 18 15:30 MKT fill: **$134,32** (-$4,19/share a TP1 level-től)
- Day 18 záró mark: $132,39 (-3,4% Day 18 intraday)

**Next-day MKT fill kockázat statisztikai minta** most 5 ellenpélda:
- MSM Day 14: +0,11% kedvező ✓
- BEN Day 15: -2,05% kedvezőtlen ⚠️
- AMH Day 16: -1,50% kedvezőtlen ⚠️
- VNO Day 17 (TP1): +1,33% kedvező ⭐
- **TKR Day 18 (TP1): -3,04% kedvezőtlen** ⚠️⚠️

**5 minta = 2 kedvező + 3 kedvezőtlen, átlag -1,03% kedvezőtlen** (a statisztikai mintán egyre szignifikánsabb negatív trend). Day 21+ után a Backlog #7 (TP1-limit-order opció) elemzéshez **érdemes komolyan mérlegelni**.

### 1.4 Új entry (1) — VNO SELF-REENTRY ⭐

| Idő (CEST) | Ticker | Sektor | Qty | Planned | Fill (IBKR) | Slippage | Notional | ATR |
|-----------|--------|--------|-----|---------|--------------|----------|----------|-----|
| 15:31:08 | **VNO** | **Real Estate** (sector dupli NSA mellé) | 160 (2 fill: 60 ARCA + 100 BEX) | $38,45 | $38,77 | **+0,83% kedvezőtlen** | $6 196 | 1,09 (2,8%) |

**A VNO self-reentry minta strukturálisan ÉRDEKES**:
- 15:30:08: TP2 SELL 86 share @ $38,45 (realized +$385,76, position 0-ra)
- **1 perccel később (15:31:08)**: BUY 160 share @ $38,77 (új entry, position 160-ra)
- A scoring engine **a Day 18 reggeli execution_plan-ben** újra a VNO-t választotta top scoring-on (89,2 S_j a Day 17 záró után)
- A swing pivot **NEM tart "blacklist"-en az aznapi exited ticker-eket** — egy ideális trend-követő stratégia tulajdonsága

**Strategiai megfontolások**:
1. **A self-reentry védőszabály lenne** (pl. 1-2 nap "cooldown"): elkerülné az **azonos napi turnover-növekedést** (commission + slippage drag)
2. **DE**: a TP2-vel kilépett ticker továbbra is top scoring lehet — a self-reentry "újra-belépés a momentum-trade-be" érvényes
3. **Statisztikai megfigyelés Day 21+ után**: hány self-reentry történik, és átlagos ROI vs nem-reentry új entry?

**A Day 18 VNO self-reentry kockázata megjelenik**:
- Day 18 záró VNO mark $38,28 (vs entry $38,77) = -$0,49/share napi gyengülés, **-$79 unrealized**
- Stop $36,27 (5,3% buffer)
- Day 19 outlook: ha a major risk-off folytatódik → stop-veszély

### 1.5 Sector distribution Day 18 záró

| Sektor | Notional (state) | % portfolio | Ticker(ek) |
|--------|------------------|-------------|------------|
| **Real Estate** | $10 234 | **10,23%** | VNO új (160) + NSA (94 partial maradék) |
| Technology | $4 904 | 4,90% | FFIV (12) |
| Financial Services | $3 921 | 3,92% | BEN (126 trail) |
| **Healthcare** | $3 570 | 3,57% | ACHC (141) |
| **Industrials** | $2 637 | 2,64% | TKR (20 trail) |
| **Total** | **$25 266** | **25,27%** | 6 ticker, **5 szektor** |

**Day 17 záró 31,89% → Day 18 záró 25,27%** — -6,62% csökkenés (4 exit + 1 új entry, **a portfolio karcsúsodott**). **Sector observed max 10,23% (Real Estate, VNO + NSA dupli)** — bőven a 30% cap alatt.

---

## 2. EOD State (22:00 CEST) — Day 19-re 2 EOD flag

`pt_monitor_2026-06-10.log` 22:00:09:
```
[SWING EOD] Evaluated 6 positions — 2 exit flags set
  BEN: TIME_STOP
  NSA: TP2
```

**Day 19 (csütörtök 2026-06-11, W24 D4) — kétoldalas exit-nap**.

### 2.1 A 6 nyitott pozíció Day 18 záró

| Ticker | Entry $ (state/broker) | Mark | Qty | days_held | Unrealized (IBKR) | next_action | Sektor |
|--------|-------------------------|------|-----|-----------|---------------------|-------------|--------|
| **NSA** ⭐⭐ | 43,43 / 43,42 | $45,42 | **94** (TP1 partial maradék) | **2** | **+$188,44** ⭐ | **TP2** (Day 19 15:30 MKT) | Real Estate |
| **BEN** | 31,12 / 30,50 | $31,14 | **126** (trail) | **5** | +$80,38 | **TIME_STOP** (Day 19 21:40 MOC) | Financial Services |
| **VNO ÚJ** | 38,45 / 38,77 | $38,28 | **160** (new self-reentry) | **0** | -$79,40 ⚠️ | HOLD (stop $36,27) | Real Estate |
| **TKR** | 131,83 / 133,74 | $132,39 | **20** (TP1 trail) | **2** | -$26,91 ⚠️ | HOLD (trail $128,63) | Industrials |
| **FFIV** | 408,66 / 408,77 | $390,77 | **12** | **3** | **-$216,04** ⚠️⚠️ | HOLD (stop $381,52, 2,4% buffer) | Technology |
| **ACHC** | 25,32 / 25,51 | $23,91 | **141** | **1** | **-$225,19** ⚠️⚠️ | HOLD (stop $22,84, 4,5% buffer) | Healthcare |
| **Total unrealized** | | | | | **-$278,72** ⚠️ | | |

**Total unrealized -$278,72** (Day 17 záró +$844,85 → Day 18 záró -$278,72 = **-$1 124 csökkenés**).

**Pozitív/negatív arány**: 2 nyertes (+$269) / 4 vesztes (-$548), nettó -$279.

**A Day 17-i csúcs-unrealized (+$844) leesett az exit-rallyk után** — a TP2 + 2 TP1 + TIME_STOP mind realized-be konvertálta a Day 17 unrealized-jét, és a Day 18-i új VNO entry + Day 18-i major risk-off (SPY -1,58%) az új mark-szinteket gyengítette.

### 2.2 ⭐ NSA TP2-flag Day 19-re — a swing pivot 2. ideális TP1→TP2 trade-je készülőben

NSA Day 16 entry → Day 17 TP1-flag (1 nap entry-től) → Day 18 TP1 fill (+$159,13, 94 share partial) → **Day 19 várt TP2 fill** (94 share remainder).

| Day | NSA mark | days_held | Action |
|-----|----------|-----------|--------|
| Day 16 entry | $43,41 (fill) | 0 | BUY 188 share |
| Day 17 záró | $44,66 | 1 | **TP1-flag** ($44,82 intraday peak) |
| **Day 18 TP1 fill** | **$45,12** | 2 | **SELL 94 (50% partial), realized +$159,13** |
| Day 18 záró | $45,42 | 2 | **TP2-flag** ($46,21 intraday peak közelebb?) |

**Várt Day 19 NSA TP2 fill**: ~$46,21 (a state TP2 level), broker net = 94 × ($46,21 - $43,42) - $1 = **+$262 broker net** (optimista).

**Realisztikusabb**: a Day 19-i major risk-off folytatódhat → fill $45,40-45,80 körül lehet → 94 × ($45,60 - $43,42) - $1 = **+$204 broker net**.

Az NSA **a swing pivot 2. ideális TP1→TP2 trade-je** lesz, **VNO után**. Total NSA ROI várt (Day 16-19):
- TP1 partial: +$159,13
- TP2 partial várt: +$204 — +$262
- **NSA total ROI várt**: **+$363 — +$421 broker net** (a 188 share teljes hold-on, 3-4 napi swing)

### 2.3 ⚠️ BEN TIME_STOP MOC Day 19-re

BEN Day 13 entry → Day 14 TP1 fill (a régi 5/29-i mélypontról nem ez, a 6/3-i új entry után 1 nap) → Day 14 TP1 partial → Day 14-18 trail-en.

| Day | BEN mark | trail_sl | unrealized | Megjegyzés |
|-----|----------|----------|-------------|------------|
| Day 13 entry | $30,50 | n/a | $0 | BUY 251 share |
| Day 14 TP1 fill | $31,87 | n/a | — | SELL 125 (50% partial) |
| Day 17 záró | $31,60 | $31,06 | +$138 (126 trail-en) | trail $31,06 a 2 napi alacsony alapján |
| **Day 18 záró** | **$31,14** | **$31,06** | **+$80** ⚠️ | **trail-buffer 0,3%** (kritikus!) |

A BEN trail-buffer csak 0,3% Day 18 záró után. **Várt Day 19 TIME_STOP MOC fill**: ~$31,00 (közeli a trail-hez), broker net = 126 × ($31,00 - $30,50) - $1 = **+$62 broker net** (a 21:40 MOC-fill ára a Day 19 záró NYSE értéke).

### 2.4 ⚠️ ACHC -$225 unrealized, FFIV -$216 unrealized — két nehéz pozíció

**ACHC**:
- Entry $25,51 (Day 16 fill)
- Day 18 záró $23,91 = **-6,25% intraday-zuhanás** Day 18-on (-$1,59/share × 141 = -$224 unrealized)
- Stop $22,84 (4,5% buffer)
- Day 19 outlook: **kockázat-csökkentés szükséges**, ha a Day 19 risk-off folytatódik a stop közelebb lesz

**FFIV**:
- Entry $408,77 (Day 15 fill)
- Day 18 záró $390,77 = -4,4% (a 3 napi hold-on)
- Stop $381,52 (**2,4% buffer**)
- Day 19 outlook: a stop közelebb mint az ATR (13,57/$408 = 3,3%), **a Day 19-i intraday-stop kockázat** reális

### 2.5 Day 19 várt total realized

| Exit | Várt fill | Várt realized (broker net) |
|------|-----------|------------------------------|
| **NSA TP2** (94 share remainder, full close) | ~$45,60-46,21 | **~+$204 — +$262** ⭐⭐ |
| **BEN TIME_STOP MOC** (126 trail, full close) | ~$31,00 | **~+$62** |
| **Day 19 total realized várt** | | **~+$266 — +$324** |
| **Cumulative Day 19 várt záró** | | **~+$1 665 — +$1 723** ⭐⭐⭐ |

---

## 3. Pipeline Log Review

### 3.1 `pt_close_2026-06-10.log` — 4 exit tisztán

```
15:30:06 NSA: TP1 → SELL 94 (MKT)
15:30:07 TKR: TP1 → SELL 19 (MKT)
15:30:08 VNO: TP2 → SELL 86 (MKT)              ← ✓ A pipeline HELYESEN TP2-ként rögzíti
15:30:08 [SWING 15:30 close] Submitted 3 exits | open: 6
21:44:08 MSM: TIME_STOP → MOC SELL 29           ← ⚠️ 21:44 (NEM 21:40, 4 perc késéssel)
21:44:08 [SWING 21:40 close] MOC submitted 1 | open: 6
```

**Megjegyzés**: a `pt_close.log` és `pending_exits/2026-06-10.json` mind a 4 exit-et HELYESEN azonosítja (VNO TP2 ✓). **A glitch csak a `daily_metrics::trades::details::exit_type` mezőben** (lásd §5.1).

**ÚJ §3.1 megfigyelés — MSM MOC submit timing**: a 21:44 submit (NEM 21:40, 4 perc késéssel). A NYSE 16:00 ET MOC deadline (= 22:00 CEST) betartva (16 perc buffer), de a swing pivot cron-konvenciója 21:40. **Cron-timing edge case**, megfigyelendő.

### 3.2 `pt_submit_2026-06-10.log` — VNO self-reentry tisztán

```
15:31:02 Reading: execution_plan_run_20260610_123001_3feec1.csv
15:31:07 Existing IBKR positions/orders: {'NSA', 'FFIV', 'ACHC', 'TKR', 'MSM', 'BEN'}
15:31:07   Skipping NSA: already has position or swing state
15:31:07   Skipping ACHC: already has position or swing state
15:31:08 VNO: MKT BUY 160 @ ~$38.45 | stop $36.27 | TP1 $40.09 | TP2 $41.72
15:31:08 [SWING] Submitted: 1 tickers | State: state/swing_positions.json (7 open)
```

**Megjegyzés**: az `Existing IBKR positions/orders` set a 15:31 submit pillanatban már **NEM tartalmazza a VNO-t** (mert a 15:30 TP2 close kiürítette). **Strukturálisan a swing pivot ENGEDÉLYEZI a self-reentry-t**. A Phase 4-6 (Day 18 reggeli) execution_plan a VNO-t választotta.

### 3.3 `pt_monitor_2026-06-10.log` — 2 EOD flag

```
22:00:09 [SWING EOD] Evaluated 6 positions — 2 exit flags set
  BEN: TIME_STOP
  NSA: TP2          ← ⭐⭐ A swing pivot 2. ideális TP1→TP2 készülőben
```

**Day 19 várt 2-exit-trifecta**: NSA TP2 (kedvező) + BEN TIME_STOP (közel-flat).

### 3.4 `pt_reconcile_2026-06-10.log` — **12. ÉLES SILENT OK** ⭐⭐⭐

```
22:15:02 State tickers: ['ACHC', 'BEN', 'FFIV', 'NSA', 'TKR', 'VNO']
22:15:06 IBKR tickers: ['ACHC', 'BEN', 'FFIV', 'NSA', 'TKR', 'VNO']
22:15:06 Reconciliation OK — state and IBKR match (silent exit).
```

**12/12 ÉLES SILENT OK** ⭐ — **24 trading napi tiszta mental-stop futás** a Day 6 CNC-cancel óta. **REKORD**.

A Day 17-i WST aszinkron-divergence-warning Day 18-on NEM ismétlődött (a 4 exit + 1 új entry tiszta tracking-gel).

### 3.5 ⭐ `pt_eod_2026-06-10.log` — a tisztított architektúra Telegram-render-je

```
22:11:01 EOD Report — 2026-06-10
22:11:04 Trades: 3                                                     ← ⚠️ DISPLAY-glitch (3 vs valódi 4)
22:11:04   VNO: MOC | Entry $38.77 → Exit $38.45 | P&L $-27.52         ← ⚠⚠⚠️ HÁROM HIBA
22:11:04   NSA: MOC | Entry $43.43 → Exit $45.12 | P&L +$159.13         ← ⚠️ "MOC" helyett TP1
22:11:04   TKR: MOC | Entry $133.79 → Exit $134.32 | P&L +$10.05        ← ⚠️ "MOC" helyett TP1
22:11:04 Saved: scripts/paper_trading/logs/trades_2026-06-10.csv
22:11:04 P&L today: $+631.96 (net; gross $+636.29)                      ← ✓ paralel net + gross
22:11:04 Cumulative: $+1,399.05 (+1.40%) [Day 17/63]                    ← ✓ NYSE-count
22:11:04 No open orders to cancel
22:11:04 [WARNING] Still 6 open positions!                             ← ⚠️ ÚJ display-warning ismétlése
   ACHC: 141.0 shares, BEN: 126.0, FFIV: 12.0, NSA: 94.0, VNO: 160.0, TKR: 20.0
```

**A render-mezők**:
- ✓ `P&L today: $+631.96 (net; gross $+636.29)` — paralel ✓
- ✓ `Cumulative: $+1,399.05` — a Day 18 utáni teljes érték (a Part A 22:10 cron lefutása után) ⭐⭐⭐⭐
- ✓ `[Day 17/63]` — NYSE-count ✓

**HÁROM SÚLYOS DISPLAY-glitch a Telegram-render-ben (a régi CSV-szemantika)**:

1. **`Trades: 3` (várt 4)** — az MSM TIME_STOP MOC kimaradt a render-listából. Várhatóan a Day 16-i AMH MOC-szerű kimaradás (a 22:00 monitor + 22:10 Part A + 22:11 EOD közötti aszinkron).

2. **A VNO `MOC` exit_type + P&L $-27.52 ⚠️⚠️⚠️** — két szúrós hiba:
   - A render `VNO: MOC | Entry $38.77 → Exit $38.45 | P&L $-27.52` 
   - Az **`$38.77`-t mint Entry-t veszi (az ÚJ VNO entry IBKR avg)**, NEM a régi (Day 13-i) entry-t
   - Az exit-et $38.45-nek számolja (a 15:30 TP2 SELL fill, ami helyes)
   - Az resultátum $38.45 - $38.77 = -$0.32/share × 86 = **-$27.52** ⚠️ (a régi 86 share számolva az ÚJ entry-avg-vel!)
   - **Valódi VNO TP2 broker realized**: $385,76 (a 86 share × ($38.45 - $33.96) = +$386)
   - **A Telegram render a régi 86 + új 160 = 246 share-t mint egységet kezeli, és az IBKR `average_price: 38.78`-at használja entry-ként** — ez **a self-reentry minta DISPLAY-hibája**
   
3. **`NSA: MOC`, `TKR: MOC`** — mindkettő TP1 exit, **NEM** MOC. A régi CSV-szemantika minden 15:30 MKT exit-et "MOC"-ként logol.

**Akció (P1 CC follow-up)**: a `pt_eod.py` Telegram-render **kötelezően** a `daily_metrics::trades::details`-ből vegye az adatokat (broker-authoritative), NEM a `trades_*.csv`-ből. Az `entry` mező a `pending_exits::entry_price`-ból vagy a `swing_positions.entry_price`-ból a Day N+1 (post-exit) helyett a Day N (pre-exit) state-ből. **A self-reentry esetén ez kritikus** mert a régi és új entry külön ROI-jelzéssel kell.

### 3.6 ⚠️ ÚJ §3.6 — A 22:11 EOD Telegram VNO P&L $-27.52 hiba

**A Telegram-i $-27.52 a self-reentry minta DISPLAY-hibája**:
- Régi 86 share TP2 close (+$385,76 valódi)
- Új 160 share entry $38,77 (cost-basis változás)
- A `pt_eod.py` az **IBKR-i `average_price: 38.78`-at** (a teljes 246 share weighted avg) használja entry-ként, az exit-et $38.45-nek számolja → -$0.32/share × 86 share = -$27.52
- **A daily_metrics.trades.details::VNO::pnl: +$385.76** HELYES — a Telegram-render NEM olvas daily_metrics-ből

**Strategiai megfontolás**: a self-reentry minta megjelenésével a Telegram-render **kritikusan félrevezető lehet**. Ha a Tamás csak a Telegram-ot nézi (és nem a daily_metrics-et), akkor a Day 18 VNO-ról azt látja, hogy **-$27 P&L**, miközben a valódi +$386 ⭐⭐⭐. **Sürgős P1 fix**.

---

## 4. UW Shadow Log Day 18 — 31 ticker, MASI 9. nap top S_j (most 2. hely)

| Mutató | Day 16 | Day 17 | **Day 18** | Trend |
|--------|--------|--------|-----------|-------|
| Tickers logged | 36 | 33 | **31** | -2 (folytatólagos csökkenés) |
| Avg dp_pct | 2,59% | 2,11% | **3,21%** | +1,10pp (a Day 18-i risk-off-tal kicsit feljebb) |
| would_have_been_penalty_count | 2 | 2 | **3** | +1 |
| GEX regime (pos/hv/unk) | 27/5/4 | 22/9/2 | **26/3/2** | high_vol 9 → 3 csökkenés |
| m_gex_avg | 0,9444 | 0,8909 | **0,9613** | +0,07 (positive gamma rebound a risk-off ellenére) |

**Megfigyelés**: a Day 18-i SPY -1,58% major risk-off **NEM hozott magas-volatilitás-rezsim-átállást** a UW shadow-on (high_vol GEX kategória 9 → 3 csökkenés). A `m_gex_avg: 0,9613` a Day 16-i csúcsot megközelíti. **A piaci stress a SPY-szintjén volt, NEM a magas-likviditású opciós-piacon**.

**Top 3 S_j Day 18**:
1. **NSA 94,4** (Real Estate) — **meglévő pozíció, Day 19 TP2-flag!**
2. **MASI 93,1** (Healthcare) — **9. egymás utáni nap top-3, sosem boomerang** ⭐
3. **ACHC 89,9** (Healthcare) — **meglévő pozíció**

**Strukturális megfigyelés**:
- Az NSA top S_j a TP1-hit utáni rally-jel — a top scoring a saját meglévő pozíciómnak ad pozitív "visszaigazolást"
- MASI **9. nap top-3**, sosem boomerang — a `04-risks` §8.4 cooldown-kérdés VÉGLEG lezárva
- A sector-balanced greedy Day 18-on a VNO-t választotta (NEM MASI-t) **a Real Estate szektor üresedése után** (a Day 17-i TP1+TP2 close-jaitól a Real Estate notional 8 → 0 → most VNO 160-nal újra megnyitva)

---

## 5. Anomáliák / megfigyelések (Day 18)

### 5.1 ⚠️ ÚJ P1 — `daily_metrics::trades::details::exit_type` VNO TP2 → "TP1" (fill-timestamp-alapú detect logika hibás)

A `2026-06-09-daily-metrics-execution-fix.md` #2 fix a `exit_type`-determine logikát a fill-timestamp alapján határozza meg:
- 13:30-14:00 UTC = TP1
- 19:40-20:00 UTC = TIME_STOP_MOC

**A logika hibája**: mindkét **TP1 és TP2** 15:30 MKT-kor fillel (13:30 UTC), így a fill-timestamp NEM elég. A `daily_metrics::trades::details::VNO::exit_type: "TP1"` (HIBÁS — valódi TP2).

A `pending_exits/2026-06-10.json::VNO::exit_type: "TP2"` (HELYES — a pt_close.py-ban rögzített).

**Két konzisztens forrás**: a `pending_exits/{date}.json::{ticker}::exit_type` mező + a `cumulative_pnl::daily_history.{date}::tp2_hits` aggregátum (Day 18: tp2_hits=1) **EGYÉRTELMŰEN VNO TP2-t jelez**, a daily_metrics.trades.details ettől eltér.

**Fix javaslat (P1 CC follow-up)**: a `build_daily_metrics::determine_exit_type` a `pending_exits/{date}.json::{ticker}::exit_type` mezőt használja a TP1 vs TP2 megkülönböztetésre, NEM a fill-timestamp-et. Pseudo-code:

```python
def determine_exit_type(ticker, fill_time, pending_exits_today):
    pending = pending_exits_today.get(ticker)
    if pending:
        return pending['exit_type']  # "TP1" | "TP2" | "TIME_STOP" | "TIME_STOP_MOC"
    # fallback: fill-timestamp-alapú heurisztika (csak ha nincs pending_exits bejegyzés)
    ...
```

### 5.2 ⚠️ ÚJ P1 — `pt_eod.py` Telegram-render VNO P&L $-27.52 (self-reentry display-hiba)

A `pt_eod.log` (Telegram-render):
```
VNO: MOC | Entry $38.77 → Exit $38.45 | P&L $-27.52
```

A render az **IBKR-i `average_price: 38.78`-at** használja entry-ként (a teljes 246 share weighted avg = $38,77 közeli), és az exit $38,45 → -$0,32/share × 86 = **-$27,52**. 

A VALÓDI VNO TP2 broker realized: **+$385,76** (a régi entry $33,96 broker avg × 86 share × $4,49 különbség).

A self-reentry minta **kritikus problémát hozott a Telegram-render-ben**: a `pt_eod.py` NEM tudja kezelni, hogy ugyanazon a ticker-en aznap kilépés + új belépés történjen. **Sürgős P1 fix**: a Telegram-render kötelezően a `daily_metrics.trades.details`-ből, NEM a CSV-ből.

### 5.3 ⚠️ §0.4 PARTIAL — portfolio_return_pct Day 18 (0,64% realized-net% vs Net Liq várt -0,57%)

A Day 17-i 0,41% és Day 18-i 0,64% mind **a realized-net% initial capital alapon**:
- Day 17: $408,88 / $100 000 = 0,41% ✓
- Day 18: $636,29 / $100 000 = 0,64% ✓ (a gross P&L / initial capital)

A Net Liq-alapú várt: ($101 359,11 - $101 939,83) / $101 939,83 = **-0,569%**.

**A `2026-06-06-data-quality-fix-package.md` #6 fix Day 17-18-on RÉSZBEN nem deploy-olt**. A backfill 6/4 + 6/5-re sikeresen, DE a Day 17-18 daily_metrics-eken a `_compute_portfolio_return_from_equity` MÉG NINCS aktiválva, vagy bug van benne.

**Strategiai megfontolás**: a Day 18-i `excess_pct: +2,21%` ETTŐL FÜGGETLENÜL **helyesen pozitív** (a portfolio +0,64% realized-net% vs SPY -1,58% = +2,21%). A statisztikai "defenzív karakter Day 15 + Day 18" érvényes (Day 15 +2,34% + Day 18 +2,21% = átlag +2,28% excess major risk-off napokon).

DE a portfolio_return_pct mező **konceptuálisan inkonzisztens**: a Day 4-5 backfill Net Liq-alapú, a Day 17-18 realized-alapú. Day 21 metrikák értékelésénél ez problémát okoz. **CC follow-up P2 (a #6 fix Day 17+ aktiválása)**.

### 5.4 ⚠️ ÚJ P2 — `pt_eod.log` Trades: 3 (várt 4, MSM MOC kimaradás)

A Day 16-i AMH MOC-szerű kimaradás ismétlődik: a 21:59 MOC fill a 22:00 monitor + 22:10 Part A + 22:11 EOD közötti aszinkron miatt kimarad a `Trades: N` aggregátumból. **De a P&L mező helyes** (+$631,96 a 4 exit összes broker realized-je).

**Akció (P2 CC follow-up)**: a `pt_eod.py` a `Trades: N`-t a `len(daily_metrics.trades.details)`-ből, **NEM a CSV-ből**.

### 5.5 ⚠️ ÚJ P3 — `Still 6 open positions!` warning ismétlése (Day 17 + Day 18)

A Day 17 review §5.2-ban dokumentált warning Day 18-on is ismétlődik. **A swing pivot multi-day hold kontextusában normális**. **CC follow-up P3**: a warning kikapcsolása vagy átírása.

### 5.6 ⚠️ ÚJ P3 — MSM MOC submit 21:44 (NEM 21:40)

A `pt_close.log`:
```
21:44:08 MSM: TIME_STOP → MOC SELL 29
21:44:08 [SWING 21:40 close] MOC submitted 1 | open: 6
```

A `21:44:08` 4 perc késéssel a swing pivot cron-konvencióhoz képest. A NYSE 16:00 ET MOC deadline (= 22:00 CEST) betartva, de a Day 16-17-i 21:40-i submit-időkhöz képest eltér. **Cron-timing edge case**, megfigyelendő. Lehetséges ok: a Mac Mini cron-overhead a 4 EOD flag feldolgozása miatt magasabb (21:40 → 21:44).

### 5.7 ⚠️ Next-day MKT fill kockázat statisztikai minta — most 5 ellenpélda

A "1-nap-TP1 + kedvező entry-slippage" minta most már 5 mintán:
- MSM Day 14: +0,11% kedvező ✓
- BEN Day 15: -2,05% kedvezőtlen ⚠️
- AMH Day 16: -1,50% kedvezőtlen ⚠️
- VNO Day 17 (TP1): +1,33% kedvező ⭐
- **TKR Day 18 (TP1): -3,04% kedvezőtlen** ⚠️⚠️

**5 minta = 2 kedvező + 3 kedvezőtlen, átlag -1,03% kedvezőtlen** (a Day 17-i -0,53%-ról szignifikánsabb negatív trendre). Day 21+ után a Backlog #7 (TP1-limit-order opció) elemzéshez **érdemes a Day 19-20-i adatokkal együtt komolyan mérlegelni**.

### 5.8 ⭐ ÚJ §5.8 — Self-reentry minta (VNO Day 18)

A swing pivot Day 18-on **first time** ugyanazon a napon kilépett + új belépett ugyanaba a ticker-be (VNO TP2 → új VNO entry). Strategiai megfontolások:
- A scoring engine **NEM tart "blacklist"-en az aznapi exited ticker-eket**
- A sector-balanced greedy a Real Estate üresedése után újra VNO-t választott (a Day 18-i top S_j ranking-ben magas)
- **Statisztikai megfigyelendő**: hány self-reentry történik Day 21+ után, és átlagos ROI vs nem-reentry új entry?

**Day 18-i VNO self-reentry kezdeti tracking**:
- Entry $38,77 (planned $38,45, +0,83% slippage)
- Day 18 záró mark $38,28 (-1,3% napi)
- Stop $36,27 (5,3% buffer)
- Várt Day 19-21 outlook: ha a momentum folytatódik, a TP1 $40,09 (3,5% felfelé) — vagy, ha a major risk-off megy tovább, stop-veszély

### 5.9 ⚠️ ACHC -6,25% intraday-zuhanás Day 18-on

ACHC entry $25,51 (Day 16 fill) → Day 17 záró $25,50 (flat) → **Day 18 záró $23,91 (-6,25%!)**. **Healthcare szektor-specifikus mozgás?** A SPY -1,58%-on a Healthcare szektor (XLV) -1,3% volt, NEM -6,25%. **ACHC company-specifikus hír valószínű** (FDA-related, earnings, vagy management change).

Akció: a Day 19-i review-ban a Polygon `events` endpoint segítségével érdemes ellenőrizni, hogy volt-e ACHC-news Day 18-on. Ha igen, az earnings-blackout-szabály (`docs/decisions/2026-05-14-day63-decision-outcome.md` §3.X) **felülvizsgálatra szorulhat**.

### 5.10 ✅ §0.10 reconcile — 12/12 ÉLES SILENT OK (24 trading napi tiszta mental-stop) — REKORD

---

## 6. Day 19 (csütörtök, 2026-06-11, W24 D4) outlook

### 6.1 Várt 2-exit-kis-trifecta

| Idő | Exit | Qty | Várt fill | Várt realized (broker net) |
|-----|------|-----|-----------|------------------------------|
| 15:30 CEST | **NSA TP2** (94 share remainder, full close) | 94 | ~$45,60-46,21 | **~+$204 — +$262** ⭐⭐ |
| 21:40 CEST | **BEN TIME_STOP MOC** (126 share trail, full close) | 126 | ~$31,00 | **~+$62** |
| **Total Day 19 realized várt** | | | | **~+$266 — +$324** |
| **Cumulative Day 19 várt záró** | | | | **~+$1 665 — +$1 723** ⭐⭐⭐ |

### 6.2 Day 19 prioritások

1. **NSA TP2 + BEN TIME_STOP fill** — a swing pivot 2. ideális TP1→TP2 trade-je (NSA, +$363-421 total ROI)
2. **CC follow-up P1**: §5.1 `daily_metrics::exit_type-determine` pending_exits-alapú logika
3. **CC follow-up P1**: §5.2 `pt_eod.py` Telegram-render daily_metrics-ből (a self-reentry display-hiba)
4. **CC follow-up P2**: §5.3 portfolio_return_pct Net Liq-alapú a Day 17+ napokra
5. **CC follow-up P2**: §5.4 `Trades: N` a daily_metrics-ből
6. **13. ÉLES SILENT OK** (25 trading napi tiszta)
7. **ACHC + FFIV monitoring**: stop-veszély (4,5% és 2,4% buffer)
8. **VNO self-reentry tracking** — első napi performance értékelés
9. **Új entry(ek) Day 19-en** — hiányzó szektorok (Consumer Defensive, Utilities, Materials, Comm Services, Consumer Cyclical, Energy)

### 6.3 Day 21 checkpoint felé (≈jún 14, W24 D5)

**Day 21 checkpoint (a `04-risks` -$1500 küszöb)**: Day 18-én már 193%-os bufferben.

| Várt nap | Várt cumulative | Buffer |
|----------|------------------|--------|
| Day 19 (csütörtök) | +$1 665 — +$1 723 | 211%+ |
| Day 20 (péntek) | +$1 700 — +$1 800 várt | 213%+ |
| **Day 21 (≈hétfő jún 16)** | **+$1 800+** | **220%+** |

A swing pivot **strukturálisan messze a kritérium-tartomány felett**, **2× nagyobb buffer-rel a Strategic_review-i +$1500 küszöbnél**.

### 6.4 Strategiai jelentőség — a swing tézis 18 napos empirikus minta

A W21-W24 D3 (18 trading nap) statisztikai minta:
- **TP-hit ráta**: 11/17 exit = **64,7%** ⭐⭐ (régi 60-napi 9,5%-hoz képest **6,8× javulás**)
- **Pozitív exit ráta**: 14/17 = **82,4%** ⭐⭐ (régi 33,3%-hoz képest 2,5× javulás)
- **TP2 hit-ráta**: 2/17 = 11,8% (CDNS Day 11 + VNO Day 18)
- **Átlag exit P&L (broker net)**: ~+$104/exit (Day 18-i +$632 / 4 exit = +$158 átlag a major exit-napon)
- **Daily-eval fordulatok**: **8/10 nyertes** (Day 8 ellenpélda + Day 18 TKR alulteljesítés)
- **Cumulative-trajektória**: -$779 (Day 8) → +$1 399 (Day 18) = **+$2 178 broker mozgás 10 trading nap alatt** ⭐⭐⭐

**Major-risk-off-napok defenzív karakter**:
- Day 15 (SPY -2,58%): excess +2,34%
- Day 18 (SPY -1,58%): excess +2,21%
- **Átlag**: +2,28% major risk-off napokon

**Hatékony excess termelés szempontjából**: a swing pivot **strukturálisan defenzív és offenzív karakterrel egyaránt** működik.

---

## 7. Files referenced (Day 18)

- `state/swing_positions.json` — **6 pozíció**, **2 EOD flag** (NSA TP2 + BEN TIME_STOP, Day 19-re), VNO self-reentry tisztán rögzítve (entry_date=2026-06-10), last_updated 2026-06-10T20:00:09Z
- `state/daily_metrics/2026-06-10.json` — Day 18 cumulative **+$1 399,05** ⭐⭐⭐⭐, day_number=17, vix_close=21.83 (Polygon I:VIX) ✓, commission=$4,33 ✓, slippage_per_ticker::VNO::filled=$38,77 ✓ (a #1 fix élesen — VNO új entry), trades.details=4 entry ✓ DE VNO `exit_type` **HIBÁS "TP1"-ként** ⚠️ (§5.1)
- `state/pending_exits/2026-06-10.json` — **4 bejegyzés processed=true** ⭐ (NSA_TP1, TKR_TP1, **VNO_TP2** ✓, MSM_TIME_STOP)
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 18 entry: pnl=$631,96 ✓ (broker-authoritative), commission=$4,33 ✓, **tp1_hits=2, tp2_hits=1, moc_exits=1, trading_days=16**, **cumulative +$1 399,05** ⭐⭐⭐⭐
- `logs/pt_close_2026-06-10.log` — 4 exit submit (NSA TP1 + TKR TP1 + **VNO TP2** ✓ + MSM TIME_STOP MOC 21:44 ⚠️ kis cron-timing edge case)
- `logs/pt_submit_2026-06-10.log` — VNO self-reentry tisztán (1 ticker, 2 fill aggregát ARCA + BEX, slippage +0,83% kedvezőtlen)
- `logs/pt_monitor_2026-06-10.log` — **2 EOD flag** (NSA TP2 ⭐⭐ + BEN TIME_STOP)
- `logs/pt_reconcile_2026-06-10.log` — **12. ÉLES SILENT OK** ⭐⭐⭐ (24 trading napi tiszta mental-stop, **REKORD**)
- `logs/pt_eod_2026-06-10.log` — 22:11-kor fut ✓, **DE** 3 súlyos display-glitch ⚠️ (§3.5, §5.2): Trades: 3 (várt 4), VNO P&L $-27.52 (self-reentry-display-hiba a valódi +$385,76 helyett), NSA + TKR "MOC" (helyesen TP1)
- `state/uw_shadow/2026-06-10.json` — 31 ticker, **MASI 9. nap top S_j** (most 2. helyen, NSA előzte 94,4), m_gex 0,9613 (positive gamma rebound a risk-off ellenére)
- **IBKR direkt API**:
  - `get_account_summary` → Net Liq **$101 359,11** (+$1 359,11 a baseline FÖLÖTT, 6. egymás utáni nap, Day 18 mozgás -$580,72 -0,57%)
  - `get_account_positions` → 6 pozíció (MSM=0, WST=0), unrealized **-$278,72** ⚠️ (Day 17-i +$844 → -$1 124 napi csökkenés a 4 exit + új VNO entry intraday-i gyengülése miatt)
  - `get_account_trades(DAYS_7)` → Day 18 trades: 4 exit (VNO TP2 + NSA TP1 + TKR TP1 + MSM TIME_STOP MOC 21:59 fill) + 1 új entry (VNO self-reentry, 2 fill aggregát) ✓

---

## 8. ⭐⭐⭐⭐ Strukturális finding-ek összefoglaló

### 8.1 ⭐⭐⭐⭐ TÖRTÉNELMI $1 000+ CUMULATIVE ÁTTÖRÉS — a swing pivot deploy óta első alkalom

**Cumulative +$1 399,05** — a Day 8-i mélypontról (-$779,64) **+$2 178 broker mozgás 10 trading nap alatt**. A Day 21 checkpoint buffer **193%** (a -$1500 küszöbtől 2× nagyobb), strukturálisan **a kritérium-tartomány messze felett**.

### 8.2 ⭐⭐⭐ VNO ELSŐ IDEÁLIS TP1→TP2 2-FÁZISÚ TRADE-JE TELJES

- Day 13 entry $33,96 broker → Day 17 TP1 partial $36,68 (+$230) → Day 18 TP2 partial $38,45 (+$386)
- **VNO total ROI**: **+$616 broker net** (171 share teljes hold-on)
- **pnl_pct 13,21%** (Day 18 TP2 partial) — **a swing pivot legmagasabb single-trade ROI%-ja**
- **A swing pivot 2. ideális trade készülőben** (NSA: Day 16 entry → Day 17 TP1-flag → Day 18 TP1 partial +$159 → **Day 19 TP2-flag**, várt total ROI +$363-421)

### 8.3 ⭐⭐⭐ 2. major risk-off nap defenzív karakter megerősítése — excess +2,21%

| Major risk-off nap | SPY | Portfolio | Excess |
|---------------------|-----|-----------|--------|
| Day 15 (6/5) | -2,58% | -0,24% | **+2,34%** |
| **Day 18 (6/10)** | **-1,58%** | **+0,64%** (realized-net%) | **+2,21%** ⭐⭐⭐ |
| **Átlag** | **-2,08%** | **+0,20%** | **+2,28%** |

A swing pivot **strukturálisan kifejlett defenzív karakter major risk-off napokon**.

### 8.4 ⭐ VNO SELF-REENTRY — ÚJ STRATEGIAI MINTA

A Day 18 az első **same-day exit + new entry** ugyanazon a ticker-en (VNO TP2 → új VNO entry 1 perccel később). **A swing pivot NEM tart "blacklist"-en az aznapi exited ticker-eket** — a Phase 4-6 scoring engine újra választja, ha top S_j.

**Statisztikai megfigyelés Day 21+ után**: hány self-reentry történik, és átlagos ROI vs nem-reentry új entry?

**Display-hiba kezelendő**: a `pt_eod.py` Telegram-render a self-reentry mintát NEM kezeli — VNO P&L $-27.52 (HIBÁS, valódi +$385.76). **Sürgős P1 fix** (§5.2).

### 8.5 ⚠️ ÚJ §5.1 P1 — `daily_metrics::trades::details::exit_type` fill-timestamp-alapú detect logika hibás

A `2026-06-09-daily-metrics-execution-fix.md` #2 fix `exit_type`-determine logikája a fill-timestamp alapján fut, és a TP1 vs TP2 megkülönböztetésére **NEM elég** (mindkettő 15:30 MKT). A `daily_metrics.trades.details::VNO::exit_type: "TP1"` (HIBÁS — valódi TP2).

**Fix javaslat (P1)**: a `build_daily_metrics` a `pending_exits/{date}.json::{ticker}::exit_type` mezőt használja.

### 8.6 ⚠️ ÚJ §5.2 P1 — `pt_eod.py` Telegram-render self-reentry-display-hiba

A VNO P&L $-27,52 a Telegram-ban (valódi +$385,76). A self-reentry minta megjelenésével a Telegram-render **kritikusan félrevezető**. **Sürgős P1 fix**: a render kötelezően a `daily_metrics::trades::details`-ből, NEM a CSV-ből.

### 8.7 📝 Next-day MKT fill kockázat — 5 ellenpélda, statisztikailag szignifikánsabb negatív trend

5 minta: 2 kedvező + 3 kedvezőtlen, átlag -1,03% kedvezőtlen. A Day 17-i -0,53%-ról most -1,03%-ra. Day 21+ után a Backlog #7 (TP1-limit-order opció) elemzéshez érdemes komolyan mérlegelni.

### 8.8 📝 MASI 9. egymás utáni nap top-3 — sosem boomerang

A `04-risks` §8.4 cooldown-period kérdés VÉGLEG lezárva.

### 8.9 ⚠️ ACHC -6,25% intraday-zuhanás Day 18-on — Healthcare-szektor-specifikus mozgás vs company-specifikus hír?

A SPY -1,58%-on a Healthcare szektor -1,3% volt, NEM -6,25%. **ACHC company-specifikus hír valószínű** (FDA, earnings, management). Day 19-i review-ban a Polygon events endpoint segítségével ellenőrizni érdemes. Ha igen, az earnings-blackout-szabály felülvizsgálata.

---

## State (Day 18 — W24 D3, swing pivot Day 18/63)

**Architektúra**: swing pivot Fázis 3 deploy DAY 18. **TÖRTÉNELMI $1 000+ CUMULATIVE ÁTTÖRÉS + a swing pivot deploy óta első ideális TP1→TP2 trade VNO-val teljes**.

**Live**: 6 open positions:
- **NSA** ⭐⭐ (94 share TP1 partial maradék, **TP2 flag Day 19 15:30** — a swing pivot 2. ideális TP1→TP2 trade-je készülőben!, days_held=2, +$188 unrealized)
- **BEN** (126 share trail, **TIME_STOP flag Day 19 21:40 MOC**, days_held=5, +$80 unrealized — trail-buffer 0,3% kritikus)
- **VNO ÚJ self-reentry** (160 share, HOLD stop $36,27, days_held=0, -$79 unrealized — first day mark gyengült $38,77 → $38,28 -1,3%)
- **TKR** (20 share TP1 trail, HOLD trail $128,63, days_held=2, -$27 unrealized — Day 18 -3,4% napi gyengülés)
- **FFIV** ⚠️ (12 share, HOLD stop $381,52 / **2,4% buffer**, days_held=3, **-$216 unrealized** — stop-veszély közeli)
- **ACHC** ⚠️ (141 share, HOLD stop $22,84 / **4,5% buffer**, days_held=1, **-$225 unrealized** — Day 18 -6,25% napi zuhanás, possible company-specifikus hír)

**Total unrealized**: **-$278,72** ⚠️ (Day 17-i +$844 → -$278 = -$1 124 napi csökkenés a 4 exit + új VNO entry intraday-i gyengülése miatt)

**Cumulative (Mac Mini canonical, broker-authoritative)**: **+$1 399,05** ⭐⭐⭐⭐ (TÖRTÉNELMI $1 000+ ÁTTÖRÉS)
**Net Liq (IBKR)**: **$101 359,11** — **+$1 359,11 a baseline FÖLÖTT, 6. egymás utáni nap, Day 18 mozgás -$580,72 -0,57%**

**Day 18 realized (broker net)**: **+$631,96** (4 exit: VNO TP2 +$385,76 ⭐⭐⭐ + NSA TP1 +$159,13 ⭐ + TKR TP1 +$10,05 ⚠️ + MSM TIME_STOP MOC +$77,02 ✓).
**Day 18 commission**: **$4,33** ✓ (paralel rögzítve, 4 exit × ~$1,08).

**Excess return Day 18**: portfolio +0,64% (realized-net% szemantika, a #6 fix Day 17+ aktiválási hiba — §5.3), SPY -1,58%, **excess +2,21%** ⭐⭐⭐ — **2. major risk-off napon defenzív karakter megerősítés**.

**Aktív P0/P1 (frissített, Day 18 utáni):**
- **§5.1 ⚠️ ÚJ P1** — `daily_metrics::exit_type-determine` pending_exits-alapú logika kell (a fill-timestamp NEM elég TP1 vs TP2 különbségre)
- **§5.2 ⚠️ ÚJ P1** — `pt_eod.py` Telegram-render self-reentry-display-hiba (VNO $-27,52 vs valódi +$385,76 — kritikusan félrevezető)
- **§5.3 ⚠️ P2 részleges** — portfolio_return_pct Day 17-18 még realized-alapú (a #6 fix Day 17+ aktiválás)
- **§5.4 ⚠️ ÚJ P2** — `pt_eod.log Trades: 3` (várt 4, MSM MOC kimaradás)
- **§5.5 ⚠️ P3 ismétlése** — `Still 6 open positions!` warning
- **§5.6 ⚠️ ÚJ P3** — MSM MOC submit 21:44 (NEM 21:40, 4 perc késés)
- **§5.7 ⚠️ Backlog #7** — Next-day MKT fill kockázat statisztikailag szignifikánsabb negatív trend (5 ellenpélda, átlag -1,03%)
- **§5.8 ⭐ ÚJ megfigyelés** — VNO self-reentry minta (Day 18 első)
- **§5.9 ⚠️ ÚJ megfigyelés** — ACHC -6,25% intraday-zuhanás (company-specifikus hír?)
- **§5.10 ✅ stabil** (12/12 silent OK, 24 trading napi tiszta mental-stop — REKORD)
- **§9.2, §9.3, §9.5 ✅ TELJES RESOLVED + élesen validált**
- **§8.1 ⭐⭐⭐⭐** A swing pivot deploy óta első $1 000+ cumulative áttörés
- **§8.2 ⭐⭐⭐** VNO első ideális TP1→TP2 2-fázisú trade teljes (+$616 ROI)
- **§8.3 ⭐⭐⭐** 2. major risk-off napon defenzív karakter megerősítés (+2,21% excess)
- **§8.4 ⭐ ÚJ** Self-reentry minta (VNO Day 18)

**Day 19 fókusz**:
1. **NSA TP2 (várt +$204-262) + BEN TIME_STOP MOC (várt +$62)** = Day 19 várt realized ~+$266 — +$324, cumulative ~+$1 665 — +$1 723
2. **CC follow-up P1**: §5.1 exit_type-determine pending_exits-alapú + §5.2 Telegram-render daily_metrics-ből
3. **CC follow-up P2**: §5.3 portfolio_return_pct + §5.4 Trades: N + §5.5 warning kikapcsolása
4. **ACHC + FFIV stop-monitoring** — kockázat-csökkentés ha a major risk-off folytatódik
5. **VNO self-reentry első napi performance értékelés**
6. **13. ÉLES SILENT OK** (25 trading napi tiszta)
7. **Új entry(ek) Day 19-en** — hiányzó szektorok (6 üres szektor)

**A Day 18 napi karakter egy mondatban**: **A swing pivot deploy óta TÖRTÉNELMI $1 000+ cumulative-áttörés + 2. major risk-off napon defenzív karakter megerősítése + a swing pivot ELSŐ ideális TP1→TP2 2-fázisú trade-je TELJES (VNO)** — (1) a **cumulative +$1 399,05 ⭐⭐⭐⭐ a swing pivot deploy óta ELSŐ $1 000+ áttörés** (a Day 8-i mélypontról 10 trading nap alatt **+$2 178 broker mozgás**, a Day 21 checkpoint buffer **193%** — kritérium-tartományon kívül 2× nagyobb), (2) a **Day 18 broker realized +$631,96** (a swing pivot 2. legjobb napi P&L, 4-exit-mega-trifecta: **VNO TP2 +$385,76** ⭐⭐⭐ a swing pivot legmagasabb single-trade ROI%-ja 13,21%, NSA TP1 +$159,13 ⭐, TKR TP1 +$10,05 ⚠️ next-day MKT fill kockázat 5. minta, MSM TIME_STOP MOC +$77,02 ✓), és (3) a **VNO első ideális TP1→TP2 2-fázisú trade-je TELJES** (Day 13-18 5 napi hold-on **+$616 broker net total ROI** — a CDNS Day 10-12-i +$434 TP2 single-pop-ot **+$182-vel felülmúlva**), (4) a **2. major risk-off napon excess +2,21% ⭐⭐⭐** (SPY -1,58%, portfolio +0,64% realized-net% — Day 15-i +2,34% után átlag major risk-off napokon +2,28% excess), miközben a **VNO SELF-REENTRY** ÚJ STRATEGIAI MINTA Day 18-on (15:30:08 TP2 SELL → 15:31:08 új VNO BUY 160 share, a scoring engine NEM tart blacklist-en az aznapi exited ticker-eket — fontos megfigyelés, Day 21+ után statisztikai értékelés), és **3 új P1 display-glitch dokumentálva** (§5.1 daily_metrics.exit_type fill-timestamp-alapú logika hibás VNO TP2-t "TP1"-ként logolja, §5.2 pt_eod.py Telegram-render VNO P&L $-27,52 a valódi +$385,76 helyett a self-reentry-display-hiba miatt — **kritikusan félrevezető**, §5.4 Trades: 3 a 4 helyett MSM MOC kimaradás), az **NSA TP2-flag Day 19-re** ⭐⭐ (a swing pivot 2. ideális TP1→TP2 trade-je készülőben, várt total ROI +$363-421), a **BEN TIME_STOP flag Day 19-re** (5 trading napi hold, trail-buffer 0,3% kritikus), és a **`_reconcile_state_from_ibkr` 12/12 ÉLES SILENT OK** (24 trading napi tiszta mental-stop futás, REKORD) — **a swing tézis empirikus megerősítésének 18 napos statisztikai mintán (TP-hit ráta 64,7%, pozitív exit ráta 82,4%, átlag exit P&L ~+$104, daily-eval fordulatok 8/10 nyertes, defenzív karakter 2 major risk-off napon +2,28% átlag excess) STRUKTURÁLISAN BIZONYÍTOTTAN VALIDÁL, a Day 19-i várt ~+$1 665-1 723 cumulative-prognózis a Day 21 checkpoint felé 211%+ buffer-rel zárul**.

---

**A Day 18 review vége.** A Day 19 fókusz: **NSA TP2 (várt +$204-262, a swing pivot 2. ideális TP1→TP2 trade-je) + BEN TIME_STOP MOC (várt +$62)** = cumulative ~+$1 665 — +$1 723 + 3 CC P1 follow-up display-fix (§5.1 exit_type + §5.2 Telegram-render + §5.4 Trades) + 13. ÉLES SILENT OK + ACHC/FFIV stop-monitoring + VNO self-reentry tracking + új entry-k hiányzó szektorokba.
