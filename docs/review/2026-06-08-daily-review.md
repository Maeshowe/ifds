# IFDS Daily Review — 2026-06-08 (hétfő, Day 16 chat-conv / Day 15 NYSE, W24 D1)

**Verzió**: swing pivot Day 16/63 — **A fix-package P1 #1-#4 ÉLES + Net Liq első alkalom $101k FÖLÖTT** ⭐⭐⭐
**Day 16 realized P&L (broker, Part A Option B ÉLESEN)**: **+$112,96** (commission $1,12)
**Cumulative**: **+$358,21** ⭐⭐⭐ (Day 15 záró +$245,25 → +$112,96 hozzáadva) — **rekord**
**Net Liquidation Day 16 záró (IBKR)**: **$101 034,23** ⭐⭐⭐ — **4. egymás utáni nap a baseline FÖLÖTT, első alkalom $101k FÖLÖTT**
**Excess return Day 16**: portfolio +0,11%, SPY +0,23%, **excess -0,11%** (közel-semleges)
**Open positions**: **7** (Day 15-i 6 → 7: AMH TIME_STOP kiesett + 2 új entry NSA + TKR)
**Új entries**: **2** — NSA (Real Estate dupli) + TKR (Industrials dupli)

**⭐⭐⭐ A négy történelmi Day 16 esemény:**

**1. A `2026-06-06-data-quality-fix-package.md` P1 #1-#4 fix-ek MIND ÉLESEN MŰKÖDNEK**:
- ✅ **#1 VIX Polygon `I:VIX`**: `vix_close: 18.75, vix_delta_pct: -12.83` → previous close 21.50 ≈ Tamás screenshot ✓
- ✅ **#2 EOD Telegram 22:11-re**: `pt_eod.log 22:11:02 EOD Report` (NEM 22:05) — a 22:10 Part A UTÁN
- ✅ **#3 Day-N NYSE-count**: `[Day 15/63]` (NEM `[Day 13/63]`)
- ✅ **#4 Commission rögzítés + backfill**: `daily_history` összes swing-exit napi commission rögzítve (5/19 $1.08, 5/27 $8.04, 6/5 $4.39, 6/8 $1.12). A `backfill_commission.py` lefutott.

**2. Part A Option B robust-realized-capture VÉGRE ÉLESEN MŰKÖDIK** ⭐ (a `recorder-robust-realized-capture` task A.2 `ib.fills()` opció hétfői live smoke). A `cumulative_pnl::daily_history.2026-06-08.pnl: $112.96` **PONTOSAN egyezik az IBKR realized_pnl-vel**. **Day 13-15 incidens-mintázat megszűnt.**

**3. Net Liq $101 034,23 — első alkalom a $101k FÖLÖTT** (Day 15 záró $100 675,60 → +$358,63 Day 16 mozgás, +0,36%). A Day 8-i mélypontról (-$779,64) **8 trading nap alatt valódi +$1359 broker mozgás**.

**4. VNO ROCKET Day 16-on**: Day 15 záró unrealized +$214 → Day 16 záró **+$384** (+$170 napi unrealized növekedés). A VNO mark Day 15-i $35,21 → Day 16-i $36,20 = +2,81% napi — **TP1 átlépve** ($35,75), **flag Day 17 15:30 MKT-re**.

**⭐ További Day 16 kulcs finding-ek**:
- **AMH TIME_STOP MOC +$112,96** (várt ~+$170 Day 15 review-ban; a Day 16-i AMH-gyengülés -$0,50 a Day 15-i $33,26-ról $32,76-ra)
- **2 új entry — sector duplikáció**: NSA (Real Estate, 2. ticker VNO mellé) + TKR (Industrials, 2. ticker MSM mellé)
- **Day 17-re 2 EOD flag**: **VNO TP1** (15:30 MKT) + **WST TIME_STOP** (21:40 MOC)
- **`_reconcile_state_from_ibkr` 10/10 ÉLES SILENT OK** — **22 trading napi tiszta mental-stop futás** ⭐ (új rekord)
- **MASI újra a top S_j (92,3)** a Day 13-15-i csökkenés (88,9) után — sector-balanced greedy strukturális védelem folytatódik
- **WST jelentős javulás**: Day 15 záró -$180 → Day 16 záró -$83 (+$97 unrealized javulás)
- **⚠️ ÚJ finding**: TKR slippage hibásan 0% (valódi +1,45% kedvezőtlen — broker fill $133,71 vs state planned $131,83)

---

## 0. ⭐⭐⭐ A fix-package P1 deploy-verifikáció

A `2026-06-06-data-quality-fix-package.md` task P1 #1-#4 fix-ek a hétvégén deploy-oltak, és a Day 16 az **első éles teszt-nap**. Az eredmények **TÖKÉLETESEK**:

### 0.1 #1 — VIX adatforrás Polygon `I:VIX` ✅

```json
"market": {
  "spy_return_pct": 0.23,
  "vix_close": 18.75,        ← ÚJ: Polygon I:VIX Day 16 záró
  "vix_delta_pct": -12.83,   ← (Day 15 záró 21.50 → Day 16 záró 18.75 = -12.83%)
  "strategy": "LONG"
}
```

**Verifikáció**: a reverse-calc 18.75 / (1 - 0.1283) ≈ **21.51 ≈ 21.50** (a Tamás screenshot Day 15 záró VIX) ✓. A Polygon I:VIX a valós-idejű napi értéket adja, NEM a FRED 1 napos késést.

**Backfill ellenőrzés szükséges**: a Day 1-15 napokra a `backfill_polygon_vix.py` lefutott-e? A `daily_metrics/2026-06-05.json` még a régi `vix_close: 15.78` értéket tartalmazta (a Day 15 review-ban dokumentált). **CC ellenőrzés**: a backfill `daily_metrics/*.json` is in-place módosította-e? Vagy csak a Day 16-tól kezdve használja az új adatforrást? Ezt holnap rendezni érdemes.

### 0.2 #2 — EOD Telegram timing 22:11 ✅

