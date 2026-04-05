Status: OPEN
Updated: 2026-04-03
Note: TV-SYNC Layer 2 — AVWAP vizualizáció (~6h CC)

# TV-SYNC Layer 2 — AVWAP stratégia vizualizáció TradingView-on

## Cél

A `pt_avwap.py` teljes logikájának vizuális megjelenítése TradingView-on:
Anchored VWAP vonal, az AVWAP state machine átmenetei (IDLE→WATCHING→DIPPED→
CONVERTING→DONE), az entry mozgatás, és a VIX-capped SL újraszámolás.

Ez a Layer 1 (statikus szintek) kiegészítése: a Level 1 megmutatja HOL vannak
a szintek, a Layer 2 megmutatja MIÉRT ott vannak (AVWAP logika vizuálisan).

## Háttér — az AVWAP stratégia lényege

A `pt_avwap.py` (`scripts/paper_trading/pt_avwap.py`) logikája:

1. Pipeline 10:00 CET → `execution_plan.csv` limit entry árakkal
2. `submit_orders.py` 15:35 → LIMIT BUY bracket IBKR-en
3. `pt_avwap.py` percenként fut 15:45-17:00 CET között:
   - Ha 15 perc után a limit nem töltődött → WATCHING
   - Polygon 1-min bars-ból AVWAP = Σ(TP×Vol) / Σ(Vol), market open-től anchored
   - Ha price ≤ AVWAP → DIPPED
   - Ha price > AVWAP (dip után) → MKT konverzió + bracket rebuild
   - Fill price alapján új TP1/TP2/SL (VIX-capped)

Az AVWAP vonalat, a dip pontot, és a konverziót vizualizálni kell.

## Scope

### 1. Pine Script — Anchored VWAP indikátor

Pine Script v5 indikátor ami a market open-től rajzol AVWAP-ot:

```pine
//@version=5
indicator("IFDS AVWAP", overlay=true, max_lines_count=1)

// Anchored VWAP from market open (9:30 ET)
is_new_session = ta.change(time("D")) != 0
var float cum_tp_vol = 0.0
var float cum_vol = 0.0

if is_new_session
    cum_tp_vol := 0.0
    cum_vol := 0.0

tp = (high + low + close) / 3
cum_tp_vol += tp * volume
cum_vol += volume

avwap = cum_vol > 0 ? cum_tp_vol / cum_vol : close

plot(avwap, "AVWAP", color=color.new(color.purple, 20), linewidth=2)

// AVWAP ±0.5% bands (optional visual cue)
plot(avwap * 1.005, "AVWAP +0.5%", color=color.new(color.purple, 70), linewidth=1, style=plot.style_circles)
plot(avwap * 0.995, "AVWAP -0.5%", color=color.new(color.purple, 70), linewidth=1, style=plot.style_circles)
```

**Telepítés:** Layer 3 (MCP) `pine_set_source` + `pine_smart_compile` toolokkal
egyszer injektálni. Utána indikátorként marad a charton.

Alternatíva: kézzel hozzáadni a TradingView-ban (Pine Editor → New Indicator),
ha az MCP nincs még telepítve.

### 2. CDP state machine markerek — `tv_sync.py` bővítés

A Layer 1 `tv_sync.py`-t bővítjük az AVWAP state vizualizációval:

```python
def draw_avwap_state(cdp, ticker: str, state: dict) -> None:
    """Draw AVWAP state machine markers on the chart."""
    
    avwap_state = state.get("avwap_state", "IDLE")
    
    # Eredeti limit entry (execution plan-ból) vs AVWAP entry
    if state.get("avwap_converted"):
        # Szaggatott vonal az eredeti limit árnál (elhalványítva)
        original_limit = get_original_limit_price(ticker)  # execution plan CSV-ből
        if original_limit:
            draw_horizontal_line(cdp, original_limit,
                color="gray", style="dotted", 
                text=f"Orig. Limit ${original_limit:.2f}")
        
        # AVWAP last érték marker
        if state.get("avwap_last"):
            draw_horizontal_line(cdp, state["avwap_last"],
                color="purple", style="dashed",
                text=f"AVWAP ${state['avwap_last']:.4f}")
        
        # Konverzió jelzés: text annotation
        draw_text(cdp, state["entry_price"],
            text=f"MKT Fill ${state['entry_price']:.2f}",
            color="orange", size="small")
    
    elif avwap_state == "WATCHING":
        draw_text(cdp, state.get("avwap_last", state["entry_price"]),
            text="AVWAP WATCHING", color="yellow", size="small")
    
    elif avwap_state == "DIPPED":
        draw_text(cdp, state.get("avwap_last", state["entry_price"]),
            text="AVWAP DIPPED — waiting for cross", color="orange", size="small")
    
    elif avwap_state == "FAILED":
        draw_text(cdp, state["entry_price"],
            text="AVWAP FAILED", color="red", size="small")
    
    # VIX info overlay
    vix_at_avwap = state.get("vix_at_avwap")
    if vix_at_avwap:
        draw_text(cdp, state["stop_loss"],
            text=f"VIX @ AVWAP: {vix_at_avwap:.1f}",
            color="gray", size="small")
```

