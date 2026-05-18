# Task: Swing Execution + Exit — 15:30 entry, mental stop, daily EOD eval

**Status:** DONE
**Updated:** 2026-05-18
**Note:** Ülés C — 33 új teszt, 1672 → 1705 passing, 0 regression
**Priority:** P0 (Fázis 3 deploy)
**Created:** 2026-05-17
**Owner:** Claude Code
**Estimated effort:** ~3h CC

**Source decision:** [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.1, §3.6, §3.8, §3.12 — Döntés [1, 6, 8, 12]: swing architektúra-karakter, entry idő, time-stop, mental stop + hard SL.

**Depends on:** [`2026-05-17-swing-sizing-phase6.md`](2026-05-17-swing-sizing-phase6.md) — az új sizing output (notional, ATR) kell

---

## 1. A változás karaktere — IBKR bracket → mental stop

A jelenlegi rendszerben a `submit_orders.py` minden pozícióhoz **3 IBKR order-t** ad fel: BUY market + SELL stop + SELL limit (bracket TP/SL). A swing pivot **csak market BUY-t** ad fel, a stop és TP **mental** (a `pt_monitor.py` daily EOD eval-ja számolja).

**Indoklás (Day 63 §3.12):**
- Az IBKR bracket stop a 6 órás intraday-en is csak ~9-12% TP1 hit-rátát produkált — a swing 3-5 napi hold **több időt** ad a flow signalnek érvényesülni, de **több noise-t** is, ami a fix bracket SL-t **prematurally** triggereli
- A mental stop daily EOD szinten értékelődik (zárás után) — a napon belüli noise-ra **nem reagál**, csak egész napi mozgásra
- A 60 napi adat 2 dokumentált "loss-exit + bracket SL duplikált zárás" bug-ja (DTE máj 1, SQM máj 7, -$1500 összesen) **lehetetlen** a mental stop architektúrán

## 2. Komponens-térkép

| Komponens | Régi | Új |
|---|---|---|
| Entry idő | 16:20 CEST (45 min market open után) | **15:30 CEST** (= 09:30 ET, market open) |
| Entry order típus | Bracket (BUY + SL + TP1 limit) | **Csak market BUY** |
| Stop-loss | IBKR stop order (1.5×ATR) | **Mental stop** (2.0×ATR, daily EOD eval) |
| TP1 | IBKR limit order (1.25×ATR, 50%) | **Mental TP1** (1.5×ATR, 50%, MARKET SELL másnap 15:30) |
| TP2 | IBKR limit order (2.0×ATR, 50%) | **Mental TP2** (3.0×ATR, 50%, MARKET SELL másnap 15:30) |
| Time-stop | (nincs explicit) | **5 trading nap** → MOC SELL |
| Hard SL | (nincs) | **-8% weekly cumulative** → MARKET SELL másnap 15:30 |
| Trail mechanika | IBKR trailing stop 1.0×ATR | **Mental trailing** (TP1 után, 1.0×ATR, daily EOD) |
| Exit napon | LOSS_EXIT -2% intraday + bracket SL + MOC | **csak** MARKET SELL 15:30 vagy MOC SELL 21:40 |

## 3. `submit_orders.py` átalakítás

```python
# Régi (bracket):
parent, sl_order, tp1_order = create_bracket_order(ticker, qty, entry, sl, tp1)
ib.placeOrder(contract, parent)
ib.placeOrder(contract, sl_order)
ib.placeOrder(contract, tp1_order)

# Új (market only):
buy_order = MarketOrder(action="BUY", totalQuantity=qty)
trade = ib.placeOrder(contract, buy_order)

# A pozíció state-be mentjük a mental stop / TP szinteket
position_state[ticker] = {
    "entry_price": expected_fill,   # később az actual fill-lel frissítjük
    "entry_date": today_iso,
    "atr": atr,
    "stop_level": expected_fill - 2.0 * atr,
    "tp1_level": expected_fill + 1.5 * atr,
    "tp2_level": expected_fill + 3.0 * atr,
    "tp1_hit": False,
    "trail_sl": None,                # csak TP1 után aktív
    "days_held": 0,
    "qty": qty,
    "qty_remaining": qty,
}
write_state(position_state)
```

A `state/swing_positions.json` az új source-of-truth a pozíció exit-szintekre. Az IBKR oldal csak a **nyitott pozíció** ténye + actual fill ár.

### 3.1. Entry idő — 15:30 CEST

A cron entry:
```
30 15 * * 1-5  cd ~/SSH-Services/ifds && python scripts/paper_trading/submit_orders.py >> logs/cron_submit_$(date +\%Y\%m\%d_\%H\%M).log 2>&1
```

A `check_gateway.py` pre-flight **15:25-kor** (5 perccel az entry előtt) — a Fázis 1 IBKR monitoring task által beállítva.

A Phase 4-6 cron **14:30 CEST** (1 órával az entry előtt) — a scoring és sizing eredménye `execution_plan.csv`-be kerül 14:55 CEST-re.

## 4. `pt_monitor.py` átalakítás — daily EOD eval

A régi `pt_monitor.py` 5 perces frekvencián fut a kereskedési nap alatt (16:00-22:00 CEST). Az új `pt_monitor.py` **napi egyszer** fut, 22:00 CEST-kor (= 16:00 ET = market close).

### 4.1. Daily EOD eval logika

```python
def evaluate_position_eod(position, today_close, today_high, today_low, config):
    """A daily EOD eval — másnap 15:30 exit-flag-ek.

    Visszaadja:
      - "HOLD" (nincs exit)
      - "HARD_SL" (másnap 15:30 MARKET SELL — -8% weekly cumulative)
      - "MENTAL_SL" (másnap 15:30 MARKET SELL — close < entry - 2.0×ATR)
      - "TP1" (másnap 15:30 MARKET SELL 50% — high >= entry + 1.5×ATR)
      - "TP2" (másnap 15:30 MARKET SELL maradék — high >= entry + 3.0×ATR)
      - "TIME_STOP" (today 21:40 MOC SELL — days_held >= 5)
      - "TRAIL_SL" (másnap 15:30 MARKET SELL maradék — close < trail_sl)
    """
    days_held = (today - position.entry_date).days

    # 1. Hard SL: -8% weekly cumulative
    cum_pnl_pct = position.weekly_cumulative_pnl_pct()
    if cum_pnl_pct < -0.08:
        return "HARD_SL"

    # 2. Mental SL: close < entry - 2.0×ATR
    if today_close < position.stop_level:
        return "MENTAL_SL"

    # 3. TP2: high reached entry + 3.0×ATR
    if today_high >= position.tp2_level:
        return "TP2"

    # 4. TP1: high reached entry + 1.5×ATR (csak ha még nem hit)
    if not position.tp1_hit and today_high >= position.tp1_level:
        return "TP1"

    # 5. Trail SL (csak TP1 után aktív)
    if position.tp1_hit:
        new_trail = today_close - 1.0 * position.atr
        if position.trail_sl is None or new_trail > position.trail_sl:
            position.trail_sl = new_trail
        if today_close < position.trail_sl:
            return "TRAIL_SL"

    # 6. Time-stop
    if days_held >= 5:
        return "TIME_STOP"  # today 21:40 MOC, NEM másnap

    return "HOLD"
```

### 4.2. State frissítés

Az EOD eval után az exit-flag-ek a `state/swing_positions.json`-be íródnak:

```json
{
  "AAPL": {
    "entry_price": 173.20,
    "entry_date": "2026-05-18",
    "atr": 2.45,
    "stop_level": 168.30,
    "tp1_level": 176.88,
    "tp2_level": 180.55,
    "tp1_hit": false,
    "trail_sl": null,
    "days_held": 0,
    "qty": 50,
    "qty_remaining": 50,
    "next_action": "HOLD",       // EOD eval kimenete
    "next_action_at": null,        // null = HOLD
    "weekly_pnl_pct": -0.012
  },
  ...
}
```

A `close_positions.py` másnap 15:30 CEST (és time-stop esetén today 21:40 CEST) ezt olvassa, és a `next_action` szerint hajt végre.

## 5. `close_positions.py` átalakítás

### 5.1. 15:30 CEST futás (másnap exit)

```python
def main():
    state = read_state("state/swing_positions.json")
    today_iso = today_str()

    for ticker, pos in state.items():
        if pos["next_action"] in ("HARD_SL", "MENTAL_SL", "TP1", "TP2", "TRAIL_SL"):
            qty_to_sell = compute_sell_qty(pos)  # TP1 → 50%, TP2/SL → 100%
            order = MarketOrder(action="SELL", totalQuantity=qty_to_sell)
            ib.placeOrder(contract(ticker), order)
            log_event("swing_exit_submitted", {
                "ticker": ticker,
                "action": pos["next_action"],
                "qty": qty_to_sell,
                "submitted_at": now_cest_iso(),
            })
            update_state(ticker, action_taken=pos["next_action"])
```

### 5.2. 21:40 CEST futás (time-stop MOC)

```python
def main_time_stop():
    state = read_state("state/swing_positions.json")
    for ticker, pos in state.items():
        if pos["next_action"] == "TIME_STOP":
            qty = pos["qty_remaining"]
            order = MarketOrder(action="SELL", totalQuantity=qty, tif="OPG")  # MOC
            ib.placeOrder(contract(ticker), order)
            # ...
```

A cron entry:
```
40 21 * * 1-5  cd ~/SSH-Services/ifds && python scripts/paper_trading/close_positions.py --mode=time_stop >> logs/cron_close_time_$(date +\%Y\%m\%d).log 2>&1
30 15 * * 1-5  cd ~/SSH-Services/ifds && python scripts/paper_trading/close_positions.py --mode=eod_flags >> logs/cron_close_eod_$(date +\%Y\%m\%d).log 2>&1
```

## 6. Hét napjai (D9 elfogadott)

Az új entry **bármely hétköznapi** napon mehet (hé-pé). A pénteki entry → maximum 5 trading nap → következő hét pénteki time-stop → tehát egy pénteki entry **hét hét** lehet hold-ra (calendar). Ez a swing 3-5 napi hold elv mellett **elfogadott** (a "5 trading nap" hard cap, NEM "5 calendar nap").

A backteszt-validáció (Fázis 4+) érdekes lehet a "csüt-pé entry rövidebb time-stop" alternatívára, de **most NEM** alkalmazzuk.

## 7. Új TUNING paraméterek (`defaults.py`)

```python
# Swing Execution + Exit (2026-05-17, Day 63 §3.1, §3.6, §3.8, §3.12)
"swing_execution_enabled": True,
"swing_entry_time_cest": "15:30",
"swing_eod_eval_time_cest": "22:00",
"swing_close_eod_action_time_cest": "15:30",  # másnap
"swing_close_time_stop_time_cest": "21:40",    # MOC

"swing_tp1_atr_multiple": 1.5,
"swing_tp2_atr_multiple": 3.0,
"swing_tp1_sell_pct": 0.50,                    # 50/50 split
"swing_mental_stop_atr_multiple": 2.0,
"swing_trail_atr_multiple": 1.0,               # TP1 után aktív
"swing_hard_sl_weekly_cumulative_pct": -0.08,  # -8%
"swing_time_stop_trading_days": 5,
"swing_positions_state_file": "state/swing_positions.json",

# IBKR bracket DEAKTIVÁLVA
"ibkr_bracket_enabled": False,                  # Csak market BUY
"loss_exit_intraday_enabled": False,           # Régi -2% intraday LOSS_EXIT KIKAPCSOLVA

# Régi monitor 5-perces frekvencián KIKAPCSOLVA
"pt_monitor_5min_mode": False,                  # Új: napi egyszer EOD
```

## 8. Implementáció lépésekben

1. **TUNING paraméterek** (15 min)
2. **`SwingPosition` dataclass** (15 min) — a state struktúra
3. **`submit_orders.py` átalakítás** (45 min) — bracket → market only, state mentés
4. **`pt_monitor.py` daily EOD eval** (60 min) — a 6 exit-feltétel logika
5. **`close_positions.py` átalakítás** (45 min) — két mode (eod_flags + time_stop)
6. **Cron entry update** (10 min) — 5 perces monitor le, daily 22:00 EOD + 15:30 close-eod + 21:40 close-time
7. **Tesztek** (45 min) — 15-18 unit teszt
8. **Smoke test** (15 min) — mock 3-day swing futás, state evolution
9. **Commit** (5 min)

**Összesen: ~3h.**

## 9. Tesztek (15-18)

```python
def test_submit_market_buy_only_not_bracket():
    """Csak 1 IBKR order (market BUY), NEM 3 (bracket)."""

def test_submit_writes_position_state():
    """state/swing_positions.json frissítve az új ticker exit szintekkel."""

def test_eod_eval_returns_hold_in_normal_range():
    """close ∈ [entry - 2×ATR, entry + 1.5×ATR] → HOLD."""

def test_eod_eval_returns_mental_sl_below_2atr():
    """close < entry - 2×ATR → MENTAL_SL."""

def test_eod_eval_returns_tp1_when_high_reaches_1_5atr():
    """high >= entry + 1.5×ATR → TP1."""

def test_eod_eval_returns_tp2_when_high_reaches_3_0atr():
    """high >= entry + 3.0×ATR → TP2."""

def test_eod_eval_returns_hard_sl_when_weekly_below_minus_8pct():
    """weekly cum P&L < -8% → HARD_SL."""

def test_eod_eval_returns_time_stop_day5():
    """days_held >= 5 → TIME_STOP (NEM másnap)."""

def test_trail_sl_activates_only_after_tp1():
    """trail_sl = None ha NOT tp1_hit, set after TP1 hit."""

def test_trail_sl_ratchets_upward_only():
    """trail_sl monotonically increases, never decreases."""

def test_trail_sl_triggers_exit_when_close_below():
    """close < trail_sl AND tp1_hit → TRAIL_SL."""

def test_close_eod_action_executes_market_sell_at_1530():
    """next_action=MENTAL_SL → másnap 15:30 market SELL submitted."""

def test_close_eod_action_tp1_sells_50pct():
    """TP1 → SELL 50%, qty_remaining = qty // 2."""

def test_close_time_stop_executes_moc_at_2140():
    """next_action=TIME_STOP → 21:40 MOC SELL today."""

def test_5min_monitor_disabled_in_swing_mode():
    """A régi 5-perces pt_monitor NEM fut ha swing_execution_enabled=True."""

def test_loss_exit_intraday_disabled():
    """A -2% intraday LOSS_EXIT NEM trigger-elődik (loss_exit_intraday_enabled=False)."""

def test_friday_entry_5_trading_days_hold():
    """Péntek entry → 5 trading nap (= következő péntek) hold."""
```

## 10. Commit message

```
feat(execution): swing 15:30 entry + mental stop + daily EOD eval

Day 63 outcome §3.1, §3.6, §3.8, §3.12: complete execution rewrite for
swing horizon. The IBKR bracket SL is replaced with mental stop architecture,
evaluated once per day at EOD (22:00 CEST = market close).

- submit_orders.py: market BUY only (no bracket); state written to
  state/swing_positions.json with mental stop/TP levels
- Entry time: 16:20 → 15:30 CEST (= 09:30 ET, market open)
- pt_monitor.py: 5-min loop → daily EOD eval (22:00 CEST)
  - 6 exit conditions: HARD_SL, MENTAL_SL, TP1, TP2, TRAIL_SL, TIME_STOP
- close_positions.py: two modes
  - --mode=eod_flags @ 15:30 next-day (HARD/MENTAL/TP/TRAIL)
  - --mode=time_stop @ 21:40 same-day (TIME_STOP MOC)
- TP structure: 1.25×/2.0× → 1.5×/3.0× ATR, 50/50 split
- Stop multiplier: 1.5× → 2.0× ATR
- Hard SL: NEW — -8% weekly cumulative
- Time-stop: 5 trading days
- LOSS_EXIT (-2% intraday) DISABLED — eliminates the DTE/SQM duplicate-close bug class

Tests: 17 unit + 1 integration (3-day swing lifecycle).

Refs: docs/decisions/2026-05-14-day63-decision-outcome.md §3.1, §3.6, §3.8, §3.12
```

## 11. Kapcsolódó

- [`docs/decisions/2026-05-14-day63-decision-outcome.md`](../decisions/2026-05-14-day63-decision-outcome.md) §3.1, §3.6, §3.8, §3.12
- [`docs/design/swing-pivot-architecture.md`](../design/swing-pivot-architecture.md) §3, §2.4
- [`docs/tasks/2026-05-17-swing-sizing-phase6.md`](2026-05-17-swing-sizing-phase6.md) (függőség)
- [`docs/tasks/2026-05-17-swing-metrics-telegram.md`](2026-05-17-swing-metrics-telegram.md) (downstream — daily metrics új field-jei)