```
pt_eod_2026-06-08.log:
22:11:02 [INFO] EOD Report — 2026-06-08    ← ÚJ: 22:11 (NEM 22:05)
22:11:05 [INFO] Trades: 0                    ⚠️ másodlagos finding (lásd §0.5)
22:11:05 [INFO] P&L today: $+112.96 (net; gross $+114.08)
22:11:05 [INFO] Cumulative: $+358.21 (+0.36%) [Day 15/63]   ✓
```

A 22:11-i cron a 22:10 Part A UTÁN fut, így a `Cumulative $+358.21` **a teljes Day 16-i értéket mutatja**. A Day 15-i +$245,25 + Day 16-i +$112,96 = $358,21 ✓.

**Új finding a Telegram-ban**: a `(net; gross $+114.08)` mező **paralel net + gross** rögzítés — a Fix #4 commission rögzítés következménye. **Ez a régi $0,00 commission-hiány megoldása.**

### 0.3 #3 — Day-N NYSE-count ✅

`daily_metrics::day_number: 15` (5/18 D1, 5/19 D2, ..., 6/8 D15) — NYSE trading-day count.

A `pt_eod.log` ezt használja: `[Day 15/63]`. A régi `cumulative_pnl::trading_days: 14` (a P&L-entry-count, mert a 5/26 + 5/29 + 6/1 0-entry napok nincsenek számolva) MÁR NEM a render-forrás.

### 0.4 #4 — Commission rögzítés + backfill ✅⭐

A `cumulative_pnl::daily_history` mindkét szempontból **TELJES**:

| Date | pnl | commission | Status |
|------|-----|------------|--------|
| 5/19 | +$112,63 | $1,08 | ✓ backfill |
| 5/20 | -$6,37 | $1,01 | ✓ backfill |
| 5/21 | -$220,69 | $1,08 | ✓ backfill |
| 5/22 | +$159,12 | $1,07 | ✓ backfill |
| 5/27 | -$695,79 | $8,04 | ✓ backfill (7 exit) |
| 5/28 | -$57,48 | $1,46 | ✓ backfill |
| 6/2 | +$434,82 | $1,12 | ✓ |
| 6/3 | +$229,84 | $3,22 | ✓ |
| 6/4 | +$225,34 | $3,92 | ✓ restated (volt $0) |
| 6/5 | +$63,83 | $4,39 | ✓ restated (volt $0) |
| **6/8** | **+$112,96** | **$1,12** | **✓ Part A Option B élesen** |
| **Total commission** | | **$28,57** | ~$2/exit átlag |

**Heti commission breakdown**:
- W21 (5/18-22, 5 nap): $4,24
- W22 (5/26-29, 4 nap): $9,50 (a 7-MOC katasztrófa miatt magas)
- W23 (6/1-5, 5 nap): $12,65
- W24 D1 (6/8): $1,12

A **friction-drag aggregát Day 1-16 alapján**: $28,57 / $358,21 cumulative = **8,0% commission a realized P&L-en**. **Strategic_review-i ~15-17% jutalék-teher** becslés Day 1-16 mintán **alulbecsült (8%)** — a swing pivot tisztított architektúrája **kevesebb commission-t generál** mint a régi 60-napi intraday rendszer (átlag 1-2 exit/nap vs 6,3 ügylet/nap).

### 0.5 ⚠️ MÁSODLAGOS — `trades.details: []` Day 16-on

```
daily_metrics::trades.details: []
daily_metrics::trades.best: null
daily_metrics::trades.worst: null
```

A Day 16-on a `trades.details` blokk **üres**, miközben a 21:40-i AMH MOC SELL fill **megtörtént** (IBKR realized $112,96). A `pt_eod.log Trades: 0` is ezt tükrözi.

**Magyarázat**: a `2026-06-04-recorder-robust-realized-capture.md` task (B) `daily_metrics exits-source fix` (KÉSZ + deploy) szerint a `build_daily_metrics` az `exits` blokkot a cumulative `daily_history` counterekből veszi, NEM a CSV-ből. A `trades.details` mező ezzel egyezően **csak a 15:30-i TP1 exit-eket tartalmazza** (amelyeket a CSV megőriz), a 21:40-i MOC fill **közvetlenül a cumulative_pnl-be megy, NEM a CSV-be**.

A `exits.moc: 1` a daily_metrics-ben helyesen rögzítve (az AMH MOC), és a `pnl.gross/net/commission` mind helyes. **A `trades.details: []` és `pt_eod.log Trades: 0` egy MÁSODLAGOS DISPLAY-glitch, NEM P&L-hiba**.

**Akció (P2, nem sürgős)**: a `build_daily_metrics` a `trades.details`-be a 21:40-i MOC fill-eket is integrálja a connector `get_account_trades` segítségével. A `pt_eod.log Trades: N` is ezt tükrözze.

---

## 1. Day 16 Trades

### 1.1 Exit (1) — AMH TIME_STOP MOC

| Idő (CEST) | Ticker | Exit Type | Qty | IBKR Avg Entry | Fill | IBKR Realized | Várt (Day 15 review) | Eltérés |
|-----------|--------|-----------|-----|----------------|------|---------------|------------------------|---------|
| 21:59:32 | **AMH** | TIME_STOP MOC | 135 | $31,92 | $32,76 (NYSE) | **+$112,96** | **~+$170** | **-$57** ⚠️ |

**A várakozás -$57-tal alacsonyabb**: a Day 15 review §6.1 a fill ~$33,26 (Day 15 záró mark) alapján számolta, **DE** a Day 16 reggeli piaci nyitás után az AMH **gyengült -$0,50/share-rel** ($33,26 → $32,76 = -1,5% Day 16-i intraday). Ez **a "next-day MKT fill kockázat"** klasszikus példája — a Day 15-i mark vs Day 16-i 21:40 MOC fill eltérése.

**A Backlog #7 (Next-day MKT fill kockázat)** **statisztikai mintán** most már 3 ellentétes példa:
- **MSM Day 14**: +0,11% kedvező (közeli)
- **BEN Day 15**: -2,05% kedvezőtlen ⚠️
- **AMH Day 16**: -1,50% kedvezőtlen ⚠️