### 3. Scenario A/B vizualizáció

```python
def draw_scenario_state(cdp, ticker: str, state: dict) -> None:
    """Draw Scenario A/B state on the chart."""
    
    if state.get("tp1_filled"):
        # Scenario A aktív: TP1 filled, Bracket B trailing
        draw_text(cdp, state["tp1_price"],
            text="TP1 FILLED → Bracket B trailing",
            color="green", size="small")
    
    if state.get("scenario_b_activated"):
        if state.get("trail_active") and state.get("trail_scope") == "full":
            # Scenario B: 19:00 profitable, full trail
            draw_text(cdp, state["trail_sl_current"],
                text="Scenario B: Full trail active",
                color="teal", size="small")
        elif not state.get("trail_active"):
            # Scenario B: loss exit happened
            draw_text(cdp, state["entry_price"],
                text="Scenario B: LOSS EXIT",
                color="red", size="small")
```

### 4. Bracket A/B qty vizualizáció (text overlay)

```python
def draw_bracket_info(cdp, ticker: str, state: dict) -> None:
    """Draw bracket sizing info as text overlay."""
    qty_a = state["total_qty"] - state["qty_b"]
    qty_b = state["qty_b"]
    
    # TP1 mellé: qty_a info
    # TP2 mellé: qty_b info  
    # Ez a Layer 1 TP1/TP2 vonalainak text-jét bővíti
    pass  # Layer 1 draw_horizontal_line text paraméterében
```

### 5. `get_original_limit_price()` helper

Az execution plan CSV-ből kiolvassa az eredeti limit árat az összehasonlításhoz:

```python
def get_original_limit_price(ticker: str) -> float | None:
    """Get original limit price from today's execution plan CSV."""
    today = date.today().strftime("%Y%m%d")
    pattern = f"output/execution_plan_run_{today}_*.csv"
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    with open(files[-1]) as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["instrument_id"] == ticker:
                return float(row["limit_price"])
    return None
```

## Integráció Layer 1-gyel

A Layer 2 NEM külön script — a `tv_sync.py`-t bővíti:

```python
def sync_ticker(cdp, ticker: str, state: dict) -> None:
    # Layer 1: statikus szintek
    draw_entry(cdp, ticker, state)
    draw_tp_levels(cdp, ticker, state)
    draw_sl_level(cdp, ticker, state)
    draw_trail_level(cdp, ticker, state)
    
    # Layer 2: AVWAP + state machine
    draw_avwap_state(cdp, ticker, state)
    draw_scenario_state(cdp, ticker, state)
```

## Előfeltétel

- Layer 1 kész (tv_sync.py + CDP client + log integráció)
- Log infrastruktúra modernizáció KÉSZ (`log_setup.py`, `event_logger.py`)
- TradingView Desktop debug módban fut
- Pine Script kézzel vagy MCP-vel hozzáadva a charthoz
- Polygon API kulcs (AVWAP számoláshoz — de a Pine Script saját AVWAP-ot rajzol)

## Logging megjegyzés

A Layer 2 a Layer 1 `tv_sync.py`-t bővíti, így a logolás öröklődik:
- Napi log: `logs/pt_tv_sync_YYYY-MM-DD.log` (via `log_setup.py`)
- Event-ek: `logs/pt_events_YYYY-MM-DD.jsonl` (via `event_logger.py`)
- Layer 2-specifikus event-ek: `tv_sync_avwap_drawn` (avwap_state, original_limit),
  `tv_sync_scenario_drawn` (scenario_a/b state)

## Tesztelés

- `test_tv_layer2.py`:
  - AVWAP converted state → original limit + AVWAP entry + MKT fill markerek
  - AVWAP WATCHING state → yellow marker
  - AVWAP FAILED state → red marker
  - Scenario A (TP1 filled) → green TP1 marker
  - Scenario B (trail full) → teal trail marker
  - Scenario B (loss exit) → red loss marker
  - No AVWAP data → graceful skip
- Manuális: vizuális ellenőrzés TV-n, összehasonlítás Telegram log-gal

## Fájlok

| Fájl | Változás |
|------|---------|
| `scripts/tradingview/tv_sync.py` | BŐVÍTÉS — Layer 2 rajzolási logika |
| `scripts/tradingview/lib/drawings.py` | BŐVÍTÉS — text annotations, state markers |
| `scripts/tradingview/pine/ifds_avwap.pine` | ÚJ — Pine Script indikátor forrás |
| `tests/tradingview/test_tv_layer2.py` | ÚJ |

## Commit

```
feat(tradingview): add AVWAP state visualization and Pine Script indicator

Layer 2: AVWAP state machine markers (WATCHING/DIPPED/CONVERTING/DONE),
original vs AVWAP entry comparison, Scenario A/B visualization,
VIX-capped SL info overlay. Includes Pine Script AVWAP indicator
for TradingView (anchored from market open, with ±0.5% bands).
```
