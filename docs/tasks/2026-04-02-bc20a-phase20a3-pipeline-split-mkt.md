Status: OPEN
Updated: 2026-04-02
Note: BC20A Phase_20A_3 — Pipeline Split + MKT Entry (~3h CC)
Depends: Phase_20A_1 (VWAP) + Phase_20A_2 (PositionTracker)

# BC20A Phase_20A_3 — Pipeline Split + MKT Entry

## Cél

A pipeline-t kettéosztani: Phase 1-3 (22:00 CET, záróárak) és Phase 4-6
(15:45 CET, intraday árak). Az entry-t LMT-ről MKT-re váltani a
garantált fill érdekében.

## Scope

### 1. `runner.py` — `--phases` CLI flag

```python
# cli.py bővítés
@click.option('--phases', type=str, default=None,
              help='Phase range to run (e.g., "1-3" or "4-6")')
def run(phases, ...):
    start, end = parse_phase_range(phases)  # "1-3" → (1, 3)
    run_pipeline(phase_range=(start, end), ...)
```

A `runner.py` `_should_run()` módosítása range-alapúra:

```python
def _should_run(phase_range: tuple[int, int] | None, current: int) -> bool:
    if phase_range is None:
        return True
    return phase_range[0] <= current <= phase_range[1]
```

### 2. Phase 1-3 context persistence

A 22:00-ás futás kimenetét el kell menteni, hogy 15:45-kor a Phase 4-6
tudja használni:

```python
# runner.py — Phase 3 után
if phase_range == (1, 3):
    save_phase13_context(ctx, "state/phase13_ctx.json.gz")

# runner.py — Phase 4 előtt
if phase_range == (4, 6):
    ctx = load_phase13_context("state/phase13_ctx.json.gz")
```

A context tartalmazza: BMI, sector_scores, vetoed_sectors, universe, macro, strategy_mode.

### 3. `scripts/deploy_intraday.sh` — Új cron script

```bash
#!/bin/bash
# 15:45 CET: Phase 4-6 with intraday data + order submission
cd ~/SSH-Services/ifds
source .venv/bin/activate

# Phase 4-6 (uses saved Phase 1-3 context)
python -m ifds run --phases 4-6

# Submit orders (MKT entry)
python scripts/paper_trading/submit_orders.py
```

Crontab:
```
45 15 * * 1-5 cd ~/SSH-Services/ifds && ./scripts/deploy_intraday.sh
```

### 4. `submit_orders.py` — MKT entry + partial bracket

Jelenlegi: LMT BUY + bracket (SL + TP1 + TP2)
Új: MKT BUY + partial bracket (SL full + TP1 50%)

```python
# MKT entry
parent = MarketOrder('BUY', qty)
parent.orderRef = f"IFDS_{sym}_MKT"
parent.transmit = False

# TP1: 50% at entry + 0.75×ATR
tp1_qty = int(qty * 0.50)
tp1 = LimitOrder('SELL', tp1_qty, tp1_price)
tp1.parentId = parent.orderId
tp1.orderRef = f"IFDS_{sym}_TP1"
tp1.ocaGroup = f"IFDS_{sym}_OCA"
tp1.ocaType = 1  # cancel with block

# SL: full qty
sl = StopOrder('SELL', qty, sl_price)
sl.parentId = parent.orderId
sl.orderRef = f"IFDS_{sym}_SL"
sl.ocaGroup = f"IFDS_{sym}_OCA"
sl.ocaType = 1
sl.transmit = True
```

### 5. VWAP guard élesítés

Phase 6 `_calculate_position()`-ban a VWAP guard aktívvá válik:

```python
if vwap_data and ticker in vwap_data:
    check = vwap_entry_check(entry, vwap_data[ticker])
    if check == "REJECT":
        logger.log(...)
        return None  # skip this ticker
    elif check == "REDUCE":
        quantity = int(quantity * 0.50)
```

### 6. PositionTracker integráció

A `submit_orders.py` minden sikeres fill-nél hívja a PositionTracker-t.
A `close_positions.py` a tracker-ből olvassa a nyitott pozíciókat.

## Tesztelés

- `test_runner_phase_range.py`: --phases "1-3", "4-6", None (all)
- `test_context_persistence.py`: save + load round-trip
- `test_submit_mkt.py`: MKT order + partial bracket + OCA
- Meglévő tesztek: all green

## Commit

```
feat(pipeline): split into Phase 1-3 (22:00) and Phase 4-6 (15:45)

Pipeline split: Phase 1-3 runs at market close (daily data),
Phase 4-6 at 15:45 CET (intraday data + VWAP). MKT entry
replaces LMT for guaranteed fills. Partial TP1 bracket (50%)
with OCA group. PositionTracker records fills.
```