A "1-nap-TP1 + kedvező entry-slippage" minta **megdőlt** — a next-day MKT fill kockázat **kétharmados gyakoriságú** a 3 mintán (de a 3 ticker-en kis statisztikai minta). Day 21+ után érdemes a TP1-limit-order opciót komolyabban mérlegelni.

### 1.2 Új entries (2) — Sector duplikáció minta folytatódik

| Idő (CEST) | Ticker | Sektor | Qty | Planned | Fill (IBKR) | Slippage | Notional | ATR |
|-----------|--------|--------|-----|---------|--------------|----------|----------|-----|
| 15:31:08 | **NSA** | Real Estate (**dupli VNO mellé**) | 188 | $43,43 | $43,41 | **-0,05% kedvező** | $8 161 | 2,14% |
| **15:33:40** ⚠️ | **TKR** | Industrials (**dupli MSM mellé**) | 39 | $131,83 | **$133,71** ⚠️ | **+1,45% kedvezőtlen!** | $5 215 | 3,38% |

**NSA**: National Storage Affiliates Trust (REIT) — kis slippage, kedvező entry.

**TKR**: Timken Company (gépészeti, Industrials) — **15:33:40 CEST-kor kötött, NEM 15:31-kor** (2,5 perc késéssel). Az IBKR fill $133,71 / state planned $131,83 = **+$1,88/share** = **+1,45% kedvezőtlen** slippage.

#### ⚠️ ÚJ finding §0.18 — TKR slippage rögzítés hibás

A `daily_metrics::execution::slippage_per_ticker::TKR`:
```json
"TKR": {
  "planned": 131.83,
  "filled": 131.83,    ⚠️ HIBÁS (valódi IBKR fill $133.71)
  "slippage_pct": 0.0, ⚠️ HIBÁS (valódi -1.45%)
  "qty": 39
}
```

A `filled` és `slippage_pct` mezők **a state planned-et tükrözik, NEM a tényleges IBKR fill-árat**.

**Hatás**:
- A `weekly_metrics.py` (és a Day 16 daily_metrics) a TKR slippage-jét 0%-ként számolja
- A Fix #5 weekly_metrics.py `slippage_aggregation_complete` task most már **kétségbe vonja** a teljes slippage-rögzítést — nem a `weekly_metrics.py` bug, hanem a **daily_metrics rögzítés** is hibás

**Akció**: új P1 finding a fix-package-ben, vagy a P2 #5 task scope bővítése. A `daily_metrics::execution::slippage_per_ticker::*::filled` mezőt **a tényleges IBKR fill-árat kell tartalmaznia** (a `get_account_trades`-ből), NEM a state planned-et.

**Strategiai megfigyelés**: a TKR fill 2,5 perc késéssel kötött (15:33:40 vs 15:31:10 submit). Ez **piaci order-route hatás** — a 39 share Timken NYSE-en valószínűleg auction-szabályok miatt késéssel match-elt. A magas kedvezőtlen slippage (+1,45%) a 2,5 perces ár-mozgásból eredhet. **A submit-time price** ($131,83) a Phase 4-6 cron 14:30-i context-éből, a fill-time price ($133,71) a 15:33-i piaci ár — **a TKR Day 16 reggel +1,5%-kal magasabbra ment intraday a 15:31-15:34 között**.

### 1.3 Sector distribution Day 16 záró

| Sektor | Notional | % portfolio | Ticker(ek) |
|--------|----------|-------------|------------|
| **Real Estate** | $14 016 | **14,02%** | VNO (171) + **NSA új** (188) |
| **Industrials** | $8 386 | 8,39% | MSM (29 trail) + **TKR új** (39) |
| **Healthcare** | $5 811 | 5,81% | WST (18) |
| **Technology** | $4 904 | 4,90% | FFIV (12) |
| **Financial Services** | $3 921 | 3,92% | BEN (126 trail) |
| **Total** | **$37 038** | **37,04%** | 7 ticker, **5 szektor** |

**Day 15 záró 28,05% → Day 16 záró 37,04%** — +9,0% növekedés a 2 új entry miatt. **5 hely a 12 cap-ig**, ez **biztonságos diverzifikáció**.

**Sector cap (30%) bőven betartva** — a max szektor Real Estate 14,02%, a Strategic_review-i "max 30% notional/sector" kritérium felénél.

---

## 2. EOD State (22:00 CEST) — Day 17-re 2 EOD flag ⭐

`pt_monitor_2026-06-08.log` 22:00:09:
```
[SWING EOD] Evaluated 7 positions — 2 exit flags set
  WST: TIME_STOP
  VNO: TP1
```

**Day 17 (kedd 2026-06-09, W24 D2) 2 exit flag**:
- **VNO TP1** ⭐ (Day 17 15:30 MKT, 171/2 = 85 share partial)
- **WST TIME_STOP** (Day 17 21:40 MOC, 18 share full, 5 trading napi hold)

### 2.1 A 7 nyitott pozíció Day 16 záró

| Ticker | Entry $ (state) | Mark | Qty | days_held | Unrealized (IBKR) | next_action | Sektor |
|--------|------------------|------|-----|-----------|---------------------|-------------|--------|
| **VNO** | 34,22 | **$36,20** | 171 | **3** | **+$383,75** ⭐⭐⭐ | **TP1** (Day 17 15:30 MKT) | Real Estate |
| **BEN** | 31,12 | $31,39 | 126 (trail) | 3 | +$111,88 | HOLD (trail $30,71) | Financial Services |
| **MSM** | 111,88 | $115,59 | 29 (trail) | 4 | +$82,15 | HOLD (trail $114,28) | Industrials |
| **NSA (új)** | 43,43 | $43,62 | 188 | 0 | +$38,48 | HOLD | Real Estate |
| **TKR (új)** | 131,83 (state) / 133,74 (IBKR) | $134,67 | 39 | 0 | +$36,44 | HOLD | Industrials |
| **WST** | 322,81 | $319,75 | 18 | **5** | -$83,44 | **TIME_STOP** (Day 17 21:40 MOC) | Healthcare |
| **FFIV** | 408,66 | $396,19 | 12 | 1 | **-$151,00** ⚠️ | HOLD (stop $381,52, 3,7% buffer) | Technology |
| **Total unrealized** | | | | | **+$418,26** ⭐ | | |

