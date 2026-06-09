Status: WIP
Updated: 2026-06-09
Note: **Implementáció KÉSZ** (commit 8c28a4b + 937dbcc, 1938 passing). Fix #1 (IBKR-fill slippage), Fix #2 (trades.details MOC merge), backfill script + connector map. Connector-validált 6/8 (TKR +1.43%, NSA -0.05%, AMH MOC entry 31.92). **HÁTRA: push + Mac Mini deploy (a ma esti 22:10 Day 17 cron ELŐTT) + backfill --apply + Day 17 esti EOD verifikáció.** ——— Eredeti finding: A `daily_metrics::execution::slippage_per_ticker::*::filled` mező a state planned-et tükrözi (NEM a valódi IBKR fill-árat — TKR Day 16 példa: filled=131.83 vs valódi $133.71, +1,45% rejtett kedvezőtlen slippage). Plus a `trades.details` blokk a 21:40 MOC fill-eket NEM tartalmazza (csak 15:30 TP1-eket).

# daily_metrics::execution & trades.details fix (P1 + P2)

**Priority**: P1 (slippage rögzítés — heti aggregátum + statisztikai elemzés torzul) + P2 (trades.details másodlagos display-glitch)
**Becsült CC effort**: ~2-3h
**Érintett**: `scripts/paper_trading/daily_metrics.py` (`build_daily_metrics`), `scripts/paper_trading/lib/trade_csv.py` (esetleg)

## Háttér

A 2026-06-08 (Day 16, W24 D1) napi review két új finding-et dokumentált a `state/daily_metrics/2026-06-08.json` adatában. Mindkettő a `daily_metrics::execution` és a `trades.details` blokkok rögzítésére vonatkozik, és a `2026-06-06-data-quality-fix-package.md` task scope-ján KÍVÜLI (külön task).

### Finding #1 — TKR slippage rögzítés hibás (§0.18)

A Day 16-i TKR (Timken Co.) új entry:
- **Submit** (15:31:10 CEST): `MKT BUY 39 @ ~$131.83 | stop $122.93 | TP1 $138.51`
- **IBKR fill** (15:33:40 CEST, **2,5 perc késéssel**): $133.71 (NYSE)
- **Valódi slippage**: $133.71 - $131.83 = **+$1.88/share = +1,45% kedvezőtlen**

A `daily_metrics/2026-06-08.json::execution::slippage_per_ticker::TKR`:
```json
"TKR": {
  "planned": 131.83,
  "filled": 131.83,    ← ⚠️ HIBÁS (a state planned-et tükrözi, NEM az IBKR fill-árat)
  "slippage_pct": 0.0, ← ⚠️ HIBÁS (valódi -1,45%)
  "qty": 39
}
```

**Strukturális ok**: a `build_daily_metrics` a `slippage_per_ticker::filled` mezőt a state-fájl `entry_price` mezőjéből veszi (a Phase 6 submit-time `planned_entry_price`), NEM az IBKR `get_account_trades`-i tényleges fill-árból.

