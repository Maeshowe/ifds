Status: DONE
Updated: 2026-04-03
Note: P0 — a split pipeline nem küld Telegram reportot (phase is None check)

# Fix: Telegram report split — makro snapshot + trading plan

## Probléma

A `runner.py` Telegram küldés feltétele:
```python
if phase is None and not dry_run:
    send_daily_report(...)
```

A `--phases 1-3` és `--phases 4-6` futásoknál `phase` nem None (hanem tuple),
ezért **egyik sem küld Telegram üzenetet**. Az új split pipeline-nal a felhasználó
elveszti a napi reportot teljesen.

## Megoldás

Két külön Telegram üzenetre bontás:

### 1. Makro snapshot (Phase 1-3 után, 22:00)

Tartalom:
- Phase 0: VIX, TNX, 2s10s, rate-sensitive
- Phase 1: BMI, regime, strategy
- Phase 2: universe méret, earnings excluded
- Phase 3: szektor tábla (ETF, momentum, status, trend, BMI, breadth)
- **Cross-Asset Regime: NORMAL/CAUTIOUS/RISK_OFF/CRISIS + votes**
- BMI momentum guard státusz
- Skip Day Shadow Guard státusz

Példa üzenet:
```
[2026-04-07 22:03 Budapest] MACRO SNAPSHOT

VIX=23.87 (elevated)  TNX=4.33%  2s10s=+0.52%
Cross-Asset: NORMAL (0/3 vote)
BMI = 46.8%  Regime = YELLOW  Strategy = LONG

Sectors:
XLRE ^ +3.28% Leader  | XLB ^ +2.69% Leader
XLE  v -3.69% Laggard VETO | XLY v -0.62% Laggard VETO

Universe: 1585 passed | Earnings excluded: 10

Holnap 15:45: Phase 4-6 + MKT entry
```

### 2. Trading plan (Phase 4-6 után, 15:45)

Tartalom:
- Phase 4: analyzed/passed/excluded breakdown
- Phase 5: GEX, MMS eloszlás, crowdedness
- Phase 6: pozíciók tábla (ticker, qty, entry, SL, TP1, risk, MMS, EARN)
- VWAP guard summary (hány REJECT/REDUCE/NORMAL)
- Cross-Asset override hatás (ha nem NORMAL)
- Korrelációs guard / VaR hatás
- Freshness Alpha count

Példa üzenet:
```
[2026-04-07 15:48 Budapest] TRADING PLAN

Analyzed: 1458 | Passed: 407 | Excluded: 1051
VWAP guard: 3 REJECT, 2 REDUCE, 395 NORMAL
Cross-Asset: NORMAL → no override
Corr guard: 1 excluded (cyclical)

Positions: 8 | Risk: $2,592 | Exposure: $61,475
TICKER  QTY    ENTRY     STOP      TP1     RISK$  MMS EARN
SKM     147 $  29.58 $  27.97 $  30.38 $  237  UND 05-11
LIN      15 $ 502.60 $ 487.87 $ 510.00 $  236  UND 05-07
...

MKT orderek beküldve. PositionTracker frissítve.
```

## Implementáció

### 1. `telegram.py` — két új függvény

```python
def send_macro_snapshot(ctx: PipelineContext, config: Config,
                        logger: EventLogger, duration: float) -> bool:
    """Phase 1-3 summary: BMI, sectors, cross-asset regime."""

def send_trading_plan(ctx: PipelineContext, config: Config,
                      logger: EventLogger, duration: float,
                      fmp=None) -> bool:
    """Phase 4-6 summary: positions, VWAP, sizing."""
```

### 2. `runner.py` — feltétel módosítás

```python
# Phase 1-3 futás végén
if isinstance(phase, tuple) and phase == (1, 3) and not dry_run:
    from ifds.output.telegram import send_macro_snapshot
    send_macro_snapshot(ctx, config, logger, duration)

# Phase 4-6 futás végén
if isinstance(phase, tuple) and phase == (4, 6) and not dry_run:
    from ifds.output.telegram import send_trading_plan
    send_trading_plan(ctx, config, logger, duration, fmp=fmp_tg)

# Full pipeline (backward compat)
if phase is None and not dry_run:
    from ifds.output.telegram import send_daily_report
    send_daily_report(ctx, config, logger, duration, fmp=fmp_tg)
```

### 3. Timestamp header frissítés

```python
def _pipeline_timestamp(label: str = "PIPELINE") -> str:
    now = datetime.now(_CET)
    return f"[{now.strftime('%Y-%m-%d %H:%M')} Budapest] {label}"
```

## Tesztelés

- Phase 1-3 futás → `send_macro_snapshot` hívódik, `send_daily_report` nem
- Phase 4-6 futás → `send_trading_plan` hívódik, `send_daily_report` nem
- Full pipeline (phase=None) → `send_daily_report` hívódik (backward compat)
- Macro snapshot tartalmazza: cross-asset regime, BMI, szektor tábla, skip day shadow
- Trading plan tartalmazza: pozíciók tábla, VWAP summary, korrelációs guard hatás
- `pytest` all green

## Commit

```
feat(telegram): split report into macro snapshot (22:00) and trading plan (15:45)

The pipeline split (--phases 1-3 / 4-6) broke Telegram reporting
because send_daily_report only fires on full runs (phase is None).
Add send_macro_snapshot (Phase 1-3: BMI, sectors, cross-asset) and
send_trading_plan (Phase 4-6: positions, VWAP, sizing).
```