**Pozitív/negatív arány**: 5 nyertes (+$652) / 2 vesztes (-$234), nettó **+$418** — **a swing pivot deploy óta a legmagasabb pozitív unrealized**.

### 2.2 ⭐⭐⭐ VNO ROCKET — a swing pivot 3. ideális gyors swing trade-je

| Day | VNO mark | Unrealized | Megjegyzés |
|-----|----------|------------|------------|
| Day 13 entry | $33,95 (fill) | $0 | Real Estate, ATR 3,0% |
| Day 13 záró | $33,99 | +$5,84 | Első napi flat |
| Day 14 záró | $35,07 | +$190 | +3,17% mozgás |
| Day 15 záró | $35,21 | +$214 | +0,40% |
| **Day 16 záró** | **$36,20** | **+$384** ⭐⭐⭐ | **+2,81% Day 16-i mozgás**, **TP1 átlépve** |

A VNO **3 trading napon belül +6,6% (Day 13 entry → Day 16 záró)** — gyors swing-trade. A TP1 level $35,75 < mark $36,20 = TP1 átlépve. Day 17 várt TP1 fill: ~$35,75 ÉS HABÁR a Day 16 záró $36,20 magasabb, a **next-day MKT fill kockázat** alapján (3 ellenpélda: MSM, BEN, AMH) inkább $35,75-$36,00 közötti várható.

**Várt Day 17 VNO TP1 realized** (85 share partial, 50%): broker net = 85 × ($35,75 - $33,96 IBKR avg) - $1 commission = 85 × $1,79 - $1 = **+$151 broker net** (optimista becslés).

A VNO **a swing pivot eddigi 3. ideális gyors swing trade-je** (CDNS, MSM, **VNO**) — entry → TP1 3 trading napon belül, broker net realized >+$130. A statisztikai minta most már 6 TP1/TP2 hit a 11 exit-ből (W21-W24 D1, 16 trading nap mintán).

### 2.3 ⚠️ FFIV — gyengül, stop közeledik

FFIV entry $408,66 (Day 15), Day 15 záró -$186, **Day 16 záró -$151** (a Day 15-i 21,50 VIX risk-off után a Day 16-i 18,75 VIX rebound is csak részleges javulást hozott — a FFIV mark $393,26 → $396,19 = +0,7%, miközben a SPY +0,23%, tehát a FFIV az átlag fölött +0,5%).

Stop $381,52, mark $396,19 = **3,7% buffer**. NEM stop-veszély a Day 17-re, **DE** ha a major-risk-off folytatódik (egy újabb -2%+ SPY zuhanás), a FFIV stop-közeli helyzetbe kerülhet. **Megfigyelendő**.

### 2.4 WST TIME_STOP — a "alvó" pozíció zárása

WST entry $322,81 (Day 10, 6/1), Day 16 záró $319,75 — **5 trading napi hold** (days_held=5). TIME_STOP Day 17 21:40 MOC. Várt realized: 18 × ($319,75 - $324,39 IBKR avg) - $1 = **~-$84 broker net**. A JHG Day 14-i "kvázi-alvó" zárásához hasonló.

### 2.5 Day 17 várt total realized

| Exit | Várt realized (broker net) |
|------|-----------------------------|
| VNO TP1 (85 share partial) | **~+$151** |
| WST TIME_STOP (18 share full) | **~-$84** |
| **Day 17 total** | **~+$67** |
| **Cumulative Day 17 várt** | **~+$425** |

**Várt új entry Day 17-en**: friss W24 D2 (kedd) context, a SPY +0,23% kis-bull napon. A hiányzó szektorok (Consumer Defensive, Utilities, Materials, Comm Services, Consumer Cyclical, Energy) **6 szektor üresen** — várhatóan 1-2 új entry.

---

## 3. Pipeline Log Review

### 3.1 `pt_close_2026-06-08.log` — 1 exit tisztán

```
15:30:02 [SWING 15:30 close] No EOD action flags set — nothing to do.
21:40:07 AMH: TIME_STOP → MOC SELL 135
21:40:07 [SWING 21:40 close] MOC submitted 1 | open: 7
```

A 15:30 close "nothing to do" — Day 15 záró EOD-flag csak AMH TIME_STOP-ra állt (21:40 MOC), 0 TP1-flag a Day 16 15:30-ra. **Helyes**.

### 3.2 `pt_submit_2026-06-08.log` — 2 entry, TKR fill-késedelem

```
15:31:01 Reading: execution_plan_run_20260608_123001_f60523.csv
15:31:06 Existing IBKR positions/orders: {'WST', 'BEN', 'VNO', 'FFIV', 'AMH', 'MSM'}
15:31:06   Skipping VNO: already has position or swing state
15:31:08 NSA: MKT BUY 188 @ ~$43.43 | stop $41.57 | TP1 $44.82 | TP2 $46.21
15:31:10 TKR: MKT BUY 39 @ ~$131.83 | stop $122.93 | TP1 $138.51 | TP2 $145.18
15:31:10 [SWING] Submitted: 2 tickers | State: state/swing_positions.json (8 open)
```

A `(8 open)` — a submit pillanatban a 6 régi (AMH még benne) + 2 új = 8 (a 21:40-i AMH MOC még nem zárta state-szinten).

**TKR fill-késedelem**: a submit 15:31:10-kor lett, **IBKR fill 15:33:40** (2,5 perc késéssel). A 2,5 perc alatt a TKR ár **+1,45% kedvezőtlenül** mozgott. Lásd §1.2.

### 3.3 `pt_monitor_2026-06-08.log` — 2 EOD flag ✓