**Hatás**:
- A W23 weekly_metrics `Avg MKT fill slippage: -3,77%` (csak az MSM Day 12-i kiugró slippage-jét veszi figyelembe) — **a daily_metrics rögzítés is hibás**, NEM csak a weekly aggregátum (a `2026-06-06-data-quality-fix-package.md #5` fix scope-ja a weekly aggregátum-re vonatkozott, de a gyökérprobléma a daily_metrics-ben)
- A Day 21+ statisztikai elemzés (a Backlog #7 next-day MKT fill kockázat) **téves alapadatokra** támaszkodik
- A `04-risks` §X.X "submit-time → fill-time késedelem" minta nem mérhető (TKR Day 16 példa: 2,5 perc fill-késéssel +1,45% slippage)

### Finding #2 — `trades.details: []` Day 16-on (§0.5)

A Day 16-i `daily_metrics/2026-06-08.json::trades`:
```json
"trades": {
  "best": null,
  "worst": null,
  "details": []      ← ⚠️ ÜRES (a 21:40-i AMH MOC fill nem szerepel)
}
```

De: `daily_history.2026-06-08.pnl: $112.96` HELYES (az AMH MOC realized), és `exits.moc: 1` is rögzítve.

**Strukturális ok**: a `2026-06-04-recorder-robust-realized-capture.md` task (B) `daily_metrics exits-source fix` (KÉSZ + deploy) szerint a `build_daily_metrics` az `exits` blokkot a cumulative `daily_history` counterekből veszi (NEM a CSV-ből). DE a `trades.details` blokk MÉG MINDIG a `trades_*.csv`-ből veszi, és a 21:40-i MOC fill **NEM kerül be a CSV-be** (a `pt_close.py` 21:40-kor MOC SELL parancsot küld, az IBKR fill 21:59-kor, az `eod_report` 22:11-kor — a CSV-ben csak a 15:30-i TP1 fill-ek szerepelnek).

**Hatás**:
- A `pt_eod.log Trades: 0` Day 16-on (a 22:11 EOD render a `trades.details` szám-számot mutatja, és csak a 15:30 TP1 fill-eket tartalmazza)
- Az `excess_return` és más másodlagos display-mezők a Day 16-on hiányosak (best/worst null)
- A Telegram-i EOD render a Day 16-i AMH +$112,96 trade-et NEM mutatja a `Trades:` listában, csak a `P&L today` aggregátumban

**P&L tracking szempontjából NEM kritikus** (a `pnl.gross/net/commission` mind helyes, a `exits.moc: 1` rögzítve), de **display-konzisztencia szempontjából probléma**.

---

## Scope

### Fix #1 (P1) — `slippage_per_ticker::filled` az IBKR-i fill-árat tükrözze

**Implementáció**:
- `build_daily_metrics` a `execution::slippage_per_ticker` mezőt a connector `get_account_trades(TODAY)`-i tényleges fill-árából vegye, NEM a state-i `planned_entry_price`-ból
- Forrás: az `ib.fills()` (Part A robust-realized-capture A.2 deploy-olta) vagy `get_account_trades(TODAY)` az aznapi BUY fill-eket adja
- A `planned` mező marad a state-i `entry_price`, csak a `filled` és `slippage_pct` változik

**Pseudo-code**:
```python
def build_slippage_per_ticker(date, new_entries, state, ibkr_fills):
    result = {}
    for ticker in new_entries:
        planned = state.get(ticker, {}).get('entry_price')  # state-i submit-time ár
        
        # ÚJ: IBKR fill-árat keresünk
        ibkr_fill = next(
            (f for f in ibkr_fills if f.symbol == ticker and f.side == 'BUY'),
            None
        )
        
        if ibkr_fill:
            filled = ibkr_fill.price  # tényleges fill-ár (broker-authoritative)
            slippage_pct = ((filled - planned) / planned * 100) if planned else 0.0
        else:
            # Fallback: state-alapú (ha az IBKR connector hiányos vagy a TKR-szerű késedelmi esetekben)
            filled = planned
            slippage_pct = 0.0
            logger.warning(f"slippage_per_ticker fallback: {ticker} no IBKR fill found")
        
        result[ticker] = {
            'planned': planned,
            'filled': filled,
            'slippage_pct': round(slippage_pct, 2),
            'qty': state.get(ticker, {}).get('qty')
        }
    return result
```

**Acceptance criteria**:
- A Day 16-i (6/8) `daily_metrics/2026-06-08.json::execution::slippage_per_ticker::TKR::filled` = **$133.71** (NEM $131.83)
- `slippage_pct` = **+1.45** (NEM 0.0)
- A Day 16-i `NSA::filled` = $43.41 (NEM $43.43, valódi IBKR fill -0,05% kedvező)
- Az `avg_fill_slippage_pct` (a `daily_metrics::execution`-ben) a két új entry súlyozott átlaga: (188 × -0.05% + 39 × +1.45%) / 227 ≈ **+0.21% súlyozott átlag**
- Backfill a W21-W24 napokra (a fix-package #5 task `weekly_metrics.py slippage_aggregation` deploy-ja után már a helyes daily_metrics-ből veszi)
- Unit-teszt mock-elve a connector get_account_trades válaszra

**Érintett fájlok**: `scripts/paper_trading/daily_metrics.py`

---

### Fix #2 (P2) — `trades.details` blokk a 21:40 MOC fill-eket is tartalmazza

**Implementáció**:
- `build_daily_metrics` a `trades.details` blokkot **MIND** a `trades_*.csv`-ből, **MIND** a connector `get_account_trades(TODAY)`-ből merge-eli
- A merge prioritás a **connector broker-authoritative**, ha ellentmondás van
- Az `exit_type` mező a `swing_state::exits_today` blokkból és a fill-timestampekből származzon (TP1 = 15:30 körüli fill, TIME_STOP MOC = 21:40-21:59 körüli fill), NEM a CSV `exit_type: "MOC"` mezőből (ami szintén hibás)

**Pseudo-code**:
```python
def build_trades_details(date, csv_trades, ibkr_trades_today, swing_exits_today):
    # Merge CSV + IBKR (broker-authoritative priority)
    all_trades = {}
    for trade in csv_trades:
        key = (trade.ticker, trade.order_id)
        all_trades[key] = trade
    
    for ibkr_trade in ibkr_trades_today:
        if ibkr_trade.side != 'SELL':
            continue  # csak SELL (exit) trade-ek
        key = (ibkr_trade.symbol, ibkr_trade.order_id)
        # IBKR adat felülírja a CSV-t (vagy hozzáadja)
        all_trades[key] = {
            'ticker': ibkr_trade.symbol,
            'entry': get_ibkr_avg_entry(ibkr_trade.symbol),  # broker-authoritative avg
            'exit': ibkr_trade.price,
            'pnl': ibkr_trade.realized_pnl,
            'qty': ibkr_trade.size,
            'commission': ibkr_trade.commission,
            'exit_type': determine_exit_type(ibkr_trade, swing_exits_today),
            'fill_time': ibkr_trade.trade_time,
            'exchange': ibkr_trade.exchange,
        }
    
    return list(all_trades.values())


def determine_exit_type(ibkr_trade, swing_exits_today):
    """A swing_state::exits_today blokkból és fill-timestampekből határozza meg az exit_type-ot."""
    # A swing_exits_today blokk pl. {'TP1': 2, 'TIME_STOP': 2, 'MOC': 1}
    # A fill-timestamp 15:30 körül = TP1, 21:40-21:59 = TIME_STOP MOC
    fill_hour_utc = ibkr_trade.trade_time.hour
    if 13 <= fill_hour_utc <= 14:  # 15:30-16:00 CEST = 13:30-14:00 UTC
        return 'TP1'
    elif 19 <= fill_hour_utc <= 20:  # 21:40-22:00 CEST = 19:40-20:00 UTC
        return 'TIME_STOP_MOC'  # vagy 'MOC' a swing_exits_today-ből
    else:
        return 'UNKNOWN'
```

**Acceptance criteria**:
- A Day 16-i `daily_metrics/2026-06-08.json::trades::details` tartalmazza az AMH MOC fill-t:
  ```json
  {
    "ticker": "AMH",
    "entry": 31.92,        ← IBKR avg entry
    "exit": 32.76,         ← IBKR MOC fill
    "pnl": 112.96,         ← broker-authoritative realized
    "qty": 135,
    "commission": 1.12,
    "exit_type": "TIME_STOP_MOC",  ← (vagy egyszerűbben "MOC")
    "fill_time": "2026-06-08T19:59:32Z",
    "exchange": "NYSE"
  }
  ```
- A `trades.best` és `trades.worst` mezők a `details` non-empty esetén kalkulálódnak
- A 22:11 EOD Telegram `Trades: 1` (a 21:40 MOC fill is megjelenik), `P&L today: $+112.96`-tal konzisztensen
- Regresszió a Day 13-16 napokra (Day 13: 3 trade-detail, Day 14: 3 trade-detail, Day 15: 4 trade-detail, Day 16: 1 trade-detail)
- A `exit_type` mező helyesen: Day 15-i AMH+BEN TP1 (NEM "MOC"), Day 16-i AMH MOC (NEM "TP1")

**Érintett fájlok**: `scripts/paper_trading/daily_metrics.py`, esetleg `scripts/paper_trading/lib/trade_csv.py`

---

## Backfill

A P1 #1 fix után a `daily_metrics/*.json` backfill-szükségletek:
- **W21** (5/18-22): nincs új entry-szlippage-merés (mind a 4 fill közeli, a Day 1-9 régi adatok)
- **W22** (5/26-29): WST 6/1 entry — backfill szükséges
- **W23** (6/1-5): MSM, BEN, VNO, FFIV — backfill szükséges
- **W24 D1** (6/8): NSA, TKR — Day 16 daily_metrics közvetlen javítása

**Backfill script**: `scripts/maintenance/backfill_slippage_per_ticker.py --start 2026-05-18 --end 2026-06-08`
- Olvas: state/swing_positions.PRE_BACKFILL_2026-06-09.json (snapshot a backfill ELŐTT, ha kell rollback)
- Connector: `get_account_trades(DAYS_30)` (az összes entry-fill az időszakból)
- Match: ticker + entry_date alapján
- Output: `state/daily_metrics/YYYY-MM-DD.json` in-place módosítás (a `slippage_per_ticker` mező frissítése)
- Idempotens: ismételt futtatás biztonságos (a `backfill_polygon_vix.py`, `backfill_commission.py` mintáját követi)

A P2 #2 fix után a `trades.details` backfill MÉG nincs szükséges (a fix csak a `build_daily_metrics` jövőbeli futásait érinti). De a Day 13-16 napokra **érdemes** lehet `regenerate_daily_metrics.py --start 2026-06-03 --end 2026-06-08` futtatni, hogy a `trades.details` MOC fill-eket is tartalmazza.

---

## Deploy-sorrend (javasolt)

### Hét közben (kedd-szerda 6/9-6/10)

1. **Fix #1 (P1)** — `slippage_per_ticker::filled` IBKR-i fill-árból. Izolált változás a `build_daily_metrics`-ben.
2. **Backfill script** `backfill_slippage_per_ticker.py` futtatása.
3. **Fix #2 (P2)** — `trades.details` MOC integration. Függés Fix #1-től (mindkét fix a `build_daily_metrics`-ben).

### Verifikáció (Day 18 vagy Day 19 esti EOD után)

- **Day 17-i (6/9, kedd) daily_metrics validáció**:
  - `slippage_per_ticker` a Day 17-i új entry-k (várhatóan 1-2) IBKR fill-árát tartalmazza
  - `trades.details` a VNO TP1 (15:30) + WST TIME_STOP MOC (21:40) mindkettő tartalmazza
- **22:11 EOD Telegram**: `Trades: 2`, `P&L today: $+67` körüli (várt értékek a Day 16 review §6.1 alapján)

### Sikerkritérium

A Day 17 (kedd 6/9) EOD-on a `daily_metrics/2026-06-09.json` mind a 2 fix-et tükrözi:
- `execution::slippage_per_ticker::*::filled` az IBKR-i fill-árat (NEM a state planned-et)
- `trades::details` a 15:30 TP1 + 21:40 MOC fill-eket egyaránt
- A `pt_eod.log` és Telegram render: `Trades: 2` (NEM 1)

---

## Kapcsolódó task-ok

- **`2026-06-06-data-quality-fix-package.md`** — a P1 #1-#4 fix-ek **mind élesen működnek** Day 16-on (lásd Day 16 review §0). A #5 weekly_metrics.py slippage_aggregation a JELEN task #1 fix UTÁN érdemes deploy-olni (mert a weekly aggregátum a daily_metrics-i `slippage_per_ticker::filled`-ből veszi). A #6 portfolio_return_pct audit **MÉG NEM** deploy-olt (Day 16 `portfolio_return_pct: 0.11` várt ~+0,356% — külön P2 task scope, ezen task-on KÍVÜL).
- **`2026-06-04-recorder-robust-realized-capture.md`** — a Part A robust-realized-capture A.2 ib.fills() hétfői (6/8) live smoke SIKERES (Day 16 AMH MOC +$112,96 broker-authoritative rögzítve). A jelen task #2 fix a `trades.details` MOC integration, ami a robust-realized-capture (B) `daily_metrics exits-source fix` folytatása.
- **Backlog #7 next-day MKT fill kockázat** (a fix-package P3 backlog) — a jelen task #1 fix nélkül a statisztikai elemzés **téves adatokra** támaszkodna (az `slippage_per_ticker` minta-bemeneti adatpontok hibásak lennének). A Day 21+ utáni statisztikai elemzés ELŐTT a #1 fix deploy-ja sürgős.

---

## Strukturális megfigyelés — submit-time vs fill-time késedelem

A TKR Day 16-i 2,5 perces fill-késedelem (15:31:10 submit → 15:33:40 fill, +1,45% kedvezőtlen ár-mozgás) **strukturális ok** lehet:
- **Likviditási oka**: a Timken Co. (TKR) átlagos napi forgalma alacsonyabb mint a magas-likviditású ticker-eké (pl. AMH, BEN, AKAM)
- **NYSE auction-szabályok**: a kis-likviditású NYSE-i ticker-eknél a piaci order-route 1-3 percig is várhat, mielőtt a fill kötődik
- **Megfigyelendő statisztikai mintán** (Day 21+ után): hány ticker-en fordul elő >1 perces submit-fill késedelem, és a slippage-eltérés statisztikai szignifikanciája

**Akció** (a JELEN task scope-ján túl): a `weekly_metrics.py` egy új mezőt érdemes lehet hozzáadni: `avg_submit_to_fill_delay_sec` és `worst_submit_to_fill_delay_sec` (ticker-szerinti aggregátum). Ez a Backlog #7 next-day MKT fill kockázat elemzéshez kapcsolódik (de NEM ugyanaz — a next-day a Day N+1 fill-re vonatkozik, ez a same-day fill-késedelmre).

---

**Vége.**