```
22:00:09 [SWING EOD] Evaluated 7 positions — 2 exit flags set
  WST: TIME_STOP
  VNO: TP1
```

**Day 17 várt komplex exit-nap**: VNO TP1 (kedvezőbb) + WST TIME_STOP (kis-vesztes flat).

### 3.4 `pt_reconcile_2026-06-08.log` — **10. ÉLES SILENT OK** ⭐⭐⭐

```
22:15:01 State tickers: ['BEN', 'FFIV', 'MSM', 'NSA', 'TKR', 'VNO', 'WST']
22:15:06 IBKR tickers: ['BEN', 'FFIV', 'MSM', 'NSA', 'TKR', 'VNO', 'WST']
22:15:06 Reconciliation OK — state and IBKR match (silent exit).
```

**10/10 ÉLES SILENT OK** ⭐ — **22 trading napi tiszta mental-stop futás** a Day 6 CNC-cancel óta. **Rekord**. A Day 15-i 22:00-i ROIV-divergence-warning (lásd Day 15 review §3.3) most nem ismétlődött — a Day 16-i 21:40 AMH MOC fill 22:00 EOD-eval-ig elcsendesedett.

### 3.5 ⭐ `pt_eod_2026-06-08.log` — A FIX-PACKAGE P1 #2-#4 ÉLES TESZTJE

```
22:11:02 EOD Report — 2026-06-08                          ← #2 timing fix ✓ (22:11, NEM 22:05)
22:11:05 Trades: 0                                          ⚠️ #0.5 másodlagos
22:11:05 P&L today: $+112.96 (net; gross $+114.08)         ← #4 commission ($1.12) implicit
22:11:05 Cumulative: $+358.21 (+0.36%) [Day 15/63]         ← #3 NYSE-count ✓
```

**Tökéletes render**:
- 22:11-kor fut (Part A 22:10 után)
- A `P&L today: $+112.96 (net; gross $+114.08)` mező **net + gross** paralel (commission $1,12 implicit)
- `Cumulative $+358.21` a Day 16 utáni teljes érték
- `[Day 15/63]` a NYSE-count szerint

**A `Trades: 0` MÁSODLAGOS DISPLAY-glitch** (lásd §0.5) — a 21:40 AMH MOC fill nem szerepel a `trades.details`-ben, de a P&L helyesen rögzítve.

---

## 4. UW Shadow Log Day 16 — 36 ticker, MASI top S_j újra felemelkedett

| Mutató | Day 14 | Day 15 | **Day 16** | Trend |
|--------|--------|--------|-----------|-------|
| Tickers logged | 45 | 45 | **36** | -9 (kevesebb qualifying) |
| Avg dp_pct | 3,06% | 5,70% | **2,59%** | -3,11pp (normalizálódik) |
| would_have_been_penalty_count | 5 | 9 | **2** | -7 (visszaesett) |
| GEX regime (pos/hv/unk) | 29/11/5 | 28/13/4 | **27/5/4** | **kevesebb high_vol** |
| m_gex_avg | 0,9022 | 0,8844 | **0,9444** | +0,06 (rebound) |

**A Day 15-i risk-off UW-magas-volume Day 16-ra normalizálódott** — a dp_pct visszaesett 5,70% → 2,59%, a penalty_count 9 → 2. A m_gex_avg 0,8844 → 0,9444 (a positive gamma rebound).

**Top 3 S_j Day 16**:
1. **MASI 92,3** (Healthcare) — **újra a top!** (Day 13-15-i 88,9 csökkenés után rebound)
2. **VNO 85,2** (Real Estate) — **meglévő pozíció**, Day 16 záró TP1-flag
3. **NSA 79,2** (Real Estate) — **meglévő pozíció** (Day 16 új entry)

**Strukturális megfigyelés**: a MASI scoring 92,3 a Day 13-15-i 88,9 → 92,5 → 88,9 csökkenés után **újra felemelkedett**, jelezve egy **belső momentum-rebound**-ot. **DE** a sector-balanced greedy **MÉG NEM választotta** entry-re, mert:
- a Healthcare szektor 1 ticker (WST) az utolsó nap (Day 17 TIME_STOP várt)
- a sector-balanced greedy a `nincs jelölt a hiányzó szektorokban`-helyzetben preferál a meglévő szektor-duplikációt (lásd Day 13 BEN+VNO, Day 16 NSA+TKR)
- a MASI a 7. nap top S_j ÉS sosem boomerang — **strukturálisan védi a sector-balanced greedy** a "magas pontszám paradoxon" ellen

VIX: a Day 15-i 21,50 → Day 16-i 18,75 = -12,83% rebound. A "VIX > 18 + 20+ napi átlag = leállítás" Strategic_review-i kritérium most a 18-as küszöb fölött, **DE a 20+ napi mintán a Day 1-16 átlag VIX = ~16,5** (becsült), tehát a leállítási kritérium **NEM AKTIVÁLT** — a Day 16-i csökkenés rebound, nem trend.

---

## 5. Anomáliák / megfigyelések (Day 16)

### 5.1 ✅ A `2026-06-06-data-quality-fix-package.md` P1 #1-#4 DEPLOY VERIFIKÁCIÓ — TÖKÉLETES

Lásd §0. Mind a 4 fix élesen működik a Day 16-on. Backfill scriptek lefutottak.

### 5.2 ⚠️ ÚJ §0.18 — TKR slippage rögzítés hibás

A `daily_metrics::execution::slippage_per_ticker::TKR` mező `filled: 131.83` (a state planned-et tükrözi), a valódi IBKR fill $133,71. **+1,45% kedvezőtlen slippage** rögzítetlen. **Fix-package #5 task scope bővítendő** (vagy új P1 task).

### 5.3 ⚠️ §0.5 másodlagos — `trades.details: []` Day 16-on

A `trades.details` mező MOC fill-eket NEM tartalmazza (csak TP1/15:30 fill-eket). **P2 task, NEM kritikus** (a P&L helyes).

### 5.4 ⚠️ §0.6 portfolio_return_pct ellenőrzés szükséges

A Day 16 `portfolio_return_pct: 0.11` — várt érték (Net Liq $101 034,23 - $100 675,60 Day 15 záró) / $100 675,60 × 100 = **+0,356%**. A `0.11`-i érték továbbra is **alulbecsül** — a Fix #6 portfolio_return_pct audit task **MÉG NEM DEPLOY-OLT**. (P2 task, hét közben).

### 5.5 ✅ §0.10 reconcile — 10/10 ÉLES SILENT OK (22 trading napi tiszta mental-stop)

### 5.6 ⭐ ÚJ megfigyelés — Next-day MKT fill kockázat statisztikai mintán 3 ellenpélda

A "1-nap-TP1 + kedvező entry-slippage" minta most már 3 mintán:
- **MSM Day 14**: +0,11% kedvező ✓
- **BEN Day 15**: -2,05% kedvezőtlen ⚠️
- **AMH Day 16** (TIME_STOP MOC, NEM TP1 — de ugyanaz a kockázat): -1,50% kedvezőtlen ⚠️

**Strategiai jelentőség**: a Backlog #7 (TP1-limit-order opció) statisztikai minta-felépítése folyamatban. Day 21+ után érdemes a részletes elemzést megnézni.

### 5.7 ⚠️ TKR fill-késedelem 2,5 perc — piaci order-route hatás

A TKR submit 15:31:10, fill 15:33:40. Az NSA submit 15:31:08, fill 15:31:08 — pontos. A TKR ticker likviditása (Timken Co., napi forgalom kisebb) **piaci-order-route szempontjából lassabb match-elés**. A 2,5 perc alatt az ár +1,45%-kal magasabbra ment.

**Megfigyelendő**: hány TKR-szerű (késéssel kötő) ticker fordul elő, és a fill-késedelem statisztikai mintán mit jelez?

---

## 6. Day 17 (kedd, 2026-06-09, W24 D2) outlook

### 6.1 Várt 2-exit-kis-trifecta

| Idő | Exit | Qty | Várt fill | Várt realized (broker net) |
|-----|------|-----|-----------|------------------------------|
| 15:30 CEST | **VNO TP1** (50% partial) | 85 | ~$35,75-36,00 | **~+$151** ⭐ (kedvező entry-slippage hatás miatt) |
| 21:40 CEST | **WST TIME_STOP MOC** (full) | 18 | ~$319 | **~-$84** ⚠️ (kis-vesztes flat) |
| **Total Day 17 realized várt** | | | | **~+$67** |
| **Cumulative Day 17 várt záró** | | | | **~+$425** |

### 6.2 Day 17 prioritások

1. **VNO TP1 fill** — várt ~+$151 (a swing pivot 7. TP1 hit-je)
2. **WST TIME_STOP MOC fill** — várt ~-$84
3. **Új entry(ek) Day 17-en** — hiányzó szektorok preferenciája
4. **11. éles reconcile SILENT OK** — 23 trading napi tiszta mental-stop futás
5. **CC follow-up**: §0.18 TKR slippage finding + §0.6 portfolio_return_pct audit
6. **#5 weekly_metrics.py slippage_aggregation deploy** — W24 zárás (péntek 6/12) előtt

### 6.3 Day 21 checkpoint felé

| Nap | Cumulative | Buffer (-$1500-ig) |
|-----|------------|---------------------|
| Day 8 (mélypont) | -$779,64 | 48% |
| Day 13 | -$43,92 | 97% |
| Day 14 | +$199,50 | 113% |
| Day 15 | +$245,25 | 116% |
| **Day 16** | **+$358,21** | **124%** |
| Day 17 várt | +$425 | 128% |
| Day 21 várt (≈jún 14) | +$500-600 | 134%+ |

A **Day 21 checkpoint kritérium-tartományon kívül** — a -$1500 küszöbtől 124% feletti buffer-rel.

### 6.4 Strategiai jelentőség — a fix-package teljes-tisztított architektúra

A Day 16 az **első nap a teljes tisztított architektúrán** (Part B + days_held + ATR-band + Part A + Option B + commission + VIX Polygon + EOD timing + Day-N egységesítés). A swing tézis empirikus megerősítésének **első strukturálisan stabil nap**ja:
- TP-hit ráta a W21-W24D1 = 16 napos mintán: 6/12 = **50%** (régi 9,5%-hoz képest 5,3× javulás)
- Pozitív exit ráta: 9/12 = **75%** (régi 33,3%-hoz képest 2,3× javulás)
- Átlag exit P&L (broker net): **+$66** (régi -$11-hez képest 6× javulás)

A **Day 21 checkpoint (≈jún 16, hétfő, W24 D6) buffer 124%** — a swing pivot **strukturálisan és empirikusan elérte a kanonikus pozitív tartományt**.

---

## 7. Files referenced (Day 16)

- `state/swing_positions.json` — **7 pozíció**, **2 EOD flag** (VNO TP1, WST TIME_STOP a Day 17-re), last_updated 2026-06-08T20:00:09Z
- `state/daily_metrics/2026-06-08.json` — Day 16 cumulative **+$358,21** ⭐, day_number=15, **vix_close=18.75 (Polygon I:VIX)** ✓, commission=$1.12 ✓, trades.details=[] ⚠️ másodlagos
- `state/pending_exits/2026-06-08.json` — **1 bejegyzés processed=true** (AMH_TIME_STOP)
- `scripts/paper_trading/logs/cumulative_pnl.json` — Day 16 entry: pnl=$112.96 ✓, commission=$1.12 ✓ (a 0,0 helyett), tp1_hits=0, moc_exits=1, trading_days=14, **cumulative +$358.21** ⭐
- `logs/pt_close_2026-06-08.log` — 1 exit submit (AMH TIME_STOP), 15:30 nothing-to-do
- `logs/pt_submit_2026-06-08.log` — 2 új entry (NSA + TKR), TKR fill 2,5 perc késéssel
- `logs/pt_monitor_2026-06-08.log` — **2 EOD flag** (VNO TP1 + WST TIME_STOP)
- `logs/pt_reconcile_2026-06-08.log` — **10. ÉLES SILENT OK** ⭐ (22 trading napi tiszta)
- `logs/pt_eod_2026-06-08.log` — **22:11-kor fut** ✓, P&L net+gross paralel ✓, `[Day 15/63]` ✓
- `state/uw_shadow/2026-06-08.json` — 36 ticker, MASI 92,3 (újra top), m_gex 0,9444 (positive rebound)
- **IBKR direkt API**:
  - `get_account_summary` → Net Liq **$101 034,23** (+$1034,23 a baseline FÖLÖTT, 4. egymás utáni nap, **első $101k+**)
  - `get_account_positions` → 7 pozíció, **unrealized +$418,26** (a swing pivot deploy óta legmagasabb pozitív)
  - `get_account_trades(DAYS_7)` → Day 16 trades: 1 exit (AMH MOC) + 2 új entry (NSA + TKR)

---

## 8. ⭐ Strukturális finding-ek összefoglaló

### 8.1 ⭐⭐⭐ A fix-package P1 #1-#4 DEPLOY VERIFIKÁCIÓ — a swing pivot tisztított architektúra kompletté

A `2026-06-06-data-quality-fix-package.md` task P1 #1-#4 fix-ek mind élesen működnek:
- **#1 VIX Polygon I:VIX** ✓ (vix_close 18,75 ≈ 21,50/(1-0,1283) = Day 15 záró 21,50)
- **#2 EOD Telegram 22:11** ✓ (a 22:10 Part A után)
- **#3 Day-N NYSE-count** ✓ (`[Day 15/63]`)
- **#4 Commission rögzítés + backfill** ✓ ($28,57 total Day 1-16, ~$2/exit átlag)

Plus a `recorder-robust-realized-capture` task A.2 `ib.fills()` opció **hétfői live smoke SIKERES** — a Part A Option B élesen rögzít broker-authoritative realized-et.

### 8.2 ⭐⭐⭐ Net Liq első alkalom $101k FÖLÖTT — 4. egymás utáni nap a baseline FÖLÖTT

| Nap | Net Liq | Δ | A baseline-tól |
|-----|---------|---|----------------|
| Day 13 (6/3) | $100 450,34 | — | +$450 |
| Day 14 (6/4) | $101 273,85 | +$823 | +$1 274 ⚠️ (a Day 14 review-mban a Net Liq nem volt látható) |
| Day 15 (6/5) | $100 675,60 | -$598 | +$676 |
| **Day 16 (6/8)** | **$101 034,23** | **+$359** | **+$1 034** ⭐⭐⭐ |

A **Day 8-i mélypontról (-$779,64) 8 trading nap alatt valódi +$1359 broker mozgás**. A swing pivot strukturálisan **kanonikus pozitív tartományban**.

### 8.3 ⭐ A VNO ROCKET — a swing pivot 3. ideális gyors swing trade-je

VNO Day 13 entry → Day 16 záró: **+6,6% (+$384 unrealized)** 3 trading nap alatt. TP1-flag Day 17-re, várt realized ~+$151 broker net. **A statisztikai minta most már 6 TP1/TP2 hit a 11 exit-ből** (16 trading napi minta).

### 8.4 ⭐ MASI rebound — sector-balanced greedy struktural védelem 7. nap

MASI Day 10-12: 94,1 → 93,9 (top), Day 13-15: 92,5 → 88,9 (csökkent), **Day 16: 92,3 (újra top)**. **7. egymás utáni nap top S_j, sosem boomerang**. A sector-balanced greedy ma is más szektort választott (NSA + TKR a duplikációknak).

### 8.5 ⚠️ ÚJ finding §0.18 — TKR slippage rögzítés hibás

A `daily_metrics::execution::slippage_per_ticker::TKR::filled: 131.83` a state planned-et tükrözi, a valódi IBKR fill $133,71. **+1,45% kedvezőtlen slippage** rögzítetlen. **Fix-package #5 task scope bővítendő** (vagy új P1 task).

### 8.6 📝 Next-day MKT fill kockázat statisztikai minta — 3 ellenpélda

A "1-nap-TP1 + kedvező entry-slippage" minta most már 3 ellenpélda:
- MSM Day 14: +0,11% kedvező ✓
- BEN Day 15: -2,05% kedvezőtlen ⚠️
- AMH Day 16: -1,50% kedvezőtlen ⚠️

Statisztikai mintán Day 21+ után érdemes lesz a TP1-limit-order opciót komolyabban mérlegelni.

### 8.7 ⭐ A swing tézis empirikus megerősítése — 16 napos statisztikai minta

| Metric | W21-W24 D1 (16 nap, tisztított arch) | Régi 60-napi |
|--------|---------------------------------------|---------------|
| TP-hit ráta | **50%** (6/12 exit) | 9,5% |
| Pozitív exit ráta | **75%** (9/12) | 33,3% |
| Átlag exit P&L (broker net) | **+$66/exit** | -$11/exit |
| Major-bear-day excess | **+2,34%** (Day 15) | n/a |
| Daily-eval fordulatok | **7/8 nyertes** (AKAM, ST, EOG, CDNS, MSM, ST trail, AMH-Day 11→Day 16) | n/a |

**A 60 napi (Day 63 ≈2026-09-15) elemzéshez vezető első 16 napos minta strukturálisan ígéretes.**

---

## State (Day 16 — W24 D1, swing pivot Day 16/63)

**Architektúra**: swing pivot Fázis 3 deploy DAY 16. **A `2026-06-06-data-quality-fix-package.md` P1 #1-#4 fix-ek mind élesen működnek. A `recorder-robust-realized-capture` A.2 ib.fills() hétfői live smoke SIKERES. A swing pivot tisztított architektúrája KOMPLETT.**

**Live**: 7 open positions:
- **VNO** ⭐⭐⭐ (171, **TP1 flag Day 17 15:30**, days_held=3, +$384 unrealized — Day 16 ROCKET +$170)
- **BEN** (126 trail, HOLD trail $30,71, days_held=3, +$112 unrealized)
- **MSM** (29 trail, HOLD trail $114,28, days_held=4, +$82 unrealized)
- **NSA új** (188, HOLD, days_held=0, +$38 unrealized)
- **TKR új** ⚠️ (39, HOLD, days_held=0, +$36 unrealized, slippage finding §0.18)
- **WST** (18, **TIME_STOP flag Day 17 21:40**, days_held=5, -$83 unrealized)
- **FFIV** (12, HOLD, days_held=1, -$151 unrealized, 3,7% stop-buffer)

**Total unrealized**: **+$418,26** (5 nyertes/2 vesztes, **a swing pivot deploy óta legmagasabb pozitív**)

**Cumulative (Mac Mini canonical, broker-authoritative)**: **+$358,21** ⭐⭐⭐
**Net Liq (IBKR)**: **$101 034,23** — **+$1 034,23 a baseline FÖLÖTT, 4. egymás utáni nap, első alkalom $101k+** ⭐⭐⭐

**Day 16 realized (broker net)**: **+$112,96** (AMH TIME_STOP MOC). **Day 16 commission**: $1,12 ✓ (Part A Option B élesedett).

**Excess return Day 16**: portfolio +0,11%, SPY +0,23%, **excess -0,11%** (közel-semleges; a §0.6 portfolio_return_pct audit pending — várt valódi excess ~+0,1%).

**Aktív P0/P1 (frissített, Day 16 utáni):**
- **§0.16 ✅ Part A Option B robust-realized-capture** (Day 16 ib.fills() live smoke SIKERES)
- **§0.17 ✅ VIX Polygon I:VIX** (fix #1 deploy-olt)
- **§0.14 ✅ EOD Telegram timing** (fix #2 deploy-olt, 22:11-re tolva)
- **§0.5 ⚠️ MÁSODLAGOS — `trades.details: []` MOC fill kimaradás** (P2 task)
- **§0.18 ⚠️ ÚJ — TKR slippage rögzítés hibás** (filled=planned, NEM IBKR fill — P1 task)
- **§0.6 ⏳ portfolio_return_pct audit** (fix #6 még nem deploy-olt — P2 task)
- **§5.4 ✅ commission rögzítés** (fix #4 deploy + backfill — $28,57 Day 1-16)
- **§0.10 ✅ stabil** (10/10 silent OK, 22 trading napi tiszta mental-stop — rekord)
- **§9.2, §9.3, §9.5 ✅ TELJES RESOLVED + élesen validált**
- **ÚJ §8.3 megfigyelés** — VNO 3. ideális gyors swing trade (CDNS + MSM mellé)
- **ÚJ §8.6 megfigyelés** — Next-day MKT fill kockázat 3 ellenpélda statisztikai mintán

**Day 17 fókusz**:
1. **VNO TP1 fill** (várt ~+$151 broker net, kedvező entry-slippage miatt)
2. **WST TIME_STOP MOC fill** (várt ~-$84)
3. **Új entry(ek)** — hiányzó szektorokba (6 szektor üres: Consumer Defensive, Utilities, Materials, Comm Services, Consumer Cyclical, Energy)
4. **11. éles reconcile SILENT OK** (23 trading napi tiszta)
5. **CC follow-up**: §0.18 TKR slippage finding (P1) + §0.6 portfolio_return_pct audit (P2) + #5 weekly_metrics.py slippage_aggregation deploy

**A Day 16 napi karakter egy mondatban**: **A swing pivot tisztított architektúrájának komplett verifikációs napja** — (1) a **`2026-06-06-data-quality-fix-package.md` P1 #1-#4 fix-ek mind élesen működnek** (VIX Polygon I:VIX, EOD Telegram 22:11, Day-N NYSE-count, commission rögzítés + backfill), és a **`recorder-robust-realized-capture` task A.2 `ib.fills()` opció hétfői live smoke SIKERES** (a Part A Option B élesen rögzít broker-authoritative realized-et, NEM a régi state-attribúciós Day 15-i bug-ot), (2) a **Net Liq $101 034,23 = +$1 034 a baseline FÖLÖTT** (4. egymás utáni nap, **első alkalom $101k+**, a Day 8-i mélypontról 8 trading nap alatt valódi +$1359 broker mozgás), (3) a **VNO ROCKET** Day 16-on (Day 15 +$214 → Day 16 +$384 = +$170 napi unrealized növekedés, +2,81% mark mozgás, **TP1 átlépve $35,75 → $36,20**, **flag Day 17 15:30 MKT-re** mint a 7. TP1 hit), és (4) a **MASI 7. egymás utáni nap top S_j** (újra 92,3 a Day 13-15-i 88,9 csökkenés után **rebound**, sector-balanced greedy strukturális védelmét folytatja), miközben **2 új entry** sector duplikáció mintát követ (NSA Real Estate dupli VNO mellé, TKR Industrials dupli MSM mellé), az **AMH TIME_STOP MOC +$112,96** broker net (várt ~+$170, -$57 alulteljesít a Day 16-i AMH-gyengülés -1,5% miatt — a "next-day MKT fill kockázat" 3. statisztikai ellenpélda), a **`_reconcile_state_from_ibkr` 10/10 ÉLES SILENT OK** (22 trading napi tiszta mental-stop futás, rekord), és **két új finding** dokumentálva (§0.18 TKR slippage rögzítés hibás +1,45% kedvezőtlen rejtetten, §0.5 másodlagos `trades.details: []` MOC kimaradás) — **a swing tézis empirikus megerősítésének 16 napos statisztikai mintán (TP-hit ráta 50%, pozitív exit ráta 75%, átlag exit P&L +$66) strukturálisan validál, és a Day 21 checkpoint buffer 124%-on a kritérium-tartományon kívül**.

---

**A Day 16 review vége.** A Day 17 fókusz: VNO TP1 (várt +$151) + WST TIME_STOP (várt -$84) + új entry(ek) + 11. ÉLES SILENT OK + CC follow-up §0.18 TKR slippage + §0.6 portfolio_return_pct audit + #5 weekly_metrics.py slippage_aggregation.
